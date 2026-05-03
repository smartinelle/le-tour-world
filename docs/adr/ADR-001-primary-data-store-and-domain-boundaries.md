# ADR-001: Primary Data Store and Domain Boundaries
- Status: Accepted
- Date: 2025-09-19

> Current direction update: this ADR was written while le-tour still had a
> Rich terminal UI. The terminal UI is now retired and should not be treated as a
> future product surface. The domain-boundary decision remains valid because the
> core must stay reusable for web, 3D browser, mobile/API, and headless
> workflows.

## Context
- At the time of this ADR, le-tour had to serve a Rich-based terminal UI
  while remaining portable to future surfaces. That specific UI requirement is
  now historical; portability remains important for web, 3D browser, mobile/API,
  and headless workflows.
- We collect high-frequency ride samples and session metadata that need durable, append-friendly storage on constrained machines.
- Early revisions stored trainer output inside UI flows without a shared persistence layer. Commits `8e3e7a1` (initial skeleton) and `4d4ca56` introduced the current repository and domain service boundaries to correct that coupling.
- We require fast querying for history/statistics views without giving up the robustness of append-only logs.

## Decision
- Keep `le_tour/domain` as the single owner of trainer orchestration and state: `TrainerService` wraps the FTMS client, publishes domain events, and exposes an API that does not depend on Rich or screen state.
- Use `TrainingRepository` as the persistence facade. It appends canonical session/sample records to JSONL files as the source of truth, and hydrates a local SQLite database for indexed lookups that power summaries and statistics.
- UI code consumes domain events and repository outputs but never reaches into
  BLE clients or filesystem implementations directly. The current UI lives in
  `le_tour/web`; the retired `le_tour/ui` package is historical only.
- CSV exports stay layered on top of the repository so future adapters (e.g., FIT/TCX exporters or remote sync) can reuse the same session graph.

## Consequences
- We get durability even if SQLite indices are corrupted; replaying JSONL keeps the data. However, we currently depend on manual intervention to trigger a rebuild when corruption happens.
- The UI can evolve (or be replaced) without breaking trainer control or storage semantics, as long as it honours the domain contracts.
- New storage backends (cloud sync, alternative databases) can slot behind the repository without disrupting higher layers.
- Domain-service indirection adds testing surface area—we need contract tests to ensure event sequencing remains stable when the BLE client changes.

## Follow-ups
- [ ] Automate SQLite rebuilds from JSONL when integrity checks fail, or document a maintenance script.
- [ ] Add integration tests that validate `TrainerService` emits domain events in the order the UI expects.
- [ ] Document guidance for adding new storage adapters (e.g., cloud sync) in the developer docs.

## References
- `8e3e7a1` Initial le-tour core implementation (UI-centric persistence)
- `4d4ca56` Domain/service refactor introducing repository and Rich decoupling
- `le_tour/store/repository.py`
- `le_tour/domain/trainer_service.py`
