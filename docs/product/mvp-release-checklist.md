# MVP Release Checklist

Use this as the manual release gate for the early-user MVP.

## Automated Checks

- `uv run pytest -q`
- `uv run black .`
- `uv run ruff check .`

## First-Run Smoke Test

- Fresh clone can run with `uv sync` and `uv run python run_web.py`.
- README first-run steps match the visible web app.
- App starts at `http://127.0.0.1:8080` with no Supabase configuration.
- The UI clearly distinguishes live hardware from demo samples.

## Hardware Smoke Matrix

For each launch-supported FTMS trainer:

- Device scan finds the trainer.
- Connect, disconnect, and reconnect work from the Devices page.
- Free Ride records power, cadence, speed, distance, and elapsed time.
- ERG starts, sends initial target power, and responds to target changes.
- SIM starts with a selected route and updates grade/segment context.
- Stopping a ride persists a history session with samples.

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

- The `/ride3d` page remains an experimental prototype.
- Web Bluetooth remains experimental and is not the default hardware path.
- Supabase auth/storage remains optional and is not required for local-first use.
- Prompt-generated routes/worlds remain deferred until route contracts are more
  stable.
