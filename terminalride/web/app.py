"""NiceGUI web interface for TerminalRide.

Clean, minimal design with orange accent.
Big metrics for visibility from bike distance.
Supports multi-user authentication via Supabase.
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any, Callable

from starlette.requests import Request
from nicegui import ui, app

from ..domain.ride_controller import RideController, RideMode
from ..domain.ride_runtime import RideRuntime, RideStopResult
from ..domain.routes import RideRoute, available_routes, route_by_id
from ..domain.session_service import get_session_service
from ..config import UserSettings, get_config
from ..devices.base import DeviceNotFoundError, ConnectionError as DeviceConnectionError
from ..store.export import DataExporter
from ..store.models import SessionModel, SessionSummary
from ..supabase_client import is_supabase_configured
from .auth import AuthManager
from .components.controls import action_button, mode_button
from .components.devices import device_row
from .components.layout import (
    apply_theme,
    panel_header,
    page_container,
    render_app_header,
    render_page_title,
)
from .components.metrics import meta_stat, metric_cell, power_panel
from .components.status import empty_state, status_tile
from .pages import render_login_page
from .ride3d import attach_ride3d_routes
from .snapshot_stream import attach_snapshot_routes

logger = logging.getLogger(__name__)


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
            ui.card().classes("scan-dialog").style("padding: 0; overflow: hidden;"),
        ):
            with ui.row().classes(
                "scan-dialog-header w-full items-center justify-between"
            ):
                ui.label(f"Find {self.title}").classes("tr-panel-title")
                ui.button(icon="close", on_click=self._cancel).props(
                    "flat round dense size=sm"
                ).classes("text-gray-600")

            with ui.column().classes("scan-dialog-body w-full"):
                self._status_label = ui.label("Scanning...").classes("tr-status-meta")

                self._device_container = ui.column().classes("w-full gap-2")

            with ui.row().classes("scan-dialog-footer w-full justify-end"):
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

        with (
            ui.card()
            .classes("scan-device-item w-full cursor-pointer")
            .on(
                "click",
                lambda d=device: self._connect_to_device(d),
            ) as item
        ):
            device["_ui_element"] = item

            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(name).classes("font-medium text-gray-900")
                    if rssi:
                        ui.label(f"Signal: {rssi} dBm").classes("text-xs text-gray-400")

                bar_html = "".join(
                    f'<span class="{"active" if index <= bars else ""}"></span>'
                    for index in range(1, 5)
                )
                ui.html(
                    f'<span class="tr-signal-bars">{bar_html}</span>',
                    sanitize=False,
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


def _get_shared_runtime() -> RideRuntime:
    """Get or create the shared RideRuntime singleton."""
    controller = _get_shared_controller()
    runtime = getattr(app, "_shared_runtime", None)
    if runtime is None or runtime.controller is not controller:
        app._shared_runtime = RideRuntime(controller)
        logger.info("Created shared RideRuntime instance (local mode)")
    return app._shared_runtime


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
        app.storage.user["runtime"] = RideRuntime(app.storage.user["controller"])
        logger.info(f"Created RideController for user {user_id}")
    elif "runtime" not in app.storage.user:
        app.storage.user["runtime"] = RideRuntime(app.storage.user["controller"])

    return app.storage.user["controller"]


def _get_user_runtime() -> RideRuntime:
    """Get or create a per-user RideRuntime instance."""
    _get_user_controller()
    return app.storage.user["runtime"]


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


def get_runtime() -> RideRuntime:
    """Get the runtime that owns sample-source lifecycle for this context."""
    if is_supabase_configured() and AuthManager.is_authenticated():
        return _get_user_runtime()
    return _get_shared_runtime()


class WebUI:
    """Web-based UI for TerminalRide."""

    def __init__(self) -> None:
        # Controller is now retrieved dynamically per request
        # Don't store a reference here - get it fresh each time
        self._update_task: Optional[Any] = None
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
        self._state_badge: Optional[ui.html] = None
        self._pause_button: Optional[Any] = None
        self._route_segment_label: Optional[ui.label] = None
        self._route_next_label: Optional[ui.label] = None
        self._route_progress_label: Optional[ui.label] = None

    @property
    def controller(self) -> RideController:
        """Get the controller for the current context.

        This property dynamically retrieves the appropriate controller,
        supporting both local mode (singleton) and multi-user mode (per-user).
        """
        return get_controller()

    @property
    def runtime(self) -> RideRuntime:
        """Get the ride runtime for the current context."""
        return get_runtime()

    def _auto_connect_enabled(self) -> bool:
        """True when automatic BLE scanning is explicitly enabled."""
        flag = os.getenv("TERMINALRIDE_ENABLE_BLE", "").lower()
        return (
            flag in {"1", "true", "yes"} and get_config().settings.auto_connect_trainer
        )

    def _default_route_id(self) -> str:
        """Return a valid configured default SIM route id."""
        configured_route_id = get_config().settings.default_sim_route_id
        try:
            return route_by_id(configured_route_id).route_id
        except Exception:
            return route_by_id(None).route_id

    def _route_select_options(self) -> dict[str, str]:
        """Return route select options keyed by stable route id."""
        return {route.route_id: route.title for route in available_routes()}

    def _set_last_stop_result(self, result: RideStopResult) -> None:
        """Store the latest stop result for the current UI context."""
        if is_supabase_configured() and AuthManager.is_authenticated():
            app.storage.user["last_stop_result"] = result
        else:
            app._last_stop_result = result

    def _get_last_stop_result(self) -> object:
        """Return the latest stop result for the current UI context."""
        if is_supabase_configured() and AuthManager.is_authenticated():
            return app.storage.user.get("last_stop_result")
        return getattr(app, "_last_stop_result", None)

    def setup(self) -> None:
        """Set up the web UI routes and pages."""
        if not getattr(app, "_terminalride_snapshot_routes_attached", False):
            attach_snapshot_routes(app, get_controller)
            attach_ride3d_routes(app, get_runtime)
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
        def session_page(mode: str, request: Request):
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_session(mode, request.query_params.get("route_id"))

        @ui.page("/summary")
        def summary_page():
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_stop_summary()

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

        @ui.page("/history/{session_id}")
        def history_detail_page(session_id: str):
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_history_detail(session_id)

        @ui.page("/settings")
        def settings_page():
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_settings()

        @ui.page("/design-system")
        def design_system_page():
            if is_supabase_configured() and not AuthManager.is_authenticated():
                ui.navigate.to("/login")
                return
            self._render_design_system()

    def _render_header(self, current: str = "") -> None:
        """Render the navigation header."""
        apply_theme()
        user = (
            AuthManager.get_current_user()
            if is_supabase_configured() and AuthManager.is_authenticated()
            else None
        )
        render_app_header(current, user=user)

    async def _render_home_with_auto_connect(self) -> None:
        """Render home page with automatic device connection on first load.

        Mirrors CLI behavior: automatically scan and connect to trainer
        when the app first loads, providing seamless device discovery.
        """
        self._render_header("Home")

        selected_mode = {"value": "free"}
        selected_route_id = {"value": self._default_route_id()}
        mode_buttons: Dict[str, Any] = {}
        mode_title: Optional[ui.label] = None
        mode_detail: Optional[ui.label] = None
        route_title: Optional[ui.label] = None
        route_detail: Optional[ui.label] = None
        route_distance: Optional[ui.label] = None
        route_gain: Optional[ui.label] = None
        route_grade: Optional[ui.label] = None
        route_badge: Optional[ui.label] = None

        def set_mode(mode: str) -> None:
            selected_mode["value"] = mode
            for key, button in mode_buttons.items():
                if key == mode:
                    button.classes(add="active")
                else:
                    button.classes(remove="active")
            titles = {
                "free": "Free Ride",
                "erg": "ERG Mode",
                "sim": "SIM Mode",
            }
            details = {
                "free": "No resistance control. Start a responsive no-fuss ride.",
                "erg": (
                    f"Target starts at {self.controller.metrics.erg_target_w} W. "
                    "Adjust during the ride."
                ),
                "sim": "Ride a bundled grade profile with segment context.",
            }
            if mode_title:
                mode_title.set_text(titles[mode])
            if mode_detail:
                mode_detail.set_text(details[mode])

        def set_route(route_id: str) -> None:
            selected_route_id["value"] = route_id
            route = route_by_id(route_id)
            if route_title:
                route_title.set_text(route.title)
            if route_detail:
                route_detail.set_text(route.description)
            if route_distance:
                route_distance.set_text(f"{route.distance_m / 1000:.2f}")
            if route_gain:
                route_gain.set_text(f"{route.elevation_gain_m:.0f}")
            if route_grade:
                route_grade.set_text(f"{route.max_grade_pct:.1f}")
            if route_badge:
                route_badge.set_text(route.difficulty)

        def start_selected() -> None:
            path = f"/session/{selected_mode['value']}"
            if selected_mode["value"] == "sim":
                path += f"?route_id={selected_route_id['value']}"
            ui.navigate.to(path)

        with page_container():
            with ui.row().classes("tr-hero-row w-full items-end justify-between gap-4"):
                render_page_title(
                    "Ride console",
                    "Start clean. Ride steady.",
                    "Trainer readiness, ride mode, and live data source in one control surface.",
                )
                action_button(
                    "Open 3D View",
                    lambda: ui.navigate.to("/ride3d"),
                    variant="secondary",
                )

            connected = self.controller.trainer.is_connected
            trainer_name = self.controller.trainer.device_info.get("name", "Trainer")
            hr_connected = self.controller.hr_service.is_connected
            hr_name = self.controller.hr_service.device_info.get("name", "HR Monitor")

            with ui.element("div").classes("tr-status-strip"):
                trainer_tile = status_tile(
                    "Trainer",
                    (
                        f"Connected to {trainer_name}"
                        if connected
                        else (
                            "Searching for trainer"
                            if self._auto_connect_enabled()
                            else "Demo data until paired"
                        )
                    ),
                    connected=connected,
                )
                self._connection_dot = trainer_tile["dot"]
                self._connection_status_label = trainer_tile["detail"]
                status_tile(
                    "Heart rate",
                    f"Connected to {hr_name}" if hr_connected else "Optional monitor",
                    connected=hr_connected,
                )
                status_tile(
                    "Source",
                    "Live BLE stream" if connected else "No-hardware demo",
                    connected=connected or hr_connected,
                )

            with ui.element("div").classes("tr-console-grid"):
                with ui.column().classes("tr-panel tr-console-main p-5"):
                    panel_header(
                        "Ride setup",
                        "Choose the training mode before launching the cockpit.",
                        badge="Ready" if connected else "Demo",
                    )

                    with ui.element("div").classes("tr-mode-grid"):
                        for key, label in [
                            ("free", "Free"),
                            ("erg", "ERG"),
                            ("sim", "SIM"),
                        ]:
                            mode_buttons[key] = mode_button(
                                label,
                                lambda key=key: set_mode(key),
                                active=key == "free",
                            )

                    with ui.element("div").classes("tr-control-band"):
                        with ui.column().classes("gap-3"):
                            with ui.row().classes("items-start justify-between gap-4"):
                                with ui.column().classes("gap-1"):
                                    mode_title = ui.label("Free Ride").classes(
                                        "tr-panel-title"
                                    )
                                    mode_detail = ui.label(
                                        "No resistance control. Start a responsive no-fuss ride."
                                    ).classes("tr-subtitle")
                                ui.label("00:00").classes("tr-control-value")

                            with ui.element("div").classes("tr-meta-grid"):
                                meta_stat(
                                    f"{self.controller.metrics.erg_target_w}",
                                    "ERG target W",
                                )
                                meta_stat(
                                    f"{self.controller.metrics.sim_grade_pct:.1f}",
                                    "SIM grade %",
                                )

                    with ui.element("div").classes("tr-route-picker"):
                        route = route_by_id(selected_route_id["value"])
                        with ui.row().classes("items-center justify-between gap-3"):
                            with ui.column().classes("gap-1"):
                                route_title = ui.label(route.title).classes(
                                    "tr-panel-title"
                                )
                                route_detail = ui.label(route.description).classes(
                                    "tr-subtitle"
                                )
                            route_badge = ui.label(route.difficulty).classes(
                                "tr-state-badge ready"
                            )
                        ui.select(
                            self._route_select_options(),
                            value=selected_route_id["value"],
                            label="SIM route",
                            on_change=lambda event: set_route(str(event.value)),
                        ).classes("w-full")
                        with ui.element("div").classes("tr-meta-grid tr-route-stats"):
                            route_distance = meta_stat(
                                f"{route.distance_m / 1000:.2f}",
                                "Distance km",
                            )
                            route_gain = meta_stat(
                                f"{route.elevation_gain_m:.0f}",
                                "Gain m",
                            )
                            route_grade = meta_stat(
                                f"{route.max_grade_pct:.1f}",
                                "Max grade %",
                            )
                            meta_stat(str(len(route.segments)), "Segments")

                    with ui.element("div").classes("tr-btn-row"):
                        action_button(
                            "Start Ride",
                            start_selected,
                            variant="primary",
                            min_width="170px",
                        )
                        action_button(
                            "Devices",
                            lambda: ui.navigate.to("/devices"),
                            variant="secondary",
                        )

                with ui.column().classes("tr-console-side"):
                    with ui.column().classes("tr-panel p-5 gap-4"):
                        panel_header(
                            "3D Road",
                            "Visualization surface fed by the same snapshot stream.",
                            badge="View",
                        )
                        ui.element("div").classes("tr-road-preview")
                        action_button(
                            "Open 3D View",
                            lambda: ui.navigate.to("/ride3d"),
                            variant="secondary",
                        )

                    with ui.column().classes("tr-panel p-5 gap-4"):
                        panel_header(
                            "Recent rides",
                            "A real log shell, kept empty until sessions are loaded.",
                        )
                        with ui.element("div").classes("tr-table-shell"):
                            with ui.element("div").classes(
                                "tr-table-row tr-table-head"
                            ):
                                ui.label("Session")
                                ui.label("Mode")
                                ui.label("Time")
                                ui.label("Power")
                            empty_state(
                                "No sessions recorded yet",
                                "Completed rides will appear here with duration, mode, and key metrics.",
                                action_label="History",
                                on_action=lambda: ui.navigate.to("/history"),
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

    def _render_session(self, mode: str, route_id: str | None = None) -> None:
        """Render the full-screen session cockpit."""
        apply_theme()

        mode_enum = {
            "free": RideMode.FREE,
            "erg": RideMode.ERG,
            "sim": RideMode.SIM,
        }.get(mode, RideMode.FREE)

        mode_title = {"free": "Free Ride", "erg": "ERG Mode", "sim": "SIM Mode"}.get(
            mode, "Free Ride"
        )
        route: RideRoute | None = None
        if mode_enum is RideMode.SIM:
            try:
                route = route_by_id(route_id or self._default_route_id())
            except Exception:
                route = route_by_id(None)
            self.runtime.set_route_profile(route)

        with ui.element("div").classes("session-view"):
            with ui.element("div").classes("tr-cockpit"):
                with ui.element("div").classes("tr-cockpit-top"):
                    action_button("Exit", lambda: self._exit_session())
                    with ui.element("div").classes("tr-cockpit-statusbar"):
                        self._state_badge = ui.html(
                            '<span class="tr-state-badge live">Active</span>',
                            sanitize=False,
                        )
                        ui.label(mode_title).classes("tr-section-label")
                        self._status_label = ui.label("Starting session").classes(
                            "text-sm font-semibold text-gray-600"
                        )
                    self._time_label = ui.label("00:00").classes("tr-control-value")

                with ui.element("div").classes("tr-panel tr-power-panel"):
                    self._power_label = power_panel()
                    if mode == "erg":
                        with ui.row().classes("items-center justify-center gap-3 mt-6"):
                            action_button(
                                "-10 W",
                                lambda: self._adjust_target(-10),
                            )
                            self._target_label = ui.label("Target 150 W").classes(
                                "text-lg font-extrabold text-gray-700"
                            )
                            action_button(
                                "+10 W",
                                lambda: self._adjust_target(10),
                            )
                    elif mode == "sim":
                        with ui.row().classes("items-center justify-center gap-3 mt-6"):
                            action_button(
                                "-0.5%",
                                lambda: self._adjust_sim_grade(-0.5),
                            )
                            self._target_label = ui.label("Grade 0.0%").classes(
                                "text-lg font-extrabold text-gray-700"
                            )
                            action_button(
                                "+0.5%",
                                lambda: self._adjust_sim_grade(0.5),
                            )
                        if route is not None:
                            with ui.element("div").classes("tr-route-live"):
                                self._route_segment_label = ui.label(
                                    route.segments[0].name
                                ).classes("tr-panel-title")
                                self._route_next_label = ui.label(
                                    f"Next {route.segments[1 % len(route.segments)].name}"
                                ).classes("tr-subtitle")
                                self._route_progress_label = ui.label(
                                    f"0.00 / {route.distance_m / 1000:.2f} km"
                                ).classes("tr-status-meta")

                with ui.element("div").classes("tr-metric-rail"):
                    self._cadence_label = metric_cell("--", "Cadence RPM")
                    self._hr_label = metric_cell("--", "Heart BPM")
                    self._speed_label = metric_cell("--", "Speed km/h")
                    self._distance_label = metric_cell("--", "Distance km")
                    metric_cell(mode.upper(), "Mode")

                with ui.element("div").classes("tr-cockpit-controls"):
                    self._pause_button = action_button(
                        "Pause", lambda: self._toggle_pause()
                    )
                    with ui.element("div").classes("tr-cockpit-statusbar"):
                        ui.label("Power cockpit").classes("tr-section-label")
                        source_label = (
                            "Live trainer data"
                            if self.controller.trainer.is_connected
                            else "Demo samples"
                        )
                        ui.label(source_label).classes("tr-status-meta")
                    action_button(
                        "Stop Ride",
                        lambda: self._stop_session(),
                        variant="primary",
                    )

        # Start session and update loop
        self._start_session(mode_enum)

    def _start_session(self, mode: RideMode) -> None:
        """Start a training session."""
        self.runtime.start_session(mode)

        if self._status_label:
            label = (
                "Waiting for trainer data"
                if self.controller.trainer.is_connected
                else "Session active (demo data)"
            )
            self._status_label.set_text(label)

        if (
            self.controller.trainer.is_connected
            or self.controller.hr_service.is_connected
        ):
            ui.timer(0.0, lambda: self._prepare_trainer_for_session(mode), once=True)

        # Start UI update loop in NiceGUI's page context.
        self._update_task = ui.timer(0.1, self._update_metrics, active=True)

    async def _prepare_trainer_for_session(self, mode: RideMode) -> None:
        """Attach connected hardware data to the active ride session."""
        await self.runtime.prepare_hardware_session(mode)

    def _update_metrics(self) -> None:
        """Update UI with current metrics."""
        if not self.controller.is_active:
            if self._update_task:
                self._update_task.cancel()
                self._update_task = None
            return

        metrics = self.controller.metrics
        self._update_session_status()

        # Update power
        if self._power_label:
            power = metrics.power_w if metrics.power_w is not None else "---"
            self._power_label.set_text(str(power))

        # Update cadence
        if self._cadence_label:
            cad = metrics.cadence_rpm if metrics.cadence_rpm is not None else "--"
            self._cadence_label.set_text(str(cad))

        # Update HR
        if self._hr_label:
            hr = metrics.hr_bpm if metrics.hr_bpm is not None else "--"
            self._hr_label.set_text(str(hr))

        # Update speed
        if self._speed_label:
            if metrics.speed_mps is not None:
                speed_kph = metrics.speed_mps * 3.6
                self._speed_label.set_text(f"{speed_kph:.1f}")
            else:
                self._speed_label.set_text("--")

        # Update distance
        if self._distance_label:
            dist_km = metrics.distance_m / 1000
            self._distance_label.set_text(f"{dist_km:.2f}")

        # Update time
        if self._time_label:
            elapsed = int(metrics.elapsed_s)
            mins, secs = divmod(elapsed, 60)
            self._time_label.set_text(f"{mins:02d}:{secs:02d}")

        # Update target for ERG
        if self._target_label:
            if self.controller.state.mode is RideMode.SIM:
                self._target_label.set_text(f"Grade {metrics.sim_grade_pct:.1f}%")
            else:
                self._target_label.set_text(f"Target {metrics.erg_target_w} W")

        # Update SIM route context
        route = self.runtime.route_profile
        if isinstance(route, RideRoute) and self.controller.state.mode is RideMode.SIM:
            position = route.position_at(metrics.distance_m)
            if self._route_segment_label:
                self._route_segment_label.set_text(
                    f"{position.segment.name} · {position.segment.grade_pct:.1f}%"
                )
            if self._route_next_label:
                self._route_next_label.set_text(
                    "Next "
                    f"{position.next_segment.name} in "
                    f"{position.segment_remaining_m:.0f} m · "
                    f"{position.next_segment.grade_pct:.1f}%"
                )
            if self._route_progress_label:
                self._route_progress_label.set_text(
                    f"{position.route_distance_m / 1000:.2f} / "
                    f"{route.distance_m / 1000:.2f} km · "
                    f"{position.route_progress:.0%}"
                )

    def _update_session_status(self) -> None:
        """Keep the cockpit status honest while hardware samples start flowing."""
        if self._status_label is None or self.controller.is_paused:
            return

        if (
            self.controller.trainer.is_connected
            and self.controller.recorded_sample_count == 0
        ):
            self._status_label.set_text("Waiting for trainer data")
            return

        label = (
            "Session active"
            if self.controller.trainer.is_connected
            else "Session active (demo data)"
        )
        self._status_label.set_text(label)

    def _adjust_target(self, delta: int) -> None:
        """Adjust ERG target power."""
        self.runtime.adjust_erg_target(delta)

    def _adjust_sim_grade(self, delta: float) -> None:
        """Adjust SIM grade."""
        self.runtime.adjust_sim_grade(delta)

    def _toggle_pause(self) -> None:
        """Toggle session pause."""
        snapshot = self.runtime.toggle_pause()
        if self._status_label:
            self._status_label.set_text(
                "Paused" if snapshot.paused else "Session active"
            )
        if self._pause_button:
            self._pause_button.set_text("Resume" if snapshot.paused else "Pause")
        if self._state_badge:
            badge_class = "demo" if snapshot.paused else "live"
            badge_text = "Paused" if snapshot.paused else "Active"
            self._state_badge.set_content(
                f'<span class="tr-state-badge {badge_class}">{badge_text}</span>'
            )

    def _stop_session(self) -> None:
        """Stop the current session."""
        result = self.runtime.stop_session_result()
        self._set_last_stop_result(result)
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None
        ui.navigate.to("/summary")

    def _exit_session(self) -> None:
        """Exit session without saving."""
        if self.controller.is_active:
            self.runtime.stop_session()
        if self._update_task:
            self._update_task.cancel()
        ui.navigate.to("/")

    def _render_stop_summary(self) -> None:
        """Render the post-ride stop result."""
        self._render_header("Summary")
        result = self._get_last_stop_result()

        with page_container():
            render_page_title(
                "Ride summary",
                "Stopped session result.",
                "Saved rides are available in history and can be exported as CSV.",
            )

            if not isinstance(result, RideStopResult):
                empty_state(
                    "No stopped ride to summarize",
                    "Start and stop a ride to see its summary here.",
                    action_label="Start Ride",
                    on_action=lambda: ui.navigate.to("/"),
                    action_variant="primary",
                )
                return

            snapshot = result.snapshot
            saved_label = "Saved" if result.saved else "Not saved"
            if result.persistence_error:
                saved_label = "Save failed"
            elif result.sample_count == 0:
                saved_label = "No samples"

            with ui.column().classes("tr-panel p-5 gap-4"):
                panel_header(
                    "Stopped ride",
                    saved_label,
                    badge="Saved" if result.saved else "Review",
                )
                with ui.element("div").classes("tr-meta-grid tr-summary-grid"):
                    meta_stat(self._format_duration(snapshot.elapsed_s), "Duration")
                    meta_stat(
                        self._format_distance(snapshot.distance_m),
                        "Distance",
                    )
                    meta_stat(self._format_power(snapshot.power_w), "Last power")
                    meta_stat(str(result.sample_count), "Samples")

                if result.persistence_error:
                    with ui.element("div").classes("connection-status error"):
                        ui.icon("error")
                        ui.label(
                            f"Session could not be saved: {result.persistence_error}"
                        )
                elif result.sample_count == 0:
                    with ui.element("div").classes("connection-status info"):
                        ui.icon("info")
                        ui.label(
                            "No trainer or demo samples were captured, so nothing was written to history."
                        )

                with ui.element("div").classes("tr-btn-row"):
                    action_button(
                        "Start Ride",
                        lambda: ui.navigate.to("/"),
                        variant="primary",
                    )
                    action_button(
                        "History",
                        lambda: ui.navigate.to("/history"),
                        variant="secondary",
                    )
                    if result.saved_session_id:
                        action_button(
                            "Export CSV",
                            lambda session_id=result.saved_session_id: self._export_session(
                                session_id
                            ),
                            variant="secondary",
                        )

    def _render_devices(self) -> None:
        """Render the devices management page."""
        self._render_header("Devices")

        with page_container():
            render_page_title(
                "Hardware bay",
                "Pair the sensors that drive the ride.",
                "Trainer and heart-rate state stay separate from the ride UI so future surfaces can reuse them.",
            )

            with ui.column().classes("tr-panel p-5 gap-3"):
                panel_header(
                    "Devices",
                    "Each row exposes connection state, signal, and the next action.",
                    badge="Hardware",
                )

                trainer_status = self.controller.trainer.connection_status()
                device_row(
                    "FTMS trainer",
                    (
                        f"Connected to {trainer_status.name or 'Trainer'}"
                        if trainer_status.connected
                        else "Not connected. Demo samples are available."
                    ),
                    connected=trainer_status.connected,
                    action_label="Disconnect" if trainer_status.connected else "Scan",
                    on_action=(
                        lambda: (
                            self._disconnect_trainer()
                            if trainer_status.connected
                            else self._scan_trainers()
                        )
                    ),
                    action_variant=(
                        "secondary" if trainer_status.connected else "primary"
                    ),
                    signal_bars=(
                        _rssi_to_bars(trainer_status.rssi)
                        if trainer_status.connected
                        else 0
                    ),
                    state_label="Paired" if trainer_status.connected else "Demo",
                )

                hr_status = self.controller.hr_service.connection_status()
                device_row(
                    "Heart-rate monitor",
                    (
                        f"Connected to {hr_status.name or 'HR Monitor'}"
                        if hr_status.connected
                        else "Optional. Pair a standard BLE HR strap."
                    ),
                    connected=hr_status.connected,
                    action_label="Disconnect" if hr_status.connected else "Scan",
                    on_action=(
                        lambda: (
                            self._disconnect_hr()
                            if hr_status.connected
                            else self._scan_hr()
                        )
                    ),
                    action_variant="secondary" if hr_status.connected else "primary",
                    signal_bars=(
                        _rssi_to_bars(hr_status.rssi) if hr_status.connected else 0
                    ),
                    state_label="Paired" if hr_status.connected else "Optional",
                )

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
            devices = await self.controller.trainer.scan_devices(timeout_s=8.0)
            return [device.to_dict() for device in devices]

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
            devices = await self.controller.hr_service.scan_devices(timeout_s=8.0)
            return [device.to_dict() for device in devices]

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
        try:
            sessions = get_session_service().list_sessions(limit=50)
        except Exception as exc:
            logger.warning("Failed to load session history: %s", exc)
            sessions = []

        with page_container():
            render_page_title(
                "Training log",
                "Completed rides from the local training repository.",
                "Only recorded sessions are shown here; demo rows are intentionally not invented.",
            )

            with ui.column().classes("tr-panel p-5 gap-3"):
                panel_header(
                    "Sessions",
                    "Duration, mode, power, and distance from saved rides.",
                    badge="Log",
                )
                with ui.element("div").classes("tr-table-shell"):
                    with ui.element("div").classes("tr-table-row tr-table-head"):
                        ui.label("Session")
                        ui.label("Mode")
                        ui.label("Duration")
                        ui.label("Power")
                        ui.label("Distance")
                        ui.label("Actions")
                    if sessions:
                        for session in sessions:
                            with ui.element("div").classes(
                                "tr-table-row tr-table-row-actions"
                            ):
                                ui.label(
                                    session.start_time.strftime("%Y-%m-%d %H:%M")
                                ).classes("font-bold text-gray-900")
                                ui.label(session.mode.value.upper())
                                ui.label(self._format_duration(session.duration_s))
                                ui.label(self._format_power(session.avg_power_w))
                                ui.label(
                                    self._format_distance(session.total_distance_m)
                                )
                                with ui.row().classes("gap-2"):
                                    action_button(
                                        "View",
                                        lambda session_id=session.session_id: ui.navigate.to(
                                            f"/history/{session_id}"
                                        ),
                                        variant="secondary",
                                    )
                                    action_button(
                                        "CSV",
                                        lambda session_id=session.session_id: self._export_session(
                                            session_id
                                        ),
                                        variant="secondary",
                                    )
                    else:
                        empty_state(
                            "No sessions recorded yet",
                            "Start and stop a ride to populate this log.",
                            action_label="Start Ride",
                            on_action=lambda: ui.navigate.to("/"),
                            action_variant="primary",
                        )

    def _render_history_detail(self, session_id: str) -> None:
        """Render one persisted session with summary and export actions."""
        self._render_header("History")
        service = get_session_service()
        session = service.get_session(session_id)
        summary = service.get_session_summary(session_id)

        with page_container():
            render_page_title(
                "Session detail",
                "Saved ride metrics and export.",
                "CSV export writes a local file under the app data directory.",
            )

            if session is None:
                empty_state(
                    "Session not found",
                    "This ride is no longer available in local history.",
                    action_label="Back to History",
                    on_action=lambda: ui.navigate.to("/history"),
                )
                return

            with ui.column().classes("tr-panel p-5 gap-4"):
                route_label = self._session_route_label(session)
                panel_header(
                    session.start_time.strftime("%Y-%m-%d %H:%M"),
                    route_label or f"{session.mode.value.upper()} ride",
                    badge=session.mode.value.upper(),
                )
                self._render_session_summary_stats(session, summary)
                with ui.element("div").classes("tr-btn-row"):
                    action_button(
                        "Export CSV",
                        lambda: self._export_session(session.session_id),
                        variant="primary",
                    )
                    action_button(
                        "Back to History",
                        lambda: ui.navigate.to("/history"),
                        variant="secondary",
                    )

    def _render_session_summary_stats(
        self,
        session: SessionModel,
        summary: SessionSummary | None,
    ) -> None:
        """Render compact stats for a persisted session."""
        distance_m = (
            summary.total_distance_m
            if summary is not None
            else session.total_distance_m
        )
        avg_power_w = (
            summary.avg_power_w if summary is not None else session.avg_power_w
        )
        avg_hr_bpm = summary.avg_hr_bpm if summary is not None else session.avg_hr_bpm
        normalized_power_w = (
            summary.normalized_power_w
            if summary is not None
            else session.normalized_power_w
        )
        intensity_factor = (
            summary.intensity_factor
            if summary is not None
            else session.intensity_factor
        )
        training_stress_score = (
            summary.training_stress_score
            if summary is not None
            else session.training_stress_score
        )

        with ui.element("div").classes("tr-meta-grid tr-summary-grid"):
            meta_stat(self._format_duration(session.duration_s), "Duration")
            meta_stat(self._format_distance(distance_m), "Distance")
            meta_stat(self._format_power(avg_power_w), "Avg power")
            meta_stat(self._format_power(session.max_power_w), "Max power")
            meta_stat(self._format_bpm(avg_hr_bpm), "Avg HR")
            meta_stat(self._format_bpm(session.max_hr_bpm), "Max HR")
            meta_stat(self._format_power(normalized_power_w), "NP")
            meta_stat(self._format_ratio(intensity_factor), "IF")
            meta_stat(self._format_score(training_stress_score), "TSS")
            meta_stat(str(session.user_ftp_w), "FTP W")

    @staticmethod
    def _session_route_label(session: SessionModel) -> str | None:
        if session.sim_route_title:
            return f"SIM route: {session.sim_route_title}"
        if session.sim_grade_pct is not None:
            return f"SIM grade {session.sim_grade_pct:.1f}%"
        if session.erg_target_power_w is not None:
            return f"ERG target {session.erg_target_power_w} W"
        return None

    def _export_session(self, session_id: str) -> None:
        """Export a saved session to CSV and notify the user."""
        output_path = DataExporter().auto_export_session(session_id)
        if output_path is None:
            ui.notify("CSV export failed", color="red")
            return
        ui.notify(f"CSV exported to {output_path}", color="green")

    def _render_settings(self) -> None:
        """Render the settings page."""
        self._render_header("Settings")

        config = get_config()

        with page_container():
            render_page_title(
                "Configuration",
                "Ride profile and defaults.",
                "These settings feed trainer control, simulation physics, and training metrics.",
            )

            with ui.column().classes("tr-panel p-5 gap-4"):
                panel_header(
                    "Profile",
                    "Rider inputs used by trainer control and simulation physics.",
                    badge="Config",
                )

                with ui.column().classes("gap-4"):
                    name_input = ui.input(
                        "Name",
                        value=config.settings.name or "",
                    ).classes("w-full")

                    with ui.element("div").classes("tr-form-grid"):
                        mass_input = ui.number(
                            "Weight (kg)",
                            value=config.settings.mass_kg,
                            min=40,
                            max=200,
                        ).classes("w-full")
                        ftp_input = ui.number(
                            "FTP (watts)",
                            value=config.settings.ftp_w,
                            min=50,
                            max=600,
                        ).classes("w-full")

                    with ui.element("div").classes("tr-form-grid"):
                        max_hr_input = ui.number(
                            "Max HR (bpm)",
                            value=config.settings.max_hr_bpm or 180,
                            min=100,
                            max=230,
                        ).classes("w-full")
                        age_input = ui.number(
                            "Age",
                            value=config.settings.age or 30,
                            min=10,
                            max=100,
                        ).classes("w-full")

                    panel_header(
                        "Ride defaults",
                        "Defaults used when a new cockpit session starts.",
                        badge="MVP",
                    )
                    with ui.element("div").classes("tr-form-grid"):
                        erg_target_input = ui.number(
                            "Default ERG target (W)",
                            value=config.settings.default_erg_power_w,
                            min=100,
                            max=400,
                        ).classes("w-full")
                        sim_grade_input = ui.number(
                            "Manual SIM grade (%)",
                            value=config.settings.default_sim_grade_pct,
                            min=-10,
                            max=15,
                            step=0.5,
                        ).classes("w-full")

                    with ui.element("div").classes("tr-form-grid"):
                        route_select = ui.select(
                            self._route_select_options(),
                            value=self._default_route_id(),
                            label="Default SIM route",
                        ).classes("w-full")
                        speed_source_select = ui.select(
                            {
                                "trainer": "Trainer reported",
                                "virtual": "Virtual physics",
                                "auto": "Auto",
                            },
                            value=config.settings.speed_source,
                            label="Speed source",
                        ).classes("w-full")

                    panel_header(
                        "App preferences",
                        "Units and connection startup behavior.",
                        badge="Local",
                    )
                    with ui.element("div").classes("tr-form-grid"):
                        units_select = ui.select(
                            {"metric": "Metric", "imperial": "Imperial"},
                            value=config.settings.units,
                            label="Units",
                        ).classes("w-full")
                        reconnect_timeout_input = ui.number(
                            "Reconnect timeout (s)",
                            value=config.settings.reconnect_timeout_s,
                            min=5,
                            max=300,
                        ).classes("w-full")

                    auto_connect_trainer_switch = ui.switch(
                        "Auto-connect trainer when BLE auto-scan is enabled",
                        value=config.settings.auto_connect_trainer,
                    )
                    auto_connect_hr_switch = ui.switch(
                        "Auto-connect heart-rate monitor",
                        value=config.settings.auto_connect_hr,
                    )

            action_button(
                "Save Settings",
                lambda: self._save_settings(
                    name_input.value,
                    mass_input.value,
                    ftp_input.value,
                    max_hr_input.value,
                    age_input.value,
                    erg_target_input.value,
                    sim_grade_input.value,
                    route_select.value,
                    speed_source_select.value,
                    units_select.value,
                    auto_connect_trainer_switch.value,
                    auto_connect_hr_switch.value,
                    reconnect_timeout_input.value,
                ),
                variant="primary",
            )

    def _render_design_system(self) -> None:
        """Render the web component preview surface."""
        self._render_header("")

        with page_container():
            render_page_title(
                "Design system",
                "Light console components.",
                "Reusable NiceGUI building blocks for the current web UI and future surfaces.",
            )

            with ui.element("div").classes("tr-status-strip"):
                status_tile("Trainer", "Connected to FTMS Bike", connected=True)
                status_tile("Heart rate", "Optional monitor", connected=False)
                status_tile("Source", "No-hardware demo", connected=True)

            with ui.element("div").classes("tr-console-grid"):
                with ui.column().classes("tr-panel p-5 gap-4"):
                    panel_header(
                        "Controls",
                        "Primary action, secondary action, and segmented modes.",
                        badge="Ready",
                    )
                    with ui.element("div").classes("tr-mode-grid"):
                        mode_button("Free", lambda: None, active=True)
                        mode_button("ERG", lambda: None)
                        mode_button("SIM", lambda: None)
                    with ui.element("div").classes("tr-btn-row"):
                        action_button("Start Ride", lambda: None, variant="primary")
                        action_button("Open 3D View", lambda: None)
                    with ui.element("div").classes("tr-meta-grid"):
                        meta_stat("150", "ERG target W")
                        meta_stat("0.0", "SIM grade %")

                with ui.column().classes("tr-panel p-5 gap-4"):
                    panel_header(
                        "Hardware row",
                        "Device rows include state, signal, and one next action.",
                        badge="Hardware",
                    )
                    device_row(
                        "FTMS trainer",
                        "Connected to Kickr Core",
                        connected=True,
                        action_label="Disconnect",
                        on_action=lambda: None,
                        action_variant="secondary",
                        signal_bars=4,
                        state_label="Paired",
                    )
                    device_row(
                        "Heart-rate monitor",
                        "Optional. Pair a standard BLE HR strap.",
                        connected=False,
                        action_label="Scan",
                        on_action=lambda: None,
                        signal_bars=0,
                        state_label="Optional",
                    )

            with ui.column().classes("tr-panel p-5 gap-4"):
                panel_header(
                    "Metric geometry",
                    "Power, secondary metrics, and empty table shells.",
                    badge="Cockpit",
                )
                with ui.element("div").classes("tr-power-panel tr-panel-tight"):
                    power_panel("186")
                with ui.element("div").classes("tr-metric-rail"):
                    metric_cell("92", "Cadence RPM")
                    metric_cell("148", "Heart BPM")
                    metric_cell("31.4", "Speed km/h")
                    metric_cell("12.08", "Distance km")
                    metric_cell("ERG", "Mode")
                with ui.element("div").classes("tr-table-shell"):
                    with ui.element("div").classes("tr-table-row tr-table-head"):
                        ui.label("Session")
                        ui.label("Mode")
                        ui.label("Duration")
                        ui.label("Power")
                    empty_state(
                        "No sessions recorded yet",
                        "The shell is designed without fake training data.",
                    )

    def _save_settings(
        self,
        name: object,
        mass_kg: object,
        ftp_w: object,
        max_hr_bpm: object,
        age: object,
        default_erg_power_w: object,
        default_sim_grade_pct: object,
        default_sim_route_id: object,
        speed_source: object,
        units: object,
        auto_connect_trainer: object,
        auto_connect_hr: object,
        reconnect_timeout_s: object,
    ) -> None:
        """Validate and persist user settings."""
        config = get_config()

        try:
            data = config.settings.model_dump()
            data.update(
                {
                    "name": (str(name).strip() if name is not None else "") or "Rider",
                    "mass_kg": self._required_float(mass_kg),
                    "ftp_w": self._optional_int(ftp_w),
                    "max_hr_bpm": self._optional_int(max_hr_bpm),
                    "age": self._required_int(age),
                    "default_erg_power_w": self._required_int(default_erg_power_w),
                    "default_sim_grade_pct": self._required_float(
                        default_sim_grade_pct
                    ),
                    "default_sim_route_id": self._required_route_id(
                        default_sim_route_id
                    ),
                    "speed_source": str(speed_source),
                    "units": str(units),
                    "auto_connect_trainer": bool(auto_connect_trainer),
                    "auto_connect_hr": bool(auto_connect_hr),
                    "reconnect_timeout_s": self._required_int(reconnect_timeout_s),
                }
            )
            settings = UserSettings.model_validate(data)
        except Exception as exc:
            ui.notify(f"Settings invalid: {exc}", color="red")
            return

        config.settings = settings
        config.user_mass_kg = settings.mass_kg
        config.user_ftp_w = settings.ftp_w if settings.ftp_w is not None else 250
        config.connection_timeout_s = settings.reconnect_timeout_s
        config.save_settings()
        ui.notify("Settings saved!", color="green")

    @staticmethod
    def _required_float(value: object) -> float:
        if value is None or value == "":
            raise ValueError("Expected a numeric value")
        return float(str(value))

    @staticmethod
    def _required_int(value: object) -> int:
        if value is None or value == "":
            raise ValueError("Expected an integer value")
        return int(float(str(value)))

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None or value == "":
            return None
        return int(float(str(value)))

    @staticmethod
    def _required_route_id(value: object) -> str:
        route_id = str(value or "").strip()
        route_by_id(route_id)
        return route_id

    @staticmethod
    def _format_duration(duration_s: float | None) -> str:
        if duration_s is None:
            return "--"
        total_seconds = max(0, int(duration_s))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:d}:{seconds:02d}"

    @staticmethod
    def _format_power(power_w: float | None) -> str:
        if power_w is None:
            return "--"
        return f"{power_w:.0f} W"

    @staticmethod
    def _format_distance(distance_m: float | None) -> str:
        if distance_m is None:
            return "--"
        return f"{distance_m / 1000:.2f} km"

    @staticmethod
    def _format_bpm(value: float | int | None) -> str:
        if value is None:
            return "--"
        return f"{value:.0f} bpm"

    @staticmethod
    def _format_ratio(value: float | None) -> str:
        if value is None:
            return "--"
        return f"{value:.2f}"

    @staticmethod
    def _format_score(value: float | None) -> str:
        if value is None:
            return "--"
        return f"{value:.0f}"


def run_web_ui(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the web UI server."""
    web_ui = WebUI()
    web_ui.setup()

    ui.run(
        host=host,
        port=port,
        title="le-tour",
        favicon="🚴",
        dark=False,
        reload=False,
        show=False,
        loop="asyncio",
        storage_secret=os.environ.get(
            "TERMINALRIDE_STORAGE_SECRET",
            "terminalride-dev-secret-change-in-production",
        ),
    )
