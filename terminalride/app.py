"""Main application controller and event loop."""

import asyncio
import time
from typing import Optional
import logging
import signal
import sys
import os

import tty
import termios
from rich.console import Console
from rich.live import Live

from .ui.views import (
    ViewState,
    AppState,
    StartupView,
    ConnectView,
    HomeView,
    FreeView,
    ErgView,
    SimView,
    DevicesView,
    StatsView,
    SettingsView,
    SummaryView,
)
from .devices.base import BikeSample, HrSample, DeviceNotFoundError
from .domain.trainer_service import TrainerService
from .domain.hr_service import HrService
from .domain.session_service import SessionService
from .modes.erg import ErgController
from .modes.sim import SimPhysics
from .store.repository import TrainingRepository
from .store.models import SessionModel, SampleModel, TrainingMode
from .config import get_config
from .logging_setup import setup_logging


logger = logging.getLogger(__name__)


class TerminalRideApp:
    """Main application controller."""

    def __init__(self) -> None:
        self.console = Console()
        self.state = AppState()
        self.running = False

        # View registry
        self.views = {
            ViewState.STARTUP: StartupView(),
            ViewState.CONNECT: ConnectView(),
            ViewState.HOME: HomeView(),
            ViewState.LIVE_FREE: FreeView(),
            ViewState.LIVE_ERG: ErgView(),
            ViewState.LIVE_SIM: SimView(),
            ViewState.DEVICES: DevicesView(),
            ViewState.STATS: StatsView(),
            ViewState.SETTINGS: SettingsView(),
            ViewState.SUMMARY: SummaryView(),
        }

        # Device services
        self.trainer = TrainerService()
        self.hr_service = HrService()

        # Training mode controllers
        self.erg_controller = ErgController()
        from .modes.sim import SimConfig

        self.sim_solver = SimPhysics(SimConfig())

        # Data persistence
        self.repository = TrainingRepository()
        self.session_service = SessionService(self.repository)
        self.current_session: Optional[SessionModel] = None

        # Metrics accumulator
        self.distance_m = 0.0
        self.last_sample_time: Optional[float] = None
        self._sample_count = 0

        # Keyboard input management
        self._key_queue: asyncio.Queue[str] = asyncio.Queue()
        self._input_mgr: Optional["_RawInputManager"] = None

        # Load persisted UI toggles
        try:
            cfg = get_config()
            self.state.show_legend = getattr(cfg.settings, "show_legend", False)
        except Exception:
            pass

        # Streaming status
        self._got_first_sample = False

    async def run(self) -> None:
        """Main application run loop."""
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Start with startup view
            self.state.current_view = ViewState.STARTUP
            self.state.status_message = "Initializing..."

            # Start UI and background tasks concurrently
            await asyncio.gather(
                self._ui_loop(),
                self._connection_loop(),
                self._metrics_loop(),
                self._device_management_loop(),
            )

        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            await self._cleanup()

    async def _ui_loop(self):
        """Main UI rendering and input loop."""
        # Start raw input manager for reliable single-key input
        self._input_mgr = _RawInputManager(self._key_queue)
        self._input_mgr.start()

        with Live(
            self.views[self.state.current_view].render(self.state),
            console=self.console,
            refresh_per_second=10,
            screen=True,
        ) as live:

            while self.running:
                # Update display
                current_view = self.views[self.state.current_view]
                live.update(current_view.render(self.state))

                # Process keyboard input
                await self._process_keyboard_input(current_view)

                # Small sleep to prevent busy loop
                await asyncio.sleep(0.1)

        # Stop input manager and restore terminal
        if self._input_mgr:
            self._input_mgr.stop()
            self._input_mgr = None

    async def _process_keyboard_input(self, current_view):
        """Process keyboard input for current view (queue-based)."""
        try:
            while True:
                try:
                    key = self._key_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                if not key:
                    continue

                # Global legend toggle persistence
                if key == "l":
                    try:
                        cfg = get_config()
                        cfg.settings.show_legend = self.state.show_legend
                        cfg.save_settings()
                    except Exception:
                        pass

                # Handle key with current view
                new_view_state = current_view.handle_key(key, self.state)

                # Handle application quit (only from Home)
                if key == "q" and self.state.current_view == ViewState.HOME:
                    self.running = False
                    return

                # Handle view transitions
                if new_view_state and new_view_state != self.state.current_view:
                    await self._handle_view_transition(new_view_state)

        except Exception as e:
            logger.debug(f"Input processing error: {e}")

    async def _get_key_async(self) -> Optional[str]:
        """Deprecated: kept for compatibility; no longer used."""
        return None

    async def _handle_view_transition(self, new_view_state: ViewState):
        """Handle transitions between views."""
        old_view = self.state.current_view
        self.state.current_view = new_view_state

        # Handle session management during transitions
        if old_view in [ViewState.LIVE_FREE, ViewState.LIVE_ERG, ViewState.LIVE_SIM]:
            if new_view_state not in [
                ViewState.LIVE_FREE,
                ViewState.LIVE_ERG,
                ViewState.LIVE_SIM,
            ]:
                # Leaving training mode
                await self._stop_training_session()

        elif new_view_state in [
            ViewState.LIVE_FREE,
            ViewState.LIVE_ERG,
            ViewState.LIVE_SIM,
        ]:
            # Entering training mode
            await self._prepare_training_mode(new_view_state)

        logger.debug(f"View transition: {old_view.value} -> {new_view_state.value}")

    async def _prepare_training_mode(self, mode_state: ViewState):
        """Prepare for entering training mode."""
        if self.trainer.is_connected:
            try:
                # Request trainer control
                await self.trainer.request_control()

                # Mode-specific setup
                if mode_state == ViewState.LIVE_ERG:
                    await self.trainer.set_target_power(150)
                    self.state.metrics["target_power_w"] = 150
                elif mode_state == ViewState.LIVE_SIM:
                    await self.trainer.set_simulation(0.0)
                    self.state.metrics["grade_pct"] = 0.0

                # Start trainer session
                await self.trainer.start()

            except Exception as e:
                logger.warning(f"Failed to prepare training mode: {e}")
                self.state.status_message = f"Training setup failed: {e}"

    async def _stop_training_session(self):
        """Stop current training session."""
        if not self.current_session:
            return

        try:
            if self.trainer.is_connected:
                await self.trainer.stop()

            elapsed_s = self.state.metrics.get("time_s", 0) or 0.0
            no_data = self._sample_count == 0 or elapsed_s <= 0.0

            if no_data:
                sid = self.current_session.session_id
                try:
                    self.session_service.delete_session(sid)
                    self.state.status_message = "Session aborted (no data)"
                    logger.info(f"Session {sid} aborted — no samples recorded")
                except Exception as e:
                    logger.warning(f"Failed to abort empty session {sid}: {e}")
                    self.state.status_message = "Session abort error"

                # Reset session state
                self.state.session_active = False
                self.state.session_paused = False
                self.state.session_start_time = None
                self.distance_m = 0.0
                self._sample_count = 0
                self.current_session = None
                return

            # Update session with final data
            from datetime import datetime

            self.current_session.end_time = datetime.now()
            self.current_session.duration_s = elapsed_s
            self.current_session.total_distance_m = self.state.metrics.get(
                "distance_m", 0
            )

            # Save updated session
            self.session_service.save_session(self.current_session)
            # Record last session id for summary
            self.state.last_session_id = self.current_session.session_id

            # Reset session state
            self.state.session_active = False
            self.state.session_paused = False
            self.state.session_start_time = None
            self.distance_m = 0.0
            self._sample_count = 0

            session_id = self.current_session.session_id
            self.current_session = None

            self.state.status_message = f"Session {session_id[:8]} finished"
            logger.info(f"Training session stopped: {session_id}")

        except Exception as e:
            logger.warning(f"Error stopping training session: {e}")
            self.state.status_message = f"Session stop error: {e}"

    async def _connection_loop(self):
        """Background loop for device connection management."""
        await asyncio.sleep(2)  # Let startup view show

        # Transition to connection view
        self.state.current_view = ViewState.CONNECT
        self.state.status_message = "Scanning for trainer..."

        # Attempt trainer connection
        try:
            await self.trainer.scan_and_connect(timeout_s=10.0)

            # Update device info
            self.state.devices["trainer"] = {
                "connected": True,
                "name": self.trainer.device_info.get("name", "Unknown"),
                "rssi": self.trainer.device_info.get("rssi"),
            }

            # Subscribe to bike data
            await self.trainer.subscribe_samples(self._on_bike_sample)

            self.state.status_message = "Trainer connected"
            logger.info("Trainer connected successfully")

            # Transition to home after short delay
            await asyncio.sleep(1)
            self.state.current_view = ViewState.HOME
            self.state.status_message = "Ready to train — pedal to stream data"

        except DeviceNotFoundError:
            self.state.status_message = "No trainer found - running in demo mode"
            logger.warning("No trainer found, continuing in demo mode")

            # Set up demo mode
            self.state.devices["trainer"] = {
                "connected": False,
                "name": "Demo Mode",
                "rssi": None,
            }

            await asyncio.sleep(2)
            self.state.current_view = ViewState.HOME

    async def _metrics_loop(self):
        """Background loop for metrics updates and calculations."""
        while self.running:
            try:
                # Update distance calculation
                if (
                    self.state.session_active
                    and not self.state.session_paused
                    and self.state.metrics.get("speed_mps")
                ):

                    current_time = time.time()
                    if self.last_sample_time:
                        dt = current_time - self.last_sample_time
                        speed_mps = self.state.metrics["speed_mps"]
                        self.distance_m += speed_mps * dt
                        self.state.metrics["distance_m"] = self.distance_m

                    self.last_sample_time = current_time

                # Handle mode transitions and control commands
                await self._apply_speed_source()
                await self._handle_mode_logic()

            except Exception as e:
                logger.debug(f"Metrics loop error: {e}")

            await asyncio.sleep(0.1)

    async def _handle_mode_logic(self):
        """Handle mode-specific logic (ERG/SIM control commands)."""
        if not self.trainer.is_connected or not self.state.session_active:
            return

        try:
            dt = 0.1  # Update interval

            # ERG mode power control with PI controller
            if (
                self.state.current_view == ViewState.LIVE_ERG
                and not self.state.session_paused
            ):
                target_power = self.state.metrics.get("target_power_w", 150)
                current_power = self.state.metrics.get("power_w", 0)

                # Use ERG controller to calculate optimal power
                optimal_power = self.erg_controller.update(
                    target_power, current_power, dt
                )

                # Send command to trainer
                await self.trainer.set_target_power(optimal_power)

            # SIM mode physics-based control
            elif (
                self.state.current_view == ViewState.LIVE_SIM
                and not self.state.session_paused
            ):
                grade_pct = self.state.metrics.get("grade_pct", 0.0)
                current_power = self.state.metrics.get("power_w", 0)

                # Calculate expected speed using physics solver
                if current_power > 0:
                    expected_speed = self.sim_solver.solve_speed(
                        current_power, grade_pct
                    )
                    self.state.metrics["expected_speed_mps"] = expected_speed

                # Send simulation parameters to trainer
                await self.trainer.set_simulation(grade_pct)

        except Exception as e:
            logger.debug(f"Mode control error: {e}")

    async def _device_management_loop(self) -> None:
        """Background loop for handling device scan/connect requests from UI."""
        while self.running:
            try:
                await self._process_device_requests()
            except Exception as e:
                logger.debug(f"Device management error: {e}")

            await asyncio.sleep(0.2)

    async def _process_device_requests(self) -> None:
        """Process pending device scan/connect/disconnect requests."""
        devices = self.state.devices

        # Handle trainer scan request
        if self.state.scanning_trainers:
            try:
                available = await self.trainer._client.scan_available(timeout_s=5.0)
                self.state.available_trainers = available
                self.state.status_message = f"Found {len(available)} trainer(s)"
            except Exception as e:
                logger.warning(f"Trainer scan failed: {e}")
                self.state.status_message = f"Scan failed: {e}"
                self.state.available_trainers = []
            finally:
                self.state.scanning_trainers = False

        # Handle HR scan request
        if self.state.scanning_hr:
            try:
                available = await self.hr_service._client.scan_available(timeout_s=5.0)
                self.state.available_hr = available
                self.state.status_message = f"Found {len(available)} HR monitor(s)"
            except Exception as e:
                logger.warning(f"HR scan failed: {e}")
                self.state.status_message = f"Scan failed: {e}"
                self.state.available_hr = []
            finally:
                self.state.scanning_hr = False

        # Handle trainer connection request
        pending_trainer = devices.pop("_pending_trainer", None)
        if pending_trainer:
            address = pending_trainer.get("address")
            name = pending_trainer.get("name", "trainer")
            try:
                # Disconnect existing if connected
                if self.trainer.is_connected:
                    await self.trainer.disconnect()

                await self.trainer._client.connect_to_device(address)

                # Update state
                devices["trainer"] = {
                    "connected": True,
                    "name": self.trainer._client.device_info.get("name", name),
                    "address": address,
                    "rssi": self.trainer._client.device_info.get("rssi"),
                }

                # Subscribe to bike data
                await self.trainer.subscribe_samples(self._on_bike_sample)

                self.state.status_message = f"Connected to {name}"
                logger.info(f"Manually connected to trainer: {name}")

            except Exception as e:
                logger.warning(f"Failed to connect to trainer {name}: {e}")
                self.state.status_message = f"Connection failed: {e}"

        # Handle HR connection request
        pending_hr = devices.pop("_pending_hr", None)
        if pending_hr:
            address = pending_hr.get("address")
            name = pending_hr.get("name", "HR monitor")
            try:
                # Disconnect existing if connected
                if self.hr_service.is_connected:
                    await self.hr_service.disconnect()

                await self.hr_service._client.connect_to_device(address)

                # Update state
                devices["hr"] = {
                    "connected": True,
                    "name": self.hr_service._client.device_info.get("name", name),
                    "address": address,
                    "rssi": self.hr_service._client.device_info.get("rssi"),
                }

                # Subscribe to HR data
                await self.hr_service.subscribe_hr_data(self._on_hr_sample)

                self.state.status_message = f"Connected to {name}"
                logger.info(f"Manually connected to HR: {name}")

            except Exception as e:
                logger.warning(f"Failed to connect to HR {name}: {e}")
                self.state.status_message = f"Connection failed: {e}"

        # Handle trainer disconnect request
        if devices.pop("_disconnect_trainer", None):
            try:
                if self.trainer.is_connected:
                    await self.trainer.disconnect()
                devices["trainer"] = {"connected": False, "name": None}
                self.state.status_message = "Trainer disconnected"
            except Exception as e:
                logger.warning(f"Failed to disconnect trainer: {e}")
                self.state.status_message = f"Disconnect failed: {e}"

        # Handle HR disconnect request
        if devices.pop("_disconnect_hr", None):
            try:
                if self.hr_service.is_connected:
                    await self.hr_service.disconnect()
                devices["hr"] = {"connected": False, "name": None}
                self.state.status_message = "HR monitor disconnected"
            except Exception as e:
                logger.warning(f"Failed to disconnect HR: {e}")
                self.state.status_message = f"Disconnect failed: {e}"

    def _on_hr_sample(self, sample: HrSample) -> None:
        """Handle incoming HR data sample."""
        hr_bpm = sample.get("hr_bpm")
        if hr_bpm is not None:
            self.state.metrics["hr_bpm"] = hr_bpm

    async def _apply_speed_source(self) -> None:
        """Apply speed source policy: trainer|virtual|auto.

        - trainer: leave speed_mps as reported by device
        - virtual: compute speed via physics (grade from metrics, default 0)
        - auto: use trainer unless implausible (>17 m/s or far above physics prediction)
        """
        try:
            from .config import get_config

            policy = getattr(get_config().settings, "speed_source", "trainer")

            # Only when session active and not paused
            if not (self.state.session_active and not self.state.session_paused):
                return

            power = self.state.metrics.get("power_w") or 0
            grade = self.state.metrics.get("grade_pct", 0.0)
            trainer_speed = self.state.metrics.get("speed_mps")

            # Compute physics-based estimate when needed
            virt_speed = None
            if power > 0:
                virt_speed = self.sim_solver.solve_speed(power, grade)

            if policy == "virtual":
                if virt_speed is not None:
                    self.state.metrics["speed_mps"] = virt_speed
            elif policy == "auto":
                # Plausibility threshold ~17 m/s (61 km/h)
                implausible = trainer_speed is None or (
                    trainer_speed is not None and trainer_speed > 17.0
                )
                if virt_speed is not None:
                    # If trainer is >30% above physics estimate, treat as implausible
                    if trainer_speed is not None and trainer_speed > virt_speed * 1.3:
                        implausible = True
                if implausible and virt_speed is not None:
                    self.state.metrics["speed_mps"] = virt_speed
                    logger.debug(
                        f"Auto speed: replacing trainer {trainer_speed} with virtual {virt_speed:.3f}"
                    )
            # Update average speed in kph from distance/time
            t = self.state.metrics.get("time_s") or 0.0
            d_m = self.state.metrics.get("distance_m") or 0.0
            if t > 0:
                self.state.metrics["avg_speed_kph"] = (d_m / t) * 3.6

        except Exception as e:
            logger.debug(f"Speed source application error: {e}")

    def _on_bike_sample(self, sample: BikeSample):
        """Handle incoming bike data sample."""
        # Update metrics with latest sample
        self.state.metrics.update(
            {
                "power_w": sample["power_w"],
                "cadence_rpm": sample["cadence_rpm"],
                "speed_mps": sample["speed_mps"],
                "timestamp": sample["ts"],
            }
        )

        if not self._got_first_sample:
            self._got_first_sample = True
            self.state.status_message = "Receiving data from trainer"
            logger.info("First trainer sample received")

        # Initialize session on first sample if in training mode
        if (
            self.state.current_view
            in [ViewState.LIVE_FREE, ViewState.LIVE_ERG, ViewState.LIVE_SIM]
            and not self.state.session_active
        ):
            self._start_training_session()

        # Record sample data if session is active
        if self.state.session_active and self.current_session:
            self._record_sample_data(sample)

    def _start_training_session(self):
        """Initialize a new training session."""
        self.state.session_active = True
        self.state.session_paused = False
        self.state.session_start_time = time.time()
        self.distance_m = 0.0
        self.last_sample_time = None
        self._sample_count = 0
        # Reset average accumulators
        self._avg_power_sum = 0.0
        self._avg_power_count = 0
        self._avg_cad_sum = 0.0
        self._avg_cad_count = 0
        self._avg_hr_sum = 0.0
        self._avg_hr_count = 0

        # Create session model
        mode_map = {
            ViewState.LIVE_FREE: TrainingMode.FREE,
            ViewState.LIVE_ERG: TrainingMode.ERG,
            ViewState.LIVE_SIM: TrainingMode.SIM,
        }

        mode = mode_map.get(self.state.current_view, TrainingMode.FREE)
        trainer_name = self.state.devices.get("trainer", {}).get("name", "Unknown")

        from datetime import datetime

        self.current_session = SessionModel(
            mode=mode,
            start_time=datetime.now(),
            trainer_name=trainer_name,
        )

        # Save session to repository
        self.session_service.save_session(self.current_session)

        # Set default values for mode
        if self.state.current_view == ViewState.LIVE_ERG:
            self.state.metrics.setdefault("target_power_w", 150)
            self.current_session.erg_target_power_w = 150
        elif self.state.current_view == ViewState.LIVE_SIM:
            self.state.metrics.setdefault("grade_pct", 0.0)

        logger.info(
            f"Training session started: {self.current_session.session_id} ({mode.value})"
        )

    def _record_sample_data(self, sample: BikeSample):
        """Record sample data to repository."""
        if not self.current_session:
            return

        try:
            elapsed_s = self.state.metrics.get("time_s", 0)
            # Update running averages (only while active and not paused)
            if self.state.session_active and not self.state.session_paused:
                pw = sample.get("power_w")
                if pw is not None:
                    self._avg_power_sum += float(pw)
                    self._avg_power_count += 1
                    self.state.metrics["avg_power_w"] = self._avg_power_sum / max(
                        1, self._avg_power_count
                    )
                cad = sample.get("cadence_rpm")
                if cad is not None:
                    self._avg_cad_sum += float(cad)
                    self._avg_cad_count += 1
                    self.state.metrics["avg_cadence_rpm"] = self._avg_cad_sum / max(
                        1, self._avg_cad_count
                    )
                # Avg speed derived from distance/time in UI (also set below on apply_speed_source)
                hr = self.state.metrics.get("hr_bpm")
                if hr is not None:
                    self._avg_hr_sum += float(hr)
                    self._avg_hr_count += 1
                    self.state.metrics["avg_hr_bpm"] = self._avg_hr_sum / max(
                        1, self._avg_hr_count
                    )

            # Create sample model
            sample_model = SampleModel(
                session_id=self.current_session.session_id,
                elapsed_s=elapsed_s,
                power_w=sample.get("power_w"),
                cadence_rpm=sample.get("cadence_rpm"),
                speed_mps=sample.get("speed_mps"),
                distance_m=self.state.metrics.get("distance_m", 0),
                erg_target_power_w=(
                    self.state.metrics.get("target_power_w")
                    if self.state.current_view == ViewState.LIVE_ERG
                    else None
                ),
                sim_grade_pct=(
                    self.state.metrics.get("grade_pct")
                    if self.state.current_view == ViewState.LIVE_SIM
                    else None
                ),
            )

            # Save to repository
            self.session_service.save_sample(sample_model)
            self._sample_count += 1

        except Exception as e:
            logger.debug(f"Failed to record sample data: {e}")

    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def _cleanup(self):
        """Clean up resources on shutdown."""
        logger.info("Cleaning up application resources...")

        try:
            if self.trainer.is_connected:
                await self.trainer.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting trainer: {e}")

        try:
            if self.hr_service.is_connected:
                await self.hr_service.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting HR: {e}")

        logger.info("Application shutdown complete")

    async def cleanup(self):
        """Clean up application resources."""
        await self._cleanup()


async def main():
    """Application entry point."""
    # Configure logging: write to file only (avoid console logs that break TUI)
    setup_logging(app_log_level="INFO", lib_log_level="WARNING", console_output=False)

    # Create and run application
    app = TerminalRideApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())


class _RawInputManager:
    """Manage terminal cbreak mode and deliver keys via asyncio queue."""

    def __init__(self, queue: asyncio.Queue[str]):
        self.queue = queue
        self._fd = sys.stdin.fileno()
        self._old_term = None
        self._old_flags = None
        self._loop = asyncio.get_event_loop()
        self._running = False
        self._esc_buffer: list[str] = []
        self._esc_timer = None  # type: ignore

    def start(self) -> None:
        try:
            # Save terminal state and enter cbreak (character-at-a-time)
            self._old_term = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)

            # Keep blocking reads; add_reader only fires when readable
            self._old_flags = None

            # Register reader callback with event loop
            self._loop.add_reader(self._fd, self._on_stdin_ready)
            self._running = True
        except Exception as e:
            logging.getLogger(__name__).debug(f"Raw input start failed: {e}")

    def stop(self) -> None:
        try:
            if self._running:
                self._loop.remove_reader(self._fd)
                self._running = False
        finally:
            try:
                if self._old_term is not None:
                    termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_term)
            except Exception:
                pass

    def _on_stdin_ready(self) -> None:
        try:
            data = os.read(self._fd, 64)
            if not data:
                return

            for b in data:
                ch = chr(b)

                # Escape sequences for arrows (ESC [ A/B/C/D)
                if ch == "\x1b":
                    # Start ESC sequence; schedule a short timeout to treat as lone ESC
                    self._esc_buffer = ["\x1b"]
                    if self._esc_timer:
                        try:
                            self._esc_timer.cancel()
                        except Exception:
                            pass
                    # 50 ms is typically enough for terminals to deliver '[' and the next code
                    self._esc_timer = self._loop.call_later(
                        0.05, self._flush_escape_if_pending
                    )
                    continue

                if self._esc_buffer:
                    self._esc_buffer.append(ch)
                    # If second byte isn't '[', treat as lone ESC
                    if len(self._esc_buffer) == 2 and self._esc_buffer[1] != "[":
                        self._put_nowait("escape")
                        self._esc_buffer.clear()
                        if self._esc_timer:
                            try:
                                self._esc_timer.cancel()
                            except Exception:
                                pass
                        continue

                    if len(self._esc_buffer) == 3:
                        mapped = None
                        if self._esc_buffer[1] == "[":
                            if self._esc_buffer[2] == "A":
                                mapped = "up"
                            elif self._esc_buffer[2] == "B":
                                mapped = "down"
                            elif self._esc_buffer[2] == "C":
                                mapped = "right"
                            elif self._esc_buffer[2] == "D":
                                mapped = "left"
                        if mapped:
                            self._put_nowait(mapped)
                        else:
                            self._put_nowait("escape")
                        self._esc_buffer.clear()
                        if self._esc_timer:
                            try:
                                self._esc_timer.cancel()
                            except Exception:
                                pass
                    continue

                # Regular keys
                if ch in ("\r", "\n"):
                    self._put_nowait("enter")
                elif ch == "\x03":  # Ctrl-C
                    self._put_nowait("q")
                elif ch == "\x7f":  # Backspace (unused)
                    pass
                elif ch == " ":
                    self._put_nowait(" ")
                else:
                    self._put_nowait(ch)

        except BlockingIOError:
            pass
        except Exception as e:
            logging.getLogger(__name__).debug(f"stdin read error: {e}")

    def _put_nowait(self, key: str) -> None:
        try:
            self.queue.put_nowait(key)
        except Exception:
            pass

    def _flush_escape_if_pending(self) -> None:
        """Timeout handler: treat a pending single ESC byte as 'escape'."""
        try:
            if self._esc_buffer == ["\x1b"]:
                self._put_nowait("escape")
                self._esc_buffer.clear()
        finally:
            self._esc_timer = None
