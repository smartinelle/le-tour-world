"""NiceGUI web interface for le-tour.

Clean, minimal design with orange accent.
Big metrics for visibility from bike distance.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from starlette.requests import Request
from nicegui import ui, app

from ..analytics.activity_graphs import (
    ActivityGraphRange,
    build_history_distance_graph,
    build_session_cadence_graph,
    build_session_hr_graph,
    build_session_power_graph,
    build_session_speed_graph,
    normalize_graph_range,
)
from ..domain.ride_controller import RideController, RideMode
from ..domain.ride_runtime import RideRuntime, RideStopResult
from ..domain.routes import RideRoute, available_routes, route_by_id
from ..domain.session_service import get_session_service
from ..config import UserSettings, get_config
from ..devices.base import DeviceNotFoundError, ConnectionError as DeviceConnectionError
from ..store.export import DataExporter
from ..store.models import SampleModel, SessionModel, SessionSummary
from .components.activity_graphs import GraphControl, activity_graph
from .components.controls import (
    ButtonVariant,
    action_button,
    hero_button,
    segmented_control,
)
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
                    'flat round dense size=sm aria-label="Close dialog"'
                ).classes("tr-cell-soft")

            with ui.column().classes("scan-dialog-body w-full"):
                self._status_label = ui.label("Scanning...").classes("tr-status-meta")

                self._device_container = ui.column().classes("w-full gap-2")

            with ui.row().classes("scan-dialog-footer w-full justify-end"):
                ui.button("Cancel", on_click=self._cancel).props("flat").classes(
                    "tr-cell-soft"
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
                    ui.label(name).classes("tr-status-name")
                    if rssi:
                        ui.label(f"Signal: {rssi} dBm").classes("tr-status-meta")

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


def get_controller() -> RideController:
    """Get the shared controller for the local app process."""
    return _get_shared_controller()


def get_runtime() -> RideRuntime:
    """Get the runtime that owns sample-source lifecycle for this context."""
    return _get_shared_runtime()


class WebUI:
    """Web-based UI for le-tour."""

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
        self._ride_controls: Optional[Any] = None
        self._pause_button: Optional[Any] = None
        self._stop_button: Optional[Any] = None
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
        flag = os.getenv("LE_TOUR_ENABLE_BLE", "").lower()
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

    def _set_last_stop_result(self, result: RideStopResult | None) -> None:
        """Store the latest stop result for the current UI context."""
        app._last_stop_result = result

    def _get_last_stop_result(self) -> object:
        """Return the latest stop result for the current UI context."""
        return getattr(app, "_last_stop_result", None)

    def setup(self) -> None:
        """Set up the web UI routes and pages."""
        if not getattr(app, "_le_tour_snapshot_routes_attached", False):
            attach_snapshot_routes(app, get_controller)
            attach_ride3d_routes(app, get_runtime)
            app._le_tour_snapshot_routes_attached = True

        @ui.page("/")
        async def home_page():
            await self._render_home_with_auto_connect()

        @ui.page("/session/{mode}")
        def session_page(mode: str, request: Request):
            self._render_session(mode, request.query_params.get("route_id"))

        @ui.page("/summary")
        def summary_page():
            self._render_stop_summary()

        @ui.page("/devices")
        def devices_page():
            ui.navigate.to("/settings?tab=devices")

        @ui.page("/history")
        def history_page(request: Request):
            self._render_history(request.query_params.get("range"))

        @ui.page("/history/{session_id}")
        def history_detail_page(session_id: str):
            self._render_history_detail(session_id)

        @ui.page("/settings")
        def settings_page(request: Request):
            self._render_settings(request.query_params.get("tab"))

        @ui.page("/settings/devices")
        def settings_devices_page():
            self._render_settings("devices")

        @ui.page("/design-system")
        def design_system_page():
            self._render_design_system()

    def _render_header(self, current: str = "") -> None:
        """Render the navigation header. Status pills only appear when a
        device is actually connected — a fresh / demo session shows a
        clean nav rather than two "No trainer" / "No HR" labels."""
        apply_theme()
        trainer = self.controller.trainer
        hr = self.controller.hr_service
        statuses: list[tuple[str, bool]] = []
        if trainer.is_connected:
            statuses.append((trainer.device_info.get("name", "Trainer"), True))
        if hr.is_connected:
            statuses.append((hr.device_info.get("name", "HR Monitor"), True))
        render_app_header(
            current,
            statuses=tuple(statuses),
        )

    async def _render_home_with_auto_connect(self) -> None:
        """Render the ride launchpad with automatic trainer connection."""
        self._render_header("Ride")

        selected_mode = {"value": "free"}
        selected_route_id = {"value": self._default_route_id()}
        mode_buttons: Dict[str, Any] = {}
        setup_container: Optional[Any] = None

        def set_mode(mode: str) -> None:
            selected_mode["value"] = mode
            for key, button in mode_buttons.items():
                if key == mode:
                    button.classes(add="active")
                else:
                    button.classes(remove="active")
            if setup_container:
                render_mode_setup()

        def set_route(route_id: str) -> None:
            selected_route_id["value"] = route_id
            if setup_container:
                render_mode_setup()

        def adjust_launch_erg_target(delta: int) -> None:
            self._adjust_target(delta)
            if setup_container:
                render_mode_setup()

        def start_selected() -> None:
            path = f"/session/{selected_mode['value']}"
            if selected_mode["value"] == "sim":
                path += f"?route_id={selected_route_id['value']}"
            ui.navigate.to(path)

        def render_route_profile(route: RideRoute) -> None:
            points = [
                50 - max(-8.0, min(8.0, segment.grade_pct)) * 3.3
                for segment in route.segments
            ]
            if not points:
                points = [50.0]
            step = 100 / max(1, len(points) - 1)
            coordinates = " ".join(
                f"{index * step:.1f},{point:.1f}" for index, point in enumerate(points)
            )
            tick_html = "".join(
                "<span "
                f'style="left:{index * 100 / max(1, len(route.segments)):.1f}%">'
                "</span>"
                for index, _ in enumerate(route.segments)
            )
            ui.html(
                f"""
                <div class="tr-route-profile" aria-hidden="true">
                    <svg viewBox="0 0 100 64" preserveAspectRatio="none">
                        <polyline points="{coordinates}" />
                    </svg>
                    <div class="tr-route-profile-ticks">{tick_html}</div>
                </div>
                """,
                sanitize=False,
            )

        def render_mode_setup() -> None:
            if setup_container is None:
                return
            setup_container.clear()
            mode = selected_mode["value"]
            with setup_container, ui.element("div").classes("tr-mode-setup"):
                if mode == "free":
                    ui.label(
                        "Ride without trainer resistance control. Power and cadence "
                        "are read from the trainer; recording stays on."
                    ).classes("tr-setup-hint")

                elif mode == "erg":
                    with ui.element("div").classes("tr-setup-erg"):
                        ui.label("ERG TARGET").classes("tr-section-label")
                        with ui.element("div").classes("tr-setup-erg-row"):
                            action_button(
                                "−10 W",
                                lambda: adjust_launch_erg_target(-10),
                                variant="secondary",
                            )
                            with ui.element("div").classes("tr-setup-erg-readout"):
                                ui.label(
                                    f"{self.controller.metrics.erg_target_w}"
                                ).classes("tr-erg-target-value")
                                ui.label("W").classes("tr-power-unit")
                            action_button(
                                "+10 W",
                                lambda: adjust_launch_erg_target(10),
                                variant="secondary",
                            )

                else:
                    route = route_by_id(selected_route_id["value"])
                    with ui.element("div").classes("tr-setup-sim"):
                        ui.select(
                            self._route_select_options(),
                            value=selected_route_id["value"],
                            label="SIM Route",
                            on_change=lambda event: set_route(str(event.value)),
                        ).classes("w-full")
                        render_route_profile(route)
                        with ui.element("div").classes("tr-meta-grid tr-route-stats"):
                            meta_stat(f"{route.distance_m / 1000:.2f}", "Distance km")
                            meta_stat(f"{route.elevation_gain_m:.0f}", "Gain m")
                            meta_stat(f"{route.max_grade_pct:.1f}", "Max grade %")
                            meta_stat(str(len(route.segments)), "Segments")

        def render_recent_rides() -> None:
            try:
                sessions = get_session_service().list_sessions(limit=6)
            except Exception as exc:
                logger.warning("Failed to load recent rides: %s", exc)
                sessions = []

            panel_header(
                "Recent rides",
                "Latest sessions on this device.",
                action=("View all →", "/history") if sessions else None,
            )
            if not sessions:
                empty_state(
                    "No rides yet",
                    "Your completed rides will appear here.",
                    action_label="Start Ride",
                    on_action=lambda: ui.navigate.to("/"),
                    action_variant="primary",
                )
                return
            with ui.element("div").classes("tr-sessions tr-sessions-compact w-full"):
                for session in sessions:
                    self._render_session_row(session, compact=True)

        connected = self.controller.trainer.is_connected
        # Status display lives in the header now; keep these handles around so
        # auto-connect can still patch text without crashing on missing nodes.
        self._connection_dot = None
        self._connection_status_label = None

        with page_container():
            with ui.element("div").classes("tr-home-grid"):
                with ui.column().classes("tr-panel p-6"):
                    panel_header(
                        "Ride setup",
                        "Choose a mode and start riding.",
                        badge="Ready" if connected else None,
                    )

                    mode_buttons.update(
                        segmented_control(
                            [
                                ("free", "Free Ride", lambda: set_mode("free")),
                                ("erg", "ERG", lambda: set_mode("erg")),
                                ("sim", "SIM", lambda: set_mode("sim")),
                            ],
                            active_key="free",
                        )
                    )

                    setup_container = ui.column().classes("w-full gap-0")
                    render_mode_setup()

                    with ui.element("div").classes("tr-action-row mt-auto"):
                        action_button(
                            "Pair Devices",
                            lambda: ui.navigate.to("/settings?tab=devices"),
                            variant="secondary",
                        )
                        hero_button("Start Ride", start_selected)

                with ui.column().classes("tr-panel p-6 gap-4"):
                    render_recent_rides()

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
                        "No trainer found — use Pair Devices to scan manually"
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
                    "Connection failed — use Pair Devices to retry"
                )
                self._connection_status_label.update()
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")
            if self._connection_status_label:
                self._connection_status_label.set_text(
                    "Connection error — use Pair Devices to retry"
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
            ui.label(shortcut).classes("tr-shortcut-label")
            ui.label(title).classes("tr-card-title")
            ui.label(description).classes("tr-card-description")

    def _render_session(self, mode: str, route_id: str | None = None) -> None:
        """Render the full-screen session cockpit."""
        apply_theme()

        mode_enum = {
            "free": RideMode.FREE,
            "erg": RideMode.ERG,
            "sim": RideMode.SIM,
        }.get(mode, RideMode.FREE)

        route: RideRoute | None = None
        if mode_enum is RideMode.SIM:
            try:
                route = route_by_id(route_id or self._default_route_id())
            except Exception:
                route = route_by_id(None)
            self.runtime.set_route_profile(route)

        with ui.element("div").classes("session-view"):
            with ui.element("div").classes("tr-cockpit"):
                # Top row: status pill (left) + clock (right). Mode is shown
                # in the bottom-right metric tile, no need to repeat it here.
                with ui.element("div").classes("tr-cockpit-top"):
                    with ui.element("div").classes("tr-cockpit-statusbar"):
                        self._state_badge = ui.html(
                            '<span class="tr-state-badge live">Active</span>',
                            sanitize=False,
                        )
                        self._status_label = ui.label("Starting session").classes(
                            "tr-status-meta"
                        )
                    ui.label("")  # grid spacer for the centre column
                    self._time_label = ui.label("00:00").classes("tr-cockpit-clock")

                # Hero card — power readout dominates, target controls inline.
                with ui.element("div").classes("tr-power-panel"):
                    self._power_label = power_panel()
                    if mode == "erg":
                        with ui.element("div").classes("tr-cockpit-target-row"):
                            action_button(
                                "−10 W",
                                lambda: self._adjust_target(-10),
                                variant="secondary",
                            )
                            self._target_label = ui.label("Target 150 W").classes(
                                "tr-cockpit-target-readout"
                            )
                            action_button(
                                "+10 W",
                                lambda: self._adjust_target(10),
                                variant="secondary",
                            )
                    elif mode == "sim":
                        with ui.element("div").classes("tr-cockpit-target-row"):
                            action_button(
                                "−0.5%",
                                lambda: self._adjust_sim_grade(-0.5),
                                variant="secondary",
                            )
                            self._target_label = ui.label("Grade 0.0%").classes(
                                "tr-cockpit-target-readout"
                            )
                            action_button(
                                "+0.5%",
                                lambda: self._adjust_sim_grade(0.5),
                                variant="secondary",
                            )
                        if route is not None:
                            with ui.element("div").classes("tr-cockpit-route"):
                                self._route_segment_label = ui.label(
                                    route.segments[0].name
                                ).classes("tr-cockpit-route-current")
                                self._route_next_label = ui.label("").classes(
                                    "tr-cockpit-route-meta"
                                )
                                self._route_progress_label = ui.label(
                                    f"0.00 / {route.distance_m / 1000:.2f} km"
                                ).classes("tr-cockpit-route-meta")

                with ui.element("div").classes("tr-metric-rail"):
                    self._cadence_label = metric_cell("--", "Cadence RPM")
                    self._hr_label = metric_cell("--", "Heart BPM")
                    self._speed_label = metric_cell("--", "Speed km/h")
                    self._distance_label = metric_cell("--", "Distance km")
                    metric_cell(mode.upper(), "Mode")

                # Bottom row: just the two ride controls. No middle banner.
                self._ride_controls = ui.element("div").classes("tr-cockpit-controls")
                self._render_live_ride_controls()

        # Start session and update loop
        self._start_session(mode_enum)

    def _start_session(self, mode: RideMode) -> None:
        """Start a training session."""
        self.runtime.start_session(mode)

        if self._status_label:
            label = (
                "Waiting for trainer"
                if self.controller.trainer.is_connected
                else "Demo session"
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
            self._status_label.set_text("Waiting for trainer")
            return

        label = (
            "Live trainer" if self.controller.trainer.is_connected else "Demo session"
        )
        self._status_label.set_text(label)

    def _adjust_target(self, delta: int) -> None:
        """Adjust ERG target power."""
        self.runtime.adjust_erg_target(delta)

    def _adjust_sim_grade(self, delta: float) -> None:
        """Adjust SIM grade."""
        self.runtime.adjust_sim_grade(delta)

    def _ride_action_button(
        self,
        text: str,
        on_click: Callable[[], Any],
        *,
        variant: ButtonVariant = "secondary",
    ) -> Any:
        """Render a same-sized cockpit action button."""
        return action_button(
            text,
            on_click,
            variant=variant,
            min_width="112px",
        )

    def _render_live_ride_controls(self) -> None:
        """Render active ride controls."""
        if self._ride_controls is None:
            return

        self._ride_controls.clear()
        self._pause_button = None
        self._stop_button = None
        with self._ride_controls:
            self._pause_button = self._ride_action_button("Pause", self._pause_session)
            ui.label("")  # grid spacer
            self._stop_button = self._ride_action_button(
                "Stop Ride",
                self._request_stop_session,
                variant="primary",
            )

    def _render_paused_review_controls(self) -> None:
        """Render resume/save/delete controls after pausing."""
        if self._ride_controls is None:
            return

        self._ride_controls.clear()
        self._pause_button = None
        self._stop_button = None
        with self._ride_controls:
            with ui.row().classes("items-center gap-2").style("flex-wrap: wrap;"):
                self._pause_button = self._ride_action_button(
                    "Resume",
                    self._resume_session,
                )
                self._ride_action_button(
                    "Save",
                    self._save_current_session,
                    variant="primary",
                )
                self._ride_action_button("Delete", self._discard_current_session)
            ui.label("")  # grid spacer

    def _render_stop_review_controls(self) -> None:
        """Render save/delete controls after requesting stop."""
        if self._ride_controls is None:
            return

        self._ride_controls.clear()
        self._pause_button = None
        self._stop_button = None
        with self._ride_controls:
            ui.label("")
            ui.label("")  # grid spacer
            with ui.row().classes("items-center gap-2").style("flex-wrap: wrap;"):
                self._stop_button = self._ride_action_button(
                    "Save",
                    self._save_current_session,
                    variant="primary",
                )
                self._ride_action_button("Delete", self._discard_current_session)

    def _set_live_state_badge(self, text: str, *, paused: bool) -> None:
        """Update the cockpit status badge."""
        if self._state_badge is None:
            return

        badge_class = "demo" if paused else "live"
        self._state_badge.set_content(
            f'<span class="tr-state-badge {badge_class}">{text}</span>'
        )

    def _cancel_update_task(self) -> None:
        """Stop the cockpit update timer if it is running."""
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None

    def _pause_session(self) -> None:
        """Pause the current session and show end-of-ride choices."""
        snapshot = self.runtime.pause_session()
        if self._status_label:
            self._status_label.set_text("Paused")
        self._set_live_state_badge("Paused", paused=snapshot.paused)
        self._render_paused_review_controls()

    def _resume_session(self) -> None:
        """Resume a paused session."""
        snapshot = self.runtime.resume_session()
        if self._status_label:
            self._status_label.set_text("Session active")
        self._set_live_state_badge("Active", paused=snapshot.paused)
        self._render_live_ride_controls()

    def _request_stop_session(self) -> None:
        """Freeze the current session until the user saves or deletes it."""
        self.runtime.request_stop_confirmation()
        if self._status_label:
            self._status_label.set_text("Stopped")
        self._set_live_state_badge("Stopped", paused=True)
        self._cancel_update_task()
        self._render_stop_review_controls()

    def _save_current_session(self) -> None:
        """Stop the current session, persist it, and show the summary."""
        result = self.runtime.stop_session_result()
        self._set_last_stop_result(result)
        self._cancel_update_task()
        ui.navigate.to("/summary")

    def _discard_current_session(self) -> None:
        """Stop the current session without saving and return home."""
        self.runtime.discard_session()
        self._set_last_stop_result(None)
        self._cancel_update_task()
        ui.navigate.to("/")

    def _exit_session(self) -> None:
        """Exit session without saving."""
        if self.controller.is_active:
            self.runtime.discard_session()
        self._cancel_update_task()
        ui.navigate.to("/")

    def _render_stop_summary(self) -> None:
        """Render the post-ride stop result."""
        self._render_header("Summary")
        result = self._get_last_stop_result()

        with page_container():
            render_page_title(
                "Ride summary",
                "Your ride has stopped.",
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
            saved_label = "Ride saved" if result.saved else "No ride data saved"
            if result.persistence_error:
                saved_label = "Save failed"
            elif result.sample_count == 0:
                saved_label = "No ride data saved"
            summary_graph_samples: list[SampleModel] = []
            summary_graph_ftp_w: int | None = None

            with ui.column().classes("tr-panel tr-object-panel p-5 gap-4"):
                panel_header(
                    saved_label,
                    saved_label,
                    badge="Saved" if result.saved else "Review",
                )
                if result.saved_session_id:
                    service = get_session_service()
                    session = service.get_session(result.saved_session_id)
                    if session is not None:
                        summary = (
                            service.get_session_summary(result.saved_session_id)
                            if self._needs_calculated_summary(session)
                            else None
                        )
                        self._render_session_summary_stats(session, summary)
                        summary_graph_samples = service.get_session_samples(
                            result.saved_session_id
                        )
                        summary_graph_ftp_w = session.user_ftp_w
                    else:
                        self._render_snapshot_summary_stats(snapshot)
                else:
                    self._render_snapshot_summary_stats(snapshot)

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
                            "No trainer or demo data was recorded, so nothing was written to history."
                        )

                with ui.element("div").classes("tr-detail-actions"):
                    action_button(
                        "Start New Ride",
                        lambda: ui.navigate.to("/"),
                        variant="primary",
                    )
                    with ui.element("div").classes("tr-detail-actions-right"):
                        action_button(
                            "View History",
                            lambda: ui.navigate.to("/history"),
                            variant="secondary",
                        )
                        saved_session_id = result.saved_session_id
                        if saved_session_id:
                            action_button(
                                "Export CSV",
                                lambda session_id=saved_session_id: self._export_session(
                                    session_id
                                ),
                                variant="secondary",
                            )

            if summary_graph_samples:
                self._render_session_activity_graphs(
                    summary_graph_samples,
                    ftp_w=summary_graph_ftp_w,
                    compact=True,
                )

    async def _disconnect_trainer(self) -> None:
        """Disconnect the trainer and refresh the page."""
        try:
            if self.controller.trainer.is_connected:
                await self.controller.trainer.disconnect()
                logger.info("Trainer disconnected via web UI")
            ui.navigate.to("/settings?tab=devices")
        except Exception as e:
            logger.warning(f"Error disconnecting trainer: {e}")
            ui.notify(f"Disconnect failed: {e}", color="red")

    async def _disconnect_hr(self) -> None:
        """Disconnect the HR monitor and refresh the page."""
        try:
            if self.controller.hr_service.is_connected:
                await self.controller.hr_service.disconnect()
                logger.info("HR monitor disconnected via web UI")
            ui.navigate.to("/settings?tab=devices")
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
            ui.navigate.to("/settings?tab=devices")

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
            ui.navigate.to("/settings?tab=devices")

        dialog = ScanDialog(
            title="Heart Rate Monitors",
            device_type="heart rate monitor",
            scan_fn=scan_fn,
            connect_fn=connect_fn,
            on_connected=on_connected,
        )
        dialog.show()

    def _render_history(self, range_value: str | None = None) -> None:
        """Render the session history page."""
        self._render_header("History")
        graph_range = normalize_graph_range(range_value)
        try:
            sessions = get_session_service().list_sessions(limit=50)
        except Exception as exc:
            logger.warning("Failed to load session history: %s", exc)
            sessions = []

        aggregates = self._aggregate_sessions(sessions)

        with page_container():
            if sessions:
                with ui.element("div").classes("tr-summary-bar w-full"):
                    self._summary_tile(aggregates["count"], "Sessions")
                    self._summary_tile(aggregates["distance"], "Distance")
                    self._summary_tile(aggregates["duration"], "Duration")
                    self._summary_tile(aggregates["power"], "Avg Power")

                activity_graph(
                    build_history_distance_graph(sessions, graph_range),
                    controls=self._history_range_controls(graph_range),
                )

            with ui.column().classes("tr-panel p-5 gap-3 w-full"):
                panel_header(
                    "Sessions",
                    f"{len(sessions)} recorded rides.",
                    action=(
                        ("Export all CSV", self._export_sessions_summary)
                        if sessions
                        else None
                    ),
                )
                if not sessions:
                    empty_state(
                        "No rides yet",
                        "Your completed rides will appear here.",
                        action_label="Start Ride",
                        on_action=lambda: ui.navigate.to("/"),
                        action_variant="primary",
                    )
                else:
                    with ui.element("div").classes(
                        "tr-sessions tr-sessions-full w-full"
                    ):
                        self._sessions_head_row()
                        for session in sessions:
                            self._render_session_row(session)

    def _render_history_detail(self, session_id: str) -> None:
        """Render one persisted session with summary and export actions."""
        self._render_header("History")
        service = get_session_service()
        session = service.get_session(session_id)
        summary = (
            service.get_session_summary(session_id)
            if session is not None and self._needs_calculated_summary(session)
            else None
        )

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

            samples = service.get_session_samples(session.session_id)
            with ui.column().classes("tr-panel tr-object-panel p-5 gap-4"):
                route_label = self._session_route_label(session)
                panel_header(
                    session.start_time.strftime("%Y-%m-%d %H:%M"),
                    route_label or f"{session.mode.value.upper()} ride",
                )
                self._render_session_summary_stats(session, summary)
                with ui.element("div").classes("tr-detail-actions"):
                    action_button(
                        "Back to History",
                        lambda: ui.navigate.to("/history"),
                        variant="secondary",
                    )
                    with ui.element("div").classes("tr-detail-actions-right"):
                        action_button(
                            "Export CSV",
                            lambda: self._export_session(session.session_id),
                            variant="secondary",
                        )
                        action_button(
                            "Delete",
                            lambda: self._confirm_delete_session(session.session_id),
                            variant="secondary",
                            classes="tr-btn-danger",
                        )

            self._render_session_activity_graphs(samples, ftp_w=session.user_ftp_w)

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
        max_power_w = (
            summary.max_power_w if summary is not None else session.max_power_w
        )
        avg_hr_bpm = summary.avg_hr_bpm if summary is not None else session.avg_hr_bpm
        max_hr_bpm = summary.max_hr_bpm if summary is not None else session.max_hr_bpm
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

        with ui.element("div").classes(
            "tr-meta-grid tr-summary-grid tr-summary-grid-session"
        ):
            meta_stat(self._format_duration(session.duration_s), "Duration")
            meta_stat(self._format_distance(distance_m), "Distance")
            meta_stat(self._format_power(avg_power_w), "Avg power")
            meta_stat(self._format_power(max_power_w), "Max power")
            meta_stat(self._format_bpm(avg_hr_bpm), "Avg HR")
            meta_stat(self._format_bpm(max_hr_bpm), "Max HR")
            meta_stat(self._format_power(normalized_power_w), "Normalized Power")
            meta_stat(self._format_ratio(intensity_factor), "Intensity")
            meta_stat(self._format_score(training_stress_score), "Training Stress")
            meta_stat(str(session.user_ftp_w), "FTP")

    @staticmethod
    def _needs_calculated_summary(session: SessionModel) -> bool:
        """Return whether an older saved session needs sample-derived metrics."""
        if session.total_distance_m is None:
            return True
        if session.avg_power_w is None or session.max_power_w is None:
            return False
        return (
            session.normalized_power_w is None
            or session.intensity_factor is None
            or session.training_stress_score is None
        )

    def _render_snapshot_summary_stats(self, snapshot: object) -> None:
        """Render fallback summary stats when no persisted session is available."""
        with ui.element("div").classes(
            "tr-meta-grid tr-summary-grid tr-summary-grid-snapshot"
        ):
            meta_stat(
                self._format_duration(getattr(snapshot, "elapsed_s", None)),
                "Duration",
            )
            meta_stat(
                self._format_distance(getattr(snapshot, "distance_m", None)),
                "Distance",
            )
            meta_stat(
                self._format_power(getattr(snapshot, "power_w", None)),
                "Last power",
            )
            meta_stat("--", "Training Stress")

    def _render_session_activity_graphs(
        self,
        samples: list[SampleModel],
        *,
        ftp_w: int | None,
        compact: bool = False,
    ) -> None:
        """Render reusable activity graphs for persisted session samples."""
        power_graph = build_session_power_graph(samples, ftp_w=ftp_w)
        activity_graph(power_graph)

        if compact:
            return

        for graph in (
            build_session_hr_graph(samples),
            build_session_cadence_graph(samples),
            build_session_speed_graph(samples),
        ):
            if graph.has_points:
                activity_graph(graph, collapsible=True)

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

    def _export_sessions_summary(self) -> None:
        """Export a CSV with one summary row per saved session."""
        export_dir = get_config().get_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_path = export_dir / f"le-tour_sessions_{timestamp}.csv"

        success = DataExporter().export_session_summary_csv(
            output_path,
            limit=10_000,
        )
        if not success:
            ui.notify("CSV export failed", color="red")
            return
        ui.notify(f"CSV exported to {output_path}", color="green")

    def _confirm_delete_session(self, session_id: str) -> None:
        """Ask before deleting a saved session and its samples."""
        dialog = ui.dialog()

        def delete_confirmed() -> None:
            dialog.close()
            deleted = get_session_service().delete_session(session_id)
            if not deleted:
                ui.notify("Delete failed", color="red")
                return
            ui.notify("Session deleted", color="green")
            ui.navigate.to("/history")

        with dialog, ui.card().classes("tr-dialog-card"):
            ui.label("Delete session?").classes("tr-panel-title")
            ui.label("This removes the saved session and its samples.").classes(
                "tr-status-meta"
            )
            with ui.element("div").classes("tr-detail-actions"):
                action_button("Cancel", dialog.close, variant="secondary")
                action_button(
                    "Delete",
                    delete_confirmed,
                    variant="primary",
                    classes="tr-btn-danger-fill",
                )

        dialog.open()

    def _render_settings(self, selected_tab: str | None = None) -> None:
        """Render all four settings sections at once in a 2x2 grid.

        The legacy `selected_tab` parameter is accepted (for backwards-
        compatible URLs like `/settings?tab=devices`) but ignored — there
        are no tabs anymore. Every section lives on the same screen.
        """
        del selected_tab  # accepted for URL compat, no longer used
        self._render_header("Settings")
        config = get_config()

        with page_container():
            render_page_title(
                "Settings",
                "Profile, ride defaults, devices, and app preferences.",
                "All sections, all the time — no tabs.",
            )

            with ui.element("div").classes("tr-settings-grid"):
                with ui.column().classes("tr-panel p-6 gap-4"):
                    self._render_profile_section(config)
                with ui.column().classes("tr-panel p-6 gap-4"):
                    self._render_ride_defaults_section(config)
                with ui.column().classes("tr-panel p-6 gap-4"):
                    self._render_devices_section()
                with ui.column().classes("tr-panel p-6 gap-4"):
                    self._render_app_preferences_section(config)

    def _render_profile_section(self, config: Any) -> None:
        panel_header(
            "Profile",
            "Rider inputs used for training metrics and physics.",
        )
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
        with ui.row().classes("tr-action-row mt-auto"):
            action_button(
                "Save Profile",
                lambda: self._save_profile_settings(
                    name_input.value,
                    mass_input.value,
                    ftp_input.value,
                    max_hr_input.value,
                    age_input.value,
                ),
                variant="primary",
            )

    def _render_ride_defaults_section(self, config: Any) -> None:
        panel_header(
            "Ride Defaults",
            "Defaults used when a new ride starts.",
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
        units_select = ui.select(
            {"metric": "Metric", "imperial": "Imperial"},
            value=config.settings.units,
            label="Units",
        ).classes("w-full")
        with ui.row().classes("tr-action-row mt-auto"):
            action_button(
                "Save Ride Defaults",
                lambda: self._save_ride_default_settings(
                    erg_target_input.value,
                    sim_grade_input.value,
                    route_select.value,
                    speed_source_select.value,
                    units_select.value,
                ),
                variant="primary",
            )

    def _render_devices_section(self) -> None:
        panel_header(
            "Devices",
            "Pair your trainer and optional heart-rate monitor.",
        )

        trainer_status = self.controller.trainer.connection_status()
        device_row(
            "Trainer",
            (
                f"Connected to {trainer_status.name or 'Trainer'}"
                if trainer_status.connected
                else "Not paired. Demo mode remains available."
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
            action_variant="secondary" if trainer_status.connected else "primary",
            signal_bars=(
                _rssi_to_bars(trainer_status.rssi) if trainer_status.connected else 0
            ),
            state_label="Connected" if trainer_status.connected else "Demo",
        )

        hr_status = self.controller.hr_service.connection_status()
        device_row(
            "Heart Rate",
            (
                f"Connected to {hr_status.name or 'HR Monitor'}"
                if hr_status.connected
                else "Optional. Pair a standard BLE HR strap."
            ),
            connected=hr_status.connected,
            action_label="Disconnect" if hr_status.connected else "Scan",
            on_action=(
                lambda: (
                    self._disconnect_hr() if hr_status.connected else self._scan_hr()
                )
            ),
            action_variant="secondary" if hr_status.connected else "primary",
            signal_bars=_rssi_to_bars(hr_status.rssi) if hr_status.connected else 0,
            state_label="Connected" if hr_status.connected else "Optional",
        )

    def _render_app_preferences_section(self, config: Any) -> None:
        panel_header(
            "App Preferences",
            "Local connection startup behavior.",
        )
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
        with ui.row().classes("tr-action-row mt-auto"):
            action_button(
                "Save App Preferences",
                lambda: self._save_app_preference_settings(
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

            with ui.element("div").classes("tr-status-strip tr-status-strip-two"):
                status_tile("Trainer", "Connected to FTMS Bike", connected=True)
                status_tile("Heart rate", "Optional monitor", connected=False)

            with ui.element("div").classes("tr-console-grid"):
                with ui.column().classes("tr-panel p-5 gap-4"):
                    panel_header(
                        "Controls",
                        "Primary action, secondary action, and segmented modes.",
                    )
                    segmented_control(
                        [
                            ("free", "Free Ride", lambda: None),
                            ("erg", "ERG", lambda: None),
                            ("sim", "SIM", lambda: None),
                        ],
                        active_key="free",
                    )
                    with ui.element("div").classes("tr-action-row"):
                        action_button("Pair Devices", lambda: None)
                        hero_button("Start Ride", lambda: None)
                    with ui.element("div").classes("tr-meta-grid"):
                        meta_stat("150", "ERG target W")
                        meta_stat("0.0", "SIM grade %")

                with ui.column().classes("tr-panel p-5 gap-4"):
                    panel_header(
                        "Hardware row",
                        "Device rows include state, signal, and one next action.",
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
                )
                with ui.element("div").classes("tr-power-panel tr-panel-tight"):
                    power_panel("186")
                with ui.element("div").classes("tr-metric-rail"):
                    metric_cell("92", "Cadence RPM")
                    metric_cell("148", "Heart BPM")
                    metric_cell("31.4", "Speed km/h")
                    metric_cell("12.08", "Distance km")
                    metric_cell("ERG", "Mode")
                with ui.element("div").classes("tr-sessions"):
                    self._sessions_head_row()
                empty_state(
                    "No sessions recorded yet",
                    "The shell is designed without fake training data.",
                )

    def _save_settings_updates(self, updates: dict[str, object]) -> None:
        """Validate and persist partial settings updates."""
        config = get_config()
        try:
            data = config.settings.model_dump()
            data.update(updates)
            settings = UserSettings.model_validate(data)
        except Exception as exc:
            ui.notify(f"Settings invalid: {exc}", color="red")
            return

        config.settings = settings
        config.user_mass_kg = settings.mass_kg
        config.user_ftp_w = settings.ftp_w if settings.ftp_w is not None else 250
        config.connection_timeout_s = settings.reconnect_timeout_s
        config.save_settings()
        ui.notify("Settings saved", color="green")

    def _save_profile_settings(
        self,
        name: object,
        mass_kg: object,
        ftp_w: object,
        max_hr_bpm: object,
        age: object,
    ) -> None:
        """Validate and save rider profile settings."""
        try:
            updates: dict[str, object] = {
                "name": (str(name).strip() if name is not None else "") or "Rider",
                "mass_kg": self._required_float(mass_kg),
                "ftp_w": self._optional_int(ftp_w),
                "max_hr_bpm": self._optional_int(max_hr_bpm),
                "age": self._required_int(age),
            }
        except Exception as exc:
            ui.notify(f"Settings invalid: {exc}", color="red")
            return
        self._save_settings_updates(updates)

    def _save_ride_default_settings(
        self,
        default_erg_power_w: object,
        default_sim_grade_pct: object,
        default_sim_route_id: object,
        speed_source: object,
        units: object,
    ) -> None:
        """Validate and save ride defaults."""
        try:
            updates: dict[str, object] = {
                "default_erg_power_w": self._required_int(default_erg_power_w),
                "default_sim_grade_pct": self._required_float(default_sim_grade_pct),
                "default_sim_route_id": self._required_route_id(default_sim_route_id),
                "speed_source": str(speed_source),
                "units": str(units),
            }
        except Exception as exc:
            ui.notify(f"Settings invalid: {exc}", color="red")
            return
        self._save_settings_updates(updates)

    def _save_app_preference_settings(
        self,
        auto_connect_trainer: object,
        auto_connect_hr: object,
        reconnect_timeout_s: object,
    ) -> None:
        """Validate and save local app preferences."""
        try:
            updates: dict[str, object] = {
                "auto_connect_trainer": bool(auto_connect_trainer),
                "auto_connect_hr": bool(auto_connect_hr),
                "reconnect_timeout_s": self._required_int(reconnect_timeout_s),
            }
        except Exception as exc:
            ui.notify(f"Settings invalid: {exc}", color="red")
            return
        self._save_settings_updates(updates)

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
    def _format_integer(value: float | int | None) -> str:
        if value is None:
            return "--"
        return f"{value:.0f}"

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

    def _render_session_row(
        self,
        session: SessionModel,
        summary: SessionSummary | None = None,
        *,
        compact: bool = False,
    ) -> None:
        """Render one body row of the sessions grid table."""
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

        with (
            ui.element("div")
            .classes("tr-sessions-row body")
            .on(
                "click",
                lambda sid=session.session_id: ui.navigate.to(f"/history/{sid}"),
            )
        ):
            ui.label(session.start_time.strftime("%d %b %Y · %H:%M"))
            ui.label(session.mode.value.upper())
            ui.label(self._format_duration(session.duration_s)).classes("num")
            ui.label(self._format_distance(distance_m)).classes("num")
            ui.label(self._format_power(avg_power_w)).classes("num")
            if compact:
                ui.label(self._format_score(training_stress_score)).classes("num")
                ui.label("")  # spacer cell
                ui.label("›").classes("chevron")
                return
            ui.label(self._format_power(session.max_power_w)).classes("num")
            ui.label(self._format_integer(avg_hr_bpm)).classes("num")
            ui.label(self._format_integer(session.max_hr_bpm)).classes("num")
            ui.label(self._format_power(normalized_power_w)).classes("num")
            ui.label(self._format_ratio(intensity_factor)).classes("num")
            ui.label(self._format_score(training_stress_score)).classes("num")
            ui.label(str(session.user_ftp_w)).classes("num")
            ui.label("")  # spacer cell
            ui.label("›").classes("chevron")

    @staticmethod
    def _sessions_head_row() -> None:
        """Render the header row of the sessions grid table."""
        with ui.element("div").classes("tr-sessions-row head"):
            ui.label("Date")
            ui.label("Mode")
            ui.label("Duration").classes("num")
            ui.label("Distance").classes("num")
            ui.label("Avg Power").classes("num")
            ui.label("Max Power").classes("num")
            ui.label("Avg HR").classes("num")
            ui.label("Max HR").classes("num")
            ui.label("NP").classes("num")
            ui.label("IF").classes("num")
            ui.label("TSS").classes("num")
            ui.label("FTP").classes("num")
            ui.label("")  # spacer
            ui.label("")  # chevron column

    @staticmethod
    def _summary_tile(value: str, label: str) -> None:
        """Render one tile of the history summary bar."""
        with ui.element("div").classes("tr-summary-tile"):
            ui.label(value).classes("tr-summary-value")
            ui.label(label).classes("tr-summary-label")

    @staticmethod
    def _history_range_controls(active: ActivityGraphRange) -> tuple[GraphControl, ...]:
        """Return range controls for history activity graphs."""
        return (
            GraphControl("7D", "/history?range=7d", active == "7d"),
            GraphControl("30D", "/history?range=30d", active == "30d"),
            GraphControl("All", "/history?range=all", active == "all"),
        )

    def _aggregate_sessions(self, sessions: list[SessionModel]) -> dict[str, str]:
        """Compute aggregate stats across the loaded session list."""
        if not sessions:
            return {
                "count": "0",
                "distance": "0.0 km",
                "duration": "0:00",
                "power": "--",
            }

        total_distance_m = sum((s.total_distance_m or 0.0) for s in sessions)
        total_duration_s = sum((s.duration_s or 0.0) for s in sessions)
        powers = [s.avg_power_w for s in sessions if s.avg_power_w is not None]
        avg_power = sum(powers) / len(powers) if powers else None

        hours, remainder = divmod(int(total_duration_s), 3600)
        minutes = remainder // 60
        duration_label = f"{hours}:{minutes:02d}" if hours else f"{minutes} min"

        return {
            "count": str(len(sessions)),
            "distance": f"{total_distance_m / 1000:.1f} km",
            "duration": duration_label,
            "power": self._format_power(avg_power),
        }


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
            "LE_TOUR_STORAGE_SECRET",
            "le-tour-dev-secret-change-in-production",
        ),
    )
