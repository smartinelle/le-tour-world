# Development Notes

le-tour is a local-first web app. Python owns trainer communication, ride state,
persistence, and domain logic. The browser UI presents that state and sends user
commands.

## Core Boundaries

- `le_tour/domain`: ride lifecycle, device services, events, and UI-neutral
  state.
- `le_tour/devices`: BLE FTMS and Heart Rate clients plus parsers.
- `le_tour/modes`: ERG and SIM mode logic.
- `le_tour/store`: repository, models, CSV export, and storage adapters.
- `le_tour/web`: NiceGUI UI, browser-facing routes, and static assets.
- `le_tour/analytics`: training metrics such as NP, IF, and TSS.

Frontend code should consume domain state through stable contracts. Avoid
reaching directly into BLE clients from presentation code.

## Running Locally

```bash
uv sync
uv run python run_web.py
```

Open `http://127.0.0.1:8080`.

The 3D prototype is available at `http://127.0.0.1:8080/ride3d`.

## Data Storage

By default, local config and data live under:

```text
~/.config/le-tour
```

Session metadata and samples are stored as JSONL files. SQLite is used for
faster local queries.

## Environment Variables

- `LE_TOUR_STORAGE_SECRET`: NiceGUI storage/session secret.
- `LE_TOUR_ENABLE_BLE`: enable automatic trainer scanning on first page load.
Cloud accounts and hosted sync are not part of the current early-access flow.

## Release Checks

See [release-checklist.md](release-checklist.md).
