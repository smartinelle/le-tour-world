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
    # Text input handling
    input_mode: Optional[str] = None
    input_buffer: str = ""

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
        try:
            from ..store.repository import TrainingRepository
            self._repository = TrainingRepository()
        except Exception:
            self._repository = None

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
                Layout(self._render_stats_header(), name="header", size=4),
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
        """Render statistics header with totals across sessions."""
        total_time_s, total_dist_km = self._compute_totals()

        # Format time as HH:MM:SS
        h = int(total_time_s // 3600)
        m = int((total_time_s % 3600) // 60)
        s = int(total_time_s % 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"

        header = Text()
        header.append("Session History\n", style="bold blue")
        header.append("\nTotals: ")
        header.append(f"Time {time_str}", style="bold")
        header.append("  |  ")
        header.append(f"Distance {total_dist_km:.1f} km", style="bold")
        return Panel(Align.center(header), title="Statistics", border_style="blue")

    def _compute_totals(self) -> tuple[float, float]:
        """Compute total time (s) and distance (km) across sessions."""
        try:
            repository = getattr(self, "_repository", None)
            if not repository:
                from ..store.repository import TrainingRepository
                repository = TrainingRepository()
                self._repository = repository

            sessions = repository.list_sessions(limit=10000)
            total_time_s = 0.0
            total_dist_m = 0.0

            for sess in sessions:
                # Prefer stored values; fall back to summary if missing
                dur = sess.duration_s or 0.0
                dist_m = sess.total_distance_m or 0.0

                if (dur == 0.0 or dist_m == 0.0):
                    summary = repository.get_session_summary(sess.session_id)
                    if summary:
                        if dur == 0.0 and summary.duration_s is not None:
                            dur = summary.duration_s
                        if dist_m == 0.0 and summary.total_distance_m is not None:
                            dist_m = summary.total_distance_m

                total_time_s += dur or 0.0
                total_dist_m += dist_m or 0.0

            return total_time_s, (total_dist_m / 1000.0)
        except Exception:
            return 0.0, 0.0

    def _render_session_list(self, state: AppState) -> Panel:
        """Render list of recent sessions."""
        repository = getattr(self, "_repository", None)
        sessions = repository.list_sessions(limit=10) if repository else []
        
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
            summary = repository.get_session_summary(session.session_id) if repository else None
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
                Layout(
                    StatusBar().render(
                        state.status_message,
                        "connected" if state.devices.get("trainer", {}).get("connected", False) else "disconnected",
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

    def _render_settings_header(self) -> Panel:
        """Render settings header."""
        header_text = Text.assemble(
            ("Application Settings", "bold blue"),
            "\n\nConfigure TerminalRide preferences"
        )
        return Panel(Align.center(header_text), title="Settings", border_style="blue")

    def _render_settings_content(self) -> Panel:
        """Render settings content."""
        import logging
        from ..config import get_config

        cfg = get_config()
        s = cfg.settings

        table = Table.grid(padding=1)
        table.add_column("Setting", style="bold")
        table.add_column("Value", justify="left")

        # File locations
        table.add_row("Data Directory", str(cfg.get_data_dir()))

        # Logging (effective)
        level_name = logging.getLevelName(
            logging.getLogger("terminalride").getEffectiveLevel()
        )
        table.add_row("Log Level", str(level_name))

        # User profile
        table.add_row("Name", s.name)
        table.add_row("Mass", f"{s.mass_kg:.1f} kg")
        table.add_row("FTP", f"{s.ftp_w} W")

        # Physics defaults
        table.add_row("CdA", f"{s.cda_m2:.3f} m²")
        table.add_row("Crr", f"{s.crr:.4f}")

        # UI / behavior
        table.add_row("Units", s.units)
        table.add_row("Refresh Rate", f"{s.refresh_rate_hz} Hz")
        table.add_row("Show Legend", "on" if s.show_legend else "off")
        table.add_row("Speed Source", s.speed_source)

        # Device prefs
        table.add_row("Auto-connect Trainer", "on" if s.auto_connect_trainer else "off")
        table.add_row("Auto-connect HR", "on" if s.auto_connect_hr else "off")
        table.add_row("Reconnect Timeout", f"{s.reconnect_timeout_s} s")

        # Training defaults
        table.add_row("Default ERG Target", f"{s.default_erg_power_w} W")
        table.add_row("Default SIM Grade", f"{s.default_sim_grade_pct:+.1f} %")

        return Panel(table, title="Current Settings", border_style="green")

    def _render_settings_controls(self) -> Panel:
        """Render settings controls."""
        controls_text = """
[m] Modify mass (kg) — later
[f] Modify FTP (watts) — later
[t] Modify reconnect timeout — later
[r] Reset to defaults — later
[Esc] Back to home
        """
        return Panel(controls_text, title="Controls", border_style="cyan")

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle settings view keys."""
        if key == "escape":
            return ViewState.HOME
        # Editing not implemented yet; let legend/help explain
        if key in ["m", "f", "t", "r"]:
            state.status_message = "Settings modification not implemented yet"
            return None

        return None
