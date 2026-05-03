# Contributing to le-tour

Thanks for helping improve le-tour. This project is early-access software, so
small, focused contributions are much easier to review than broad rewrites.

## Before You Start

- Open an issue or discussion before large feature work.
- Keep trainer control, ride state, persistence, and analytics independent from
  the web UI.
- Keep UI code in `le_tour/web` and domain logic in `le_tour/domain`.
- Do not add terminal UI surfaces; le-tour is web-first.

## Development Setup

```bash
uv sync
uv run python run_web.py
```

Open `http://127.0.0.1:8080`.

## Quality Checks

Run these before opening a pull request:

```bash
uv run pytest -q
uv run black --check le_tour tests run_web.py examples
uv run ruff check le_tour tests run_web.py examples
```

If you change typed core logic, also run:

```bash
uv run mypy le_tour
```

The current strict `mypy` target still has existing issues, so mention whether
your change adds, removes, or leaves those errors unchanged.

## Pull Request Guidelines

- Keep changes scoped to one problem.
- Add or update tests for behavior changes.
- Avoid unrelated formatting churn.
- Document hardware assumptions when touching BLE, FTMS, ERG, SIM, or HR code.
- Do not commit real `.env` files, tokens, ride data, or personal health data.

By contributing, you agree that your contribution may be distributed under the
project license, AGPL-3.0.
