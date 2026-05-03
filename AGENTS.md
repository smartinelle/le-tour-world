# Agent Instructions

- Maintain a clear separation between frontend/UI code and backend/domain logic.
- Do not add or revive terminal UI surfaces; le-tour is web-first.
- When modifying code, prefer modular designs and abstractions that keep the UI replaceable.
- Run `uv run pytest -q` before committing to ensure tests pass.
- Format code with `black` and lint with `ruff` (line length 88).
- Keep type hints and the strict `mypy` config in mind.
- Use `rg` for searching; avoid expensive `grep -R` or `ls -R`.
- Core logic lives in `le_tour/domain`, while the current UI resides in `le_tour/web`.
- This is a web-first indoor cycling app with a replaceable UI; design features so they can also power richer browser/3D surfaces, API clients, mobile clients, and headless workflows.
