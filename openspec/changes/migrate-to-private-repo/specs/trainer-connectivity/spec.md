# trainer-connectivity

Rewrite of the BLE layer. Implemented from the Bluetooth SIG FTMS and
Heart Rate Service specifications (public protocol documents), not from
the old client code.

## ADDED Requirements

### Requirement: Device discovery and connection

The app SHALL scan for BLE fitness machines (FTMS service) and heart-rate
straps (HRS service), list them with name and signal strength, and
connect/disconnect on request. Connection state and device names are
visible in the snapshot contract. Scan and connect failures surface as
messages, never as silent no-ops.

#### Scenario: Trainer appears and connects
- **WHEN** the user scans and selects an FTMS trainer
- **THEN** the app subscribes to its data stream and the snapshot reports
  the trainer connected by name

### Requirement: Sample ingestion

Connected devices SHALL stream samples into the domain through the same
handler interface the demo source uses: bike samples (timestamp, power W,
cadence rpm, wheel speed m/s) and HR samples (timestamp, bpm). Malformed
notifications are dropped with a log, never crash the stream.

#### Scenario: Hardware and demo source are interchangeable
- **WHEN** a session runs with hardware vs the demo source
- **THEN** the domain code paths beyond the source are identical

### Requirement: Trainer control

In ERG mode the app SHALL request control and set target power (clamped to
a trainer-safe range, default 100–400 W); in SIM mode it SHALL send the
simulation grade. Control writes are asynchronous and rate-limited by the
0.1-grade rounding rule from ride-physics.

#### Scenario: ERG target change mid-ride
- **WHEN** the user adjusts the ERG target during an active ERG session
- **THEN** the new clamped target is written to the trainer and reflected
  in the snapshot
