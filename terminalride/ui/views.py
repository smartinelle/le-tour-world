"""TUI views for different application screens."""

import time
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table

from ..config import get_config
from ..domain.session_service import get_session_service

from .widgets import (
    MetricsDisplay,
    AverageMetricsDisplay,
    StatusBar,
    HelpOverlay,
    DeviceList,
    LegendPanel,
    DistanceProgressBar,
)
from .keymap import condensed_line


logger = logging.getLogger(__name__)


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
    SUMMARY = "summary"


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

    # Devices (connected)
    devices: Optional[Dict[str, Dict[str, Any]]] = None

    # Available devices (from scan)
    available_trainers: Optional[list] = None
    available_hr: Optional[list] = None
    scanning_trainers: bool = False
    scanning_hr: bool = False

    # UI state
    show_help: bool = False
    show_legend: bool = False
    status_message: str = "Starting up..."
    # Text input handling
    input_mode: Optional[str] = None
    input_buffer: str = ""

    # Last saved/finished session id for summary
    last_session_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.metrics is None:
            self.metrics = {}
        if self.devices is None:
            self.devices = {}
        if self.available_trainers is None:
            self.available_trainers = []
        if self.available_hr is None:
            self.available_hr = []


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
        # Handle help overlay: Esc or ? closes it
        if state.show_help:
            if key in ("?", "escape"):
                state.show_help = False
                return None
            # While help is shown, ignore other keys
            return None

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

    def _with_legend(
        self, content: Layout, state: AppState, live: bool = False
    ) -> Layout:
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
        connected = state.devices.get("trainer", {}).get("connected", False)

        # Training modes - grayed out if not connected
        mode_style = "" if connected else "[dim]"
        mode_end = "" if connected else "[/dim]"

        menu = Text()
        menu.append("Training Modes:\n", style="bold cyan")
        menu.append(f"  {mode_style}[1] Free Ride{mode_end}\n")
        menu.append(f"  {mode_style}[2] ERG Mode (Target Power){mode_end}\n")
        menu.append(f"  {mode_style}[3] SIM Mode (Virtual Route){mode_end}\n")
        menu.append("\n")
        menu.append("Options:\n", style="bold cyan")
        menu.append("  [d] Device Management\n")
        menu.append("  [s] Statistics\n")
        menu.append("  [c] Settings\n")
        menu.append("  [q] Quit\n")

        return Panel(menu, title="TerminalRide", border_style="blue")

    def _get_connection_status(self, state: AppState) -> str:
        """Get connection status string."""
        if state.devices.get("trainer", {}).get("connected", False):
            return "connected"
        return "disconnected"

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle home view keys."""
        connected = state.devices.get("trainer", {}).get("connected", False)

        # Training modes require trainer connection
        if key in ("1", "2", "3"):
            if not connected:
                state.status_message = "Connect trainer first (press 'd' for devices)"
                return None
            if key == "1":
                return ViewState.LIVE_FREE
            elif key == "2":
                return ViewState.LIVE_ERG
            elif key == "3":
                return ViewState.LIVE_SIM

        # Options - always available
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
        self.avg_display = AverageMetricsDisplay()

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

            # Build side-by-side metrics panels
            metrics_row = Layout()
            metrics_row.split_row(
                Layout(
                    self.metrics_display.render(state.metrics, self.mode),
                    name="metrics_live",
                ),
                Layout(self.avg_display.render(state.metrics), name="metrics_avg"),
            )

            progress = DistanceProgressBar().render(state.metrics)

            main.split_column(
                Layout(metrics_row, name="metrics"),
                Layout(progress, name="progress", size=4),
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
        # Compact, structured controls
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left")
        table.add_column(justify="left")

        common = f"Space: {'Resume' if state.session_paused else 'Pause'}   L: Lap   s: Save & Summary   Esc: Home"
        if self.mode == "erg":
            target_power = state.metrics.get("target_power_w", 150)
            table.add_row("Mode", f"ERG  (Target {target_power} W)")
            table.add_row("Adjust", "+ / - : Target Power")
        elif self.mode == "sim":
            grade_pct = state.metrics.get("grade_pct", 0.0)
            table.add_row("Mode", f"SIM  (Grade {grade_pct:+.1f} %)")
            table.add_row("Adjust", "↑ / ↓ : Grade")
        else:
            table.add_row("Mode", "FREE")
            table.add_row("Adjust", "—")

        table.add_row("", common)
        return Panel(table, title=f"{self.mode.upper()} Controls", border_style="cyan")

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
        elif key == "s":  # Finish and show summary
            state.session_active = False
            state.status_message = "Finishing session..."
            return ViewState.SUMMARY
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
    """Device management view with manual device selection."""

    def render(self, state: AppState) -> Layout:
        """Render devices view."""
        main = Layout()
        main.split_column(
            Layout(self._render_connected_devices(state), name="connected", size=6),
            Layout(self._render_available_devices(state), name="available"),
            Layout(self._render_device_controls(state), name="controls", size=7),
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

    def _render_connected_devices(self, state: AppState) -> Panel:
        """Render currently connected devices."""
        table = Table.grid(padding=(0, 2))
        table.add_column("Type", style="bold")
        table.add_column("Device")
        table.add_column("Status")

        # Trainer
        trainer = state.devices.get("trainer", {})
        if trainer.get("connected"):
            trainer_status = Text("● Connected", style="green")
            trainer_name = trainer.get("name", "Unknown")
        else:
            trainer_status = Text("○ Not connected", style="dim")
            trainer_name = "—"
        table.add_row("Trainer", trainer_name, trainer_status)

        # HR Monitor
        hr = state.devices.get("hr", {})
        if hr.get("connected"):
            hr_status = Text("● Connected", style="green")
            hr_name = hr.get("name", "Unknown")
        else:
            hr_status = Text("○ Not connected", style="dim")
            hr_name = "—"
        table.add_row("HR Monitor", hr_name, hr_status)

        return Panel(table, title="Connected Devices", border_style="green")

    def _render_available_devices(self, state: AppState) -> Panel:
        """Render available devices from scan."""
        layout = Layout()
        layout.split_row(
            Layout(self._render_trainer_list(state), name="trainers"),
            Layout(self._render_hr_list(state), name="hr"),
        )
        return Panel(layout, title="Available Devices", border_style="cyan")

    def _render_trainer_list(self, state: AppState) -> Panel:
        """Render list of available trainers."""
        if state.scanning_trainers:
            content = Text("Scanning...", style="yellow italic")
        elif not state.available_trainers:
            content = Text("No trainers found.\nPress [t] to scan.", style="dim")
        else:
            table = Table.grid(padding=(0, 1))
            table.add_column("Key", style="bold cyan")
            table.add_column("Name")
            table.add_column("Signal", justify="right")

            for i, device in enumerate(state.available_trainers[:9], 1):
                name = device.get("name", "Unknown")[:20]
                rssi = device.get("rssi")
                signal = f"{rssi} dBm" if rssi else "—"
                table.add_row(f"[{i}]", name, signal)

            content = table

        return Panel(content, title="Trainers [t]", border_style="blue")

    def _render_hr_list(self, state: AppState) -> Panel:
        """Render list of available HR monitors."""
        if state.scanning_hr:
            content = Text("Scanning...", style="yellow italic")
        elif not state.available_hr:
            content = Text("No HR monitors found.\nPress [h] to scan.", style="dim")
        else:
            table = Table.grid(padding=(0, 1))
            table.add_column("Key", style="bold cyan")
            table.add_column("Name")
            table.add_column("Signal", justify="right")

            # Use letters a-i for HR monitors
            for i, device in enumerate(state.available_hr[:9]):
                key = chr(ord('a') + i)
                name = device.get("name", "Unknown")[:20]
                rssi = device.get("rssi")
                signal = f"{rssi} dBm" if rssi else "—"
                table.add_row(f"[{key}]", name, signal)

            content = table

        return Panel(content, title="HR Monitors [h]", border_style="magenta")

    def _render_device_controls(self, state: AppState) -> Panel:
        """Render device control panel."""
        controls = Text()
        controls.append("Scan:  ", style="bold")
        controls.append("[t] Trainers  [h] HR Monitors\n")
        controls.append("Connect:  ", style="bold")
        controls.append("[1-9] Select trainer  [a-i] Select HR\n")
        controls.append("Disconnect:  ", style="bold")
        controls.append("[T] Trainer  [H] HR Monitor\n")
        controls.append("Navigation:  ", style="bold")
        controls.append("[Esc] Back to home")

        return Panel(controls, title="Controls", border_style="blue")

    def _get_connection_status(self, state: AppState) -> str:
        """Get connection status string."""
        trainer_connected = state.devices.get("trainer", {}).get("connected", False)
        hr_connected = state.devices.get("hr", {}).get("connected", False)

        if trainer_connected and hr_connected:
            return "all connected"
        elif trainer_connected:
            return "trainer only"
        elif hr_connected:
            return "HR only"
        return "disconnected"

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        """Handle devices view keys."""
        if key == "escape":
            return ViewState.HOME

        # Scan commands
        elif key == "t":
            state.status_message = "Scanning for trainers..."
            state.scanning_trainers = True
            # Actual scan will be triggered by app controller
            return None
        elif key == "h":
            state.status_message = "Scanning for HR monitors..."
            state.scanning_hr = True
            return None

        # Trainer selection (1-9)
        elif key.isdigit() and key != "0":
            idx = int(key) - 1
            if idx < len(state.available_trainers or []):
                device = state.available_trainers[idx]
                state.status_message = f"Connecting to {device.get('name', 'trainer')}..."
                # Store selection for app controller to process
                state.devices["_pending_trainer"] = device
            else:
                state.status_message = "Invalid selection"
            return None

        # HR selection (a-i)
        elif key.lower() in "abcdefghi" and key.islower():
            idx = ord(key.lower()) - ord('a')
            if idx < len(state.available_hr or []):
                device = state.available_hr[idx]
                state.status_message = f"Connecting to {device.get('name', 'HR')}..."
                state.devices["_pending_hr"] = device
            else:
                state.status_message = "Invalid selection"
            return None

        # Disconnect commands (uppercase)
        elif key == "T":
            if state.devices.get("trainer", {}).get("connected"):
                state.status_message = "Disconnecting trainer..."
                state.devices["_disconnect_trainer"] = True
            return None
        elif key == "H":
            if state.devices.get("hr", {}).get("connected"):
                state.status_message = "Disconnecting HR..."
                state.devices["_disconnect_hr"] = True
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
        self._session_service = get_session_service()

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
            sessions = self._session_service.list_sessions(limit=10000)
            total_time_s = 0.0
            total_dist_m = 0.0

            for sess in sessions:
                # Prefer stored values; fall back to summary if missing
                dur = sess.duration_s or 0.0
                dist_m = sess.total_distance_m or 0.0

                if dur == 0.0 or dist_m == 0.0:
                    summary = self._session_service.get_session_summary(sess.session_id)
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
        sessions = self._session_service.list_sessions(limit=10)

        if not sessions:
            content = Text(
                "No training sessions found.\nComplete some workouts to see statistics here!",
                style="dim",
                justify="center",
            )
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
            summary = self._session_service.get_session_summary(session.session_id)
            avg_power = (
                f"{summary.avg_power_w:.0f} W"
                if summary and summary.avg_power_w
                else "--- W"
            )
            max_power = (
                f"{summary.max_power_w} W"
                if summary and summary.max_power_w
                else "--- W"
            )

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
                        (
                            "connected"
                            if state.devices.get("trainer", {}).get("connected", False)
                            else "disconnected"
                        ),
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
            "\n\nConfigure TerminalRide preferences",
        )
        return Panel(Align.center(header_text), title="Settings", border_style="blue")

    def _render_settings_content(self) -> Panel:
        """Render settings content."""
        import logging

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


class SummaryView(BaseView):
    """End-of-ride summary with save/discard choice."""

    def __init__(self) -> None:
        super().__init__()
        self._session_service = get_session_service()

    def render(self, state: AppState) -> Layout:
        main = Layout()
        main.split_column(
            Layout(self._render_summary(state), name="summary"),
            Layout(self._render_summary_controls(state), name="controls", size=5),
            Layout(StatusBar().render(state.status_message), name="status", size=3),
        )
        return main

    def _render_summary(self, state: AppState) -> Panel:
        username = get_config().settings.name
        table = Table.grid(padding=1)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        # Pull latest saved session id from state
        session_id = state.last_session_id
        summary = None
        if session_id:
            try:
                summary = self._session_service.get_session_summary(session_id)
            except Exception as e:
                logger.debug(f"Failed to load session summary: {e}")
                # Continue with fallback to live metrics

        # Duration
        duration_s = 0.0
        if summary and summary.duration_s is not None:
            duration_s = summary.duration_s
        else:
            duration_s = state.metrics.get("time_s", 0.0)
        h = int(duration_s // 3600)
        m = int((duration_s % 3600) // 60)
        s = int(duration_s % 60)
        table.add_row("Duration", f"{h:02d}:{m:02d}:{s:02d}")

        # Distance
        dist_km = 0.0
        if summary and summary.total_distance_m is not None:
            dist_km = summary.total_distance_m / 1000.0
        else:
            dist_km = (state.metrics.get("distance_m") or 0.0) / 1000.0
        table.add_row("Distance", f"{dist_km:.2f} km")

        # Averages
        avg_power = (
            getattr(summary, "avg_power_w", None)
            if summary
            else state.metrics.get("avg_power_w")
        )
        avg_cad = (
            getattr(summary, "avg_cadence_rpm", None)
            if summary
            else state.metrics.get("avg_cadence_rpm")
        )
        avg_speed_kph = None
        if summary and summary.avg_speed_mps is not None:
            avg_speed_kph = summary.avg_speed_mps * 3.6
        else:
            t = duration_s or 0.0
            d_m = state.metrics.get("distance_m") or 0.0
            if t > 0:
                avg_speed_kph = (d_m / t) * 3.6

        table.add_row(
            "Avg Power", f"{int(round(avg_power))} W" if avg_power else "--- W"
        )
        table.add_row(
            "Avg Cadence", f"{int(round(avg_cad))} rpm" if avg_cad else "--- rpm"
        )
        table.add_row(
            "Avg Speed", f"{avg_speed_kph:.1f} km/h" if avg_speed_kph else "--- km/h"
        )

        # Max power (if available)
        max_power = getattr(summary, "max_power_w", None) if summary else None
        if max_power:
            table.add_row("Max Power", f"{max_power} W")

        # Heart rate (if available)
        avg_hr = (
            getattr(summary, "avg_hr_bpm", None)
            if summary
            else state.metrics.get("avg_hr_bpm")
        )
        max_hr_recorded = (
            getattr(summary, "max_hr_bpm", None)
            if summary
            else None
        )
        if avg_hr:
            hr_str = f"{int(round(avg_hr))} bpm"
            if max_hr_recorded:
                hr_str += f" (max {max_hr_recorded})"
            table.add_row("Avg Heart Rate", hr_str)

        header = Text.assemble((f"Good job, {username}!", "bold green"))
        return Panel(
            Align.center(Align.left(table)),
            title=header,
            border_style="green",
        )

    def _render_summary_controls(self, state: AppState) -> Panel:
        controls = "[s] Save and finish   [d] Discard session   [Esc] Home"
        return Panel(Text(controls), title="Summary", border_style="cyan")

    def _handle_key_impl(self, key: str, state: AppState) -> Optional[ViewState]:
        if key == "escape" or key == "s":
            # Keep session (already saved), return Home
            return ViewState.HOME
        if key == "d":
            # Delete session and return Home
            sid = state.last_session_id
            if sid:
                try:
                    if self._session_service.delete_session(sid):
                        state.status_message = "Session discarded"
                    else:
                        state.status_message = "Failed to discard session"
                except Exception as e:
                    logger.warning(f"Error deleting session {sid}: {e}")
                    state.status_message = "Failed to discard session"
            return ViewState.HOME
        return None
