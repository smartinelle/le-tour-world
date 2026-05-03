# le-tour - Claude Memory

## Project Overview

- **Goal:** Web-first indoor cycling app that connects to Wahoo KICKR via BLE FTMS and keeps the ride domain reusable for richer browser/3D surfaces, API clients, mobile clients, and headless workflows.
- **Stack:** Python 3.11, uv, NiceGUI, bleak, numpy, pydantic, pytest.
- **Modes:** Free Ride, ERG (constant power), SIM (grade-based resistance).
- **Data:** JSONL/SQLite persistence, CSV export, local analytics.
- **Current UI:** Browser app in `le_tour/web`, started with `run_web.py`.
- **Retired UI:** The old Rich terminal UI entry points are removed on this branch. Do not plan for that UI to return.

## Development Commands

```bash
# Setup
uv sync

# Testing & Quality
uv run pytest -q
uv run ruff check le_tour tests run_web.py
uv run black le_tour tests run_web.py
uv run mypy le_tour
```

## Architecture Principles

- Keep core ride/session logic in `le_tour/domain`.
- Keep presentation code in `le_tour/web`.
- Do not couple trainer control, persistence, or analytics to NiceGUI.
- Expose UI-neutral ride state so richer browser/3D, mobile, API, and headless interfaces can reuse the same domain.
- Keep BLE I/O isolated in `le_tour/devices`.
- Keep parsers and physics deterministic and testable.
- Do not invent FTMS details; add `TODO(FTMS: confirm...)` markers when specs need verification.

## Repository Structure

```text
le_tour/
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
5. Decouple `le_tour/web/app.py` from private device client internals.
6. Build the first Three.js prototype against the snapshot stream.
