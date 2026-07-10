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

The primary ride surface is `http://127.0.0.1:8080/ride3d` (the home
dashboard's Start Ride and route cards open it). `LE_TOUR_HOST` /
`LE_TOUR_PORT` override the bind address; startup fails fast with a clear
message when the port is taken.

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
- `LE_TOUR_HOST` / `LE_TOUR_PORT`: web app bind address.
- `LE_TOUR_E2E=1`: opt in to the browser smoke tests (see below).
- `LE_TOUR_CHROMIUM`: explicit Chromium binary for the e2e harness.
- `LE_TOUR_E2E_ARTIFACTS`: directory for e2e screenshot artifacts.
Cloud accounts and hosted sync are not part of the current early-access flow.

## Browser smoke tests (e2e)

The unit suite (`uv run pytest`) is browser-free. A separate opt-in smoke
test drives the real app in Chromium — launch, ride the flagship map on
the demo source, assert HUD updates, zero frame errors, and the frame
budget below, and capture a screenshot artifact:

```bash
uv sync --group e2e          # installs playwright
LE_TOUR_E2E=1 uv run pytest tests/e2e -q
```

The harness (`tests/e2e/harness.py`) starts `run_web.py` on a free port
and reads renderer ground truth from `window.__rideDebug` (distance,
speed, camera FOV/roll, draw calls, triangles, frame errors). This is the
same scaffold the generative plan's eval loop (Experiment 3) runs on.

`tests/e2e/capture_flagship_screenshots.py` regenerates the
`docs/screenshots/` baseline by riding the full flagship loop (~20 min).

## Performance budget

Target: **60 FPS at 1440x900 on a mid-range GPU** with full scenery on the
flagship map. The world is built once per route load; per frame only the
camera, pacers, cockpit, and HUD update — so frame cost is dominated by
raster load, and the budget is expressed in what the GPU must draw:

| Metric | Budget | Measured (flagship, 2026-07-10) |
|---|---|---|
| Triangles per frame | ≤ 500,000 | 218,628 |
| Draw calls per frame | ≤ 200 | 16 |
| Frame errors per ride | 0 | 0 |

Draw calls stay low because scenery props are `InstancedMesh` per part and
the road/terrain are merged vertex-colored meshes. The smoke test asserts
these budgets on every run (`window.__rideDebug.triangles` / `.drawCalls`).

Dev-container caveat: headless runs use SwiftShader (software GL), which
rasterizes this scene at only a few FPS — that is a CPU rasterizer floor,
not a GPU number. The 60 FPS exit check must be run once on real hardware
(open `/ride3d`, ride, and watch frame pacing; `__rideDebug.frameAt`
deltas give frame times).

## Release Checks

See [release-checklist.md](release-checklist.md).
