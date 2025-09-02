# Agent Instructions

- Maintain a clear separation between frontend/UI code and backend/domain logic.
- Avoid coupling core functionality to the Rich terminal interface so we can migrate to a different UI in the future.
- When modifying code, prefer modular designs and abstractions that keep the UI replaceable.
- Run `python -m pytest -q` before committing to ensure tests pass.
- Format code with `black` and lint with `ruff` (line length 88).
- Keep type hints and the strict `mypy` config in mind.
- Use `rg` for searching; avoid expensive `grep -R` or `ls -R`.
- Core logic lives in `terminalride/domain`, while UI resides in `terminalride/ui`.
- This is a terminal-first indoor cycling app; design features so they can eventually power non-terminal interfaces.
