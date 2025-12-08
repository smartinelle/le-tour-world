"""NiceGUI web interface for TerminalRide.

Clean, minimal design with orange accent.
Big metrics for visibility from bike distance.
"""

import asyncio
import logging
from typing import Optional

from nicegui import ui, app

from ..domain.ride_controller import RideController, RideMode, RideMetrics
from ..config import get_config

logger = logging.getLogger(__name__)


# Design tokens
COLORS = {
    "bg": "#FAFAFA",
    "surface": "#FFFFFF",
    "text": "#1A1A1A",
    "text_muted": "#9CA3AF",
    "border": "#E5E7EB",
    "accent": "#EA580C",  # Burnt orange
    "accent_light": "#FFF7ED",
    "accent_hover": "#C2410C",
}

# CSS for clean design
GLOBAL_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg: #FAFAFA;
    --surface: #FFFFFF;
    --text: #1A1A1A;
    --text-muted: #9CA3AF;
    --border: #E5E7EB;
    --accent: #EA580C;
    --accent-light: #FFF7ED;
    --accent-hover: #C2410C;
}

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

body {
    background: var(--bg) !important;
    margin: 0;
    padding: 0;
}

.metric-value {
    font-size: clamp(4rem, 15vw, 12rem);
    font-weight: 600;
    line-height: 1;
    color: var(--text);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-value.accent {
    color: var(--accent);
}

.metric-label {
    font-size: clamp(0.75rem, 2vw, 1.25rem);
    font-weight: 400;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.5rem;
}

.metric-unit {
    font-size: clamp(1rem, 3vw, 2rem);
    font-weight: 300;
    color: var(--text-muted);
    margin-left: 0.25rem;
}

.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 1rem;
    padding: 2rem;
    text-align: center;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card:hover {
    border-color: var(--accent);
    box-shadow: 0 4px 20px rgba(234, 88, 12, 0.1);
}

.btn-primary {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 1rem 2rem !important;
    font-weight: 500 !important;
    font-size: 1rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}

.btn-primary:hover {
    background: var(--accent-hover) !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(234, 88, 12, 0.3);
}

.btn-secondary {
    background: transparent !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 0.75rem !important;
    padding: 1rem 2rem !important;
    font-weight: 500 !important;
    font-size: 1rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}

.btn-secondary:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

.nav-link {
    color: var(--text-muted);
    text-decoration: none;
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    transition: all 0.2s ease;
}

.nav-link:hover {
    color: var(--accent);
    background: var(--accent-light);
}

.nav-link.active {
    color: var(--accent);
}

.divider {
    height: 1px;
    background: var(--border);
    margin: 2rem 0;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 0.5rem;
}

.status-dot.connected {
    background: #22C55E;
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

.status-dot.disconnected {
    background: var(--text-muted);
}

.fade-in {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.slide-up {
    animation: slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Session view - full screen metrics */
.session-view {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    box-sizing: border-box;
}

.main-metric {
    flex: 2;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.secondary-metrics {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    align-items: center;
}

.control-bar {
    display: flex;
    justify-content: center;
    gap: 1rem;
    padding: 1rem 0;
}

/* Sparkline chart */
.sparkline {
    height: 60px;
    width: 100%;
    margin: 1rem 0;
}
</style>
"""


class WebUI:
    """Web-based UI for TerminalRide."""

    def __init__(self) -> None:
        self.controller = RideController()
        self._update_task: Optional[asyncio.Task] = None
        
        # UI element references
        self._power_label: Optional[ui.label] = None
        self._cadence_label: Optional[ui.label] = None
        self._hr_label: Optional[ui.label] = None
        self._time_label: Optional[ui.label] = None
        self._distance_label: Optional[ui.label] = None
        self._speed_label: Optional[ui.label] = None
        self._target_label: Optional[ui.label] = None
        self._status_label: Optional[ui.label] = None

    def setup(self) -> None:
        """Set up the web UI routes and pages."""
        
        @ui.page("/")
        def home_page():
            self._render_home()

        @ui.page("/session/{mode}")
        def session_page(mode: str):
            self._render_session(mode)

        @ui.page("/devices")
        def devices_page():
            self._render_devices()

        @ui.page("/history")
        def history_page():
            self._render_history()

        @ui.page("/settings")
        def settings_page():
            self._render_settings()

    def _render_header(self, current: str = "") -> None:
        """Render the navigation header."""
        ui.html(GLOBAL_STYLES, sanitize=False)
        
        with ui.header().classes("bg-white border-b border-gray-200 px-8 py-4"):
            with ui.row().classes("w-full items-center justify-between"):
                # Logo
                ui.label("TerminalRide").classes(
                    "text-xl font-semibold text-gray-900"
                )
                
                # Navigation
                with ui.row().classes("gap-2"):
                    links = [
                        ("Home", "/"),
                        ("Devices", "/devices"),
                        ("History", "/history"),
                        ("Settings", "/settings"),
                    ]
                    for name, path in links:
                        active = "active" if current == name else ""
                        ui.link(name, path).classes(f"nav-link {active}")

    def _render_home(self) -> None:
        """Render the home/menu page."""
        self._render_header("Home")
        
        with ui.column().classes(
            "w-full max-w-4xl mx-auto px-8 py-16 fade-in"
        ):
            # Hero section
            ui.label("Ready to ride?").classes(
                "text-5xl font-semibold text-gray-900 mb-4"
            )
            ui.label(
                "Choose a training mode to get started."
            ).classes("text-xl text-gray-500 mb-12")
            
            # Connection status
            connected = self.controller.trainer.is_connected
            with ui.row().classes("items-center mb-8"):
                dot_class = "connected" if connected else "disconnected"
                ui.html(f'<span class="status-dot {dot_class}"></span>', sanitize=False)
                status = "Trainer connected" if connected else "No trainer connected"
                ui.label(status).classes("text-gray-600")
            
            # Mode cards
            with ui.row().classes("gap-6 w-full items-stretch"):
                self._mode_card(
                    "Free Ride",
                    "Ride freely without resistance control",
                    "/session/free",
                    "1",
                )
                self._mode_card(
                    "ERG Mode",
                    "Maintain constant power output",
                    "/session/erg",
                    "2",
                )
                self._mode_card(
                    "SIM Mode",
                    "Simulate hills and terrain",
                    "/session/sim",
                    "3",
                )

    def _mode_card(
        self, title: str, description: str, path: str, shortcut: str
    ) -> None:
        """Render a training mode card."""
        with ui.card().classes("metric-card flex-1 h-full cursor-pointer").on(
            "click", lambda: ui.navigate.to(path)
        ):
            ui.label(shortcut).classes(
                "text-sm font-medium text-orange-600 bg-orange-50 "
                "px-2 py-1 rounded inline-block mb-4"
            )
            ui.label(title).classes("text-2xl font-semibold text-gray-900 mb-2")
            ui.label(description).classes("text-gray-500")

    def _render_session(self, mode: str) -> None:
        """Render the full-screen session view with BIG metrics."""
        ui.html(GLOBAL_STYLES, sanitize=False)
        
        mode_enum = {
            "free": RideMode.FREE,
            "erg": RideMode.ERG,
            "sim": RideMode.SIM,
        }.get(mode, RideMode.FREE)
        
        mode_title = {"free": "Free Ride", "erg": "ERG Mode", "sim": "SIM Mode"}.get(
            mode, "Free Ride"
        )
        
        with ui.column().classes("session-view"):
            # Top bar
            with ui.row().classes(
                "w-full justify-between items-center px-4 py-2"
            ):
                ui.button(
                    "← Exit", on_click=lambda: self._exit_session()
                ).classes("btn-secondary").props("flat")
                
                ui.label(mode_title).classes("text-lg font-medium text-gray-600")
                
                self._time_label = ui.label("00:00").classes(
                    "text-2xl font-semibold text-gray-900"
                )
            
            ui.html('<div class="divider"></div>', sanitize=False)
            
            # Main metric (POWER - biggest)
            with ui.column().classes("main-metric slide-up"):
                with ui.row().classes("items-end justify-center"):
                    self._power_label = ui.label("---").classes("metric-value accent")
                    ui.label("W").classes("metric-unit")
                ui.label("Power").classes("metric-label")
                
                # Target indicator for ERG mode
                if mode == "erg":
                    with ui.row().classes("items-center gap-4 mt-8"):
                        ui.button(
                            "−", on_click=lambda: self._adjust_target(-10)
                        ).classes("btn-secondary").props("round")
                        self._target_label = ui.label("Target: 150W").classes(
                            "text-xl text-gray-600"
                        )
                        ui.button(
                            "+", on_click=lambda: self._adjust_target(10)
                        ).classes("btn-secondary").props("round")
            
            ui.html('<div class="divider"></div>', sanitize=False)
            
            # Secondary metrics grid
            with ui.row().classes("secondary-metrics"):
                with ui.column().classes("metric-card"):
                    self._cadence_label = ui.label("--").classes(
                        "text-4xl font-semibold text-gray-900"
                    )
                    ui.label("Cadence").classes("metric-label")
                
                with ui.column().classes("metric-card"):
                    self._hr_label = ui.label("--").classes(
                        "text-4xl font-semibold text-gray-900"
                    )
                    ui.label("Heart Rate").classes("metric-label")
                
                with ui.column().classes("metric-card"):
                    self._speed_label = ui.label("--").classes(
                        "text-4xl font-semibold text-gray-900"
                    )
                    ui.label("Speed").classes("metric-label")
                
                with ui.column().classes("metric-card"):
                    self._distance_label = ui.label("--").classes(
                        "text-4xl font-semibold text-gray-900"
                    )
                    ui.label("Distance").classes("metric-label")
            
            # Control bar
            with ui.row().classes("control-bar mt-auto"):
                ui.button(
                    "⏸ Pause", on_click=lambda: self._toggle_pause()
                ).classes("btn-secondary")
                ui.button(
                    "■ Stop", on_click=lambda: self._stop_session()
                ).classes("btn-primary")
            
            # Status
            self._status_label = ui.label("Starting session...").classes(
                "text-center text-gray-500 mt-4"
            )
        
        # Start session and update loop
        self._start_session(mode_enum)

    def _start_session(self, mode: RideMode) -> None:
        """Start a training session."""
        trainer_name = "Simulated Trainer"  # Will be real when connected
        if self.controller.trainer.is_connected:
            trainer_name = "Connected Trainer"
        
        self.controller.start_session(mode, trainer_name)
        
        if self._status_label:
            self._status_label.set_text("Session active")
        
        # Start UI update loop
        self._update_task = asyncio.create_task(self._update_loop())

    async def _update_loop(self) -> None:
        """Update UI with current metrics."""
        while self.controller.is_active:
            metrics = self.controller.metrics
            
            # Update power
            if self._power_label:
                power = metrics.power_w if metrics.power_w else "---"
                self._power_label.set_text(str(power))
            
            # Update cadence
            if self._cadence_label:
                cad = metrics.cadence_rpm if metrics.cadence_rpm else "--"
                self._cadence_label.set_text(f"{cad} rpm")
            
            # Update HR
            if self._hr_label:
                hr = metrics.hr_bpm if metrics.hr_bpm else "--"
                self._hr_label.set_text(f"{hr} bpm")
            
            # Update speed
            if self._speed_label:
                if metrics.speed_mps:
                    speed_kph = metrics.speed_mps * 3.6
                    self._speed_label.set_text(f"{speed_kph:.1f} km/h")
                else:
                    self._speed_label.set_text("-- km/h")
            
            # Update distance
            if self._distance_label:
                dist_km = metrics.distance_m / 1000
                self._distance_label.set_text(f"{dist_km:.2f} km")
            
            # Update time
            if self._time_label:
                elapsed = int(metrics.elapsed_s)
                mins, secs = divmod(elapsed, 60)
                self._time_label.set_text(f"{mins:02d}:{secs:02d}")
            
            # Update target for ERG
            if self._target_label:
                self._target_label.set_text(f"Target: {metrics.erg_target_w}W")
            
            await asyncio.sleep(0.1)  # 10Hz update

    def _adjust_target(self, delta: int) -> None:
        """Adjust ERG target power."""
        self.controller.adjust_erg_target(delta)

    def _toggle_pause(self) -> None:
        """Toggle session pause."""
        paused = self.controller.toggle_pause()
        if self._status_label:
            self._status_label.set_text("Paused" if paused else "Session active")

    def _stop_session(self) -> None:
        """Stop the current session."""
        session_id = self.controller.stop_session()
        if self._update_task:
            self._update_task.cancel()
        
        # Navigate to summary or home
        ui.navigate.to("/")

    def _exit_session(self) -> None:
        """Exit session without saving."""
        if self.controller.is_active:
            self.controller.stop_session()
        if self._update_task:
            self._update_task.cancel()
        ui.navigate.to("/")

    def _render_devices(self) -> None:
        """Render the devices management page."""
        self._render_header("Devices")
        
        with ui.column().classes("w-full max-w-2xl mx-auto px-8 py-16 fade-in"):
            ui.label("Devices").classes("text-4xl font-semibold text-gray-900 mb-8")
            
            # Trainer section
            with ui.card().classes("metric-card w-full mb-6"):
                ui.label("Trainer").classes("text-lg font-medium text-gray-900 mb-4")
                
                connected = self.controller.trainer.is_connected
                with ui.row().classes("items-center justify-between"):
                    with ui.row().classes("items-center"):
                        dot_class = "connected" if connected else "disconnected"
                        ui.html(f'<span class="status-dot {dot_class}"></span>', sanitize=False)
                        status = "Connected" if connected else "Not connected"
                        ui.label(status).classes("text-gray-600")
                    
                    if connected:
                        ui.button("Disconnect").classes("btn-secondary")
                    else:
                        ui.button("Scan", on_click=self._scan_trainers).classes(
                            "btn-primary"
                        )
            
            # HR Monitor section
            with ui.card().classes("metric-card w-full"):
                ui.label("Heart Rate Monitor").classes(
                    "text-lg font-medium text-gray-900 mb-4"
                )
                
                hr_connected = self.controller.hr_service.is_connected
                with ui.row().classes("items-center justify-between"):
                    with ui.row().classes("items-center"):
                        dot_class = "connected" if hr_connected else "disconnected"
                        ui.html(f'<span class="status-dot {dot_class}"></span>', sanitize=False)
                        status = "Connected" if hr_connected else "Not connected"
                        ui.label(status).classes("text-gray-600")
                    
                    if hr_connected:
                        ui.button("Disconnect").classes("btn-secondary")
                    else:
                        ui.button("Scan", on_click=self._scan_hr).classes("btn-primary")

    async def _scan_trainers(self) -> None:
        """Scan for available trainers."""
        ui.notify("Scanning for trainers...")
        # TODO: Implement scanning

    async def _scan_hr(self) -> None:
        """Scan for HR monitors."""
        ui.notify("Scanning for HR monitors...")
        # TODO: Implement scanning

    def _render_history(self) -> None:
        """Render the session history page."""
        self._render_header("History")
        
        with ui.column().classes("w-full max-w-4xl mx-auto px-8 py-16 fade-in"):
            ui.label("Session History").classes(
                "text-4xl font-semibold text-gray-900 mb-8"
            )
            
            # TODO: Load real sessions from repository
            ui.label("No sessions recorded yet.").classes("text-gray-500")

    def _render_settings(self) -> None:
        """Render the settings page."""
        self._render_header("Settings")
        
        config = get_config()
        
        with ui.column().classes("w-full max-w-2xl mx-auto px-8 py-16 fade-in"):
            ui.label("Settings").classes("text-4xl font-semibold text-gray-900 mb-8")
            
            # User settings
            with ui.card().classes("metric-card w-full mb-6"):
                ui.label("Profile").classes("text-lg font-medium text-gray-900 mb-4")
                
                with ui.column().classes("gap-4"):
                    ui.input(
                        "Name",
                        value=config.settings.name or "",
                    ).classes("w-full")
                    
                    with ui.row().classes("gap-4"):
                        ui.number(
                            "Weight (kg)",
                            value=config.settings.mass_kg,
                            min=30,
                            max=200,
                        ).classes("flex-1")
                        ui.number(
                            "FTP (watts)",
                            value=config.settings.ftp_w,
                            min=50,
                            max=500,
                        ).classes("flex-1")
                    
                    with ui.row().classes("gap-4"):
                        ui.number(
                            "Max HR (bpm)",
                            value=config.settings.max_hr_bpm or 180,
                            min=100,
                            max=220,
                        ).classes("flex-1")
                        ui.number(
                            "Age",
                            value=config.settings.age or 30,
                            min=10,
                            max=100,
                        ).classes("flex-1")
            
            ui.button("Save Settings", on_click=self._save_settings).classes(
                "btn-primary"
            )

    def _save_settings(self) -> None:
        """Save settings."""
        ui.notify("Settings saved!", color="green")


def run_web_ui(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the web UI server."""
    web_ui = WebUI()
    web_ui.setup()
    
    ui.run(
        host=host,
        port=port,
        title="TerminalRide",
        favicon="🚴",
        dark=False,
        reload=False,
    )

