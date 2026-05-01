# Agent Instructions

- Maintain a clear separation between frontend/UI code and backend/domain logic.
- Avoid coupling core functionality to the Rich terminal interface so we can migrate to a different UI in the future.
- When modifying code, prefer modular designs and abstractions that keep the UI replaceable.
- Run `uv run pytest -q` before committing to ensure tests pass.
- Format code with `black` and lint with `ruff` (line length 88).
- Keep type hints and the strict `mypy` config in mind.
- Use `rg` for searching; avoid expensive `grep -R` or `ls -R`.
- Core logic lives in `terminalride/domain`, while the current UI resides in `terminalride/web`.
- This is a web-first indoor cycling app with a replaceable UI; design features so they can also power a future terminal UI or 3D browser interface.
