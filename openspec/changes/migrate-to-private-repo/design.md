# Design: Private repo migration and re-authoring

## Context

The current repo (`smartinelle/le-tour-world`) is a public GitHub fork of
an AGPL-3.0 upstream authored by the cofounder (pre-incorporation). GitHub
forks cannot be made private, and the AGPL history cannot ship in a
proprietary product. Line-level `git blame` (2026-07-10, on
`claude/world-builder-plan-dpiyz1`) gives the exact ownership map:

**Clean — 0% upstream, carry verbatim**

| File | Lines |
|---|---|
| `le_tour/web/static/world_builder.js` | 753 |
| `le_tour/web/static/route_path.js` | 215 |
| `tests/e2e/` (harness, smoke test, capture tool) | 400 |
| `le_tour/assets/routes/col_du_rivelet.json` | — |
| Fork-era docs + screenshots baseline | — |
| `vendor/three.module.js` (MIT) + THREE_LICENSE | — |

**Upstream-authored — rewrite, never copy** (upstream/total lines)

- 100%: `devices/` (ftms_client 437, hr_client 377, parsers, base),
  `store/` (repository 453, models, export), `analytics/` (metrics 412,
  activity_graphs), `domain/` services (trainer_service, hr_service,
  session_service, device_state, events), `modes/erg.py`, `config.py`,
  `logging_setup.py`, `web/components/*`, `snapshot_stream.py`, `ble.js`
  565, `live_snake.js` 364, and all their tests.
- Majority: `web/app.py` 2232/2280, `web/theme.py` 2067/2116,
  `routes.py` 405/431, `ride_motion.js` 227/263, `ride_runtime.py`
  223/260, `state.py` 108/131, `ride_controller.py` 488/604,
  `ride_client.js` 106/132, `ride3d.py` 534/821, `ride3d.js` 573/1012,
  `sim.py` 148/223, `fake_samples.py` 128/306.

Copyright protects expression (the lines), not ideas (the architecture).
Re-implementing the same behaviors to our own specs, in our own words and
structure, is the standard and defensible path — and we intend to change
the interfaces regardless.

## Goals / Non-Goals

**Goals:**

- A private repo where 100% of code was authored in that repo by the
  founders/agents, with fresh git history.
- Feature parity for the product that matters now: 3D ride surface,
  physics speed authority, BLE FTMS/HR hardware path, sessions + history
  + analytics, virtual-rider dev harness.
- Interface redesign in the same pass (new dashboard, slimmer domain API,
  single snapshot contract).
- The public fork remains untouched and AGPL-compliant.

**Non-Goals:**

- Migrating git history (would carry upstream commits).
- Rewriting the 2D ride view, `ble.js` Web Bluetooth path, live-snake, or
  the upstream demo routes — dropped, not ported.
- Formal two-team clean-room ceremony. The founders own both sides
  amicably; the goal is provenance (no upstream lines in the new repo),
  not litigation-grade isolation. A lawyer should still bless the overall
  plan before first sale.
- Choosing the commercial license/pricing (separate founder decision).

## Decisions

1. **Fresh history, empty start.** The new repo begins with the carried
   clean files + specs, commit one. The fork is never a remote of the new
   repo, preventing accidental cherry-picks.
2. **Spec-first rewrite discipline.** For every rewritten capability, the
   requirement lives in `specs/` (this change) written from behavior, not
   from code. Implementation in the new repo works from the spec and the
   public protocol documents (FTMS spec, BLE GATT), not from the old
   source. The old repo may be consulted to *state requirements*, not
   while writing replacement code.
3. **Rewrite order follows testability without hardware**: route-model →
   ride-physics → ride-session → ride-surface → dev-harness →
   ride-history → home-dashboard → trainer-connectivity last (needs the
   KICKR to verify anyway; the FTMS protocol layer is rewritten from the
   Bluetooth SIG spec).
4. **Domain slimming while rewriting**: one `RideSnapshot` contract
   consumed by every surface; controller exposes lifecycle + samples only;
   NiceGUI stays for the dashboard shell (it is a dependency, not
   upstream code) unless the founders decide otherwise later.
5. **Carried JS keeps its API**: `buildRoutePath(route)` and
   `buildWorld(path)` are the stable seam; the rewritten surface plugs
   into them unchanged. This also keeps the generative plan's compiler
   seam intact.
6. **Same stack** (Python 3.11 + FastAPI/NiceGUI + three.js): the value
   is the product, not a platform change; keeping the stack lets the
   carried renderer and e2e harness work day one.
7. **Naming**: new package name chosen at migration time (also serves
   trademark hygiene); route/asset formats keep `schema_version` so
   flagship content carries.

## Risks / Trade-offs

- **Residual similarity risk**: rewritten code may converge on similar
  shapes (same stack, same behaviors). Mitigation: spec-first discipline,
  different module boundaries (by design), and the cofounder — the only
  upstream rights-holder — signs a short IP assignment/consent for the
  venture regardless, which caps this risk entirely. Doing both belt and
  suspenders is deliberate.
- **Hardware path regression**: the BLE layer is rewritten but cannot be
  hardware-verified until the trainer is available. Mitigation: protocol
  unit tests from FTMS spec vectors; the release checklist already gates
  on a real KICKR ride.
- **Feature loss**: dropping the 2D view removes the only
  hardware-verified surface. Accepted: the 3D surface is the product, and
  parity is a release-checklist item.
- **Timeline**: ~12–14k lines re-authored. The compensating factor is
  that specs, tests-as-contracts, and the carried renderer/harness make
  this mostly mechanical; estimate before starting each capability in
  `tasks.md` order.
- **Public traces**: everything pushed to the fork so far is public
  forever (clones, archives). The clean baseline protects the future, not
  the past; nothing secret has been pushed.
