"""Common TUI widgets and components."""

from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from .keymap import get_hints


class MetricsDisplay:
    """Widget for displaying live training metrics."""

    def __init__(self) -> None:
        self.console = Console()

    def render(self, metrics: Dict[str, Any], mode: str = "free") -> Panel:
        """Render metrics as a Rich panel.

        Args:
            metrics: Dictionary of current metrics
            mode: Current training mode ("free", "erg", "sim")

        Returns:
            Rich Panel with formatted metrics
        """
        table = Table.grid(padding=1)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        # Time
        time_s = metrics.get("time_s", 0)
        time_str = f"{int(time_s // 60):02d}:{int(time_s % 60):02d}"
        table.add_row("Time", time_str)

        # Power
        power_w = metrics.get("power_w")
        if power_w is not None:
            power_str = f"{power_w:3d} W"
            if mode == "erg":
                target_power = metrics.get("target_power_w", 0)
                power_str += f" / {target_power} W"
            table.add_row("Power", power_str)
        else:
            table.add_row("Power", "--- W")

        # Cadence
        cadence_rpm = metrics.get("cadence_rpm")
        cadence_str = f"{cadence_rpm:3d} rpm" if cadence_rpm else "--- rpm"
        table.add_row("Cadence", cadence_str)

        # Speed
        speed_mps = metrics.get("speed_mps")
        if speed_mps is not None:
            speed_kph = speed_mps * 3.6
            speed_str = f"{speed_kph:4.1f} km/h"
        else:
            speed_str = "--- km/h"
        table.add_row("Speed", speed_str)

        # Distance
        distance_m = metrics.get("distance_m", 0)
        distance_km = distance_m / 1000.0
        table.add_row("Distance", f"{distance_km:4.1f} km")

        # Heart rate (if available)
        hr_bpm = metrics.get("hr_bpm")
        if hr_bpm is not None:
            table.add_row("Heart Rate", f"{hr_bpm:3d} bpm")

        # Mode-specific info
        if mode == "sim":
            grade_pct = metrics.get("grade_pct", 0)
            table.add_row("Grade", f"{grade_pct:+4.1f} %")

        # Create panel with mode-specific title color
        mode_colors = {"free": "blue", "erg": "red", "sim": "green"}
        title = f"TerminalRide — {mode.upper()} Mode"

        return Panel(table, title=title, border_style=mode_colors.get(mode, "white"))


class AverageMetricsDisplay:
    """Widget showing session average metrics."""

    def __init__(self) -> None:
        self.console = Console()

    def render(self, metrics: Dict[str, Any]) -> Panel:
        table = Table.grid(padding=1)
        table.add_column("Average", style="bold")
        table.add_column("Value", justify="right")

        # Elapsed time
        time_s = metrics.get("time_s", 0)
        h = int(time_s // 3600)
        m = int((time_s % 3600) // 60)
        s = int(time_s % 60)
        table.add_row("Time", f"{h:02d}:{m:02d}:{s:02d}")

        # Average power
        avg_power = metrics.get("avg_power_w")
        table.add_row("Power", f"{int(round(avg_power))} W" if avg_power is not None else "--- W")

        # Average cadence
        avg_cad = metrics.get("avg_cadence_rpm")
        table.add_row("Cadence", f"{int(round(avg_cad))} rpm" if avg_cad is not None else "--- rpm")

        # Average speed (prefer km/h value if present, else compute)
        avg_speed_kph = metrics.get("avg_speed_kph")
        if avg_speed_kph is None:
            dist_m = metrics.get("distance_m") or 0.0
            if time_s > 0:
                avg_speed_kph = (dist_m / time_s) * 3.6
        table.add_row("Speed", f"{avg_speed_kph:4.1f} km/h" if avg_speed_kph else "--- km/h")

        # Average heart rate
        avg_hr = metrics.get("avg_hr_bpm")
        table.add_row("Heart Rate", f"{int(round(avg_hr))} bpm" if avg_hr is not None else "--- bpm")

        return Panel(table, title="Session Averages", border_style="white")


class StatusBar:
    """Bottom status bar widget."""

    def render(self, status: str, connection: str = "disconnected", hints_line: str | None = None) -> Panel:
        """Render status bar.

        Args:
            status: Main status message
            connection: Connection status

        Returns:
            Rich Panel with status information
        """
        connection_colors = {
            "connected": "green",
            "connecting": "yellow",
            "disconnected": "red",
        }

        connection_text = Text(
            f"● {connection.title()}", style=connection_colors.get(connection, "white")
        )

        status_text = Text(status)

        # Combine status elements
        full_text = Text.assemble(connection_text, "  |  ", status_text)
        if hints_line:
            full_text.append("  |  ")
            full_text.append(hints_line)

        return Panel(Align.center(full_text), height=3, style="dim")


class HelpOverlay:
    """Help overlay widget showing key bindings."""

    def render(self, mode: str = "home") -> Panel:
        """Render help overlay.

        Args:
            mode: Current UI mode to show relevant keys

        Returns:
            Rich Panel with help information
        """
        table = Table.grid(padding=1)
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")
        # Map simple mode to a view name used in keymap
        view_map = {
            "home": "home",
            "free": "live_free",
            "erg": "live_erg",
            "sim": "live_sim",
            "devices": "devices",
            "stats": "stats",
            "settings": "settings",
        }
        current_view = view_map.get(mode, "home")
        hints = get_hints(current_view, connected=True)

        # View-specific
        for key, label, enabled in hints["view"]:
            style = None if enabled else "dim"
            table.add_row(Text(key, style=style), Text(label, style=style))

        # Global
        for key, label, enabled in hints["global"]:
            style = None if enabled else "dim"
            table.add_row(Text(key, style=style), Text(label, style=style))

        return Panel(table, title="Help", border_style="cyan")


class DeviceList:
    """Widget for displaying device connection status."""

    def render(self, devices: Dict[str, Dict[str, Any]]) -> Panel:
        """Render device list.

        Args:
            devices: Dictionary of device info by type

        Returns:
            Rich Panel with device status
        """
        table = Table()
        table.add_column("Device Type", style="bold")
        table.add_column("Name")
        table.add_column("Status", justify="center")
        table.add_column("Signal", justify="center")

        # Trainer device
        trainer = devices.get("trainer", {})
        trainer_status = "●" if trainer.get("connected") else "○"
        trainer_color = "green" if trainer.get("connected") else "red"

        table.add_row(
            "Trainer",
            trainer.get("name", "Not found"),
            Text(trainer_status, style=trainer_color),
            str(trainer.get("rssi", "---")),
        )

        # Heart rate device
        hr = devices.get("heart_rate", {})
        hr_status = "●" if hr.get("connected") else "○"
        hr_color = "green" if hr.get("connected") else "red"

        table.add_row(
            "Heart Rate",
            hr.get("name", "Not found"),
            Text(hr_status, style=hr_color),
            str(hr.get("rssi", "---")),
        )

        return Panel(table, title="Device Status", border_style="blue")


class LegendPanel:
    """Non-modal legend panel with contextual key hints."""

    def render(self, current_view: str, connected: bool, in_live: bool) -> Panel:
        table = Table.grid(padding=(0,1))
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")

        hints = get_hints(current_view, connected)

        # Global
        table.add_row(Text("Global", style="bold magenta"), Text(""))
        for key, label, enabled in hints["global"]:
            style = None if enabled else "dim"
            table.add_row(Text(key, style=style), Text(label, style=style))

        # View-specific
        table.add_row(Text("\nThis View", style="bold magenta"), Text(""))
        for key, label, enabled in hints["view"]:
            style = None if enabled else "dim"
            table.add_row(Text(key, style=style), Text(label, style=style))

        return Panel(table, title="Legend", border_style="cyan")


class DistanceProgressBar:
    """2D progress bar showing progress within the current kilometer."""

    def __init__(self, width_cells: int = 40) -> None:
        self.width = width_cells

    def render(self, metrics: Dict[str, Any]) -> Panel:
        dist_m = float(metrics.get("distance_m") or 0.0)
        km_completed = int(dist_m // 1000)
        within_km = max(0.0, dist_m - km_completed * 1000)
        frac = 0.0 if dist_m <= 0 else min(1.0, within_km / 1000.0)

        filled = int(self.width * frac)
        empty = self.width - filled

        # Build a boxed bar with top/middle/bottom lines
        top = "┌" + ("─" * self.width) + "┐"
        mid = "│" + ("█" * filled + " " * empty) + "│"
        bot = "└" + ("─" * self.width) + "┘"

        label = f"KM {km_completed}  •  {int(frac*100):3d}%  •  {int(within_km):3d} m"

        grid = Table.grid(padding=(0, 1))
        grid.add_column(justify="left")
        grid.add_row(Text(top, style="green"))
        grid.add_row(Text(mid, style="green"))
        grid.add_row(Text(bot, style="green"))
        grid.add_row(Text(label, style="dim"))
        return Panel(grid, title="Next Kilometer", border_style="green")
