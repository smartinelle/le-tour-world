# le-tour

le-tour is an early-access, local-first indoor cycling app for Bluetooth FTMS
trainers. It runs a local Python process with a browser UI so the app can talk
to nearby trainers and heart-rate monitors without sending ride control through
a cloud service.

The project is currently aimed at technical early users. There are no packaged
installers yet; you run it from source with `uv`.

## Current Status

- Local browser UI for solo indoor rides.
- Python/Bleak hardware path for FTMS trainers and BLE heart-rate monitors.
- Free Ride, ERG, and SIM modes.
- Local ride history with session samples.
- CSV export.
- Primary ride surface at `/ride3d`: a world-fixed 3D map with terrain,
  physics-computed speed (rider mass/CdA/Crr + route grade), an in-ride HUD
  with live avg power/NP and FTP-zone coloring, a post-ride summary, and a
  virtual trainer panel for riding without hardware. Flagship route: Col du
  Rivelet, a 17.2 km loop with 260 m of climbing. The home dashboard's route
  cards and Start Ride open it directly.

Tested hardware so far:

- Wahoo KICKR CORE 6043 on macOS.

Other FTMS trainers may work, but they are not launch-supported until someone
has tested scan, connect, Free Ride, ERG, SIM, stop, history, and export.

## Safety

le-tour can control trainer resistance in ERG and SIM modes. Stop riding and
disconnect the trainer if resistance feels wrong, unexpected, or unsafe. Treat
this as alpha software and keep your bike/trainer setup physically safe before
testing new builds.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- macOS or Linux with Bluetooth access
- BLE FTMS-compatible trainer for real rides
- Optional BLE heart-rate monitor

Windows is not currently launch-supported. Chrome or Edge is recommended for the
browser UI; Chrome/Edge are required if you experiment with browser-side Web
Bluetooth.

## Quick Start

```bash
git clone https://github.com/jimfable/le-tour.git
cd le-tour
uv sync
uv run python run_web.py
```

Open:

```text
http://127.0.0.1:8080
```

If another local service already uses port 8080 (SearXNG, Jenkins, and other
tools often do), run on a different one:

```bash
LE_TOUR_PORT=8180 uv run python run_web.py
```

The app stores local config and ride data under:

```text
~/.config/le-tour
```

If no trainer is connected, le-tour uses demo samples so the cockpit, history,
and export flow can still be explored.

## Basic Ride Flow

1. Open **Settings** and set rider weight, FTP, units, ERG target, and default
   SIM route.
2. Open **Settings** > **Devices** and scan for an FTMS trainer.
3. Optionally connect a BLE heart-rate monitor.
4. Start **Free**, **ERG**, or **SIM** from the ride cockpit.
5. Stop the ride and review the saved summary.
6. Open **History** to inspect saved rides or export CSV.

## Bluetooth Notes

On macOS, grant Bluetooth permission to the terminal app that launches
`uv run python run_web.py`. If scanning fails after granting permission, restart
that terminal app and try again.

Close Zwift, Wahoo, Garmin, TrainerRoad, or other apps that may already hold the
trainer connection.

Automatic trainer scanning on first page load is disabled by default. To enable
it, set:

```bash
LE_TOUR_ENABLE_BLE=1 uv run python run_web.py
```

Manual scanning from the Devices page remains available without that flag.

## Features

- **Trainer support:** BLE FTMS trainers through Python/Bleak.
- **Heart rate:** BLE Heart Rate Service monitors.
- **Free Ride:** ride and record trainer data without resistance control.
- **ERG:** target-power training with adjustable target watts.
- **SIM:** grade-based simulation with bundled route profiles.
- **History:** local sessions and samples stored on disk.
- **Export:** per-session and summary CSV exports.
- **3D ride surface:** the primary ride cockpit at `/ride3d` — world-fixed
  terrain, in-ride HUD, route progress, and post-ride summary. The classic
  2D view stays available from the home dashboard as a fallback.

## Known Limitations

- No packaged app or installer yet.
- Hardware support is only lightly tested.
- Browser-side Web Bluetooth is experimental and not the default hardware path.
- The 3D ride surface's 60 FPS target and trainer resistance feel are not
  yet verified on real hardware (dev environments render via software GL).
- No login, hosted accounts, or cloud sync in the current early-access flow.
- No FIT, TCX, Strava, Garmin, or Wahoo cloud integrations yet.
- No multiplayer, racing, events, chat, clubs, or social features.

## Development

Useful commands:

```bash
uv sync
uv run pytest -q
uv run black --check le_tour tests run_web.py examples
uv run ruff check le_tour tests run_web.py examples
```

Optional browser smoke test (rides the flagship map in headless Chromium):

```bash
uv sync --group e2e
LE_TOUR_E2E=1 uv run pytest tests/e2e -q
```

Format before submitting changes:

```bash
uv run black le_tour tests run_web.py examples
uv run ruff check le_tour tests run_web.py examples
```

Architecture notes live in [docs/development.md](docs/development.md).

## Contributing

Issues and focused pull requests are welcome. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) before starting larger changes.

## Security

Please do not report security issues in public GitHub issues. See
[SECURITY.md](SECURITY.md).

## License

le-tour is licensed under the GNU Affero General Public License v3.0. See
[LICENSE](LICENSE).
