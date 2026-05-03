# Early-User MVP Spec

## Purpose

The first launchable version of le-tour should be a local-first indoor cycling
app for early users: tech-comfortable indoor cyclists, makers, and
training-focused riders who can tolerate some rough edges if the core ride loop
is useful and reliable.

This MVP is not the broad consumer app, not a full Zwift replacement, and not
the prompt-generated 3D world product. It is the product phase that proves the
solo ride loop, hardware path, local data model, and basic onboarding before the
project invests heavily in broader distribution.

## MVP Product Promise

A rider can install/run le-tour, pair an FTMS trainer and optional heart-rate
monitor, start a solo ride in Free Ride, ERG, or SIM mode, see trustworthy live
metrics in a clean non-3D cockpit, stop the ride, and find the saved session in
history with exportable data.

## Target Users

- Indoor cyclists who already understand trainers, power, cadence, and FTP.
- Riders who want a solo training app without multiplayer/social pressure.
- Technical early adopters who can handle a local app while the product matures.
- Contributors or power users interested in routes/worlds later.

## Non-Goals For This MVP

- Hosted multi-user SaaS as the default product.
- Prompt-generated route/world UI.
- Production subscriptions or billing.
- Multiplayer, racing, chat, clubs, events, or social feeds.
- Full native desktop packaging for all platforms if a simpler early-user
  install path is enough.
- A polished 3D world as the primary ride surface.
- Deep third-party integrations beyond CSV export.

## Launch Bar

The MVP is launchable when:

- A non-developer early user can follow the install/run docs without reading the
  codebase but just the README.
- Trainer and heart-rate pairing flows explain what is happening and recover
  from common failures.
- Free Ride, ERG, and SIM can be used from the non-3D cockpit.
- SIM has explicit route/grade context instead of only a hidden or manual grade.
- Live metrics are stable and readable from riding distance.
- Sessions persist reliably and appear in history.
- CSV export is available from the product surface or clearly documented.
- The app is honest about demo data, experimental 3D, Web Bluetooth, Supabase,
  and unsupported hardware.
- `uv run pytest -q`, `black`, and `ruff` pass before release branches.

## Feature Audit

Status meanings:

- `Ready`: viable for MVP after normal verification.
- `Partial`: meaningful implementation exists, but launch work remains.
- `Missing`: not yet implemented in a user-facing way.
- `Defer`: deliberately outside this MVP.

| Feature | MVP Expectation | Current Situation | Status | Work Needed |
| --- | --- | --- | --- | --- |
| Product positioning | App is presented as le-tour, an early-user local-first solo training app. | README and roadmap now state the early-user strategy, but user-facing app title and config paths still mostly say TerminalRide. | Partial | Decide public naming boundary. Rename visible UI/docs where appropriate while avoiding risky package churn unless planned. Add a concise early-access README section. |
| Install/run onboarding | Early user can get running without understanding the codebase. | README documents `uv sync` and `uv run python run_web.py`; no packaged launcher or simplified release flow yet. | Partial | Add a first-run guide, platform notes for Bluetooth permissions, troubleshooting, and a single recommended command path. Later evaluate a packaged app/launcher. |
| Local-first architecture | Python owns hardware/runtime/data; browser UI remains replaceable. | Domain services, runtime, snapshots, repository, and NiceGUI UI are separated. 3D consumes browser contracts. | Ready | Preserve boundaries during feature work. Add ADRs when storage/auth/route contracts change. |
| Non-3D ride cockpit | Main ride surface is usable without 3D. | NiceGUI home/session pages exist with large metrics, start/stop/pause, ERG/SIM controls, and demo-data fallback. | Partial | Polish session states, stop/summary flow, error states, route context, and real riding-distance readability. Remove explanatory UI copy that feels like internal implementation notes. |
| Settings device pairing | Rider can scan, select, connect, disconnect, and understand trainer state. | Device pairing lives under Settings. Scan dialogs exist for trainer and HR. `TrainerService` wraps FTMS client. Auto-connect is gated by `TERMINALRIDE_ENABLE_BLE`. | Partial | Hardware-test with real trainers, improve retry/reconnect, document OS Bluetooth permissions, clarify demo-vs-live state, and resolve/verify FTMS command TODOs. |
| Heart-rate monitor pairing | Optional BLE HR strap works independently of trainer. | `HrService`, HR parsing, scan/connect UI, and tests exist. Runtime can use real HR with simulated trainer samples. | Partial | Show richer HR status, sensor contact where available, connection loss state, and hardware-test common straps. |
| Free Ride | Rider can record a no-control session. | `RideController` and `RideRuntime` start Free Ride, attach samples, and persist when samples exist. UI exposes Free mode. | Partial | Verify with real hardware. Make post-ride save behavior obvious, especially when no samples were captured. |
| ERG mode | Rider can start ERG, see target, and adjust target power. | ERG target defaults come from config. UI has +/- 10 W controls. Runtime requests control and sends target power. | Partial | Verify FTMS target-power command behavior on hardware. Add clearer target controls and failure state if trainer control is unavailable. |
| SIM mode | Rider can ride grade-based simulation with understandable route/grade context. | SIM physics, route selection in the main ride setup, route profile preview, live route progress, and manual grade adjustment exist. `/ride3d` can also select bundled routes against the same runtime contract. | Partial | Hardware-test route-driven trainer control and improve live SIM context where needed, especially current/upcoming grade clarity and route progress readability. |
| SIM route metadata | Built-in routes have clear names, distance, segments, grades, surface/scenery metadata. | `terminalride/domain/routes.py` validates bundled JSON specs. Two bundled routes exist. The main ride setup shows a route selector, elevation/profile preview, distance, gain, max grade, and segments. Tests cover selection, validation, lookup, and serialization. | Partial | Add a richer route library/cards surface and docs for the route spec format when custom routes become user-facing. |
| Live metrics | Rider sees power, cadence, HR, speed, distance, elapsed time, mode/target. | Session cockpit displays core metrics. Snapshot model includes UI-neutral ride state. | Partial | Validate metric update smoothness, missing-data states, unit choices, and layout at riding distance and smaller screens. |
| Pause/stop lifecycle | Rider can pause/resume and stop without corrupting data. | Runtime and UI expose pause/stop. Controller stops and persists samples. | Partial | Add clearer paused visual state, stop confirmation if needed, post-ride summary, and explicit behavior for exit vs stop. |
| Persistence | Completed sessions and samples are saved locally. | Repository writes JSONL as source and SQLite for queries. Controller records samples and saves on stop. Tests cover repository behavior. | Ready | Add failure visibility in UI. Verify longer ride durability and duplicate/partial-write behavior. |
| History | Rider can see completed sessions. | History page lists repository sessions with responsive metric columns. Session detail shows summary metrics and supports CSV export and delete. Empty states exist. | Partial | Hardware-test longer histories and refine error/empty states where needed. Add future secondary detail panels such as charts, notes, route profile, or sample timeline after the core list is stable. |
| CSV export | Rider can export training data. | `DataExporter` supports per-session CSV, summary CSV, and auto-export. History exposes summary CSV export, and session detail/stop summary expose per-session CSV export when applicable. Tests cover CSV export. | Ready | Verify export file naming and destination copy in early-user docs. Consider FIT/TCX only after CSV feedback. |
| Rider settings | Rider can persist profile/defaults used by physics and metrics. | Settings shows Profile, Ride Defaults, Devices, and App Preferences together. It saves name, mass, FTP, max HR, age, default ERG target, default SIM route/grade, units, speed source, reconnect timeout, and auto-connect preferences. | Partial | Improve validation messaging and hardware-state recovery. Decide which advanced physics settings, if any, should become user-facing. |
| Analytics | Basic training metrics are available from stored data. | Repository summary calculates NP, IF, and TSS from samples. History table, session detail, and stop summary expose training metrics where data supports them. | Partial | Verify FTP assumptions and metric accuracy against known rides. Add explanatory labels only if early users need them. |
| 3D prototype | Experimental route/world surface proves future direction without blocking MVP. | `/ride3d` exists with Three.js, route selection, snapshot stream, device controls, and start/stop controls. Tests cover browser contracts. | Ready for prototype | Keep experimental label. Do not make it the MVP-critical surface. Use it to validate route contracts. |
| Snapshot/API contracts | Browser/3D clients consume runtime state without trainer internals. | `/api/ride/snapshot`, SSE snapshots, device endpoints, and 3D ride endpoints exist. | Ready | Keep contract stable or version changes. Add route/session metadata only through domain/application models. |
| Web Bluetooth | Browser-side BLE is optional/experimental. | `ble.js` exists and README describes limited support. Python/Bleak remains primary. | Defer | Keep out of MVP default. Document as experimental only. |
| Supabase auth/storage | Optional auth/storage exists but local-first remains default. | Supabase client/auth/repository/schema exist. README and roadmap mark it unfinished for production. | Defer | Do not require Supabase for MVP. Decide local-vs-cloud strategy before production persistence. |
| Prompt-generated routes/worlds | Future differentiator, not required for first launch. | Product exploration doc exists. Domain route profile abstraction is already emerging. No generator implementation. | Defer | Define route/world contracts later. Avoid prompt UI until route save/replay/validation is stable. |
| Integrations | Early users can at least get data out. | CSV export exists. No Strava/Garmin/etc. | Defer | Collect early feedback. Consider FIT/TCX/Strava only after core ride loop is stable. |
| Packaging/distribution | Early users can run the app with acceptable friction. | Dev setup only. No packaged app, installer, updater, or release artifacts. | Missing | Choose first distribution path: documented `uv` early access, script/launcher, or packaged desktop app. Add release checklist. |
| QA/release process | Release candidate has passing tests/format/lint and hardware smoke tests. | Tests exist across core domains. AGENTS requires pytest, black, ruff before committing. | Partial | Add MVP release checklist, manual hardware test matrix, and browser smoke test steps. |

## Recommended Build Order

1. Harden the non-3D cockpit ride loop: start, pause, stop, summary, and visible
   live/demo source state.
2. Make device pairing and failure recovery good enough for real trainer use.
3. Polish SIM route context in the main setup and live cockpit.
4. Harden history, session detail, delete, and CSV export against real ride data.
5. Improve settings validation and hardware-state recovery around FTP, units,
   ERG target, SIM defaults, speed source, and auto-connect.
6. Write first-run and troubleshooting docs for early users.
7. Run a hardware smoke-test pass and fix the high-friction failures.
8. Decide whether the first public release is `uv`-based early access, a simple
   launcher, or a packaged app.

## Open Decisions

- Should the first public name be fully `le-tour`, or should internal
  `terminalride` naming remain visible during early access?
- Is an `uv`-based early-access install acceptable for the first external users?
- What exact trainer models should be considered supported at launch?
- Is CSV export enough, or do early users expect FIT/TCX immediately?
- What additional SIM route context belongs in the live cockpit versus the
  pre-ride setup?
- What secondary session-detail panels matter first: chart, route profile,
  notes/tags, sample timeline, or export/history tools?
- What manual hardware test checklist must pass before calling a release
  launchable?
