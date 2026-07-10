# ride-history

Rewrite of persistence and post-ride analytics (`store/`, `analytics/`,
`session_service`). The schema may be redesigned; behavior below is the
contract.

## ADDED Requirements

### Requirement: Local-first persistence

Sessions and their samples SHALL persist locally (no cloud dependency)
under the user's config directory. A saved session carries mode, start/end
times, duration, trainer name, rider profile at ride time, route id/title
for SIM, totals (distance), aggregates (avg/max power, avg cadence, avg
speed, avg/max HR), and training metrics. Storage failures surface to the
caller; a failed save never crashes the ride.

#### Scenario: Storage failure on stop
- **WHEN** persistence raises during stop
- **THEN** the session still ends cleanly and the stop result carries the
  error message

### Requirement: Training metrics

The analytics layer SHALL compute normalized power (30 s rolling-average
fourth-power method), intensity factor (NP/FTP), and training stress
score from a session's power samples and the rider's FTP.

#### Scenario: Known vectors
- **WHEN** metrics run on fixture power series with hand-computed values
- **THEN** NP/IF/TSS match within rounding

### Requirement: History access and export

The app SHALL list sessions (recency-ordered, filterable by range), show a
session's detail with samples, delete sessions, and export per-session and
summary CSV files to a local exports directory.

#### Scenario: Export a ride
- **WHEN** the user exports a saved session
- **THEN** a readable CSV lands in the exports directory with one row per
  sample
