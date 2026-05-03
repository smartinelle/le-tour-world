# Architecture Decision Records

This directory tracks the significant technical and product decisions that shape le-tour.

## How we use ADRs
- Start a new ADR whenever a change affects cross-cutting architecture, persistence, trainer/device integration, or user-facing workflows that other surfaces will need to honor.
- Use the template in `docs/adr/template.md`. Copy it to the next sequential number (e.g. `ADR-002.md`) and update the title, status, and sections.
- Keep ADRs concise but explicit: capture the context that led to the decision, the decision itself, the consequences, and any follow-up tasks.
- Reference ADRs in pull requests and other docs so future contributors understand why things are the way they are.
- Prefer updating an existing ADR with an "Amended" status if a decision changes rather than silently editing history.

## Index
- [ADR-001](ADR-001-primary-data-store-and-domain-boundaries.md): Current storage model and domain/UI boundaries
