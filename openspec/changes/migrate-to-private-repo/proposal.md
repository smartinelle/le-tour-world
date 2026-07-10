# Proposal: Migrate to a private repo with a clean ownership baseline

## Why

le-tour is becoming a commercial product, but this repo is a public GitHub
fork of an AGPL-3.0 project whose original code is copyrighted by the
upstream author. A fork cannot be made private, and upstream-authored code
cannot be relicensed for proprietary sale. We need a new private repo whose
every line is owned by the founders — and we want to redesign the
interfaces anyway, so the rewrite is the redesign.

## What Changes

- **New private repo, fresh git history.** No history is migrated: the
  fork's history contains upstream commits, so the new repo starts at
  commit zero. The public fork stays up, unchanged, under AGPL.
- **Carry only clean files verbatim.** Per line-level `git blame`, these
  are 0% upstream-authored and are carried as-is: `route_path.js`,
  `world_builder.js`, the `tests/e2e/` harness (3 files),
  `col_du_rivelet.json`, the fork-era docs (core-ride-plan,
  technical-assessment, architecture, generative-world-plan,
  app-landscape-notes, screenshots baseline), and vendored three.js (MIT,
  keep its license file).
- **Rewrite everything with upstream authorship**, spec-first: write the
  requirement (in our own words, below and in `specs/`), then implement
  fresh against it in the new repo. Never copy lines from the fork for
  these files. This covers the BLE device layer, session store, analytics,
  domain services, config, the 3D surface's page/API scaffolding, motion
  model, physics solver internals, and the home dashboard.
- **BREAKING: drop legacy surfaces instead of rewriting them.** The 2D
  ride view, browser-side Web Bluetooth (`ble.js`), the live-snake
  visualization, and the two upstream demo routes are not carried; the 3D
  surface is the only ride cockpit. New routes replace the demo maps.
- **Redesign interfaces while rewriting**: new home dashboard around route
  cards + history, a single typed snapshot contract, and a slimmer domain
  API shaped by what the 3D surface actually consumes.

## Capabilities

### New Capabilities

- `trainer-connectivity`: BLE FTMS trainer + heart-rate scan/connect,
  sample streams, ERG target power and SIM grade control. (Rewrite of
  `devices/`, `trainer_service`, `hr_service`, `device_state`.)
- `ride-session`: session lifecycle (start/pause/resume/stop/discard),
  live metrics, in-ride analytics (avg/NP), speed authority via rider
  physics, sample recording. (Rewrite of `ride_controller`,
  `ride_runtime`, `state`, `sim.py`.)
- `ride-physics`: power→speed dynamics with inertia, route grade
  smoothing, rider profile (mass/CdA/Crr). (Rewrite of `SimPhysics` +
  carry-over of the `RiderDynamics` requirements.)
- `route-model`: route spec schema, validation, distance-indexed
  positions, elevation/difficulty stats. (Rewrite of `routes.py`; the JS
  path compiler is carried, not rewritten.)
- `ride-surface`: the 3D cockpit — HUD, session controls, virtual rider
  panel, post-ride summary, snapshot stream + HTTP API. (Rewrite of
  `ride3d.py` HTML/API, `ride_client.js`, `ride_motion.js`, and the
  upstream-origin parts of `ride3d.js`; world renderer carried.)
- `ride-history`: session persistence, NP/IF/TSS analytics, history
  views, export. (Rewrite of `store/`, `analytics/`, `session_service`;
  simpler schema is fine.)
- `home-dashboard`: launch surface — route cards, recent rides, settings,
  device pairing. (Replaces upstream NiceGUI app with our own design.)
- `dev-harness`: virtual rider effort model + demo sample source +
  e2e smoke harness. (Sample source rewritten; e2e files carried.)

### Modified Capabilities

None — the new repo starts with no existing specs; all capabilities above
are written fresh.

## Impact

- **Ownership**: every line in the new repo is authored by the founders
  (or their agents) in that repo; licensable on our terms. The founders'
  own fork-era contributions are theirs to carry despite having been
  published under AGPL.
- **Scope of rewrite** (from blame, lines upstream/total): app.py
  2232/2280, theme.py 2067/2116, devices+store+analytics+services ≈4,600
  lines at 100%, ride_controller 488/604, ride3d.py 534/821, ride3d.js
  573/1012, plus their tests. Roughly 12–14k lines to re-author; ~2,500
  lines and all fork-era docs/assets carry over clean.
- **Product**: no 2D fallback during the transition; hardware-path parity
  (FTMS ERG/SIM) must be re-verified on the KICKR when hardware arrives.
- **Open questions for founder sign-off**: new repo name; license posture
  (all-rights-reserved vs dual); whether any public open-core repo is kept
  beyond the frozen fork.
