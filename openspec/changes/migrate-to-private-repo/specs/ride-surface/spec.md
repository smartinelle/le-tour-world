# ride-surface

The 3D cockpit. The world renderer (`world_builder.js`, `route_path.js`)
is carried verbatim; this capability rewrites the page, HTTP API, client,
motion model, and the upstream-origin parts of the scene entry (HUD
wiring, actors, controls) — redesigning the markup and API shapes as we go.

## ADDED Requirements

### Requirement: Ride API

The surface SHALL be driven by an HTTP+SSE API: list routes, get route,
start (mode + route), stop (returns a post-ride summary), toggle-pause,
ERG target and SIM grade adjustment, virtual-rider control, health
(pid/start time/session state), and a snapshot event stream. Launch
parameters in the URL preselect a route and may auto-start a mode — but
never over an already-active session.

#### Scenario: Refresh mid-ride is safe
- **WHEN** the page reloads with auto-start parameters while a session is
  active
- **THEN** the session continues untouched

### Requirement: Smooth world motion

The browser SHALL integrate its own render distance from snapshot speeds
(converging gently on the server's distance, snapping only across resets),
ease speed changes so 1 Hz snapshot steps glide, and coast to a stop when
the stream goes stale (~3 s). The camera follows the compiled path with a
damped look target, leans with local path curvature scaled by speed, and
eases FOV mildly with speed. The camera SHALL NOT carry any artificial
rhythmic motion (no bob): vertical movement comes from terrain only.

#### Scenario: Dead server
- **WHEN** snapshots stop arriving
- **THEN** the world coasts to a stop instead of riding forever

#### Scenario: Steady state is steady
- **WHEN** riding constant power on smooth road
- **THEN** short-period vertical camera oscillation stays under 1 cm

### Requirement: In-ride HUD

The HUD SHALL show power (colored by Coggan FTP zone when FTP is set),
speed, cadence, HR, distance, elapsed time, average power, NP, and current
grade; segment context (current + next with distance); and a route
elevation strip with rider marker and completed-portion fill. Cards blank
when idle and clear on stop.

#### Scenario: Zone coloring
- **WHEN** power crosses a zone boundary relative to FTP
- **THEN** the power card's zone color updates accordingly

### Requirement: Resilient frame loop

One bad frame SHALL never end rendering (loop scheduled before the frame
body; errors counted and exposed on a debug object alongside distance,
speed, camera pose, FOV, draw calls, and triangle count). Control failures
surface in the status line. A CSS fallback covers the canvas until WebGL
provably renders.

#### Scenario: Frame exception
- **WHEN** a frame throws
- **THEN** the next frame still runs and the error count increments

### Requirement: Post-ride summary

Stopping SHALL present duration, distance, lap-aware elevation gain, avg
power, NP, IF, TSS, saved/unsaved state, and a link to history — from the
persisted session's analytics when saved, else from live snapshot stats.

#### Scenario: Short unsaved ride
- **WHEN** a ride too short to persist is stopped
- **THEN** the summary still shows duration/distance/avg from live stats
  and says the ride was not saved
