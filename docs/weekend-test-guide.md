# Weekend Hardware Test Guide

First real-trainer test of the 3D ride surface. Everything below has been
verified headless with the virtual rider; **your ride is the first time
this code meets real hardware**, so the goal is signal quality and feel,
not polish. Budget ~45–60 minutes on the bike.

## Setup (before getting on the bike)

```bash
git clone -b claude/world-builder-plan-dpiyz1 https://github.com/smartinelle/le-tour-world
cd le-tour-world
uv sync
uv run python run_web.py
```

Open `http://127.0.0.1:8080`. If port 8080 is taken the app tells you;
use `LE_TOUR_PORT=8180 uv run python run_web.py`.

macOS: grant Bluetooth permission to the terminal app that launches the
server (System Settings → Privacy → Bluetooth), and close Zwift/Wahoo/
anything else that may hold the trainer. If a scan fails right after
granting permission, restart the terminal app.

**Dry run first (no trainer):** click a route card → SIM → ride the demo
source for a minute. If the world renders and the HUD moves, the install
is good. Stop the ride before pairing.

## The test protocol

Pair the trainer **before** starting the ride (Devices panel on the
/ride3d start screen, or home → Pair Devices). Connecting mid-ride should
also work now — it hands the session over to hardware — but do the simple
order first.

1. **Free Ride, 5 min — signal sanity.** Power and cadence on the HUD
   should track what your legs are doing with ~1 s lag. Speed is
   app-computed (physics), so it will NOT match the trainer's own
   speed — that's by design. Capture both:
   `curl -s localhost:8080/api/ride/snapshot | python3 -m json.tool`
   → compare `speed_mps` (physics) vs `trainer_speed_mps` (wheel).
2. **SIM on Col du Rivelet — the main event.** Ride 20–30 min (the climb
   starts ~3.6 km). Judge:
   - Resistance follows terrain and **ramps** across grade changes — no
     steps or jolts (grade is smoothed over 30 m and rounded to 0.1%).
   - Speed feel: does 200 W on the flat / on the 8% wall feel plausible?
   - Visual smoothness at your real GPU's frame rate: steady camera (no
     bumping — this was a bug, now fixed), gentle lean into switchbacks,
     slight FOV widening at speed.
   - Sprint once out of the saddle: HUD power card should go red (zone 6),
     world speed should surge with inertia, not snap.
3. **ERG, 5 min.** Start ERG, nudge target ±10 W a few times: the trainer
   should clamp your power to target within a few seconds regardless of
   cadence.
4. **Stop.** Post-ride summary should show time/km/gain/avg/NP/IF/TSS and
   "Saved to ride history"; the ride appears in History; CSV export works.

## Robustness pokes (do these — they're the point)

- Pause mid-climb, wait 30 s, resume (you restart from a standstill).
- Refresh the browser mid-ride: the ride must continue, not restart.
- Turn the trainer off mid-ride, wait ~10 s, turn it on: the app
  auto-reconnects with backoff and samples resume.
- Disconnect from the Devices panel, reconnect, start a new ride:
  samples must flow (this exact sequence was a bug, fixed 2026-07-10).
- Kill the server mid-ride (Ctrl-C): the world should coast to a stop in
  ~3 s, and the buttons should show errors instead of doing nothing.

## What to capture for feedback

- The terminal (server log) — copy anything that looks like a stack trace.
- In the browser console: `window.__rideDebug` — screenshot it if anything
  feels off (it has fps timestamps, distances, camera, draw calls,
  `frameErrorCount`, which should stay 0).
- One snapshot JSON during steady riding (curl above) for the
  physics-vs-wheel speed comparison.
- Feel notes, free-form: what did the apps you know do better? Grade
  transitions, steady-state calm, sprint response, HUD legibility.

## Known gaps — don't file these

- No third-person avatar yet (first-person cockpit only; avatar mode is
  the next planned change). No steering/turning — the bike follows the
  route, like ERG-era Zwift.
- NP reads low/unstable for the first ~30 s (rolling window fills up).
- The 2D ride view is still reachable from home ("2D view") as fallback.
- HR strap optional; demo HR fills in if none is paired.
