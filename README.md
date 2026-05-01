# TerminalRide (Le-tour)

Web-first indoor cycling application for connecting to Wahoo KICKR and other
BLE FTMS trainers.

The current application runs as a local Python process with a browser UI. Python
owns trainer communication, ride state, persistence, and domain logic; the
browser is the presentation layer. This keeps the core usable for future
interfaces such as a Three.js ride world, mobile app, or restored terminal UI.

## Current Status

- **Active UI:** NiceGUI web app in `terminalride/web`, started by `run_web.py`.
- **Core domain:** UI-neutral ride/controller/device services in
  `terminalride/domain`.
- **Trainer connection:** Python/Bleak FTMS client remains the primary local
  hardware path.
- **Native terminal UI:** the old Rich/TUI entry points and `terminalride/ui`
  package have been removed during the web migration. The README no longer
  documents `python -m terminalride` as a working app entry point.
- **Browser BLE:** `terminalride/web/static/ble.js` is an experimental
  Web Bluetooth client. It is not the default path and browser support is
  limited compared with the Python/Bleak local app.

## Features

- **BLE FTMS Support:** connect to Wahoo KICKR and compatible trainers.
- **Heart Rate Monitors:** connect to standard BLE HR straps such as Wahoo
  TICKR, Garmin HRM, and Polar H10/H9/OH1.
- **Training Modes:**
  - Free Ride: natural cycling without resistance control.
  - ERG Mode: target-power training.
  - SIM Mode: grade-based simulation and virtual speed/distance.
- **Web UI:** browser-based ride surface, device management, settings, and
  optional Supabase authentication.
- **Data Persistence:** session and sample storage through the repository layer.
- **CSV Export:** export training data for external analysis.
- **Real-time Metrics:** power, cadence, speed, distance, heart rate, elapsed
  time, ERG target, and SIM grade.
- **Training Analytics:** Normalized Power (NP), Intensity Factor (IF), and
  Training Stress Score (TSS).

## Installation

### Prerequisites

- Python 3.11+
- macOS/Linux with Bluetooth available
- BLE FTMS trainer for real hardware rides
- Chrome/Edge only if experimenting with Web Bluetooth directly

### Setup

```bash
git clone <repository-url>
cd le-tour

uv sync
```

`uv sync` provisions Python 3.11 (per `.python-version`), creates `.venv`,
installs runtime + dev dependencies from `uv.lock`, and editable-installs the
project. Use `uv run <cmd>` to run anything inside the project environment.

## Running The Web App

```bash
uv run python run_web.py
```

Then open:

```text
http://127.0.0.1:8080
```

The local web app will:

1. Render the browser UI.
2. Scan for compatible trainers when requested or during auto-connect flows.
3. Connect to the trainer through the Python FTMS client.
4. Start Free Ride, ERG, or SIM sessions from the web UI.
5. Record metrics and session samples through the domain/store layers.

## Architecture

### Core Boundaries

- `terminalride/domain`: ride lifecycle, device services, event models, and
  UI-neutral state.
- `terminalride/devices`: BLE FTMS and Heart Rate clients plus parsers.
- `terminalride/modes`: ERG and SIM mode logic.
- `terminalride/store`: repository, models, CSV export, and storage adapters.
- `terminalride/web`: NiceGUI UI, auth, pages, and browser-facing assets.

The frontend must consume domain state through stable contracts instead of
reaching into BLE clients directly. This is especially important for the planned
Three.js ride world: the 3D layer should consume a ride snapshot/stream, not
trainer internals.

### Current Migration Notes

The project used to be terminal-first with a Rich-based UI. The current branch
has moved toward a browser-first app and the native terminal surface is not
available in the working tree. The core rule still stands: keep business logic
in the domain layer so a terminal UI can be restored later without rewriting
trainer control, persistence, or analytics.

## Training Modes

### Free Ride

Records live trainer and heart-rate data without controlling resistance.

### ERG Mode

Tracks a target power range and sends target power commands to the trainer when
the trainer is connected and control is available.

### SIM Mode

Uses grade-based simulation parameters and the local SIM physics model to
calculate virtual speed and distance.

The SIM physics solver is in `terminalride/modes/sim.py` and uses:

```text
P = 0.5 * rho * CdA * v^3 + m * g * Crr * v + m * g * sin(theta) * v + P0
```

## Data Management

- Session metadata and samples flow through `terminalride/store`.
- JSONL remains the durable append-friendly source of truth.
- SQLite supports faster local history/statistics queries.
- CSV export is layered on top of repository data.

By default, local data is written below the TerminalRide config directory:

```text
~/.config/terminalride/data
```

## Configuration

Edit:

```text
~/.config/terminalride/config.json
```

Example:

```json
{
  "name": "Rider",
  "age": 30,
  "gender": "male",
  "mass_kg": 75.0,
  "ftp_w": 250,
  "max_hr_bpm": 185,
  "default_erg_power_w": 150,
  "default_sim_grade_pct": 0.0,
  "speed_source": "trainer"
}
```

## Development

See `docs/adr/` for accepted architecture decisions before structural changes.

### Tests

```bash
uv run pytest -q
```

### Code Quality

```bash
uv run black .
uv run ruff check .
uv run mypy .
```

The mypy configuration is strict. Some existing modules may still need cleanup
before a full-project mypy run is clean; keep new domain code typed and
UI-neutral.

## Testing With Real Hardware

1. Power on the FTMS trainer.
2. Ensure Bluetooth is enabled.
3. Run `uv run python run_web.py`.
4. Open `http://127.0.0.1:8080`.
5. Connect the trainer from the Devices flow or use the auto-connect path.
6. Start a ride mode and verify live metrics update.

## Technical Details

### BLE FTMS Protocol

- Service UUID: `00001826-0000-1000-8000-00805f9b34fb`
- Indoor Bike Data characteristic: live power, cadence, and speed.
- Fitness Machine Control Point: ERG target power and SIM parameters.
- Fitness Machine Status: optional status notifications.

### BLE Heart Rate Profile

- Service UUID: `0000180D-0000-1000-8000-00805f9b34fb`
- Measurement characteristic: heart rate and optional RR intervals.
- Whoop is not supported because it does not expose standard BLE HR broadcast
  data for this use case.

## Troubleshooting

### BLE Connection Issues

1. Ensure the trainer is powered on and awake.
2. Close other apps connected to the trainer.
3. Confirm the OS has granted Bluetooth permission.
4. On Linux, confirm the BLE adapter and permissions are configured correctly.

### Data Issues

1. Check `~/.config/terminalride/data/sessions.jsonl`.
2. Check `~/.config/terminalride/data/samples.jsonl`.
3. If SQLite query results are stale or corrupt, remove the SQLite cache and
   rebuild/import from JSONL once a maintenance tool exists.
