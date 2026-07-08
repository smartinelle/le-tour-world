# Technical Assessment — Bottlenecks, Benchmarks, and Budgets

Status: working assessment (2026-07-08). Companion to
[core-ride-plan.md](core-ride-plan.md) (the build order) and
[architecture.md](architecture.md) (the target architecture). Where those
documents say *what to build*, this one says *where it can fail, how we will
measure it, and what it costs*. Numbers marked **[measured]** were taken on
this repo at the date above; everything else is an estimate with its
reasoning shown.

The two challenges, in the product's own terms:

1. **Ride experience** — speed calculation, visual smoothness, trainer feel.
   The best platforms win users here; this must hit a defined precision bar.
2. **Generative fidelity per token** — the world builder must clear a quality
   threshold at minimal compute, with a known-size template library.

---

## Challenge 1 — Ride experience

### 1.1 The pipeline (where quality is created and lost)

```
KICKR (BLE FTMS notify ~1 Hz)
   │ power / cadence / wheel speed
   ▼
Python: bleak → RideController._on_bike_sample        [per sample]
   ├─ distance += speed × dt        (rectangle rule at sample cadence)
   ├─ grade_at(distance) → if changed → set_simulation(grade) → trainer
   └─ snapshot state
   ▼
SSE snapshot stream (4 Hz, interval_s=0.25)           [measured]
   ▼
Browser: RideMotionModel
   ├─ speed smoothing: τ ≈ 133 ms (speedResponse=7.5)
   └─ renderDistanceM: integrate speed, converge on snapshot distance
   ▼
60 fps render loop: poseAt(renderDistance) → camera   [76 ns/lookup, measured]
```

Two loops matter: the **display loop** (pedal → number/motion on screen) and
the **resistance loop** (terrain → trainer force → legs). The resistance loop
is the one riders describe as "feel," and it has a physical floor: the KICKR's
electromechanical response to a resistance command is on the order of 1–2
seconds and cannot be engineered away — only anticipated.

### 1.2 Findings, ranked by product impact

**F1 — There is no virtual-rider physics in the ride loop. (largest gap)**
`SimPhysics` (the Newton power→speed solver in `le_tour/modes/sim.py`) is
implemented and tested but **wired to nothing** — it is used only by an
example script. In-ride speed is whatever the trainer reports as wheel speed
(`RideController._on_bike_sample`). Consequences:

- Virtual speed depends on the trainer's internal flywheel emulation, not on
  our world. Rider mass, CdA, and drafting can never matter.
- Behavior varies by trainer model — directly against the launch-support
  strategy of validating specific hardware.
- Descent speed is whatever the trainer coasts to; the world's -8% grade
  produces no 60 km/h reward.

**Decision needed:** make app-computed speed authoritative (trainer supplies
power; we integrate speed/distance from the physics model), which is how the
major platforms work. The trainer-reported speed stays as a diagnostic.

**F2 — The solver is steady-state only; there is no inertia model.**
`solve_speed(power, grade)` returns equilibrium speed. At 200 W, crossing
from 0% to 5.6% is an instantaneous 33.8 → 14.7 km/h drop **[measured]** —
a 19 km/h step in one tick. Riding feel requires integrating acceleration:

```
dv/dt = (η·P/v − F_gravity(grade) − F_rolling − F_aero(v)) / m
```

A 10–20 Hz explicit Euler integration in the controller is sufficient (the
architecture doc's Cardano treatment solves the same steady-state equation
and has the same gap — inertia is what makes both feel right). Solver cost is
3.8 µs/solve **[measured]**, so rate is a non-issue. `MAX_SPEED = 20 m/s`
(72 km/h) also needs revisiting once descents are real.

**F3 — Resistance is sent as steps.** Grade goes to the trainer as
piecewise-constant per segment, written when the value changes at sample
cadence. Crossing into Ridge Steps is a single 0 → 5.6% command. M3's grade
ramping (interpolate the profile the same way the renderer's spline does)
fixes this; the trainer's mechanical lag currently masks part of it, which
means it will become *more* noticeable as trainers get faster.

**F4 — Display-loop latency is budget-able and mostly inherited.** Current
worst-case pedal→screen chain: BLE notify interval (~1000 ms typical FTMS) +
snapshot interval (≤250 ms) + SSE (~ms) + motion smoothing (τ ≈ 133 ms) ≈
**1.2–1.5 s worst case**. That is within the range riders tolerate on
incumbent platforms (power displays are typically 1–3 s smoothed), but we've
never measured our own chain end-to-end — it must be instrumented, not
assumed. The two cheap levers, if measurement says we need them: subscribe
cadence on the FTMS characteristic (some trainers notify at 2–4 Hz) and raise
snapshot rate.

**F5 — Rendering is now structurally sound; the risk is regression, not
architecture.** After M1: world built once, poseAt lookup 76 ns, route
compile 35 ms at 2 km / 55 ms at 20 km **[measured]** — one-time, at load.
Remaining render risks: per-frame allocation creep (GC hitches), prop count
growth in M2 without instancing, and low-end GPUs. 60 fps could not be
verified in the dev container (software WebGL); it needs a reference-hardware
baseline.

### 1.3 The benchmark: a ride-quality scorecard

Five benches, each cheap enough to run on every change. The "99% precision"
target belongs to B1/B5 (correctness benches); B2–B4 get explicit numeric
targets instead, because latency and smoothness are threshold phenomena, not
precision phenomena.

| # | Bench | Metric | Target | How |
|---|---|---|---|---|
| B1 | Physics correctness | Speed vs published power models (Martin et al. / gribble.org-style calculators) at a grid of (P, grade, mass) | ≤ 1% deviation at steady state; strict monotonicity; solver convergence < 10 µs | Extend `test_sim_physics.py` with golden values (250 W flat → 36.8 km/h with default config **[measured]** — already in the plausible band) |
| B2 | Feel / transitions | Max grade step per trainer write; speed settle profile over a segment boundary | No single grade write > 0.5%; settle to ±5% of new equilibrium in 3–8 s (inertia-governed, mass-dependent) | Simulated ride harness: drive controller with scripted power, record every `set_simulation` call and speed trace |
| B3 | Display latency | Timestamp ladder: t(BLE notify) → t(snapshot publish) → t(browser receive) → t(next frame) | p95 pedal→HUD < 1.5 s now; < 800 ms after cadence work | Add timestamps at each hop (samples already carry `ts`); log ladder in dev mode; measure with demo source and with the KICKR |
| B4 | Frame pacing | rAF delta histogram over a 5-min ride; route-switch stall | p99 frame < 20 ms, dropped frames < 1%, zero > 100 ms stalls, route switch < 200 ms | `?debug` overlay + Playwright run on **reference hardware** (the macOS machine that drives the trainer), not the CI container |
| B5 | Positional integrity | \|renderDistance − serverDistance\| during ride; pose gap at lap seam | p95 < 2 m; seam gap = 0 (currently 0.000 m **[measured]**) | Browser-side counter + the existing `path_check` numeric harness |

**What must be near-perfect vs what must merely be good:** distance/speed
correctness and resistance continuity (B1/B2/B5) are the trust layer — errors
there read as "this game is lying about my workout" and are product-fatal.
Latency (B3) and frame pacing (B4) have thresholds below which improvement is
imperceptible; hitting the targets is enough. Pacers, gates, scenery variety
are pure upside — no precision bar.

**Sequencing note:** F1+F2 (wire the physics with inertia) should be pulled
forward — the plan placed grade-ramping in M3, but speed authority changes
what "distance" means everywhere (history, analytics, route position), so it
should land before the flagship map makes feel judgments (M2/M3 boundary).

---

## Challenge 2 — Generative fidelity per token

### 2.1 The fidelity benchmark: a four-layer pyramid

Cheap deterministic gates first; the expensive judge only sees worlds that
survive them. Every layer produces a scalar, so the composite score the
Karpathy-style loop optimizes is well-defined from day one.

| Layer | Question | Metric | Cost | Exists? |
|---|---|---|---|---|
| L0 validity | Does the spec compile? | `route_from_spec()` pass rate | ~0 (deterministic) | ✅ today |
| L1 constraint fidelity | Did it obey the prompt's numbers? | requested vs computed distance (±10%), difficulty class match, elevation gain | ~0 | ✅ `RideRoute` computes all of it |
| L2 physical coherence | Is it a sane place to ride? | compiler lints: closure drift & extra-turns (now emitted by `route_path.js` **[measured]**: demo route 333 m / −1 turn), grade/turn-radius sanity, corridor self-intersection, scenery-adjacency rules | ~0 | ⚠️ partial — closure exists, lints need writing |
| L3 perceptual quality | Would you ride it? | LLM judge on deterministic screenshots, rubric: variety / coherence / landmark memorability / desire-to-ride, scored pairwise against anchors | $ (see 2.3) | ❌ needs M6's Playwright harness |

**L3 calibration is the scientific risk of the whole program.** Before the
judge's score is allowed to steer anything, it must be validated: collect a
frozen anchor set (~20 worlds spanning awful→great, including the M2 flagship
map as the "great" anchor), have humans do pairwise preferences, and require
judge–human pairwise agreement ≥ 75% (chance = 50%). Re-check periodically —
an autonomous loop optimizing against a judge will find its blind spots
(Goodhart). The frozen human-anchored set is the guard rail; a human
spot-check per overnight run is the alarm.

Two judge design choices that cut cost and variance: judge **pairwise**
(world A vs B screenshots) rather than absolute scores — LLMs rank far more
reliably than they rate — and judge against the **prompt** ("misty forest
climb") as a separate fidelity axis from generic quality.

### 2.2 Token economics — measured, then extrapolated

The compact-DSL thesis holds better than the architecture doc's own estimate:

- Current route spec (schema v1): **~225 output tokens** compact-serialized
  **[measured]** for a 5-segment route. The doc's 300–1,500 token claim is
  the right order; a richer schema v2 (10–20 segments + world vocabulary)
  projects to **400–900 output tokens**.
- Generation input: system prompt + DSL grammar + few-shot examples ≈ 2–4K
  tokens, almost all of it cacheable (static prefix → ~0.1× on cache reads).

Cost per generated world, at current API pricing (Haiku 4.5 $1/$5 per MTok,
Sonnet 4.6 $3/$15, Opus 4.8 $5/$25; halve everything via the Batches API for
the offline loop):

| Step | Tokens (in / out) | Haiku 4.5 | Sonnet 4.6 | Opus 4.8 |
|---|---|---|---|---|
| Generate spec (cached prefix) | ~3K / ~700 | ~$0.005 | ~$0.014 | ~$0.023 |
| Judge, 4 screenshots (~2K image tokens each) + rubric | ~10K / ~300 | ~$0.012 | ~$0.035 | ~$0.058 |

So an overnight eval cycle of **30 iterations × 20 worlds** ≈ 600 generations
+ ~600 judge calls runs **≈ $10 (Haiku) to $50 (Opus), half that batched.**
And the user-facing path (one prompt → one world, no judge) is **well under a
cent** per world at any tier.

**Implication that reframes the goal:** token cost is not the bottleneck —
*wall-clock and judge validity are*. Rendering + screenshotting a world
(~5–15 s headless) dominates cycle time, not the LLM. "Best benchmark score
with as few tokens as possible" therefore operationalizes as:

1. **Fidelity-per-dollar curve, not minimum dollars.** Run the same prompt
   set through Haiku/Sonnet/Opus; because the deterministic compiler
   guarantees L0 and the schema is enum-constrained (use structured outputs
   with `strict` schemas — validity becomes free), the hypothesis is that
   small models saturate L0–L2 and the tiers only separate at L3. Measure
   where the curve bends; that model is the default.
2. **Escalation ladder instead of a big default model:** generate with the
   small model; on an L1/L2 gate failure, retry once with feedback; only
   escalate tiers on repeated failure. Expected effect: ≥ 90% of worlds never
   touch the expensive model.
3. **Judge budget discipline:** gates L0–L2 filter free; batch the L3 calls;
   judge pairwise against a small anchor set rather than all-pairs.

### 2.3 Template library sizing — how much must be pre-built

The DSL's whole premise is that the LLM picks from **pre-authored, style-
consistent templates** and never emits geometry. So library size is the
authoring budget question. Estimate, reasoning shown:

- **Per biome** (fields / forest / village / ridge / river today, alpine /
  desert / coast plausible later): 3–5 vegetation variants, 2–3 rocks/ground
  clutter, 3–6 buildings/structures where applicable, 1–3 **landmarks**
  (the memorability carriers — bridge, chapel, summit cairn, water tower),
  plus biome palette + fog/sky parameters. → **12–20 templates/biome.**
- **Shared road furniture** (signs, gates, rails, dashes, chevrons, km
  markers, start/finish arch): **10–15 templates**, already half-built.
- With ~40% cross-biome reuse, launch scale (5 biomes) lands at
  **~60–100 distinct authored templates**; a mature 8-biome world at
  **~150–200**. Each is cheap at our art style — the current props are
  30–80 lines of primitive composition **[measured in `world_builder.js`]** —
  so this is days-to-weeks of authoring, not months.
- **Perceived variety multiplies for free** via parametric variation (seeded
  scale/color/rotation jitter, already the pattern in `buildProps`) — a
  5–10× multiplier on perceived distinct objects, i.e. an effective
  vocabulary of ~500–1,000 entities from ~100 authored ones.
- **Landmarks are the highest-leverage authoring hour.** Rider memory of a
  route is anchored on 3–5 moments; one good landmark per biome does more
  for L3 scores than ten tree variants. (Direct analogy: incumbent platforms
  ship a handful of set-piece landmarks per world and reuse mundane props
  heavily.)

**Don't trust the estimate — measure the knee.** The library size question is
itself an ablation benchmark once L3 exists: generate the same routes with a
template vocabulary restricted to N ∈ {10, 25, 50, 100}, plot variety/quality
score vs N, and stop authoring where the curve flattens. That turns an
open-ended art budget into a measured stopping rule.

### 2.4 Non-LLM compute

Client compile is already negligible (55 ms for 20 km **[measured]**); the
loop's compute is headless rendering (parallelize Playwright workers; ~4
workers ≈ 1–2 s/world amortized) and — later, if M2 terrain gets heavier —
chunked generation off the main thread. One caveat for eval reproducibility:
screenshots in CI render via SwiftShader (software GL), which differs subtly
from real GPUs. Pin one render environment for the anchor set so judge inputs
stay comparable over time.

### 2.5 Risks specific to the loop

1. **Judge miscalibration / Goodhart** — mitigations in 2.1 (frozen anchors,
   pairwise, periodic human agreement checks).
2. **DSL expressiveness ceiling** — the segment-sequence model can't express
   forks, out-and-backs sharing a road, or set-piece placement ("tunnel at
   the summit"). Defer until L3 scores plateau *because of* layout monotony —
   that's the signal to move to a graph/spline DSL, not before.
3. **Schema drift vs cache** — the generation prompt embeds the DSL grammar;
   every schema change invalidates the cached prefix and the few-shot set.
   Version the grammar and regenerate few-shots mechanically from the schema.

---

## 3. What to instrument next (feeds M2–M6)

1. **Decide speed authority** (F1) and add the inertia integrator (F2) —
   physics decision before the flagship map tunes feel. Small, isolated:
   controller + `sim.py`, golden tests extend `test_sim_physics.py`.
2. **Timestamp ladder** through sample → snapshot → browser (B3) — a day of
   plumbing, permanent observability.
3. **`?debug` frame-pacing overlay** (B4) and a reference-hardware baseline
   run.
4. **L2 lints** in the route compiler (closure drift is already computed —
   surface it as a score instead of a console line).
5. **Anchor-set scaffolding** — deterministic screenshot positions become the
   eval baseline; M2's flagship-map screenshot set doubles as the first
   "great" anchor.

Items 1–3 are Challenge-1 work that belongs inside M2/M3; items 4–5 are
Challenge-2 work that M6 was already scheduled to seed.
