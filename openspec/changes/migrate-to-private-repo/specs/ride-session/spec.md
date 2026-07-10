# ride-session

Rewrite of session lifecycle and live metrics (old `ride_controller`,
`ride_runtime`, `state`). The domain is UI-neutral: every surface consumes
one snapshot contract.

## ADDED Requirements

### Requirement: Session lifecycle

The domain SHALL support start(mode, route), pause, resume, stop, and
discard. Modes are FREE (no trainer control), ERG (hold target watts), and
SIM (grade-based resistance). Starting while a session is active stops the
previous session first. Pause freezes elapsed time, metrics, and
recording; resume restarts the rider from a standstill. Stop persists the
session when samples were recorded; discard never persists.

#### Scenario: Pause freezes the ride
- **WHEN** a session is paused and trainer samples keep arriving
- **THEN** elapsed time, distance, and displayed metrics do not change
  until resume

#### Scenario: Stop with no samples
- **WHEN** a session is stopped before any sample arrived
- **THEN** no history entry is created and the stop result says so

### Requirement: Speed authority

With a route attached, speed and distance SHALL come from ride-physics
(measured power + route grade + rider profile); the trainer's own wheel
speed is retained as a diagnostic field with a source marker. Without a
route, trainer-reported speed is used directly.

#### Scenario: Route attached
- **WHEN** a bike sample arrives during a routed session
- **THEN** the snapshot's speed comes from the physics engine and both
  `speed_source: "physics"` and the raw trainer speed are exposed

### Requirement: Live in-ride analytics

The session SHALL maintain running average power and normalized power
(fourth-root of the mean fourth power of a 30-sample rolling average),
incrementally, and expose them plus the configured FTP on every snapshot.
Stats reset on session start and ignore samples without power.

#### Scenario: Steady effort
- **WHEN** the rider holds a constant wattage
- **THEN** average power equals it and NP converges onto it

### Requirement: One snapshot contract

A single serializable snapshot SHALL carry session state, mode, elapsed
time, power/cadence/HR, speed (+source, +trainer speed), distance, ERG
target, SIM grade, avg/NP/FTP, and device connection status. All
transports (HTTP, SSE stream, UI bindings) serve this same contract.

#### Scenario: Surfaces agree
- **WHEN** the HTTP endpoint and the SSE stream are read at the same time
- **THEN** they present the same fields with the same meanings
