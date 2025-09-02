"""TUI views for different application screens."""

import time
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table

from .widgets import MetricsDisplay, StatusBar, HelpOverlay, DeviceList, LegendPanel
from .keymap import condensed_line


class ViewState(Enum):
    """Application view states."""

    STARTUP = "startup"
    CONNECT = "connect"
    HOME = "home"
    LIVE_FREE = "live_free"
    LIVE_ERG = "live_erg"
    LIVE_SIM = "live_sim"
    DEVICES = "devices"
    STATS = "stats"
    SETTINGS = "settings"


@dataclass
class AppState:
    """Application state container."""

    # Current view
    current_view: ViewState = ViewState.STARTUP

    # Training session
    session_active: bool = False
    session_paused: bool = False
    session_start_time: Optional[float] = None

    # Live metrics
    metrics: Optional[Dict[str, Any]] = None

    # Devices
    devices: Optional[Dict[str, Dict[str, Any]]] = None

    # UI state
    show_help: bool = False
    show_legend: bool = False
    status_message: str = "Starting up..."

    def __post_init__(self) -> None:
        if self.metrics is None:
            self.metrics = {}
        if self.devices is None:
            self.devices = {}


class BaseView:
    """Base class for TUI views."""

    def __init__(self) -> None:
        self.console = Console()
        self.layout = Layout()

    def render(self, state: AppState) -> Layout:
        """Render the view with current app state.

        Args:
            state: Current application state

        Returns:
            Rich Layout ready for display
        """
        raise NotImplementedError

    def handle_key(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle keyboard input.

        Args:
            key: Key pressed
            state: Current application state

        Returns:
            New view state if transition needed, None otherwise
        """
        # Common keys for all views
        if key == "?":
            state.show_help = not state.show_help
            return None
        if key == "l":
            state.show_legend = not state.show_legend
            return None

        return self._handle_key_impl(key, state)

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """View-specific key handling implementation."""
        return None

    def _with_legend(self, content: Layout, state: AppState, live: bool = False) -> Layout:
        """Wrap content with a right-side legend when enabled."""
        if not state.show_legend:
            self.layout = content
            return self.layout

        wrapper = Layout()
        devices = state.devices or {}
        legend = LegendPanel().render(
            current_view=state.current_view.value,
            connected=devices.get("trainer", {}).get("connected", False),
            in_live=live,
        )
        wrapper.split_row(
            Layout(content, name="content"),
            Layout(legend, name="legend", size=30),
        )
        self.layout = wrapper
        return self.layout


class StartupView(BaseView):
    """Startup/splash screen view."""

    def render(self, state: AppState) -> Layout:
        """Render startup view."""
        main = Layout()
        main.split_column(
            Layout(self._render_splash(), name="splash"),
            Layout(StatusBar().render(state.status_message), name="status", size=3),
        )
        return self._with_legend(main, state)

    def _render_splash(self) -> Panel:
        """Render splash screen."""
        splash_text = """
╔╦╗┌─┐┬─┐┌┬┐┬┌┐┌┌─┐┬  ╦═╗┬┌┬┐┌─┐
 ║ ├┤ ├┬┘│││││││├─┤│  ╠╦╝│ ││ ├┤ 
 ╩ └─┘┴└─┴ ┴┴┘└┘┴ ┴┴─┘╩╚═┴─┴┘ └─┘

Terminal-first indoor cycling app
        """

        return Panel(
            Align.center(Text(splash_text, style="bold blue")),
            title="Welcome",
            border_style="blue",
        )


class ConnectView(BaseView):
    """Device connection view."""

    def render(self, state: AppState) -> Layout:
        """Render connection view."""
        main = Layout()
        main.split_column(
            Layout(self._render_connection_status(state), name="connect"),
            Layout(StatusBar().render(state.status_message), name="status", size=3),
        )
        return self._with_legend(main, state)

    def _render_connection_status(self, state: AppState) -> Panel:
        """Render connection status."""
        devices = state.devices or {}
        if not devices.get("trainer", {}).get("connected", False):
            status_text = (
                "Scanning for trainer devices...\n\nPress 'r' to retry or 'q' to quit"
            )
        else:
            status_text = "Trainer connected!\n\nPress any key to continue"

        return Panel(
            Align.center(Text(status_text)),
            title="Device Connection",
            border_style="yellow",
        )

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle connection view keys."""
        if key == "r":
            state.status_message = "Retrying connection..."
            return None
        elif key == "q":
            return None  # Will be handled by app to quit
        elif state.devices.get("trainer", {}).get("connected", False):
            return ViewState.HOME
        return None


class HomeView(BaseView):
    """Main menu/home view."""

    def render(self, state: AppState) -> Layout:
        """Render home view."""
        main = Layout()
        if state.show_help:
            main.split_column(
                Layout(HelpOverlay().render("home"), name="help"),
                Layout(
                    StatusBar().render(
                        state.status_message, self._get_connection_status(state)
                    ),
                    name="status",
                    size=3,
                ),
            )
        else:
            main.split_column(
                Layout(self._render_home_menu(state), name="home"),
                Layout(DeviceList().render(state.devices), name="devices"),
                Layout(
                    StatusBar().render(
                        state.status_message,
                        self._get_connection_status(state),
                        hints_line=condensed_line(
                            state.current_view.value,
                            state.devices.get("trainer", {}).get("connected", False),
                        ),
                    ),
                    name="status",
                    size=3,
                ),
            )
        return self._with_legend(main, state)

    def _render_home_menu(self, state: AppState) -> Panel:
        """Render home menu options."""
        menu_text = """
[bold cyan]Training Modes:[/bold cyan]
  [1] Free Ride
  [2] ERG Mode (Target Power)
  [3] SIM Mode (Virtual Route)

[bold cyan]Options:[/bold cyan]
  [d] Device Management
  [s] Statistics
  [c] Settings
  [q] Quit
        """

        return Panel(menu_text, title="TerminalRide", border_style="blue")

    def _get_connection_status(self, state: AppState) -> str:
        """Get connection status string."""
        if state.devices.get("trainer", {}).get("connected", False):
            return "connected"
        return "disconnected"

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle home view keys."""
        if not state.devices.get("trainer", {}).get("connected", False):
            state.status_message = "Connect trainer first"
            return None

        if key == "1":
            return ViewState.LIVE_FREE
        elif key == "2":
            return ViewState.LIVE_ERG
        elif key == "3":
            return ViewState.LIVE_SIM
        elif key == "d":
            return ViewState.DEVICES
        elif key == "s":
            return ViewState.STATS
        elif key == "c":
            return ViewState.SETTINGS
        elif key == "q":
            return None  # Will be handled by app to quit

        return None


class LiveView(BaseView):
    """Live training view (base class for Free/ERG/SIM)."""

    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode
        self.metrics_display = MetricsDisplay()

    def render(self, state: AppState) -> Layout:
        """Render live training view."""
        main = Layout()
        if state.show_help:
            main.split_column(
                Layout(HelpOverlay().render(self.mode), name="help"),
                Layout(
                    StatusBar().render(state.status_message, "connected"),
                    name="status",
                    size=3,
                ),
            )
        else:
            # Calculate session time
            if state.session_start_time and not state.session_paused:
                state.metrics["time_s"] = time.time() - state.session_start_time

            main.split_column(
                Layout(
                    self.metrics_display.render(state.metrics, self.mode),
                    name="metrics",
                ),
                Layout(self._render_mode_controls(state), name="controls", size=8),
                Layout(
                    StatusBar().render(
                        self._get_status(state),
                        "connected",
                        hints_line=condensed_line(
                            f"live_{self.mode}",
                            True,
                        ),
                    ),
                    name="status",
                    size=3,
                ),
            )
        return self._with_legend(main, state, live=True)

    def _render_mode_controls(self, state: AppState) -> Panel:
        """Render mode-specific controls."""
        if self.mode == "erg":
            target_power = state.metrics.get("target_power_w", 150)
            controls_text = f"""
Target Power: {target_power} W

[+/-] Adjust target power
[Space] {"Resume" if state.session_paused else "Pause"}
[L] Mark lap  [s] Save & stop  [Esc] Home
            """
        elif self.mode == "sim":
            grade_pct = state.metrics.get("grade_pct", 0.0)
            controls_text = f"""
Road Grade: {grade_pct:+4.1f} %

[↑/↓] Adjust grade
[Space] {"Resume" if state.session_paused else "Pause"}  
[L] Mark lap  [s] Save & stop  [Esc] Home
            """
        else:  # free mode
            controls_text = """
Free Ride Mode

[Space] {"Resume" if state.session_paused else "Pause"}
[L] Mark lap  [s] Save & stop  [Esc] Home
            """

        return Panel(
            controls_text, title=f"{self.mode.upper()} Controls", border_style="cyan"
        )

    def _get_status(self, state: AppState) -> str:
        """Get training status message."""
        if state.session_paused:
            return "Session paused"
        return f"{self.mode.title()} mode active"

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle live view keys."""
        if key == " ":  # Space - pause/resume
            state.session_paused = not state.session_paused
            return None
        elif key == "L":  # Mark lap (Shift+L)
            state.status_message = "Lap marked"
            return None
        elif key == "s":  # Save and stop
            state.session_active = False
            state.status_message = "Session saved"
            return ViewState.HOME
        elif key == "escape":  # Return to home
            state.session_active = False
            return ViewState.HOME
        elif self.mode == "erg" and key in ["+", "="]:
            # Increase target power
            current = state.metrics.get("target_power_w", 150)
            state.metrics["target_power_w"] = min(400, current + 5)
            return None
        elif self.mode == "erg" and key == "-":
            # Decrease target power
            current = state.metrics.get("target_power_w", 150)
            state.metrics["target_power_w"] = max(100, current - 5)
            return None
        elif self.mode == "sim" and key == "up":
            # Increase grade
            current = state.metrics.get("grade_pct", 0.0)
            state.metrics["grade_pct"] = min(15.0, current + 0.5)
            return None
        elif self.mode == "sim" and key == "down":
            # Decrease grade
            current = state.metrics.get("grade_pct", 0.0)
            state.metrics["grade_pct"] = max(-10.0, current - 0.5)
            return None

        return None


class DevicesView(BaseView):
    """Device management view."""

    def render(self, state: AppState) -> Layout:
        """Render devices view."""
        main = Layout()
        main.split_column(
            Layout(DeviceList().render(state.devices), name="devices"),
            Layout(self._render_device_controls(), name="controls"),
            Layout(
                StatusBar().render(
                    state.status_message,
                    self._get_connection_status(state),
                    hints_line=condensed_line(
                        state.current_view.value,
                        state.devices.get("trainer", {}).get("connected", False),
                    ),
                ),
                name="status",
                size=3,
            ),
        )
        return self._with_legend(main, state)

    def _render_device_controls(self) -> Panel:
        """Render device control panel."""
        controls_text = """
[r] Rescan for devices
[c] Connect/Disconnect trainer
[h] Connect/Disconnect heart rate  
[Esc] Back to home
        """

        return Panel(controls_text, title="Device Controls", border_style="blue")

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle devices view keys."""
        if key == "escape":
            return ViewState.HOME
        elif key == "r":
            state.status_message = "Scanning for devices..."
            return None
        elif key == "c":
            state.status_message = "Toggling trainer connection..."
            return None
        elif key == "h":
            state.status_message = "Toggling HR connection..."
            return None

        return None


# Create view instances for each mode
class FreeView(LiveView):
    def __init__(self) -> None:
        super().__init__("free")


class ErgView(LiveView):
    def __init__(self) -> None:
        super().__init__("erg")


class SimView(LiveView):
    def __init__(self) -> None:
        super().__init__("sim")


class StatsView(BaseView):
    """Statistics and session history view."""

    def __init__(self) -> None:
        super().__init__()

    def render(self, state: AppState) -> Layout:
        """Render statistics view."""
        main = Layout()
        if state.show_help:
            main.split_column(
                Layout(HelpOverlay().render("stats"), name="help"),
                Layout(
                    StatusBar().render(state.status_message, "connected"),
                    name="status",
                    size=3,
                ),
            )
        else:
            main.split_column(
                Layout(self._render_stats_header(), name="header", size=3),
                Layout(self._render_session_list(state), name="sessions"),
                Layout(self._render_stats_controls(), name="controls", size=6),
                Layout(
                    StatusBar().render(
                        state.status_message,
                        "connected",
                        hints_line=condensed_line(state.current_view.value, True),
                    ),
                    name="status",
                    size=3,
                ),
            )
        return self._with_legend(main, state)

    def _render_stats_header(self) -> Panel:
        """Render statistics header."""
        header_text = Text.assemble(
            ("Session History", "bold blue"),
            "\n\nRecent training sessions and performance data"
        )
        return Panel(Align.center(header_text), title="Statistics", border_style="blue")

    def _render_session_list(self, state: AppState) -> Panel:
        """Render list of recent sessions."""
        from ..store.repository import TrainingRepository
        
        # Get session data from repository
        repository = TrainingRepository()
        sessions = repository.list_sessions(limit=10)
        
        if not sessions:
            content = Text("No training sessions found.\nComplete some workouts to see statistics here!", 
                          style="dim", justify="center")
            return Panel(content, title="Recent Sessions", border_style="yellow")

        # Create sessions table
        table = Table()
        table.add_column("Date", style="cyan")
        table.add_column("Mode", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Distance", justify="right")
        table.add_column("Avg Power", justify="right")
        table.add_column("Max Power", justify="right")

        for session in sessions:
            # Format session data
            date_str = session.start_time.strftime("%m/%d %H:%M")
            duration_str = self._format_duration(session.duration_s or 0)
            distance_str = f"{(session.total_distance_m or 0) / 1000:.1f} km"
            
            # Get session summary for additional stats
            summary = repository.get_session_summary(session.session_id)
            avg_power = f"{summary.avg_power_w:.0f} W" if summary and summary.avg_power_w else "--- W"
            max_power = f"{summary.max_power_w} W" if summary and summary.max_power_w else "--- W"
            
            table.add_row(
                date_str,
                session.mode.value.upper(),
                duration_str,
                distance_str,
                avg_power,
                max_power,
            )

        return Panel(table, title="Recent Sessions", border_style="green")

    def _render_stats_controls(self) -> Panel:
        """Render statistics controls."""
        controls_text = """
[e] Export latest session to CSV
[a] Export all sessions to CSV
[d] Delete session
[Esc] Back to home
        """
        return Panel(controls_text, title="Controls", border_style="cyan")

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle statistics view keys."""
        if key == "escape":
            return ViewState.HOME
        elif key == "e":
            state.status_message = "Export feature not implemented yet"
            return None
        elif key == "a":
            state.status_message = "Export all feature not implemented yet"
            return None
        elif key == "d":
            state.status_message = "Delete feature not implemented yet"
            return None

        return None


class SettingsView(BaseView):
    """Application settings view."""

    def __init__(self) -> None:
        super().__init__()

    def render(self, state: AppState) -> Layout:
        """Render settings view."""
        main = Layout()
        if state.show_help:
            main.split_column(
                Layout(HelpOverlay().render("settings"), name="help"),
                Layout(
                    StatusBar().render(state.status_message),
                    name="status",
                    size=3,
                ),
            )
        else:
            main.split_column(
                Layout(self._render_settings_header(), name="header", size=3),
                Layout(self._render_settings_content(), name="settings"),
                Layout(self._render_settings_controls(), name="controls", size=8),
                Layout(StatusBar().render(
                    state.status_message,
                    self._get_connection_status(state),
                    hints_line=condensed_line(
                        state.current_view.value,
                        state.devices.get("trainer", {}).get("connected", False),
                    ),
                ), name="status", size=3),
            )
        return self._with_legend(main, state)

    def _render_settings_header(self) -> Panel:
        """Render settings header."""
        header_text = Text.assemble(
            ("Application Settings", "bold blue"),
            "\n\nConfigure TerminalRide preferences"
        )
        return Panel(Align.center(header_text), title="Settings", border_style="blue")

    def _render_settings_content(self) -> Panel:
        """Render settings content."""
        from ..config import get_config
        
        config = get_config()
        table = Table.grid(padding=1)
        table.add_column("Setting", style="bold")
        table.add_column("Value", justify="left")

        # Display user profile
        ftp_display = (
            f"{config.settings.ftp_w} W" if config.settings.ftp_w is not None else "Not set"
        )
        table.add_row("Name", config.settings.name)
        table.add_row("Age", f"{config.settings.age}")
        table.add_row("Gender", config.settings.gender.title())
        table.add_row("Weight", f"{config.user_mass_kg} kg")
        table.add_row("FTP", ftp_display)

        table.add_row("---", "---")
        # Display other configuration
        table.add_row("Data Directory", str(config.get_data_dir()))
        table.add_row("Log Level", config.log_level.upper())
        table.add_row("Connection Timeout", f"{config.connection_timeout_s} s")

        return Panel(table, title="Current Settings", border_style="green")

    def _render_settings_controls(self) -> Panel:
        """Render settings controls."""
        controls_text = """
[n] Modify name
[a] Modify age
[g] Modify gender (male/female)
[m] Modify weight (kg)
[f] Modify FTP (watts)
[t] Modify connection timeout
[l] Change log level
[r] Reset to defaults
[Esc] Back to home
        """
        return Panel(controls_text, title="Controls", border_style="cyan")

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle settings view keys."""
        if key == "escape":
            return ViewState.HOME

        from ..config import get_config

        config = get_config()
        if key == "n":
            name = input("Enter name: ").strip()
            if name:
                config.settings.name = name
                config.save_settings()
                state.status_message = "Name updated"
            else:
                state.status_message = "Name not changed"
        elif key == "a":
            try:
                age = int(input("Enter age: ").strip())
                config.settings.age = age
                config.save_settings()
                state.status_message = "Age updated"
            except Exception:
                state.status_message = "Invalid age"
        elif key == "g":
            gender = input("Enter gender (male/female): ").strip().lower()
            if gender in ["male", "female"]:
                config.settings.gender = gender
                config.save_settings()
                state.status_message = "Gender updated"
            else:
                state.status_message = "Invalid gender"
        elif key == "m":
            try:
                mass = float(input("Enter weight (kg): ").strip())
                config.settings.mass_kg = mass
                config.user_mass_kg = mass
                config.save_settings()
                state.status_message = "Weight updated"
            except Exception:
                state.status_message = "Invalid weight"
        elif key == "f":
            val = input("Enter FTP (watts, blank to unset): ").strip()
            if val == "":
                config.settings.ftp_w = None
                config.user_ftp_w = 250
                config.save_settings()
                state.status_message = "FTP cleared"
            else:
                try:
                    ftp = int(val)
                    config.settings.ftp_w = ftp
                    config.user_ftp_w = ftp
                    config.save_settings()
                    state.status_message = "FTP updated"
                except Exception:
                    state.status_message = "Invalid FTP"
        elif key in ["t", "l", "r"]:
            state.status_message = "Settings modification not implemented yet"

        return None
