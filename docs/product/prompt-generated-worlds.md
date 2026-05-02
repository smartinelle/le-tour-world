# Prompt-Generated Routes And Worlds

## Product Thesis

TerminalRide can make indoor cycling feel personal by letting riders create a
route or world from a short prompt, then ride it immediately. The important
product promise is not "AI art in the background"; it is:

> Tell the app what kind of ride you want, get a coherent route with matching
> terrain, visuals, and training intent, then start pedaling without setup.

Examples:

- "A 35 minute alpine climb with switchbacks, 6 to 9 percent gradients, and a
  hard final kilometer."
- "A relaxed forest recovery ride, mostly flat, soft morning light, 25 minutes."
- "A cyberpunk time trial through a rainy city, short ramps, no long climbs."
- "A gravel route through Icelandic lava fields with three punchy climbs."

The feature should be designed as a domain capability first. The current web UI
and future 3D browser surface should consume generated route/world data through
stable contracts, not through renderer-specific state.

## What We Are Actually Generating

We should avoid treating generation as "make a Three.js scene" directly. The
canonical output should be a structured route/world specification:

1. `RouteSpec`: distance, elevation profile, grade segments, events, and ride
   intent.
2. `WorldSpec`: biome, time of day, weather, lighting, landmarks, roadside
   assets, surface type, and atmosphere.
3. `TrainingSpec`: target duration, intensity profile, recovery/hard sections,
   optional ERG/SIM behavior.
4. `RenderManifest`: renderer-friendly assets, seed values, object placements,
   and level-of-detail hints.

The 3D renderer should be one consumer of this spec. API/mobile clients,
headless tooling, and offline preview workflows should be able to consume the
same route data as structured text, elevation profiles, upcoming grade cards,
and training prompts.

## Core User Flow

1. Rider opens the route generator.
2. Rider enters a prompt, optionally with quick controls:
   - duration
   - difficulty
   - route type
   - visual world style
   - climbing amount
   - realism vs fantasy
3. App returns a preview within a few seconds:
   - route title
   - distance and estimated duration
   - elevation gain
   - grade profile
   - short world description
   - difficulty estimate
   - safety note if the route is unusually hard
4. Rider can:
   - ride now
   - regenerate
   - edit prompt
   - adjust difficulty
   - save route
5. During the ride:
   - SIM mode follows the route grade.
   - The 3D world renders from the generated manifest.
   - HUD shows upcoming gradient, section name, and distance to next event.
6. After the ride:
   - Session is linked to the generated route version.
   - Rider can reride, share, or remix the route.

## Frontend Product Shape

### Generator Surface

The generator should feel like a route builder, not a chatbot. The prompt is the
main input, but controls keep the output bounded and rideable.

Primary controls:

- Prompt text area.
- Duration: 15, 30, 45, 60, custom.
- Difficulty: recovery, endurance, tempo, threshold, brutal.
- Terrain: flat, rolling, climb, mixed, intervals.
- World: realistic, stylized, fantasy, sci-fi, minimal.
- Regenerate button.
- Ride now button.

Preview content:

- Route name and one-sentence description.
- Route stats: duration, distance, elevation gain, max grade, average grade.
- Elevation/grade chart.
- Section list: warmup, climb, descent, interval, landmark, cooldown.
- Visual preview thumbnail or low-fidelity 3D flythrough.
- Warnings for long high-gradient sections or mismatch with rider FTP.

### In-Ride 3D UX

The route/world should affect the ride in ways the rider can feel:

- Road pitch follows generated grade in SIM mode.
- Scenery density and landmarks create progress markers.
- Section transitions are visible before they affect resistance.
- Descents and recoveries are visually distinct from climbs.
- The route should not visually lie about effort. A brutal ramp should look like
  a brutal ramp.

The HUD should stay operationally useful:

- current power, cadence, speed, HR
- current grade
- upcoming grade
- current route section
- remaining section distance/time
- route progress

### Editing And Remixing

The first version can keep editing simple:

- "Make it easier."
- "Add more climbing."
- "Make the world darker."
- "Shorten to 30 minutes."
- "Keep the route shape, change the world to desert."

Internally this should produce a new route/world version rather than mutating
the prior one in place. That gives repeatability and makes saved rides stable.

## Backend Product Shape

### Generation Pipeline

The generation process should be asynchronous, even if early prototypes return
quickly:

1. Accept prompt and constraints.
2. Normalize user intent into a generation request.
3. Generate a structured `RouteSpec` and `WorldSpec`.
4. Validate constraints and safety limits.
5. Compile route into simulation-ready grade samples.
6. Compile world into renderer-ready manifest.
7. Persist route, world, manifest, prompt, seed, model metadata, and version.
8. Return preview data to frontend.

Suggested service boundary:

```text
terminalride/domain/generated_routes/
  models.py          # RouteSpec, WorldSpec, TrainingSpec, RenderManifest
  generator.py       # prompt + constraints -> candidate specs
  validator.py       # safety and schema validation
  compiler.py        # specs -> grade samples + render manifest
  repository.py      # storage facade or extension of store layer
```

The generator may call an LLM or a local procedural generator, but domain code
should depend on a protocol, not on a specific provider.

### Canonical Data Model

The key idea is that a route is data, not UI code.

```json
{
  "id": "route_...",
  "version": 1,
  "prompt": "A 35 minute alpine climb...",
  "seed": 183742,
  "training": {
    "target_duration_s": 2100,
    "difficulty": "tempo",
    "intensity_notes": ["progressive climb", "hard final kilometer"]
  },
  "route": {
    "distance_m": 14500,
    "elevation_gain_m": 640,
    "segments": [
      {
        "start_m": 0,
        "end_m": 1800,
        "grade_pct": 1.5,
        "kind": "warmup"
      },
      {
        "start_m": 1800,
        "end_m": 5200,
        "grade_pct": 6.0,
        "kind": "climb"
      }
    ]
  },
  "world": {
    "biome": "alpine",
    "time_of_day": "morning",
    "weather": "clear",
    "style": "realistic",
    "landmarks": [
      {
        "distance_m": 4800,
        "kind": "switchback_viewpoint",
        "label": "Valley overlook"
      }
    ]
  }
}
```

This object should be validated before it reaches ride simulation or rendering.
For runtime, the route should compile into dense samples such as:

```json
{
  "route_id": "route_...",
  "sample_spacing_m": 10,
  "samples": [
    {"distance_m": 0, "grade_pct": 1.5, "section_id": "warmup_1"},
    {"distance_m": 10, "grade_pct": 1.5, "section_id": "warmup_1"}
  ]
}
```

### Runtime Integration

Generated routes should extend SIM mode rather than bypassing it.

Current SIM accepts a grade. Generated route runtime should provide:

- current grade at rider distance
- upcoming grade window
- current section metadata
- route progress
- completion state

The ride controller should not know whether the grade came from a static slider,
a saved real-world route, or a prompt-generated route. It should consume a
`RouteProfile` abstraction.

Potential domain protocol:

```python
class RouteProfile(Protocol):
    def grade_at(self, distance_m: float) -> float: ...
    def upcoming(self, distance_m: float, horizon_m: float) -> list[RoutePoint]: ...
    def section_at(self, distance_m: float) -> RouteSection: ...
```

### Renderer Integration

The 3D renderer should consume:

- live ride snapshots from the existing snapshot stream
- route profile preview data
- world render manifest

It should not own route truth. It can interpolate visuals locally, but the
domain layer owns progress, grade, and section state.

This keeps the browser replaceable and makes generated routes usable for:

- current NiceGUI/web UI
- future richer Three.js world
- API/mobile clients
- headless/offline route consumers
- offline route preview tooling
- tests and scripted demos

## Constraints And Safety

Generated rides need hard bounds:

- maximum grade
- maximum sustained grade duration
- minimum warmup/cooldown for hard workouts
- maximum route duration
- no impossible elevation profile
- no negative distance or overlapping segments
- no renderer-only concepts required for ride simulation

Safety should be rider-aware later:

- FTP
- mass
- recent ride history
- selected difficulty
- HR response
- explicit "race/hard" confirmation

Early MVP can use conservative defaults:

- grade range: -8 percent to 12 percent
- sustained grade above 8 percent requires explicit hard difficulty
- generated ride duration capped at 90 minutes
- every ride over tempo includes warmup and cooldown sections

## MVP Definition

The first useful version does not need full AI-generated 3D assets.

MVP:

- Prompt plus controls create a validated generated route.
- Route has stable segments, grade profile, title, and world metadata.
- Preview shows profile and stats.
- Ride now starts SIM mode using the generated grade profile.
- 3D prototype changes road pitch, scenery palette, and landmark labels from
  `WorldSpec`.
- Saved session records the generated route id and version.
- Route can be reridden exactly.

Not MVP:

- photorealistic generated meshes
- multiplayer worlds
- sharing marketplace
- full route editor
- arbitrary user-uploaded assets
- cloud-only generation dependency

## Important Questions To Answer

### Product

- Is the main job "make training more fun" or "make route creation faster"?
- Should users start from prompt first, controls first, or templates first?
- How much control does a serious rider expect before trusting the route?
- What makes a generated route feel good after ten rides instead of only once?
- Should generated routes be private by default?
- Can users share prompts, generated specs, or both?
- Should a route be remixable while a ride is active?
- What is the minimum preview needed before a rider trusts the workout?
- Should we optimize for realistic cycling routes or expressive fantasy worlds?
- How do we explain that visuals and resistance are linked without cluttering
  the UI?

### Training And Ride Feel

- How should prompt difficulty map to FTP, grade, and duration?
- Should generated routes target power zones, HR zones, RPE, or only terrain?
- What should happen when rider speed makes the route longer or shorter than the
  requested duration?
- Should distance be derived from requested duration and expected speed, or
  should duration be estimated after route generation?
- How aggressive can grade changes be before they feel bad on a trainer?
- Do descents reduce resistance, become recovery segments, or both?
- Should ERG workouts be able to use generated worlds without SIM grade control?

### Frontend

- Is generation part of the main ride screen or a separate route library flow?
- Should preview be 2D-first, 3D-first, or both?
- How do users compare multiple generated candidates?
- What states are needed for pending, failed, unsafe, saved, and stale routes?
- How do we keep prompt input fast on small screens?
- How do we show generation provenance without making the UI feel technical?
- What should the rider see if world assets are still compiling but the route is
  ready to ride?

### Backend And Architecture

- What is the canonical schema for generated route/world specs?
- Which parts must be deterministic from `seed`?
- Do we store prompts, generated specs, compiled manifests, or all three?
- Should generation be local-only, cloud-backed, or provider-pluggable?
- How do we version generated route schemas?
- How do we migrate saved routes when the compiler changes?
- Should generated assets be cached globally, per user, or per route version?
- What is the failure mode if generation succeeds but manifest compilation
  fails?
- How do we keep generated route logic independent from NiceGUI and Three.js?
- How do tests prove that a generated route cannot violate SIM constraints?

### Data And Persistence

- How are generated route ids linked to sessions and samples?
- Can a route be deleted while historical sessions still reference it?
- What metadata is needed for reproducibility: prompt, seed, model, compiler
  version, schema version?
- Are generated routes synced to Supabase or stored locally first?
- How large can render manifests become before they need asset storage?
- Do route previews belong in the database or should they be regenerated?

## Suggested Next Decisions

1. Define `RouteSpec`, `WorldSpec`, and `CompiledRouteProfile` as pure domain
   models.
2. Decide whether route generation is local-procedural first or LLM-assisted
   first.
3. Add a route profile abstraction to SIM mode so grade can come from distance
   rather than only a manual slider.
4. Build a non-AI procedural generator behind the same protocol for tests and
   demos.
5. Add the prompt UI only after the domain contract can produce, validate, save,
   and replay generated routes.
