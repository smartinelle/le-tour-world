# Le-tour (TerminalRide) - Claude Memory

## Project Overview
- **Goal:** Terminal-first indoor cycling app (Zwift-lite) that connects to Wahoo KICKR via BLE FTMS
- **Stack:** Python 3.11+, bleak (BLE), rich (TUI), numpy, pydantic, pytest-asyncio
- **Modes:** Free Ride, ERG (constant power), SIM (grade-based resistance)
- **Data:** JSONL logging, CSV export, local persistence

## Key Constraints
- Temperature 0.1 (deterministic generation)
- Tests-first approach (TDD)
- No invented FTMS details - add TODO(FTMS: confirm...) markers
- Dependencies limited to: bleak, rich, numpy, pydantic, pytest, pytest-asyncio
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
pip install -e ".[dev]"

# Testing & Quality
pytest -q
mypy --strict terminalride
ruff check terminalride
black terminalride
```

## Architecture Principles
- Protocol interfaces in devices/base.py
- FTMS parser as pure function (bit-field parsing)
- ERG PI controller: bounds [100,400]W, rate limit �10W/5s, anti-windup
- SIM physics: power�speed solver with Newton/fixed-point method
- BLE I/O isolated from business logic

## Repository Structure
```
terminalride/
  docs/           # Documentation
  terminalride/   # Main package
    app.py        # State machine + router
    config.py     # Configuration management
    __main__.py   # Entry point
    logging_setup.py # Logging configuration
    ui/           # Views and widgets
      views.py    # Rich-based TUI views
      widgets.py  # Reusable UI components
      keymap.py   # Keyboard bindings
    devices/      # BLE device clients + parsers
      base.py     # Protocol interfaces
      ftms_client.py  # FTMS trainer BLE client
      ftms_parse.py   # FTMS frame parser
      hr_client.py    # Heart rate BLE client
      hr_parse.py     # HR measurement parser
    modes/        # Free/ERG/SIM logic
      erg.py      # ERG mode implementation
      sim.py      # SIM mode implementation
    domain/       # Business logic
      events.py   # Event definitions
      state.py    # Application state
      trainer_service.py  # Trainer service
      hr_service.py       # Heart rate service
      session_service.py  # Session persistence service
    store/        # Persistence + export
      models.py   # Data models
      repository.py   # Data access
      export.py   # CSV export
    analytics/    # Training metrics (NP, IF, TSS)
      metrics.py  # Normalized Power, Intensity Factor, TSS calculations
  tests/          # Test suite
```

## Development Steps - COMPLETED ✅
1. **Setup:** Repo+CI+tests for parser/erg/physics ✅
2. **Core Logic:** BLE client + ERG implementation ✅
3. **Physics:** SIM physics + persistence+CSV ✅
4. **Polish:** Hardening + packaging + v0.1.0 release ✅

## CURRENT STATUS: MVP v0.1.0 - COMPLETE ✅

### Project Implementation Summary:
- **Core components implemented and fully tested (112 tests passing)**
- **Full BLE FTMS protocol support with Wahoo KICKR compatibility**
- **Complete TUI with all training modes (Free/ERG/SIM)**
- **Data persistence with store module (models, repository, export)**
- **CSV export functionality**
- **Domain-driven architecture with events, trainer service, and session service**
- **Comprehensive documentation (README.md, ADRs)**

### Key Achievements:
- ERG mode with advanced PI controller (anti-windup, rate limiting)
- SIM mode with Newton's method physics solver
- Real-time metrics display at 10Hz
- Robust error handling and auto-reconnection
- Clean architecture with protocol-oriented design
- Type-safe implementation with mypy compliance
- Modern packaging with pyproject.toml
- SessionService layer decoupling UI from storage
- Analytics module with NP/IF/TSS calculations
- Heart rate monitor support (Wahoo TICKR, Garmin HRM, Polar, etc.)
- Manual device selection (scan, list, and choose specific devices)

**PROJECT STATUS: MVP v0.1.0 COMPLETE** ✅