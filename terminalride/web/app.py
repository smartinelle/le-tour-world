"""NiceGUI web interface for TerminalRide.

Clean, minimal design with orange accent.
Big metrics for visibility from bike distance.
Supports multi-user authentication via Supabase.
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any, Callable

from nicegui import ui, app

from ..domain.fake_samples import FakeTrainerSampleSource
from ..domain.ride_controller import RideController, RideMode
from ..config import get_config
from ..devices.base import DeviceNotFoundError, ConnectionError as DeviceConnectionError
from ..supabase_client import is_supabase_configured
from .auth import AuthManager
from .pages import render_login_page
from .ride3d import attach_ride3d_routes
from .snapshot_stream import attach_snapshot_routes

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

/* Scanning dialog styles */
.scan-dialog {
    max-width: 480px;
    width: 90vw;
}

.scan-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.scan-spinner {
    width: 24px;
    height: 24px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.scan-pulse {
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.device-list {
    max-height: 300px;
    overflow-y: auto;
    margin: 1rem 0;
}

.device-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--surface);
}

.device-item:hover {
    border-color: var(--accent);
    background: var(--accent-light);
}

.device-item.connecting {
    border-color: var(--accent);
    background: var(--accent-light);
    cursor: wait;
}

.device-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.device-name {
    font-weight: 500;
    color: var(--text);
}

.device-address {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: monospace;
}

/* Signal strength bars */
.signal-bars {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    height: 16px;
}

.signal-bar {
    width: 4px;
    background: var(--border);
    border-radius: 1px;
    transition: background 0.2s;
}

.signal-bar.active {
    background: var(--accent);
}

.signal-bar:nth-child(1) { height: 4px; }
.signal-bar:nth-child(2) { height: 8px; }
.signal-bar:nth-child(3) { height: 12px; }
.signal-bar:nth-child(4) { height: 16px; }

/* Empty state */
.empty-state {
    text-align: center;
    padding: 2rem;
    color: var(--text-muted);
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}

.empty-state-title {
    font-weight: 500;
    color: var(--text);
    margin-bottom: 0.5rem;
}

.empty-state-tips {
    font-size: 0.875rem;
    text-align: left;
    margin-top: 1rem;
    padding: 1rem;
    background: var(--accent-light);
    border-radius: 0.5rem;
}

.empty-state-tips li {
    margin-bottom: 0.5rem;
}

/* Progress text */
.scan-progress {
    font-size: 0.875rem;
    color: var(--text-muted);
    text-align: center;
    margin: 1rem 0;
}

/* Connection status */
.connection-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem;
    border-radius: 0.75rem;
    margin: 1rem 0;
}

.connection-status.success {
    background: #DCFCE7;
    color: #166534;
}

.connection-status.error {
    background: #FEE2E2;
    color: #991B1B;
}

.connection-status.info {
    background: var(--accent-light);
    color: var(--accent);
}
</style>
"""


def _rssi_to_bars(rssi: Optional[int]) -> int:
    """Convert RSSI dBm value to signal bar count (1-4)."""
    if rssi is None:
        return 2  # Unknown, show medium
    if rssi >= -50:
        return 4  # Excellent
    if rssi >= -60:
        return 3  # Good
    if rssi >= -70:
        return 2  # Fair
    return 1  # Weak


class ScanDialog:
    """Reusable scanning dialog with progress, device list, and connection flow."""

    def __init__(
        self,
        title: str,
        device_type: str,
        scan_fn: Callable[[], Any],
        connect_fn: Callable[[str], Any],
        on_connected: Optional[Callable[[], None]] = None,
    ) -> None:
        self.title = title
        self.device_type = device_type
        self.scan_fn = scan_fn
        self.connect_fn = connect_fn
        self.on_connected = on_connected

        self._dialog: Optional[ui.dialog] = None
        self._device_container: Optional[ui.column] = None
        self._status_label: Optional[ui.label] = None
        self._scan_task: Optional[asyncio.Task] = None
        self._is_scanning = False
        self._is_connecting = False
        self._devices: List[Dict[str, Any]] = []

    def show(self) -> None:
        """Show the scanning dialog and start scanning."""
        self._create_dialog()
        self._dialog.open()
        ui.timer(0.1, self._run_scan, once=True)

    def _create_dialog(self) -> None:
        """Create the dialog UI with clean, modern design."""
        self._dialog = ui.dialog().props("persistent maximized=false")

        with (
            self._dialog,
            ui.card()
            .classes("scan-dialog")
            .style("min-width: 400px; max-width: 500px; padding: 0; overflow: hidden;"),
        ):
            # Clean header with title and X button
            with (
                ui.row()
                .classes("w-full items-center justify-between")
                .style(
                    "padding: 1.25rem 1.5rem; border-bottom: 1px solid #E5E7EB; background: #FAFAFA;"
                )
            ):
                ui.label(f"Find {self.title}").classes(
                    "text-lg font-semibold text-gray-900"
                )
                ui.button(icon="close", on_click=self._cancel).props(
                    "flat round dense size=sm"
                ).classes("text-gray-500")

            # Content area
            with ui.column().classes("w-full").style("padding: 1.5rem;"):
                # Status text (shows scanning progress)
                self._status_label = ui.label("Scanning...").classes(
                    "text-sm text-gray-500 mb-4"
                )

                # Device list container
                self._device_container = ui.column().classes("w-full gap-2")

            # Footer
            with (
                ui.row()
                .classes("w-full justify-end")
                .style(
                    "padding: 1rem 1.5rem; border-top: 1px solid #E5E7EB; background: #FAFAFA;"
                )
            ):
                ui.button("Cancel", on_click=self._cancel).props("flat").classes(
                    "text-gray-600"
                ).style("min-width: 80px")

    async def _run_scan(self) -> None:
        """Execute the scan and update UI with results."""
        self._is_scanning = True
        self._devices = []

        try:
            if self._status_label:
                self._status_label.set_text("Looking for nearby devices...")

            # Run the scan
            devices = await self.scan_fn()
            self._devices = devices

            self._is_scanning = False

            if self._status_label:
                if devices:
                    count = len(devices)
                    self._status_label.set_text(
                        f"Found {count} device{'s' if count != 1 else ''}"
                    )
                else:
                    self._status_label.set_text("No devices found")

            # Update device list
            self._update_device_list()

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            self._is_scanning = False
            if self._status_label:
                self._status_label.set_text("Scan failed")
            self._show_error(str(e))

    def _update_device_list(self) -> None:
        """Update the device list UI."""
        if not self._device_container:
            return

        self._device_container.clear()

        if not self._devices:
            self._show_empty_state()
            return

        with self._device_container:
            for device in self._devices:
                self._create_device_item(device)

    def _create_device_item(self, device: Dict[str, Any]) -> None:
        """Create a device list item with clean, clickable card design."""
        name = device.get("name", "Unknown Device")
        rssi = device.get("rssi")
        bars = _rssi_to_bars(rssi)

        # Clean card-style device item
        with (
            ui.card()
            .classes("w-full cursor-pointer")
            .style("padding: 1rem; transition: all 0.2s ease;")
            .on(
                "click",
                lambda d=device: self._connect_to_device(d),
            )
            .on(
                "mouseenter",
                lambda e: e.sender.style("border-color: #EA580C; background: #FFF7ED;"),
            )
            .on(
                "mouseleave",
                lambda e: e.sender.style("border-color: #E5E7EB; background: white;"),
            ) as item
        ):
            device["_ui_element"] = item

            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(name).classes("font-medium text-gray-900")
                    if rssi:
                        ui.label(f"Signal: {rssi} dBm").classes("text-xs text-gray-400")

                # Signal strength indicator
                with ui.row().classes("items-end gap-0.5").style("height: 20px;"):
                    for i in range(1, 5):
                        bar_color = "#EA580C" if i <= bars else "#E5E7EB"
                        bar_height = 4 + (i * 4)
                        ui.element("div").style(
                            f"width: 4px; height: {bar_height}px; background: {bar_color}; border-radius: 1px;"
                        )

    def _show_empty_state(self) -> None:
        """Show empty state when no devices found."""
        if not self._device_container:
            return

        with self._device_container:
            with ui.element("div").classes("empty-state"):
                ui.html(
                    '<div class="empty-state-icon">📡</div>',
                    sanitize=False,
                )
                ui.label(f"No {self.device_type}s found").classes("empty-state-title")
                ui.label("Make sure your device is powered on and in range.").classes(
                    "text-sm"
                )

                with ui.element("div").classes("empty-state-tips"):
                    ui.label("Troubleshooting tips:").classes("font-medium mb-2")
                    ui.html(
                        """
                        <ul style="margin: 0; padding-left: 1.25rem;">
                            <li>Is Bluetooth enabled on this computer?</li>
                            <li>Is the device powered on and awake?</li>
                            <li>Is the device within range (< 10m)?</li>
                            <li>Is another app connected to it?</li>
                        </ul>
                        """,
                        sanitize=False,
                    )

                ui.button(
                    "Scan Again",
                    on_click=self._rescan,
                ).classes("btn-primary mt-4")

    def _show_error(self, message: str) -> None:
        """Show an error message."""
        if not self._device_container:
            return

        self._device_container.clear()

        with self._device_container:
            with ui.element("div").classes("connection-status error"):
                ui.icon("error").classes("text-2xl")
                with ui.column().classes("gap-1"):
                    ui.label("Scan failed").classes("font-medium")
                    ui.label(message).classes("text-sm")

            ui.button(
                "Try Again",
                on_click=self._rescan,
            ).classes("btn-primary mt-4")

    async def _rescan(self) -> None:
        """Rescan for devices."""
        if self._device_container:
            self._device_container.clear()
        if self._status_label:
            self._status_label.set_text("Scanning...")
            self._status_label.classes(add="scan-pulse")
        await self._run_scan()

    async def _connect_to_device(self, device: Dict[str, Any]) -> None:
        """Connect to the selected device."""
        if self._is_connecting or self._is_scanning:
            return

        self._is_connecting = True
        address = device.get("address", "")
        name = device.get("name", "device")

        # Update UI to show connecting state
        if self._status_label:
            self._status_label.set_text(f"Connecting to {name}...")
            self._status_label.classes(add="scan-pulse")

        # Update device item visual state
        ui_element = device.get("_ui_element")
        if ui_element:
            ui_element.classes(add="connecting")

        try:
            await self.connect_fn(address)

            # Success!
            self._is_connecting = False
            if self._status_label:
                self._status_label.set_text("")
                self._status_label.classes(remove="scan-pulse")

            # Show success message briefly
            if self._device_container:
                self._device_container.clear()
                with self._device_container:
                    with ui.element("div").classes("connection-status success"):
                        ui.icon("check_circle").classes("text-2xl")
                        with ui.column().classes("gap-1"):
                            ui.label("Connected!").classes("font-medium")
                            ui.label(f"Successfully connected to {name}").classes(
                                "text-sm"
                            )

            # Wait a moment then close
            await asyncio.sleep(1.5)
            self._dialog.close()

            # Call callback if provided
            if self.on_connected:
                self.on_connected()

        except DeviceNotFoundError as e:
            logger.error(f"Device not found: {e}")
            self._is_connecting = False
            self._show_connection_error(
                name,
                "Device not found. It may have gone out of range or powered off.",
            )

        except DeviceConnectionError as e:
            logger.error(f"Connection failed: {e}")
            self._is_connecting = False
            self._show_connection_error(name, str(e))

        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            self._is_connecting = False
            self._show_connection_error(name, str(e))

    def _show_connection_error(self, device_name: str, message: str) -> None:
        """Show connection error and allow retry."""
        if self._status_label:
            self._status_label.set_text("")
            self._status_label.classes(remove="scan-pulse")

        if not self._device_container:
            return

        self._device_container.clear()

        with self._device_container:
            with ui.element("div").classes("connection-status error"):
                ui.icon("error").classes("text-2xl")
                with ui.column().classes("gap-1"):
                    ui.label(f"Failed to connect to {device_name}").classes(
                        "font-medium"
                    )
                    ui.label(message).classes("text-sm")

            with ui.row().classes("gap-2 mt-4"):
                ui.button(
                    "Scan Again",
                    on_click=self._rescan,
                ).classes("btn-secondary")

    def _cancel(self) -> None:
        """Cancel scanning and close dialog."""
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
        self._dialog.close()


def _get_shared_controller() -> RideController:
    """Get or create the shared RideController singleton.

    Used in local-only mode (Supabase not configured) where there's a single user.
    Uses NiceGUI's app storage to persist the controller across page loads,
    ensuring device connections are maintained throughout the session.
    """
    if not hasattr(app, "_shared_controller") or app._shared_controller is None:
        app._shared_controller = RideController()
        logger.info("Created shared RideController instance (local mode)")
    return app._shared_controller


def _get_user_controller() -> RideController:
    """Get or create a per-user RideController instance.

    Each authenticated user gets their own RideController stored in their
    session storage. This ensures device connections and ride state are
    isolated between users.

    In multi-user mode with Web Bluetooth, the RideController manages state
    while the actual BLE communication happens in the browser.

    Returns:
        RideController instance for the current user

    Raises:
        ValueError: If user is not authenticated
    """
    if not AuthManager.is_authenticated():
        raise ValueError("User not authenticated - cannot get user controller")

    # Store controller in user's session storage
    if "controller" not in app.storage.user:
        user = AuthManager.get_current_user()
        user_id = user.get("id", "unknown") if user else "unknown"
        app.storage.user["controller"] = RideController()
        logger.info(f"Created RideController for user {user_id}")

    return app.storage.user["controller"]


def get_controller() -> RideController:
    """Get the appropriate controller based on current mode.

    - If Supabase is configured and user is authenticated: per-user controller
    - Otherwise: shared singleton controller (local mode)

    This provides backward compatibility for local-only usage while
    supporting multi-user scenarios.
    """
    if is_supabase_configured() and AuthManager.is_authenticated():
        return _get_user_controller()
    return _get_shared_controller()


class WebUI:
    """Web-based UI for TerminalRide."""

    def __init__(self) -> None:
        # Controller is now retrieved dynamically per request
        # Don't store a reference here - get it fresh each time
        self._update_task: Optional[Any] = None
        self._fake_source: Optional[FakeTrainerSampleSource] = None
        self._auto_connect_attempted: bool = False

        # UI element references
        self._power_label: Optional[ui.label] = None
        self._cadence_label: Optional[ui.label] = None
        self._hr_label: Optional[ui.label] = None
        self._time_label: Optional[ui.label] = None
        self._distance_label: Optional[ui.label] = None
        self._speed_label: Optional[ui.label] = None
        self._target_label: Optional[ui.label] = None
        self._status_label: Optional[ui.label] = None
        self._connection_status_label: Optional[ui.label] = None
        self._connection_dot: Optional[ui.html] = None

    @property
    def controller(self) -> RideController:
        """Get the controller for the current context.

        This property dynamically retrieves the appropriate controller,
        supporting both local mode (singleton) and multi-user mode (per-user).
        """
        return get_controller()

    def _auto_connect_enabled(self) -> bool:
        """True when automatic BLE scanning is explicitly enabled."""
        flag = os.getenv("TERMINALRIDE_ENABLE_BLE", "").lower()
        return (
            flag in {"1", "true", "yes"} and get_config().settings.auto_connect_trainer
        )

    def setup(self) -> None:
        """Set up the web UI routes and pages."""
        if not getattr(app, "_terminalride_snapshot_routes_attached", False):
            attach_snapshot_routes(app, get_controller)
            attach_ride3d_routes(app, get_controller)
            app._terminalride_snapshot_routes_attached = True

        # =====================================================================
        # Authentication Routes
        # =====================================================================

        @ui.page("/login")
        def login_page():
            """Login page with Google OAuth."""
            # If already authenticated, redirect to home
            if AuthManager.is_authenticated():
                ui.navigate.to("/")
                return
            render_login_page()

        @ui.page("/auth/callback")
        async def auth_callback():
            """Handle OAuth callback from Supabase/Google."""
            # Get tokens from URL fragment (Supabase returns them in hash)
            # NiceGUI can't read hash directly, so we use JS
            ui.html("""
                <script>
                    // Extract tokens from URL hash
                    const hash = window.location.hash.substring(1);
                    const params = new URLSearchParams(hash);
                    const accessToken = params.get('access_token');
                    const refreshToken = params.get('refresh_token');
                    
                    if (accessToken) {
                        // Send tokens to server
                        fetch('/auth/complete', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                access_token: accessToken,
                                refresh_token: refreshToken
                            })
                        }).then(() => {
                            window.location.href = '/';
                        });
                    } else {
                        // No tokens, redirect to login
                        window.location.href = '/login?error=auth_failed';
                    }
                </script>
                <div style="display: flex; justify-content: center; align-items: center; height: 100vh;">
                    <p>Completing login...</p>
                </div>
            """)

        @app.post("/auth/complete")
        async def auth_complete(request):
            """Complete OAuth flow by storing tokens in session."""
            try:

                body = await request.json()
                access_token = body.get("access_token")
                refresh_token = body.get("refresh_token")

                if access_token:
                    success = await AuthManager.handle_oauth_callback(
                        access_token, refresh_token or ""
                    )
                    return {"success": success}
                return {"success": False, "error": "No access token"}
            except Exception as e:
                logger.error(f"Auth complete error: {e}")
                return {"success": False, "error": str(e)}

        @ui.page("/logout")
        async def logout_page():
            """Log out and redirect to login."""
            await AuthManager.logout()
            ui.navigate.to("/login")

        # =====================================================================
        # Main Application Routes (Protected)
        # =====================================================================

        @ui.page("/")
        async def home_page():
            # If auth is configured and user not logged in, redirect
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            await self._render_home_with_auto_connect()

        @ui.page("/session/{mode}")
        def session_page(mode: str):
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_session(mode)

        @ui.page("/devices")
        def devices_page():
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_devices()

        @ui.page("/history")
        def history_page():
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_history()

        @ui.page("/settings")
        def settings_page():
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_settings()

    def _render_header(self, current: str = "") -> None:
        """Render the navigation header."""
        ui.html(GLOBAL_STYLES, sanitize=False)

        with ui.header().classes("bg-white border-b border-gray-200 px-8 py-4"):
            with ui.row().classes("w-full items-center justify-between"):
                # Logo
                ui.link("TerminalRide", "/").classes(
                    "text-xl font-semibold text-gray-900 no-underline"
                )

                # Navigation + User
                with ui.row().classes("gap-4 items-center"):
                    # Nav links
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

                    # User section (only if authenticated)
                    if is_supabase_configured() and AuthManager.is_authenticated():
                        user = AuthManager.get_current_user()
                        if user:
                            with ui.row().classes(
                                "gap-2 items-center ml-4 pl-4 border-l border-gray-200"
                            ):
                                # Avatar or initial
                                avatar_url = user.get("avatar_url", "")
                                if avatar_url:
                                    ui.image(avatar_url).classes(
                                        "w-8 h-8 rounded-full object-cover"
                                    )
                                else:
                                    initial = user.get("name", "U")[0].upper()
                                    ui.element("div").classes(
                                        "w-8 h-8 rounded-full bg-orange-100 text-orange-600 "
                                        "flex items-center justify-center font-medium text-sm"
                                    ).text(initial)

                                # User name (hidden on mobile)
                                ui.label(user.get("name", "User")).classes(
                                    "text-sm text-gray-600 hidden md:block"
                                )

                                # Logout button
                                ui.link("Logout", "/logout").classes(
                                    "text-sm text-gray-400 hover:text-orange-600 ml-2"
                                )

    async def _render_home_with_auto_connect(self) -> None:
        """Render home page with automatic device connection on first load.

        Mirrors CLI behavior: automatically scan and connect to trainer
        when the app first loads, providing seamless device discovery.
        """
        self._render_header("Home")

        with ui.column().classes("w-full max-w-4xl mx-auto px-8 py-16 fade-in"):
            # Hero section
            ui.label("Ready to ride?").classes(
                "text-5xl font-semibold text-gray-900 mb-4"
            )
            ui.label("Choose a training mode to get started.").classes(
                "text-xl text-gray-500 mb-12"
            )

            # Connection status (will be updated dynamically)
            connected = self.controller.trainer.is_connected
            with ui.row().classes("items-center mb-8"):
                dot_class = "connected" if connected else "disconnected"
                self._connection_dot = ui.html(
                    f'<span class="status-dot {dot_class}"></span>', sanitize=False
                )
                if connected:
                    trainer_name = self.controller.trainer.device_info.get(
                        "name", "Trainer"
                    )
                    status = f"Connected to {trainer_name}"
                elif self._auto_connect_enabled():
                    status = "Searching for trainer..."
                else:
                    status = "No trainer connected — sessions use demo data"
                self._connection_status_label = ui.label(status).classes(
                    "text-gray-600"
                )

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
                self._mode_card(
                    "3D Road",
                    "View live ride motion",
                    "/ride3d",
                    "4",
                )

        # Auto-connect if not already connected (like CLI does on startup)
        # Use a NiceGUI timer so UI updates run with a valid page slot.
        if not self.controller.trainer.is_connected and self._auto_connect_enabled():
            ui.timer(0.1, self._auto_connect_trainer, once=True)

    async def _auto_connect_trainer(self) -> None:
        """Automatically scan and connect to first available trainer.

        This mirrors the CLI's _connection_loop() behavior, providing
        seamless device discovery without requiring manual intervention.
        """
        try:
            if self._connection_status_label:
                self._connection_status_label.set_text("Scanning for trainers...")
                self._connection_status_label.update()

            logger.info("Auto-connect: Scanning for FTMS trainers...")

            # Scan for available trainers
            available = await self.controller.trainer.scan_available(timeout_s=8.0)

            if not available:
                logger.info("Auto-connect: No trainers found")
                if self._connection_status_label:
                    self._connection_status_label.set_text(
                        "No trainer found — click Devices to scan manually"
                    )
                    self._connection_status_label.update()
                return

            # Connect to first/strongest trainer (like CLI does)
            trainer = available[0]
            trainer_name = trainer.get("name", "Trainer")
            trainer_address = trainer.get("address")

            if self._connection_status_label:
                self._connection_status_label.set_text(
                    f"Connecting to {trainer_name}..."
                )
                self._connection_status_label.update()

            logger.info(
                f"Auto-connect: Connecting to {trainer_name} at {trainer_address}"
            )
            await self.controller.trainer.connect_to_device(trainer_address)

            # Update UI to show connected state
            if self._connection_dot:
                self._connection_dot.set_content(
                    '<span class="status-dot connected"></span>'
                )
                self._connection_dot.update()
            if self._connection_status_label:
                self._connection_status_label.set_text(f"Connected to {trainer_name}")
                self._connection_status_label.update()

            logger.info(f"Auto-connect: Successfully connected to {trainer_name}")

            # Bike data is subscribed when a session starts so the controller
            # receives samples for the active session.

        except DeviceNotFoundError:
            logger.info("Auto-connect: Device not found during connection")
            if self._connection_status_label:
                self._connection_status_label.set_text(
                    "Connection failed — click Devices to retry"
                )
                self._connection_status_label.update()
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")
            if self._connection_status_label:
                self._connection_status_label.set_text(
                    "Connection error — click Devices to retry"
                )
                self._connection_status_label.update()

    def _mode_card(
        self, title: str, description: str, path: str, shortcut: str
    ) -> None:
        """Render a training mode card."""
        with (
            ui.card()
            .classes("metric-card flex-1 h-full cursor-pointer")
            .on("click", lambda: ui.navigate.to(path))
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
            with ui.row().classes("w-full justify-between items-center px-4 py-2"):
                ui.button("← Exit", on_click=lambda: self._exit_session()).classes(
                    "btn-secondary"
                ).props("flat")

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
                ui.button("⏸ Pause", on_click=lambda: self._toggle_pause()).classes(
                    "btn-secondary"
                )
                ui.button("■ Stop", on_click=lambda: self._stop_session()).classes(
                    "btn-primary"
                )

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
            trainer_name = self.controller.trainer.device_info.get(
                "name", "Connected Trainer"
            )

        self.controller.start_session(mode, trainer_name)

        if self._status_label:
            self._status_label.set_text("Session active")

        if self.controller.trainer.is_connected:
            ui.timer(0.0, lambda: self._prepare_trainer_for_session(mode), once=True)
            self._stop_fake_samples()
        else:
            self._start_fake_samples()

        # Start UI update loop in NiceGUI's page context.
        self._update_task = ui.timer(0.1, self._update_metrics, active=True)

    def _start_fake_samples(self) -> None:
        """Start no-hardware development samples for the active session."""
        self._stop_fake_samples()

        hr_handler = self.controller.handle_hr_sample
        if self.controller.hr_service.is_connected:

            def ignore_hr_sample(sample):
                return None

            hr_handler = ignore_hr_sample

        self._fake_source = FakeTrainerSampleSource(
            bike_handler=self.controller.handle_bike_sample,
            hr_handler=hr_handler,
            snapshot_provider=self.controller.snapshot,
            interval_s=1.0,
        )
        self._fake_source.start()
        logger.info("Started fake trainer sample source")

        if self._status_label:
            self._status_label.set_text("Session active (demo data)")

    def _stop_fake_samples(self) -> None:
        """Stop the no-hardware development sample source if it is running."""
        if self._fake_source is None:
            return
        self._fake_source.stop()
        self._fake_source = None

    async def _prepare_trainer_for_session(self, mode: RideMode) -> None:
        """Attach connected trainer data to the active ride session."""
        try:
            if not self.controller.trainer.is_connected:
                return

            await self.controller.trainer.subscribe_samples(
                self.controller.handle_bike_sample
            )

            if mode in {RideMode.ERG, RideMode.SIM}:
                await self.controller.trainer.request_control()
                if mode is RideMode.ERG:
                    await self.controller.trainer.set_target_power(
                        self.controller.metrics.erg_target_w
                    )
                else:
                    await self.controller.trainer.set_simulation(
                        self.controller.metrics.sim_grade_pct
                    )

            logger.info("Trainer sample stream attached to active session")
        except Exception as e:
            logger.warning(f"Failed to prepare trainer for session: {e}")
            if self._status_label:
                self._status_label.set_text("Trainer data unavailable")

    def _update_metrics(self) -> None:
        """Update UI with current metrics."""
        if not self.controller.is_active:
            if self._update_task:
                self._update_task.cancel()
                self._update_task = None
            return

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
        self._stop_fake_samples()
        self.controller.stop_session()
        if self._update_task:
            self._update_task.cancel()

        # Navigate to summary or home
        ui.navigate.to("/")

    def _exit_session(self) -> None:
        """Exit session without saving."""
        self._stop_fake_samples()
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
                trainer_name = (
                    self.controller.trainer.device_info.get("name", "Trainer")
                    if connected
                    else None
                )

                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        dot_class = "connected" if connected else "disconnected"
                        ui.html(
                            f'<span class="status-dot {dot_class}"></span>',
                            sanitize=False,
                        )
                        if connected:
                            status = f"Connected to {trainer_name}"
                        else:
                            status = "Not connected"
                        ui.label(status).classes("text-gray-600")

                    if connected:
                        ui.button(
                            "Disconnect", on_click=lambda: self._disconnect_trainer()
                        ).classes("btn-secondary").style("min-width: 120px")
                    else:
                        ui.button("Scan", on_click=self._scan_trainers).classes(
                            "btn-primary"
                        ).style("min-width: 120px")

            # HR Monitor section
            with ui.card().classes("metric-card w-full"):
                ui.label("Heart Rate Monitor").classes(
                    "text-lg font-medium text-gray-900 mb-4"
                )

                hr_connected = self.controller.hr_service.is_connected
                hr_name = (
                    self.controller.hr_service.device_info.get("name", "HR Monitor")
                    if hr_connected
                    else None
                )

                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        dot_class = "connected" if hr_connected else "disconnected"
                        ui.html(
                            f'<span class="status-dot {dot_class}"></span>',
                            sanitize=False,
                        )
                        if hr_connected:
                            status = f"Connected to {hr_name}"
                        else:
                            status = "Not connected"
                        ui.label(status).classes("text-gray-600")

                    if hr_connected:
                        ui.button(
                            "Disconnect", on_click=lambda: self._disconnect_hr()
                        ).classes("btn-secondary").style("min-width: 120px")
                    else:
                        ui.button("Scan", on_click=self._scan_hr).classes(
                            "btn-primary"
                        ).style("min-width: 120px")

    async def _disconnect_trainer(self) -> None:
        """Disconnect the trainer and refresh the page."""
        try:
            if self.controller.trainer.is_connected:
                await self.controller.trainer.disconnect()
                logger.info("Trainer disconnected via web UI")
            # Refresh page to show updated status
            ui.navigate.to("/devices")
        except Exception as e:
            logger.warning(f"Error disconnecting trainer: {e}")
            ui.notify(f"Disconnect failed: {e}", color="red")

    async def _disconnect_hr(self) -> None:
        """Disconnect the HR monitor and refresh the page."""
        try:
            if self.controller.hr_service.is_connected:
                await self.controller.hr_service.disconnect()
                logger.info("HR monitor disconnected via web UI")
            # Refresh page to show updated status
            ui.navigate.to("/devices")
        except Exception as e:
            logger.warning(f"Error disconnecting HR: {e}")
            ui.notify(f"Disconnect failed: {e}", color="red")

    async def _scan_trainers(self) -> None:
        """Scan for available trainers."""

        async def scan_fn() -> List[Dict[str, Any]]:
            return await self.controller.trainer.scan_available(timeout_s=8.0)

        async def connect_fn(address: str) -> None:
            await self.controller.trainer.connect_to_device(address)

        def on_connected() -> None:
            # Refresh the devices page to show updated connection status
            ui.navigate.to("/devices")

        dialog = ScanDialog(
            title="Trainers",
            device_type="trainer",
            scan_fn=scan_fn,
            connect_fn=connect_fn,
            on_connected=on_connected,
        )
        dialog.show()

    async def _scan_hr(self) -> None:
        """Scan for HR monitors."""

        async def scan_fn() -> List[Dict[str, Any]]:
            return await self.controller.hr_service.scan_available(timeout_s=8.0)

        async def connect_fn(address: str) -> None:
            await self.controller.hr_service.connect_to_device(address)

        def on_connected() -> None:
            # Refresh the devices page to show updated connection status
            ui.navigate.to("/devices")

        dialog = ScanDialog(
            title="Heart Rate Monitors",
            device_type="heart rate monitor",
            scan_fn=scan_fn,
            connect_fn=connect_fn,
            on_connected=on_connected,
        )
        dialog.show()

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
        show=False,
        loop="asyncio",
        storage_secret="terminalride-dev-secret-change-in-production",
    )
