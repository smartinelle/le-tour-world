# Tasks: migrate-to-private-repo

## 1. Legal and repo setup (founders)

- [ ] 1.1 Founder creates the new private GitHub repo (name = working
      product name; decides license posture: default all-rights-reserved)
- [ ] 1.2 Cofounder (upstream author) signs a short IP consent/assignment
      for the venture covering his upstream work — belt-and-suspenders on
      top of the rewrite; template from counsel
- [ ] 1.3 Freeze the public fork: final push, README note that active
      development moved (no link needed), stop pushing new work there
- [ ] 1.4 Add the new repo to the Claude session (`add_repo`) so migration
      work happens there

## 2. Seed the new repo (carry-only commit, no fork history)

- [ ] 2.1 Scaffold: pyproject (new package name), uv setup, ruff/black
      config, README stub, .gitignore — written fresh
- [ ] 2.2 Copy clean files verbatim: `route_path.js`, `world_builder.js`,
      `vendor/three.module.js` + THREE_LICENSE, `col_du_rivelet.json`,
      `tests/e2e/` (3 files), fork-era docs + `docs/screenshots/`
- [ ] 2.3 Copy `openspec/` (this change) into the new repo; archive the
      change here once migration completes
- [ ] 2.4 Verify the seed: `git log` shows only new commits; grep confirms
      no other files came across

## 3. Rewrite: route-model + ride-physics (pure Python, no I/O)

- [ ] 3.1 Implement route spec validation + distance queries per
      `specs/route-model/spec.md`, with tests from the spec's scenarios
- [ ] 3.2 Implement the power-balance integrator + grade smoothing per
      `specs/ride-physics/spec.md`; verify the three scenarios numerically
- [ ] 3.3 Round-trip check: flagship JSON validates and compiles through
      the carried `buildRoutePath`

## 4. Rewrite: ride-session + dev-harness source

- [ ] 4.1 Implement session lifecycle, speed authority, live avg/NP, and
      the single snapshot contract per `specs/ride-session/spec.md`
- [ ] 4.2 Implement the virtual rider demo source per
      `specs/dev-harness/spec.md` (auto/hold/ramp/sprint envelopes)
- [ ] 4.3 Sample-recording plumbing behind an interface ride-history can
      implement later

## 5. Rewrite: ride-surface

- [ ] 5.1 New HTTP+SSE API per `specs/ride-surface/spec.md` (routes,
      start/stop/pause, ERG/SIM, virtual rider, health, snapshots)
- [ ] 5.2 New page + client + motion model: redesigned markup/HUD, damped
      camera (no bob), stale-stream coast, resilient frame loop, debug
      object, post-ride summary
- [ ] 5.3 Wire carried renderer (`buildWorld`/`poseAt` seam unchanged);
      adapt the carried e2e harness paths; smoke test green
- [ ] 5.4 Regenerate the screenshot baseline in the new repo

## 6. Rewrite: ride-history

- [ ] 6.1 Local store (sessions + samples) per `specs/ride-history/spec.md`
      — schema redesigned, simpler than the fork's
- [ ] 6.2 NP/IF/TSS analytics with hand-computed test vectors
- [ ] 6.3 History list/detail/delete + CSV export

## 7. Rewrite: home-dashboard

- [ ] 7.1 Fresh theme + component set (no upstream chrome) per
      `specs/home-dashboard/spec.md`
- [ ] 7.2 Route cards, mode picker → 3D launch, recent rides
- [ ] 7.3 Settings: rider profile, defaults, device pairing UI

## 8. Rewrite: trainer-connectivity (last; hardware-gated verification)

- [ ] 8.1 FTMS + HRS clients written from the Bluetooth SIG specs, with
      parser unit tests from spec-derived byte vectors
- [ ] 8.2 Scan/connect/control services behind the same handler interface
      as the demo source
- [ ] 8.3 KICKR verification ride when hardware is available (release
      checklist items)

## 9. Close out

- [ ] 9.1 Full suite + e2e smoke green in the new repo; provenance check:
      every non-carried file has new-repo-only history
- [ ] 9.2 Port the living docs (core-ride-plan status, development.md,
      release checklist) and update names/links
- [ ] 9.3 Archive this OpenSpec change; subsequent work (third-person
      avatar mode, generative layer) proposed as new changes in the
      private repo
