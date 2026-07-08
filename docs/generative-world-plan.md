# Generative World Modeling — Repo Map & Experiment Plan

Status: working plan (2026-07-08). Companion to [architecture.md](architecture.md),
which describes the target architecture (LLM → compact DSL → procedural compiler →
instanced Three.js scene). This document records where the repo actually stands
against that vision and the ordered experiments to close the gap.

## 1. Where the repo stands

The ride engine foundation is largely done. The generative layer has not started.

| Layer | State |
|---|---|
| Hardware | BLE FTMS trainer + HR via Python/Bleak (`le_tour/devices`). ERG and SIM resistance control work; tested on Wahoo KICKR CORE. |
| Physics | Power→speed solver in `le_tour/modes/sim.py` (Newton's method, bisection fallback). Equivalent to the architecture doc's Cardano approach, minus wind modeling. |
| Route model | `le_tour/domain/routes.py` — versioned, validated JSON route spec (`schema_version: 1`). Segments carry length, grade, turn, road width, plus constrained enums: `kind` (warmup/rolling/climb/descent/recovery), `surface` (asphalt/gravel/dirt), `scenery` (fields/forest/village/ridge/river). |
| 3D | `/ride3d` prototype (`le_tour/web/static/ride3d.js`): procedural road ribbon rebuilt per frame from route samples, scenery palettes, per-scenery roadside prop variants, pacer riders, cockpit, HUD, elevation profile. |
| Data | Local session store (JSONL + SQLite), CSV export, NP/IF/TSS analytics, ride history, activity calendar. |

## 2. Gap to the vision

Measured against `architecture.md`:

1. **No generative front-end.** There is no LLM call anywhere in the codebase.
   The prompt → world path — the core thesis — has not started.
2. **No scene DSL.** The route spec is a real proto-DSL for the *road profile*,
   but the world is a single coarse `scenery` enum per segment. Nothing like the
   doc's asset-template index arrays, Placer-Provider pattern, or landmark
   vocabulary exists yet.
3. **Rendering depth.** No `InstancedMesh` (props are individually recycled
   groups), no real terrain (flat plane + decorative cones), no chunked terrain
   deformation, CSG tunnels, or texture atlases.

**Key structural insight:** the route spec JSON is already the compile target
the architecture doc describes. `route_from_spec()` is a deterministic
validator/compiler, and the renderer already consumes its output. The seam for
the LLM exists — it is simply unplugged.

## 3. Method: loop engineering (the Karpathy method)

The direction is not "add an LLM feature" but to engineer the improvement loop
itself, per Andrej Karpathy's autonomous-experiment pattern (an agent ran ~700
experiments over two days unattended). The generalizable mechanism is three
primitives:

1. **An editable asset** — the single thing the agent may modify.
2. **A scalar metric** — the single number that says whether a change improved things.
3. **A time-boxed cycle** — so experiments are directly comparable.

The insight: manual hand-tuning is the bottleneck. "Is this generated world
good?" is exactly the judgment we would otherwise hand-tune forever, so we build
the loop that answers it automatically and let it run.

References: [The New Stack on Karpathy's experiment loop](https://thenewstack.io/karpathy-autonomous-experiment-loop/),
[Fortune — "The Karpathy Loop"](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/),
"Loop Engineering: The Karpathy Method" (@0xCodila on X).

## 4. Experiments (smallest first)

### Experiment 1 — Plug the LLM into the existing seam (~1–2 days)

Build `le_tour/gen/`: prompt → LLM → route-spec JSON (schema v1, unchanged) →
existing `route_from_spec()` validation → write into the bundled routes → ride
it at `/ride3d`.

- CLI shape: `uv run python -m le_tour.gen "misty forest climb, 12km, brutal switchbacks"`
- Zero renderer changes; prompt-to-rideable-world end to end immediately.
- Free metrics: validator pass rate; constraint fidelity (requested
  distance / elevation / difficulty vs. `RideRoute`'s computed properties).

**Success criterion:** ≥90% of generated specs pass validation on first try;
generated routes match requested distance within ±10% and requested difficulty
class exactly.

### Experiment 2 — Grow the DSL, keep the compiler deterministic (~1 week)

Extend the spec to `schema_version: 2` with world vocabulary from the
architecture doc: prop density, landmark templates, palette parameters, biome
transitions — still compact enums/indices, never coordinates. The renderer
grows a deterministic placer for the new vocabulary (this is where
`InstancedMesh` becomes worth adopting).

- The LLM's job stays "pick templates and sequence them."
- The compiler's job stays "make it physically coherent."

**Success criterion:** two prompts differing only in mood/biome produce visibly
distinct worlds; frame rate holds at 60 FPS with the richer scenes.

### Experiment 3 — Close the loop (the differentiator)

Wire the three primitives into an autonomous eval harness:

- **Editable asset:** the generator prompt + DSL schema + compiler heuristics.
- **Scalar metric:** composite score per generated world — validator pass rate
  + constraint fidelity + an LLM-judge score on headless screenshots
  (Playwright can screenshot `/ride3d` deterministically), rubric'd for
  variety, coherence, and "would you ride this."
- **Time-boxed cycle:** generate a batch of N worlds → compile → render →
  score → the agent proposes one change to the asset → repeat overnight.

**Success criterion:** the composite score improves monotonically over ≥10
unattended cycles, and a human spot-check agrees with the judge's ranking.

The harness — not the cycling app itself — is the durable applied-AI artifact:
a deterministic compiler + eval layer over the LLM, applied to generative 3D.

## 5. Open questions

- Judge calibration: how well does an LLM screenshot-judge correlate with human
  "would ride this" judgment? (Experiment 3 should measure this explicitly.)
- DSL expressiveness ceiling: at what point does the segment-sequence model
  need a spline/graph representation instead? (Defer until Experiment 2 hurts.)
- Wind + Cardano solver from the architecture doc: not a current gap that
  matters; revisit only if trainer feel demands it.
