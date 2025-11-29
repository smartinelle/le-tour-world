"""RideController: UI-agnostic session and ride management.

This controller encapsulates all business logic for training sessions,
allowing any UI (terminal, web, desktop, mobile) to drive the same core
functionality.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from enum import Enum

from ..devices.base import BikeSample, HrSample
from ..modes.erg import ErgController
from ..modes.sim import SimPhysics, SimConfig
from ..store.models import SessionModel, SampleModel, TrainingMode
from ..store.repository import TrainingRepository
from ..config import get_config
from .session_service import SessionService
from .trainer_service import TrainerService
from .hr_service import HrService


logger = logging.getLogger(__name__)


class RideMode(str, Enum):
    """Training mode."""
    FREE = "free"
    ERG = "erg"
    SIM = "sim"


@dataclass
class RideMetrics:
    """Current ride metrics snapshot."""
    # Time
    elapsed_s: float = 0.0
    
    # Live values
    power_w: Optional[int] = None
    cadence_rpm: Optional[int] = None
    speed_mps: Optional[float] = None
    hr_bpm: Optional[int] = None
    
    # Accumulated
    distance_m: float = 0.0
    
    # Averages
    avg_power_w: Optional[float] = None
    avg_cadence_rpm: Optional[float] = None
    avg_speed_kph: Optional[float] = None
    avg_hr_bpm: Optional[float] = None
    
    # Mode-specific
    erg_target_w: int = 150
    sim_grade_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI consumption."""
        return {
            "time_s": self.elapsed_s,
            "power_w": self.power_w,
            "cadence_rpm": self.cadence_rpm,
            "speed_mps": self.speed_mps,
            "hr_bpm": self.hr_bpm,
            "distance_m": self.distance_m,
            "avg_power_w": self.avg_power_w,
            "avg_cadence_rpm": self.avg_cadence_rpm,
            "avg_speed_kph": self.avg_speed_kph,
            "avg_hr_bpm": self.avg_hr_bpm,
            "target_power_w": self.erg_target_w,
            "grade_pct": self.sim_grade_pct,
        }


@dataclass
class RideState:
    """Current ride state."""
    mode: Optional[RideMode] = None
    active: bool = False
    paused: bool = False
    start_time: Optional[float] = None
    session_id: Optional[str] = None


# Event callback types
OnMetricsUpdate = Callable[[RideMetrics], None]
OnStateChange = Callable[[RideState], None]
OnSessionSaved = Callable[[str], None]  # session_id
OnError = Callable[[str, str], None]  # code, message


class RideController:
    """UI-agnostic controller for ride/training session management.
    
    This class handles:
    - Session lifecycle (start, stop, pause, resume)
    - Metrics accumulation and averaging
    - Sample recording to storage
    - Mode-specific control (ERG power, SIM grade)
    - Device data integration
    
    Example usage:
        controller = RideController()
        controller.on_metrics_update = lambda m: update_ui(m)
        
        await controller.start_session(RideMode.ERG)
        controller.set_erg_target(200)
        # ... ride ...
        summary = await controller.stop_session()
    """
    
    def __init__(
        self,
        trainer_service: Optional[TrainerService] = None,
        hr_service: Optional[HrService] = None,
        repository: Optional[TrainingRepository] = None,
    ) -> None:
        # Services (injected or created)
        self._trainer = trainer_service or TrainerService()
        self._hr = hr_service or HrService()
        self._repository = repository or TrainingRepository()
        self._session_service = SessionService(self._repository)
        
        # Mode controllers
        self._erg_controller = ErgController()
        self._sim_solver = SimPhysics(SimConfig())
        
        # State
        self._state = RideState()
        self._metrics = RideMetrics()
        self._current_session: Optional[SessionModel] = None
        
        # Accumulation state
        self._last_sample_time: Optional[float] = None
        self._sample_count = 0
        self._power_sum = 0.0
        self._power_count = 0
        self._cadence_sum = 0.0
        self._cadence_count = 0
        self._hr_sum = 0.0
        self._hr_count = 0
        
        # Event callbacks (set by UI)
        self.on_metrics_update: Optional[OnMetricsUpdate] = None
        self.on_state_change: Optional[OnStateChange] = None
        self.on_session_saved: Optional[OnSessionSaved] = None
        self.on_error: Optional[OnError] = None
    
    # Properties
    @property
    def state(self) -> RideState:
        """Current ride state."""
        return self._state
    
    @property
    def metrics(self) -> RideMetrics:
        """Current metrics snapshot."""
        return self._metrics
    
    @property
    def trainer(self) -> TrainerService:
        """Trainer service for device operations."""
        return self._trainer
    
    @property
    def hr_service(self) -> HrService:
        """HR service for heart rate device operations."""
        return self._hr
    
    @property
    def is_active(self) -> bool:
        """True if a session is currently active."""
        return self._state.active
    
    @property
    def is_paused(self) -> bool:
        """True if current session is paused."""
        return self._state.paused
    
    # Session lifecycle
    def start_session(self, mode: RideMode, trainer_name: str = "Unknown") -> str:
        """Start a new training session.
        
        Args:
            mode: Training mode (FREE, ERG, SIM)
            trainer_name: Name of connected trainer
            
        Returns:
            Session ID
        """
        if self._state.active:
            logger.warning("Session already active, stopping first")
            self.stop_session()
        
        # Reset state
        self._state = RideState(
            mode=mode,
            active=True,
            paused=False,
            start_time=time.time(),
        )
        
        # Reset metrics
        self._metrics = RideMetrics()
        if mode == RideMode.ERG:
            cfg = get_config()
            self._metrics.erg_target_w = cfg.settings.default_erg_power_w
        elif mode == RideMode.SIM:
            cfg = get_config()
            self._metrics.sim_grade_pct = cfg.settings.default_sim_grade_pct
        
        # Reset accumulators
        self._last_sample_time = None
        self._sample_count = 0
        self._power_sum = 0.0
        self._power_count = 0
        self._cadence_sum = 0.0
        self._cadence_count = 0
        self._hr_sum = 0.0
        self._hr_count = 0
        
        # Create session model
        mode_map = {
            RideMode.FREE: TrainingMode.FREE,
            RideMode.ERG: TrainingMode.ERG,
            RideMode.SIM: TrainingMode.SIM,
        }
        
        self._current_session = SessionModel(
            mode=mode_map[mode],
            start_time=datetime.now(),
            trainer_name=trainer_name,
        )
        
        # Save initial session
        self._session_service.save_session(self._current_session)
        self._state.session_id = self._current_session.session_id
        
        logger.info(f"Session started: {self._state.session_id} ({mode.value})")
        self._emit_state_change()
        
        return self._state.session_id
    
    def stop_session(self) -> Optional[str]:
        """Stop the current session.
        
        Returns:
            Session ID if session was saved, None if no data
        """
        if not self._state.active or not self._current_session:
            return None
        
        session_id = self._current_session.session_id
        
        # Check if we have any data
        if self._sample_count == 0:
            logger.info(f"Session {session_id} aborted - no samples")
            try:
                self._session_service.delete_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to delete empty session: {e}")
            self._reset_state()
            return None
        
        # Update session with final data
        self._current_session.end_time = datetime.now()
        self._current_session.duration_s = self._metrics.elapsed_s
        self._current_session.total_distance_m = self._metrics.distance_m
        self._current_session.avg_power_w = self._metrics.avg_power_w
        self._current_session.avg_cadence_rpm = self._metrics.avg_cadence_rpm
        self._current_session.avg_hr_bpm = self._metrics.avg_hr_bpm
        
        # Save final session
        self._session_service.save_session(self._current_session)
        
        logger.info(f"Session stopped: {session_id}")
        
        if self.on_session_saved:
            self.on_session_saved(session_id)
        
        self._reset_state()
        return session_id
    
    def pause(self) -> None:
        """Pause the current session."""
        if self._state.active and not self._state.paused:
            self._state.paused = True
            logger.debug("Session paused")
            self._emit_state_change()
    
    def resume(self) -> None:
        """Resume a paused session."""
        if self._state.active and self._state.paused:
            self._state.paused = False
            self._last_sample_time = None  # Reset time tracking
            logger.debug("Session resumed")
            self._emit_state_change()
    
    def toggle_pause(self) -> bool:
        """Toggle pause state. Returns new paused state."""
        if self._state.paused:
            self.resume()
        else:
            self.pause()
        return self._state.paused
    
    # Mode control
    def set_erg_target(self, watts: int) -> None:
        """Set ERG mode target power."""
        watts = max(100, min(400, watts))
        self._metrics.erg_target_w = watts
        logger.debug(f"ERG target set to {watts}W")
    
    def adjust_erg_target(self, delta: int) -> int:
        """Adjust ERG target by delta. Returns new target."""
        new_target = self._metrics.erg_target_w + delta
        self.set_erg_target(new_target)
        return self._metrics.erg_target_w
    
    def set_sim_grade(self, grade_pct: float) -> None:
        """Set SIM mode grade percentage."""
        grade_pct = max(-10.0, min(15.0, grade_pct))
        self._metrics.sim_grade_pct = grade_pct
        logger.debug(f"SIM grade set to {grade_pct:.1f}%")
    
    def adjust_sim_grade(self, delta: float) -> float:
        """Adjust SIM grade by delta. Returns new grade."""
        new_grade = self._metrics.sim_grade_pct + delta
        self.set_sim_grade(new_grade)
        return self._metrics.sim_grade_pct
    
    # Data handling
    def handle_bike_sample(self, sample: BikeSample) -> None:
        """Process incoming bike data sample.
        
        Call this when trainer sends new data.
        """
        # Update live metrics
        self._metrics.power_w = sample.get("power_w")
        self._metrics.cadence_rpm = sample.get("cadence_rpm")
        self._metrics.speed_mps = sample.get("speed_mps")
        
        # Only accumulate if session active and not paused
        if not self._state.active or self._state.paused:
            self._emit_metrics_update()
            return
        
        # Update elapsed time
        if self._state.start_time:
            self._metrics.elapsed_s = time.time() - self._state.start_time
        
        # Update distance
        current_time = time.time()
        if self._last_sample_time and self._metrics.speed_mps:
            dt = current_time - self._last_sample_time
            self._metrics.distance_m += self._metrics.speed_mps * dt
        self._last_sample_time = current_time
        
        # Update averages
        if self._metrics.power_w is not None:
            self._power_sum += self._metrics.power_w
            self._power_count += 1
            self._metrics.avg_power_w = self._power_sum / self._power_count
        
        if self._metrics.cadence_rpm is not None:
            self._cadence_sum += self._metrics.cadence_rpm
            self._cadence_count += 1
            self._metrics.avg_cadence_rpm = self._cadence_sum / self._cadence_count
        
        # Average speed from distance/time
        if self._metrics.elapsed_s > 0:
            self._metrics.avg_speed_kph = (
                self._metrics.distance_m / self._metrics.elapsed_s
            ) * 3.6
        
        # Record sample
        self._record_sample(sample)
        self._sample_count += 1
        
        self._emit_metrics_update()
    
    def handle_hr_sample(self, sample: HrSample) -> None:
        """Process incoming heart rate sample."""
        hr_bpm = sample.get("hr_bpm")
        if hr_bpm is not None:
            self._metrics.hr_bpm = hr_bpm
            
            # Update HR average if session active
            if self._state.active and not self._state.paused:
                self._hr_sum += hr_bpm
                self._hr_count += 1
                self._metrics.avg_hr_bpm = self._hr_sum / self._hr_count
        
        self._emit_metrics_update()
    
    def _record_sample(self, sample: BikeSample) -> None:
        """Record sample to storage."""
        if not self._current_session:
            return
        
        try:
            sample_model = SampleModel(
                session_id=self._current_session.session_id,
                elapsed_s=self._metrics.elapsed_s,
                power_w=sample.get("power_w"),
                cadence_rpm=sample.get("cadence_rpm"),
                speed_mps=sample.get("speed_mps"),
                distance_m=self._metrics.distance_m,
                hr_bpm=self._metrics.hr_bpm,
                erg_target_power_w=(
                    self._metrics.erg_target_w
                    if self._state.mode == RideMode.ERG
                    else None
                ),
                sim_grade_pct=(
                    self._metrics.sim_grade_pct
                    if self._state.mode == RideMode.SIM
                    else None
                ),
            )
            self._session_service.save_sample(sample_model)
        except Exception as e:
            logger.debug(f"Failed to record sample: {e}")
    
    # ERG/SIM control loop (call periodically from UI)
    async def update_mode_control(self, dt: float = 0.1) -> None:
        """Update mode-specific control. Call this periodically (~10Hz).
        
        Args:
            dt: Time delta since last call in seconds
        """
        if not self._state.active or self._state.paused:
            return
        
        if not self._trainer.is_connected:
            return
        
        try:
            if self._state.mode == RideMode.ERG:
                # ERG PI control
                current_power = self._metrics.power_w or 0
                target = self._metrics.erg_target_w
                
                optimal = self._erg_controller.update(target, current_power, dt)
                await self._trainer.set_target_power(optimal)
                
            elif self._state.mode == RideMode.SIM:
                # SIM grade control
                await self._trainer.set_simulation(self._metrics.sim_grade_pct)
                
        except Exception as e:
            logger.debug(f"Mode control error: {e}")
    
    # Helpers
    def _reset_state(self) -> None:
        """Reset controller state after session end."""
        self._state = RideState()
        self._current_session = None
        self._emit_state_change()
    
    def _emit_metrics_update(self) -> None:
        """Emit metrics update to UI."""
        if self.on_metrics_update:
            try:
                self.on_metrics_update(self._metrics)
            except Exception as e:
                logger.debug(f"Metrics callback error: {e}")
    
    def _emit_state_change(self) -> None:
        """Emit state change to UI."""
        if self.on_state_change:
            try:
                self.on_state_change(self._state)
            except Exception as e:
                logger.debug(f"State callback error: {e}")
    
    def _emit_error(self, code: str, message: str) -> None:
        """Emit error to UI."""
        if self.on_error:
            try:
                self.on_error(code, message)
            except Exception as e:
                logger.debug(f"Error callback error: {e}")


# Singleton instance
_ride_controller: Optional[RideController] = None


def get_ride_controller() -> RideController:
    """Get (or create) the shared ride controller instance."""
    global _ride_controller
    if _ride_controller is None:
        _ride_controller = RideController()
    return _ride_controller

