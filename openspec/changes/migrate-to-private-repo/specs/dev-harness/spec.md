# dev-harness

No-hardware development and verification. The e2e harness files carry
verbatim; the demo sample source is rewritten (41% upstream).

## ADDED Requirements

### Requirement: Virtual rider

Without hardware, sessions SHALL be driven by a demo source producing
trainer-shaped signals at 1 Hz through the same handlers as BLE: power
approaches targets over 1–2 s, every sample carries small multiplicative
pedal-stroke wobble, cadence tracks effort (and stops instantly at 0 W),
HR trails power. Effort modes: auto (wandering demo), hold (target
watts), ramp (linear build over a duration), sprint (fast attack, fatigue
decay, then sit up), steerable live via API and the ride surface's panel.

#### Scenario: Hold reads like a trainer
- **WHEN** the rider holds 200 W
- **THEN** emitted power settles near 200 within a few samples and keeps
  wobbling a few percent, never flat-lining

#### Scenario: Sprint envelope
- **WHEN** a sprint is triggered mid-hold
- **THEN** power attacks to the peak in ~1 s, decays with fatigue, and
  returns to the previous hold when the sprint ends

### Requirement: Browser smoke harness

An opt-in e2e suite SHALL launch the real app with the demo source, ride
the flagship map in headless Chromium, and assert: world compiles, canvas
takes over, HUD updates, zero frame errors, and the perf budget
(≤500k triangles, ≤200 draw calls per frame). A checked-in tool
regenerates the screenshot baseline at fixed route distances. (Files
carried from the fork; this requirement pins the contract.)

#### Scenario: Budget regression
- **WHEN** a world change pushes a route over the triangle budget
- **THEN** the smoke test fails naming the measured number
