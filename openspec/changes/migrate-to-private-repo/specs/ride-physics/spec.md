# ride-physics

Rewrite of the power→speed model. Implemented from the physics (standard
cycling power balance), not from the old solver's code.

## ADDED Requirements

### Requirement: App-computed speed with inertia

The engine SHALL compute rider speed by integrating the power balance
dv/dt = (P_wheel/v − F_gravity − F_rolling − F_aero) / m, using the rider
profile (mass kg, CdA m², Crr) and the route grade at the rider's current
distance. Wheel power applies a fixed drivetrain loss. Integration uses
substeps of at most 0.1 s; sample gaps are clamped to 3 s; speed is capped
at 30 m/s and never negative.

#### Scenario: Steady flat power settles at terminal speed
- **WHEN** a rider holds constant power on 0% grade
- **THEN** speed converges within 2% of the analytic steady-state speed
  for that power and profile, and stays there

#### Scenario: Grade step decays, not jumps
- **WHEN** the grade steps upward mid-ride at constant power
- **THEN** speed decreases smoothly over multiple seconds (inertia), with
  no instantaneous drop between consecutive samples

#### Scenario: Coasting to standstill
- **WHEN** power goes to 0 W on flat ground
- **THEN** speed decays monotonically to 0 and distance stops increasing

### Requirement: Smoothed route grade

Grade fed to both the physics and the trainer SHALL be smoothed over a
~30 m window across segment boundaries (matching the renderer's visual
smoothing), and the value sent to trainer hardware SHALL be clamped to the
trainer-safe range and rounded to 0.1 to avoid BLE write chatter.

#### Scenario: Segment boundary ramps
- **WHEN** the rider crosses a boundary between segments of different
  authored grade
- **THEN** the effective grade transitions progressively over the window
  rather than stepping
