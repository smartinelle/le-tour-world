# Frontend MVP Screen Spec

This spec captures the locked MVP frontend decisions for le-tour. The goal is a
focused local-first cycling app UI: start a ride, read the cockpit, stop safely,
review history, export data, and configure rider/hardware settings.

## Global Navigation

- Main nav: `Ride`, `History`, `Settings`.
- `Devices` is not a top-level nav item. Hardware pairing lives under Settings.
- `3D` is not a top-level MVP nav item. The prototype route can remain available
  but should not compete with the primary ride flow.
- The app shell uses compact navigation, a small `LT` mark, and `le-tour`.
- Header status uses `Demo Mode` or `Live Trainer`; there is no separate Source
  tile on the launchpad.

## Ride Launchpad

### Goal

Let the rider understand hardware status, choose a mode, configure only the
inputs required for that mode, and start riding.

### Layout

- Header with `Ride`, `History`, `Settings`.
- Compact title: `Ride Console`.
- Two status tiles:
  - `Trainer`
  - `Heart Rate`
- Segmented mode selector:
  - `Free Ride`
  - `ERG Mode`
  - `SIM Mode`
- Mode setup uses variable density:
  - Free Ride: compact.
  - ERG Mode: medium.
  - SIM Mode: rich/full.
- Actions:
  - Primary: `Start Ride`.
  - Secondary: `Pair Devices`.
- Recent rides table below the setup area, populated only by real saved sessions.

### Mode Setup

Free Ride:

- Title: `Free Ride`.
- Copy: `Ride without trainer resistance control.`
- Small facts only: `Control Off`, `Recording On`, `Mode Free`.
- No fake zero metrics.
- No internal sample wording.

ERG Mode:

- Title: `ERG Target Power`.
- Large target value.
- Stepper controls for target power.
- Copy: `Trainer holds this target when the ride starts.`
- Optional small fact: `Adjustable during ride`.
- No workouts, intervals, plans, or filler stats until those exist.

SIM Mode:

- Requires an existing route profile.
- Shows route selector, route title, route description, route difficulty.
- Shows route stats:
  - Distance
  - Gain
  - Max grade
  - Segments
- Shows a compact route/elevation profile.

## Active Ride Cockpit

### Goal

Let the rider read core metrics from riding distance, pause/resume, and stop the
ride safely.

### Layout

- No normal app nav inside the active cockpit.
- No `Exit`, `Exit Setup`, back, or discard action in the MVP cockpit.
- Top bar:
  - Mode/status cluster.
  - `Active` or `Paused`.
  - Elapsed time.
- Main metric panel:
  - Huge power value.
  - Unit `Watts`.
  - Mode-specific subline where useful.
- Secondary metric rail:
  - Cadence
  - Heart Rate
  - Speed
  - Distance
  - Mode-specific fifth metric
- Bottom controls:
  - `Pause` / `Resume`
  - `Stop Ride`

### Mode Setup

Free Ride:

- Sparse cockpit.
- Power, secondary metrics, pause, stop.
- No filler panel.

ERG Mode:

- Shows target near power and in compact controls.
- Controls: `-10 W`, current target, `+10 W`.
- No workout or interval UI.

SIM Mode:

- Shows current segment, next segment, route progress, and grade.
- Grade buttons are compact. If route-driven grade and manual adjustment conflict,
  call the manual control a grade override in future UI.

### Stop Behavior

- `Stop Ride` is the only normal way to leave an active ride.
- It ends the ride and opens the stop summary.
- `Pause` only pauses or resumes the ride.

## Stop Summary

### Goal

Confirm the result of stopping a ride and give clear next actions.

### States

- `Ride saved`
- `No ride data saved`
- `Save failed`

### Content

- Show only the actual state, not all possible states.
- Summary metrics should use useful training labels:
  - Duration
  - Distance
  - Avg Power
  - Max Power
  - Avg Heart Rate
  - Max Heart Rate
  - Normalized Power
  - Intensity
  - Training Stress
  - FTP
- Actions:
  - `Start New Ride`
  - `View History`
  - `Export CSV` only when saved

## History

### Goal

Let the rider review completed rides and export session data.

### Layout

- Table-first.
- Session detail stays a separate page for MVP.
- No inline preview required.

### Table Columns

- Date
- Mode
- Duration
- Distance
- Avg Power
- Training Stress
- Actions

### Actions

- `View`
- `CSV`

### Empty State

- `No rides yet`
- `Your completed rides will appear here.`

## Settings

### Goal

Configure rider profile, ride defaults, hardware devices, and app preferences
without cluttering the ride flow.

### Sections

- `Profile`
- `Ride Defaults`
- `Devices`
- `App`

### Profile

- Name
- Weight
- FTP
- Max Heart Rate
- Age

### Ride Defaults

- Default ERG target
- Default SIM route
- Manual SIM grade/default grade
- Speed source
- Units

### Devices

- Trainer and heart-rate hardware live here.
- Launchpad `Pair Devices` opens Settings > Devices.
- Trainer absence is not an error because demo mode is supported.
- Heart rate is optional.
- Device states:
  - Not paired
  - Scanning
  - Connecting
  - Connected
  - Failed

### App

- Auto-connect trainer
- Auto-connect heart-rate monitor
- Reconnect timeout

### Implementation Preference

- Start with one `/settings` route using internal tabs.
- `/devices` may remain as a legacy redirect to Settings > Devices.
