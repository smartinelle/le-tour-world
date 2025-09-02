# TerminalRide (Le-tour)

Terminal-first indoor cycling application for connecting to Wahoo KICKR and other BLE FTMS trainers.

## Features

- **BLE FTMS Support**: Connect to Wahoo KICKR and compatible trainers
- **Training Modes**: 
  - Free Ride: Natural cycling without constraints
  - ERG Mode: Target power training with PI controller
  - SIM Mode: Physics-based simulation with grade control
- **Terminal UI**: Rich-based TUI for full-screen experience
- **Data Persistence**: Session recording with JSONL/SQLite dual storage
- **CSV Export**: Export training data for analysis
- **Real-time Metrics**: Power, cadence, speed, distance, heart rate

## Installation

### Prerequisites

- Python 3.9+ 
- macOS/Linux (Windows support requires additional BLE stack configuration)
- BLE adapter for trainer connectivity

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd le-tour

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

### Starting the Application

```bash
python main.py
```

The app will:
1. Show startup screen
2. Scan for BLE FTMS trainers  
3. Connect automatically when found
4. Display home menu

### Navigation

**Home Menu:**
- `1` - Free Ride Mode
- `2` - ERG Mode (Target Power)  
- `3` - SIM Mode (Virtual Route)
- `d` - Device Management
- `s` - Statistics & History
- `c` - Settings
- `q` - Quit

**Training Views:**
- `Space` - Pause/Resume session
- `+/-` - Adjust target power (ERG mode)
- `↑/↓` - Change grade (SIM mode)  
- `l` - Mark lap
- `s` - Save & stop session
- `Esc` - Return to home

**General:**
- `?` - Toggle help overlay

### Training Modes

#### Free Ride
Natural cycling experience with no constraints. Pedal at your own pace while the app records all metrics.

#### ERG Mode  
Target power training using advanced PI controller:
- Set target power (100-400W)
- Trainer automatically adjusts resistance
- Maintains consistent power output
- Anti-windup and rate limiting for smooth control

#### SIM Mode
Physics-based cycling simulation:
- Realistic power/speed relationship
- Grade control (-10% to +15%)
- Accounts for rolling resistance, air resistance, and gravity
- Uses Newton's method for accurate speed calculations

### Data Management

#### Session Recording
- Automatic session creation when entering training modes
- Real-time sample recording (power, cadence, speed, distance)
- Session metadata (mode, duration, trainer info)

#### Data Storage
- Primary: JSONL format for data integrity
- Secondary: SQLite for fast queries and analysis
- Location: `~/.terminalride/` directory

#### Export Options
- CSV export for individual sessions
- Compatible with external analysis tools
- Session summaries with calculated metrics

## Architecture

### Core Components

- **`terminalride/app.py`** - Main application controller with async event loops
- **`terminalride/ui/views.py`** - Rich-based TUI views and navigation
- **`terminalride/devices/ftms_client.py`** - BLE FTMS protocol implementation
- **`terminalride/modes/`** - Training mode controllers (ERG/SIM)
- **`terminalride/store/`** - Data persistence and export

### Key Features

- **Protocol-oriented design** - Clean device abstractions
- **Async/await** - Non-blocking BLE communication and UI updates  
- **Type safety** - Comprehensive mypy type checking
- **Robust error handling** - Graceful degradation and recovery
- **Comprehensive testing** - Unit tests for all core functionality

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Code Quality

```bash
# Linting
ruff check .
ruff check . --fix  # Auto-fix issues

# Formatting  
black .

# Type checking
mypy .
```

### Testing with Real Hardware

1. Power on your FTMS trainer (e.g., Wahoo KICKR)
2. Ensure Bluetooth is enabled
3. Run the app - it will auto-discover and connect
4. Enter training mode and start pedaling
5. Data will be recorded automatically

### Demo Mode

If no trainer is found, the app runs in demo mode with simulated data for development and testing.

## Technical Details

### BLE FTMS Protocol

- Service UUID: `00001826-0000-1000-8000-00805f9b34fb`
- Indoor Bike Data: Real-time power, cadence, speed
- Control Point: ERG power control, SIM grade control
- Auto-reconnection with exponential backoff

### ERG Controller 

PI controller with:
- Proportional gain: 0.5
- Integral gain: 0.1  
- Anti-windup protection
- Rate limiting: ±2W/second
- Power range: 100-400W

### SIM Physics

Power balance equation:
```
P = 0.5 * ρ * CdA * v³ + m * g * Crr * v + m * g * sin(θ) * v + P₀
```

Where:
- ρ = air density (1.225 kg/m³)
- CdA = aerodynamic drag (0.4 m²)  
- m = rider mass (configurable)
- Crr = rolling resistance (0.0045)
- P₀ = drivetrain loss (10W)

## Configuration

Edit `~/.config/terminalride/config.json` (or via the in-app Settings view):

```json
{
    "name": "Rider",
    "age": 30,
    "gender": "male",
    "mass_kg": 75.0,
    "ftp_w": 250,
    "log_level": "info",
    "connection_timeout_s": 10.0
}
```

## Troubleshooting

### BLE Connection Issues

1. **Trainer not found**: Ensure trainer is in pairing mode
2. **Connection drops**: Check BLE adapter power management  
3. **Permission denied**: Run with sudo on some Linux distributions
4. **macOS permissions**: Grant Bluetooth access in System Preferences

### Performance Issues

1. **High CPU usage**: Reduce UI refresh rate in code
2. **Memory leaks**: Check for unclosed BLE connections
3. **Slow startup**: Clear old log files from data directory

### Data Issues

1. **Missing sessions**: Check `~/.terminalride/sessions.jsonl`
2. **Corrupt data**: SQLite auto-rebuilds from JSONL primary storage
3. **Export failures**: Verify write permissions in export directory

## Contributing

1. Fork the repository
2. Create feature branch
3. Ensure all tests pass
4. Add tests for new functionality  
5. Submit pull request

## License

[License information to be added]

## Acknowledgments

- Rich library for excellent TUI capabilities
- Bleak for cross-platform BLE support
- FTMS specification for standardized trainer communication
- Wahoo for creating robust training hardware