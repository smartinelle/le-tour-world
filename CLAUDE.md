# Le-tour (TerminalRide) - Claude Memory

## Project Overview

- **Goal:** Web-first indoor cycling app that connects to Wahoo KICKR via BLE FTMS and keeps the ride domain reusable for future UIs.
- **Stack:** Python 3.11, uv, NiceGUI, bleak, numpy, pydantic, pytest.
- **Modes:** Free Ride, ERG (constant power), SIM (grade-based resistance).
- **Data:** JSONL/SQLite persistence, CSV export, local analytics.
- **Current UI:** Browser app in `terminalride/web`, started with `run_web.py`.
- **Retired UI:** The old Rich terminal UI entry points are removed on this branch.

## Development Commands

```bash
# Setup
uv sync

# Testing & Quality
uv run pytest -q
uv run ruff check terminalride tests run_web.py
uv run black terminalride tests run_web.py
uv run mypy terminalride
```

## Architecture Principles

- Keep core ride/session logic in `terminalride/domain`.
- Keep presentation code in `terminalride/web`.
- Do not couple trainer control, persistence, or analytics to NiceGUI.
- Expose UI-neutral ride state so future terminal, mobile, or Three.js interfaces can reuse the same domain.
- Keep BLE I/O isolated in `terminalride/devices`.
- Keep parsers and physics deterministic and testable.
- Do not invent FTMS details; add `TODO(FTMS: confirm...)` markers when specs need verification.

## Repository Structure

```text
terminalride/
  config.py
  logging_setup.py
  devices/
    base.py
    ftms_client.py
    ftms_parse.py
    hr_client.py
    hr_parse.py
  modes/
    erg.py
    sim.py
  domain/
    ride_controller.py
    events.py
    state.py
    trainer_service.py
    hr_service.py
    session_service.py
  store/
    models.py
    repository.py
    supabase_repository.py
    export.py
  web/
    app.py
    auth.py
    pages/
    static/
  analytics/
    metrics.py
tests/
```

## Current Status

- Branch baseline is web-first.
- Domain has a restored `RideController`.
- Web sessions have live trainer metrics fixed.
- Supabase auth/storage support exists.
- Tooling has moved from pip/requirements to uv + `uv.lock`.

## Near-Term Technical Direction

1. Add a UI-neutral `RideSnapshot`.
2. Add `RideController.snapshot()`.
3. Stream snapshots to the browser.
4. Add a fake trainer/sample source for no-hardware development.
5. Decouple `terminalride/web/app.py` from private device client internals.
6. Build the first Three.js prototype against the snapshot stream.
