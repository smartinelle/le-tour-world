# le-tour

Web-first indoor cycling application for connecting to Wahoo KICKR and other
BLE FTMS trainers.

The current application runs as a local Python process with a browser UI. Python
owns trainer communication, ride state, persistence, and domain logic; the
browser is the presentation layer. This keeps the core usable for future
interfaces such as a richer Three.js ride world, mobile app, or API clients.

## Product Direction

This README is private project context for me and the agents working in this
repository. It should stay candid and useful for implementation decisions, not
polished as a public marketing page.

### Background and Goal

This project started solely as a terminal-first indoor cycling app just for
myself. The ambition has expanded: build a real application with real users,
free or paid, while keeping the codebase small enough to move quickly.

The broad product idea is a Zwift-like indoor cycling app, but with
improvements: only the actually useful features, and no multiplayer/social
features for now. The differentiator is not a social network; it is ride quality,
usable training flows, and generated riding environments.

Like Zwift, we want 3D worlds and routes. Ours are built with Three.js and should
remain data-driven instead of hard-wired into the web UI. The future standout
feature is that a rider can "vibe-code" / generate new worlds and routes on the
spot through a prompt, or possibly by importing a fitting file. Earlier versions
may simply allow importing worlds from other sources if those worlds follow our
standards.

Current rough business assumptions are deliberately exploratory: something like
a 5 Euros/month base subscription, with generated worlds/routes as a higher tier
or add-on, maybe around 10 Euros/month if users want to generate them on our
platform with a certain amount of credits. This is a vision and working
assumption, not a fixed product commitment.

### First Launch Strategy

The first launchable version should target early users rather than a broad
consumer audience. The likely first users are tech-comfortable indoor cyclists,
makers, and training nerds who can tolerate some local-app rough edges if the
core ride loop is useful, reliable, and interesting.

This phase is the bridge between a personal tool and a larger product. It should
validate whether people want the core solo training experience before the project
invests heavily in packaging polish, hosted accounts, subscriptions, broad
integrations, or generated 3D worlds.

The first MVP should be a polished non-3D ride cockpit:

- Installable/runnable without requiring users to understand the codebase.
- Reliable trainer and heart-rate connection flows.
- Usable Free Ride, ERG, and SIM modes.
- Persisted rider settings and defaults.
- Repository-backed ride history.
- CSV export for external analysis.
- Simple SIM route choices with clear route metadata.
- Honest documentation about what works, what is experimental, and what is not
  built yet.

The 3D route/world work should continue in parallel as a data-contract and
runtime-surface effort, but it should not block the first useful launch. Prompt
generated worlds and routes remain a future differentiator after the route/world
contract is stable.

The working MVP spec and feature audit live in
`docs/product/mvp-spec.md`.

### Agent Guidance

- Preserve the local-first, web-first shape while keeping the domain reusable.
- Do not couple trainer control, generated routes, persistence, analytics, or
  product rules directly to NiceGUI.
- Keep generated route/world logic behind domain or application contracts so it
  can power the current web UI, a richer 3D browser interface, and API/mobile
  clients.
- Use `docs/product/` for deeper product exploration and `docs/adr/` for
  architecture decisions that affect boundaries, storage, auth, or generated
  route contracts.
- Because the project vision changed after the initial implementation, current
  structures may not be optimal for the new goals. When working here, do not
  blindly continue an old structure if it conflicts with the new direction.
  Actively mention the discrepancy and propose a solution; sooner rewrites are
  better than carrying structural mismatch indefinitely.

## Current Status

- **Active UI:** NiceGUI web app in `le_tour/web`, started by `run_web.py`.
- **Core domain:** UI-neutral ride/controller/device services in
  `le_tour/domain`.
- **Trainer connection:** Python/Bleak FTMS client remains the primary local
  hardware path.
- **Native terminal UI:** the old Rich/TUI entry points and `le_tour/ui`
  package have been removed during the web migration. It is a thing of the past,
  not a future product surface.
- **Browser BLE:** `le_tour/web/static/ble.js` is an experimental
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
- **3D Ride Prototype:** a Three.js browser surface at `/ride3d` consumes the
  same ride snapshot/control contracts instead of reaching into trainer internals.
- **Data Persistence:** session and sample storage through the repository layer.
- **Training Log:** recorded sessions are shown from the repository-backed
  history surface.
- **Persisted Settings:** rider profile defaults are saved to the local
  le-tour config.
- **CSV Export:** export training data for external analysis.
- **Real-time Metrics:** power, cadence, speed, distance, heart rate, elapsed
  time, ERG target, and SIM grade.
- **Training Analytics:** Normalized Power (NP), Intensity Factor (IF), and
  Training Stress Score (TSS).

## Installation

### Early Access First Run

This MVP is a local-first early-access app. The recommended path is:

```bash
uv sync
uv run python run_web.py
```

Then open `http://127.0.0.1:8080`.

Use the browser UI from there:

1. Open **Settings** and set rider weight, FTP, units, ERG target, and SIM route.
2. Open **Settings** > **Devices** and scan for an FTMS trainer. Pair a
   heart-rate monitor only if you want HR in the ride.
3. Start **Free**, **ERG**, or **SIM** from the ride console.
4. Stop the ride from the cockpit and check the summary.
5. Use **History** to review the saved session or export CSV.

If no trainer is connected, le-tour clearly runs on demo samples so the cockpit,
history, and export flow can still be tested.

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

The 3D prototype is available at:

```text
http://127.0.0.1:8080/ride3d
```

The local web app will:

1. Render the browser UI.
2. Scan for compatible trainers when requested or during auto-connect flows.
3. Connect to the trainer through the Python FTMS client.
4. Start Free Ride, ERG, or SIM sessions from the web UI.
5. Record metrics and session samples through the domain/store layers.

Automatic Python/Bleak trainer scanning on first page load is gated behind
`LE_TOUR_ENABLE_BLE=1`. Manual device scanning from the Devices page remains
available without that flag.

### Bluetooth Platform Notes

- **macOS:** grant Bluetooth permission to the terminal app that launches
  `uv run python run_web.py`. If scanning fails after granting permission,
  restart that terminal app and reconnect the trainer.
- **Codex/agent sessions:** do not launch the hardware server from Codex when
  testing BLE on macOS. CoreBluetooth can abort the Python process if the host
  app lacks the right Bluetooth permission metadata. Launch from `Terminal.app`
  or another Bluetooth-approved terminal instead.
- **Linux:** confirm the Bluetooth adapter is visible, powered, and accessible
  to your user. BlueZ permissions and distro service configuration vary.
- **Windows:** the project is not treated as launch-supported for the current
  MVP unless a contributor validates Bleak/FTMS behavior there.
- Close Zwift, Wahoo, Garmin, TrainerRoad, or other apps that may already hold
  the trainer connection.

## Architecture

### Core Boundaries

- `le_tour/domain`: ride lifecycle, device services, event models, and
  UI-neutral state.
- `le_tour/devices`: BLE FTMS and Heart Rate clients plus parsers.
- `le_tour/modes`: ERG and SIM mode logic.
- `le_tour/store`: repository, models, CSV export, and storage adapters.
- `le_tour/web`: NiceGUI UI, auth, pages, and browser-facing assets.

The frontend must consume domain state through stable contracts instead of
reaching into BLE clients directly. This is especially important for the planned
Three.js ride world: the 3D layer should consume a ride snapshot/stream, not
trainer internals.

### Current Migration Notes

The project used to be terminal-first with a Rich-based UI. That direction is
retired. The current product is browser-first, with future surfaces expected to
be richer web/3D experiences, mobile clients, API clients, or headless
automation. The core rule still stands: keep business logic in the domain layer
so trainer control, persistence, analytics, and generated routes are not coupled
to NiceGUI or any single presentation layer.

## Training Modes

### Free Ride

Records live trainer and heart-rate data without controlling resistance.

### ERG Mode

Tracks a target power range and sends target power commands to the trainer when
the trainer is connected and control is available.

### SIM Mode

Uses grade-based simulation parameters and the local SIM physics model to
calculate virtual speed and distance.

The SIM physics solver is in `le_tour/modes/sim.py` and uses:

```text
P = 0.5 * rho * CdA * v^3 + m * g * Crr * v + m * g * sin(theta) * v + P0
```

## Data Management

- Session metadata and samples flow through `le_tour/store`.
- JSONL remains the durable append-friendly source of truth.
- SQLite supports faster local history/statistics queries.
- CSV export is layered on top of repository data.
- The web History page exports per-session CSV files under `exports/` in the
  local app data directory.

By default, local data is written below the le-tour config directory:

```text
~/.config/le-tour/data
```

## Configuration

### Environment

Copy `.env.example` only when you need optional environment-backed behavior such
as Supabase auth or a non-development NiceGUI storage secret.

```bash
cp .env.example .env
```

Relevant variables:

- `LE_TOUR_STORAGE_SECRET`: NiceGUI storage/session secret. Set this to a
  long random value outside local development.
- `LE_TOUR_ENABLE_BLE`: set to `1`, `true`, or `yes` to allow automatic
  BLE trainer scanning on first page load when the user setting also enables it.
- `SUPABASE_URL` and `SUPABASE_ANON_KEY`: enable optional Supabase auth.
- `APP_URL`: OAuth redirect base URL, usually `http://localhost:8080` locally.
- `SUPABASE_SERVICE_ROLE_KEY`: optional admin key; never expose it to clients or
  commit a real value.

### Rider Settings

Edit:

```text
~/.config/le-tour/config.json
```

The web Settings page also writes this file.

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
  "default_sim_route_id": "demo_rolling_route",
  "units": "metric",
  "auto_connect_trainer": true,
  "auto_connect_hr": false,
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

Current hardware smoke coverage:

- Wahoo KICKR CORE 6043: scan/connect, Free Ride, ERG target changes, SIM route
  context, stop/summary, persistence, and CSV export passed.
- BLE heart-rate strap: not yet tested.

1. Power on the FTMS trainer.
2. Ensure Bluetooth is enabled.
3. Run `uv run python run_web.py`.
4. Open `http://127.0.0.1:8080`.
5. Connect the trainer from Settings > Devices or use the auto-connect path.
6. Start a ride mode and verify live metrics update.
7. For ERG, verify the trainer responds to target changes.
8. For SIM, select each bundled route and verify grade/segment context updates.
9. Pair a standard BLE heart-rate strap and verify HR survives trainer changes.

## Release Checklist

Before calling an MVP release candidate launchable:

- Run `uv run pytest -q`.
- Run `uv run black .`.
- Run `uv run ruff check .`.
- Smoke test Free, ERG, and SIM with at least one real FTMS trainer.
- Smoke test optional BLE HR pairing with at least one standard strap.
- Confirm History shows the stopped ride and CSV export creates a readable file.
- Confirm README first-run steps match the actual app surface.

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

1. Check `~/.config/le-tour/data/sessions.jsonl`.
2. Check `~/.config/le-tour/data/samples.jsonl`.
3. If SQLite query results are stale or corrupt, remove the SQLite cache and
   rebuild/import from JSONL once a maintenance tool exists.
