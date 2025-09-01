# Le-tour (TerminalRide) - Claude Memory

## Project Overview
- **Goal:** Terminal-first indoor cycling app (Zwift-lite) that connects to Wahoo KICKR via BLE FTMS
- **Stack:** Python 3.11, bleak (BLE), rich (TUI), numpy, pydantic, pytest
- **Modes:** Free Ride, ERG (constant power), SIM (grade-based resistance)
- **Data:** JSONL logging, CSV export, local persistence

## Key Constraints
- Temperature 0.1 (deterministic generation)
- Tests-first approach (TDD)
- No invented FTMS details - add TODO(FTMS: confirm...) markers
- Dependencies limited to: bleak, rich, numpy, pydantic, pytest
- Pure functions separated from I/O operations
- JSONL logging with stdlib only

## Success Criteria (MVP v0.1.0)
- KICKR connects via BLE in <5 seconds
- ERG mode responds to +/- keys in <2 seconds
- Live metrics display at 10Hz
- Session saves to JSONL and exports CSV
- UI navigation works intuitively (1/2/3, +/-, space, q, ?)
- Reconnects after brief disconnection
- All tests pass

## Development Commands
```bash
# Setup
python3.11 -m venv .venv && source .venv/bin/activate
pip install bleak rich numpy pydantic pytest mypy ruff black

# Testing & Quality
pytest -q
mypy --strict terminalride
ruff check terminalride
black terminalride
```

## Architecture Principles
- Protocol interfaces in devices/base.py
- FTMS parser as pure function (bit-field parsing)
- ERG PI controller: bounds [100,400]W, rate limit ±10W/5s, anti-windup
- SIM physics: power’speed solver with Newton/fixed-point method
- BLE I/O isolated from business logic

## Repository Structure
```
terminalride/
  docs/           # Documentation
  terminalride/   # Main package
    app.py        # State machine + router
    ui/           # Views and widgets
    devices/      # BLE FTMS client + parser
    modes/        # Free/ERG/SIM logic
    store/        # Persistence + export
  tests/          # Test suite
```

## Development Steps
1. **Setup:** Repo+CI+tests for parser/erg/physics
2. **Core Logic:** BLE client + ERG implementation
3. **Physics:** SIM physics + persistence+CSV
4. **Polish:** Hardening + packaging + v0.1.0 release