# Core Ride Plan — One Map, a Good Dashboard, a Good Ride

Status: working plan (2026-07-08). This plan **precedes** the experiments in
[generative-world-plan.md](generative-world-plan.md). Before building an AI
loop that generates worlds, the world it generates into has to be good: a
solid renderer, one genuinely enjoyable map, and a ride experience worth
repeating. Everything here is the foundation the generative layer compiles
into — nothing in this plan is throwaway.

## 1. Where we start

- `/ride3d` (`le_tour/web/static/ride3d.js`, ~1,200 lines, single file) is a
  working prototype, but it renders a **treadmill**: the road ribbon and props
  are rebuilt/recycled every frame from a short window of route samples around
  the rider. There is no persistent world — flat ground plane, decorative cone
  hills, individually recycled prop groups.
- The route model (`le_tour/domain/routes.py`, spec `schema_version: 1`) is
  solid: validated segments with length, grade, turn, width, kind, surface,
  scenery. Two bundled routes exist.
- Physics, trainer control (ERG/SIM), session store, and NP/IF/TSS analytics
  all live in Python and already work. The browser consumes a snapshot stream
  plus a local motion model (`ride_motion.js`).
- The NiceGUI home dashboard (`le_tour/web/app.py`) has history, calendar, and
  activity graphs; the 2D ride view is still the primary ride surface.

## 2. The deliverable

A rider opens le-tour, picks the flagship map from a route card with a preview,
starts a ride, and spends 30–45 minutes on a route that feels like a place —
fields, a village, a forest climb with switchbacks, a ridge, a descent to a
river. Trainer resistance follows the terrain smoothly. The HUD answers every
in-ride question at a glance. Stopping shows a ride summary. 60 FPS throughout.

## 3. Milestones

Each milestone ends in a ridable state. Order matters: M1 unblocks everything.

### M1 — World-fixed renderer (the architectural change)

Replace the per-frame treadmill with world geometry **built once at route
load**. This is the single change that unlocks visual quality, and it is also
what the generative architecture ([architecture.md](architecture.md)) assumes.

- Compile the route spec into a 3D centerline: integrate segment headings and
  grades (as `buildRoutePath` already does) into a polyline, then fit a
  `CatmullRomCurve3` so grade and turn transitions are smooth rather than
  kinked at segment boundaries.
- Build the road ribbon, shoulders, lane dashes, and rails as static
  `BufferGeometry` from the spline (architecture doc §"Procedural Road
  Construction"). The camera/rider moves along the spline by distance; the
  snapshot stream and `RideMotionModel` are unchanged.
- **Loop closure decision:** the runtime wraps distance modulo route length
  (`RideRoute.position_at`), but nothing guarantees the compiled path closes
  geometrically. For a world-fixed map this matters. Recommendation: author
  the flagship map to close (turns sum to ±360°, elevation returns to start)
  and add a closure check to the route compiler with a small corrective blend
  over the final segment. Non-closing routes remain valid but are ridden
  out-and-back or with a fade at the seam.
- Split `ride3d.js` into ES modules (`scene.js`, `roadBuilder.js`, `props.js`,
  `hud.js`, `main.js`). Stay build-free (import map / esm.sh, as today);
  introduce Vite only if/when the generative layer needs a real toolchain.
- Exit criteria: both bundled routes ridable on the new renderer, geometry
  constructed once (only actors and HUD update per frame), 60 FPS.

**Status: done (2026-07-08).** Implementation notes where reality diverged
from the sketch above:

- The centerline is a dense arc-length-indexed polyline (4 m spacing) with
  grade/turn-rate smoothed over 30 m transition windows, not a
  `CatmullRomCurve3` — distance → pose lookups must stay exact for trainer
  sync, and a parametric spline would need arc-length reparameterization for
  no visual gain at this sample density.
- Loop closure (`route_path.js`): residual net turn is removed, and the
  compiler may bend in one extra full turn in either direction — curling
  routes that were never authored as loops into one — before redistributing
  the remaining position/elevation drift along the path. A route authored to
  close picks zero extra turns naturally, so the flagship map (M2) still
  wants a closure check at authoring time.
- Modules are `route_path.js` (path compiler), `world_builder.js` (static
  world, merged vertex-colored meshes), `ride3d.js` (entry: camera, actors,
  HUD). The HUD split waits for M4 when the HUD actually grows.
- Surface and scenery colors are baked per-vertex into the static road,
  shoulder, and ground-corridor ribbons; only sky/fog/distant-terrain swap
  with the rider's current scenery.
- three.js is vendored at `le_tour/web/static/vendor/three.module.js` — a
  local-first app should not need a CDN at runtime to render its ride
  surface.

### M2 — One good map: terrain and scenery

- **Terrain:** seeded-noise heightfield chunks along the route corridor,
  deformed to meet the road with the cubic-falloff blend from the architecture
  doc — replaces the flat plane and cone hills. Only chunks near the corridor
  are generated; distant relief can stay a cheap skyline mesh.
- **Props:** move trees/rocks/buildings to `InstancedMesh` per scenery type,
  placed deterministically (seeded) along the corridor with density varying by
  segment scenery. This replaces the recycled prop groups and is the pattern
  the future DSL placer will drive.
- **Atmosphere:** gradient skydome, per-scenery fog color/density, sun angle,
  and a lighting pass so the five scenery palettes read as different places.
- **The flagship map:** hand-author one ~15–20 km route spec with intent —
  warmup through fields → village → forest climb with switchbacks → ridge →
  descent → river run-in — closing geometrically per M1. This map is the
  quality bar, and later the reference against which generated worlds are
  judged.
- Exit criteria: 60 FPS with full scenery on the flagship map; a set of
  screenshots from fixed route distances checked into `docs/` (these become
  the baseline for the future eval loop).

### M3 — Ride feel

- **Grade smoothing:** constant-grade segments produce resistance steps in SIM
  mode. Ramp the grade sent to the trainer across segment transitions (Python
  side, `le_tour/modes/sim.py` / ride controller) to match the visually
  smoothed spline.
- **Camera:** pitch with grade, subtle lean into turns, mild speed-sensitive
  FOV, damped follow — tuned so it reads as motion, not sway.
- **Motion:** verify snapshot cadence + `RideMotionModel` interpolation give
  smooth 60 FPS motion at real ride speeds; tune `speedResponse`.
- **Pacers:** keep them simple, but move them onto the spline so they hold the
  road through turns and climbs.
- Exit criteria: a real ride on the flagship map with the KICKR CORE —
  resistance transitions feel gradual, no visual pops or camera jumps.

**Status: partially done (2026-07-09).** Done ahead of schedule: physics
speed authority with an inertia integrator (`RiderDynamics`, pulled forward
from the assessment's F1/F2), grade ramping via `RideRoute.smoothed_grade_at`
(same 30 m window as the renderer; feeds both the trainer and the physics),
and pacers riding the compiled path (landed with M1). A virtual trainer
panel on `/ride3d` (live watt slider, `/api/ride/virtual-power`) enables
no-hardware feel testing. Remaining: camera tuning pass and the KICKR
verification ride.

### M4 — In-ride dashboard (HUD)

Keep the metric-card language that exists; make the HUD answer every in-ride
question:

- Add elapsed time and average power / NP (live values from the analytics
  layer) alongside power, speed, cadence, HR, distance.
- Current grade indicator, and segment context: "Forest Climb · 1.2 km to
  Ridge" (all available from `RoutePosition`).
- Route progress: the existing elevation profile strip gains a rider position
  marker and completed-portion fill.
- FTP-zone coloring on the power card when an FTP is configured.
- Verify pause/stop states and reconnect messaging are clean.

### M5 — Pre-ride and post-ride flow

- **Home dashboard route cards:** distance, elevation gain, difficulty (all
  already computed on `RideRoute`), plus a mini elevation sparkline; clicking
  one opens `/ride3d` with the route preselected.
- **Post-ride summary:** on stop, an overlay with duration, distance,
  elevation gain, avg/NP/IF/TSS (session store + analytics already compute
  these), with a link to ride history.
- Make `/ride3d` the primary ride surface from the home dashboard; keep the 2D
  ride view as a fallback until parity is confirmed, then retire it.

### M6 — Hardening and baseline for what comes next

- Playwright smoke test: launch with the fake/demo data source, start a ride
  on the flagship map, assert the canvas renders and HUD values update, and
  capture a deterministic screenshot. This is deliberately the same harness
  Experiment 3 of the generative plan needs.
- Document the performance budget in `docs/development.md`: 60 FPS target,
  draw-call and triangle budgets (architecture doc suggests ≤500k triangles).
- Update README's `/ride3d` section to reflect its new primary status.

## 4. Sequencing

M1 → M2 → M3 can only go in that order (each builds on the last). M4 and M5
are independent of M2/M3 and can interleave once M1 lands. M6 closes the
phase. Rough shape: M1 and M2 are the bulk of the work; M3–M5 are smaller,
tuning-and-UI milestones.

## 5. How this feeds the generative plan

- Experiment 1 (LLM → route spec) plugs into the **same** compiler and
  renderer this plan improves — `route_from_spec()` stays the seam.
- The flagship map defines "good," giving the future LLM judge a calibrated
  reference; M2's fixed-position screenshots seed its baseline.
- M6's Playwright harness is the scaffold Experiment 3's eval loop runs on.
- M2's instanced, seeded placer is the deterministic placement engine the
  schema-v2 DSL (Experiment 2) will parameterize.

## 6. Non-goals for this phase

No LLM calls, no `schema_version: 2`, no multiplayer, no structured-workout 3D
integration, no Windows support, no packaged installers. Wind modeling and the
Cardano solver stay deferred as noted in the generative plan's open questions.
