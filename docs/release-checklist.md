# Release Checklist

Use this as the manual release gate for early-access builds.

## Automated Checks

- `uv run pytest -q`
- `uv run black --check le_tour tests run_web.py examples`
- `uv run ruff check le_tour tests run_web.py examples`
- Browser smoke test (needs Chromium): `uv sync --group e2e` then
  `LE_TOUR_E2E=1 uv run pytest tests/e2e -q` — rides the flagship map,
  checks HUD updates, zero frame errors, and the perf budget from
  [development.md](development.md).

## First-Run Smoke Test

- Fresh clone can run with `uv sync` and `uv run python run_web.py`.
- README first-run steps match the visible web app.
- App starts at `http://127.0.0.1:8080` with only local configuration.
- The UI clearly distinguishes live hardware from demo samples.
- On macOS hardware tests, the server is launched from a Bluetooth-approved
  terminal app.

## Hardware Smoke Matrix

For each launch-supported FTMS trainer:

- Device scan finds the trainer.
- Connect, disconnect, and reconnect work from the Devices page.
- Free Ride records power, cadence, speed, distance, and elapsed time.
- ERG starts, sends initial target power, and responds to target changes.
- SIM starts with a selected route and updates grade/segment context.
- Stopping a ride persists a history session with samples.
- On `/ride3d`: SIM resistance ramps smoothly across grade changes (no
  steps), and the app-computed speed feels plausible against the trainer's
  own reading (`speed_mps` vs `trainer_speed_mps` in the snapshot stream).
- On `/ride3d` with a real GPU: frame pacing holds ~60 FPS with full
  scenery on Col du Rivelet (`window.__rideDebug` has frame timestamps,
  draw calls, and triangle counts).

Current FTMS smoke status:

- Wahoo KICKR CORE 6043 passed scan/connect, Free Ride, ERG target changes, SIM
  route context, stop/summary, persistence, and CSV export on May 2, 2026.

For each launch-supported BLE heart-rate strap:

- Device scan finds the strap.
- Connect and disconnect work from the Devices page.
- HR appears during a trainer ride.
- HR remains available when trainer samples are simulated.

## Data And Export

- Stopped rides land on a summary page.
- Saved sessions appear in History.
- Session detail shows duration, distance, power, HR, NP, IF, and TSS when data
  supports those metrics.
- CSV export writes a readable file under the local data `exports/` directory.
- A ride with no captured samples is reported as unsaved instead of creating a
  misleading history row.

## Known Non-MVP Surfaces

- Web Bluetooth remains experimental and is not the default hardware path.
- Hosted accounts and cloud sync are not part of the current early-access flow.
