"""UI-neutral ride orchestration.

The controller owns ride lifecycle state and live metrics. Device access,
storage, and UI rendering stay behind services so terminal, web, and future
3D surfaces can consume the same domain state.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine, Sequence
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from le_tour.analytics import calculate_training_metrics
from le_tour.config import get_config
from le_tour.devices.base import BikeSample, HrSample
from le_tour.modes.sim import RiderDynamics, SimConfig
from le_tour.store.models import SampleModel, SessionModel, TrainingMode

from .hr_service import HrService
from .routes import RouteProfile
from .session_service import SessionService, get_session_service
from .state import RideMetrics, RideMode, RideSnapshot, RideState
from .trainer_service import TrainerService

logger = logging.getLogger(__name__)


class RideController:
    """Coordinate ride state, metrics, devices, and persistence.

    The public surface intentionally uses plain dataclasses and methods that do
    not depend on any UI toolkit.
    """

    MIN_ERG_TARGET_W = 100
    MAX_ERG_TARGET_W = 400
    MIN_SIM_GRADE_PCT = -10.0
    MAX_SIM_GRADE_PCT = 15.0

    def __init__(
        self,
        trainer: Optional[TrainerService] = None,
        hr_service: Optional[HrService] = None,
        session_service: Optional[SessionService] = None,
    ) -> None:
        config = get_config()

        self.trainer = trainer or TrainerService()
        self.hr_service = hr_service or HrService()
        self._session_service = session_service

        self._state = RideState()
        self._metrics = RideMetrics(
            erg_target_w=config.settings.default_erg_power_w,
            sim_grade_pct=config.settings.default_sim_grade_pct,
        )
        self._started_monotonic: Optional[float] = None
        self._paused_started_monotonic: Optional[float] = None
        self._total_paused_s: float = 0.0
        self._last_sample_ts: Optional[float] = None
        self._sample_records: list[SampleModel] = []
        self._route_profile: Optional[RouteProfile] = None
        self._dynamics = self._build_dynamics()
        self._last_persistence_error: Optional[str] = None

        self.on_metrics_update: Optional[Callable[[RideMetrics], None]] = None
        self.on_state_change: Optional[Callable[[RideState], None]] = None

    @property
    def state(self) -> RideState:
        """Current lifecycle state."""
        return self._state

    @property
    def metrics(self) -> RideMetrics:
        """Current live metrics."""
        return self._metrics

    @property
    def is_active(self) -> bool:
        """True while a session is active."""
        return self._state.active

    @property
    def is_paused(self) -> bool:
        """True while an active session is paused."""
        return self._state.paused

    @property
    def recorded_sample_count(self) -> int:
        """Number of samples captured for the active or just-stopped session."""
        return len(self._sample_records)

    @property
    def last_persistence_error(self) -> Optional[str]:
        """Most recent persistence failure from stopping a session."""
        return self._last_persistence_error

    def snapshot(self) -> RideSnapshot:
        """Return a UI-neutral snapshot of current ride state and metrics."""
        session_state = "inactive"
        if self.is_active:
            session_state = "paused" if self.is_paused else "active"

        elapsed_s = self._metrics.elapsed_s
        if self.is_active:
            elapsed_s = self._elapsed_s()

        trainer_info = self.trainer.device_info if self.trainer.is_connected else {}
        hr_info = self.hr_service.device_info if self.hr_service.is_connected else {}

        return RideSnapshot(
            session_state=session_state,
            active=self.is_active,
            paused=self.is_paused,
            session_id=self._state.session_id,
            mode=self._state.mode,
            elapsed_s=elapsed_s,
            power_w=self._metrics.power_w,
            cadence_rpm=self._metrics.cadence_rpm,
            speed_mps=self._metrics.speed_mps,
            trainer_speed_mps=self._metrics.trainer_speed_mps,
            speed_source=self._metrics.speed_source,
            distance_m=self._metrics.distance_m,
            hr_bpm=self._metrics.hr_bpm,
            erg_target_w=self._metrics.erg_target_w,
            sim_grade_pct=self._metrics.sim_grade_pct,
            trainer_connected=self.trainer.is_connected,
            trainer_name=trainer_info.get("name") or self._state.trainer_name,
            hr_connected=self.hr_service.is_connected,
            hr_name=hr_info.get("name"),
        )

    def start_session(
        self,
        mode: RideMode,
        trainer_name: str = "Unknown Trainer",
    ) -> str:
        """Start a ride session.

        Args:
            mode: Training mode for the new session.
            trainer_name: Human-readable trainer name for persisted metadata.

        Returns:
            Newly created session identifier.
        """
        if self.is_active:
            self.stop_session()

        config = get_config()
        session_id = str(uuid4())
        now = datetime.now(UTC)

        self._state = RideState(
            mode=mode,
            active=True,
            paused=False,
            session_id=session_id,
            started_at=now,
            trainer_name=trainer_name,
        )
        self._metrics = RideMetrics(
            erg_target_w=config.settings.default_erg_power_w,
            sim_grade_pct=config.settings.default_sim_grade_pct,
        )
        if mode is RideMode.SIM:
            self._sync_sim_grade_from_route(notify=False)
        self._dynamics = self._build_dynamics()
        self._started_monotonic = time.monotonic()
        self._paused_started_monotonic = None
        self._total_paused_s = 0.0
        self._last_sample_ts = None
        self._sample_records = []
        self._last_persistence_error = None

        self._notify_state()
        self._notify_metrics()
        return session_id

    def stop_session(self) -> Optional[str]:
        """Stop the active session and persist it when samples exist.

        Returns:
            The saved session id when samples were captured, otherwise None.
        """
        return self._finish_session(persist=True)

    def discard_session(self) -> None:
        """Stop the active session without persisting samples."""
        self._finish_session(persist=False)

    def _finish_session(self, *, persist: bool) -> Optional[str]:
        if not self.is_active:
            return None

        self._metrics.elapsed_s = self._elapsed_s()
        self._state.ended_at = datetime.now(UTC)
        session_id = self._state.session_id
        saved_session_id: Optional[str] = None

        if persist and session_id is not None and self._sample_records:
            session = self._build_session_model(session_id)
            try:
                service = self._session_service or get_session_service()
                service.save_session(session)
                for sample in self._sample_records:
                    service.save_sample(sample)
                saved_session_id = session_id
            except Exception as exc:
                logger.warning("Failed to persist session %s: %s", session_id, exc)
                self._last_persistence_error = str(exc)

        self._state.active = False
        self._state.paused = False
        self._started_monotonic = None
        self._paused_started_monotonic = None
        self._total_paused_s = 0.0
        self._last_sample_ts = None
        self._notify_state()
        return saved_session_id

    def pause(self) -> None:
        """Pause the active session."""
        if not self.is_active or self.is_paused:
            return
        self._metrics.elapsed_s = self._elapsed_s()
        self._state.paused = True
        self._paused_started_monotonic = time.monotonic()
        self._last_sample_ts = None
        self._notify_state()
        self._notify_metrics()

    def resume(self) -> None:
        """Resume a paused active session."""
        if not self.is_active or not self.is_paused:
            return
        if self._paused_started_monotonic is not None:
            self._total_paused_s += time.monotonic() - self._paused_started_monotonic
        self._paused_started_monotonic = None
        self._state.paused = False
        self._last_sample_ts = None
        # The rider restarts from a standstill after a pause.
        self._dynamics.reset()
        self._notify_state()

    def toggle_pause(self) -> bool:
        """Toggle pause state.

        Returns:
            True when the session is now paused, otherwise False.
        """
        if self.is_paused:
            self.resume()
        else:
            self.pause()
        return self.is_paused

    def set_erg_target(self, watts: int) -> int:
        """Set ERG target power, clamped to the trainer-safe range."""
        target = min(self.MAX_ERG_TARGET_W, max(self.MIN_ERG_TARGET_W, int(watts)))
        self._metrics.erg_target_w = target
        self._notify_metrics()

        if (
            self.is_active
            and self._state.mode is RideMode.ERG
            and self.trainer.is_connected
        ):
            self._schedule_trainer_command(self.trainer.set_target_power(target))

        return target

    def adjust_erg_target(self, delta_w: int) -> int:
        """Adjust ERG target power by a watt delta."""
        return self.set_erg_target(self._metrics.erg_target_w + delta_w)

    def set_sim_grade(self, grade_pct: float) -> float:
        """Set SIM grade percentage, clamped to supported bounds."""
        grade = self._clamp_sim_grade(grade_pct)
        self._metrics.sim_grade_pct = grade
        self._notify_metrics()

        if (
            self.is_active
            and self._state.mode is RideMode.SIM
            and self.trainer.is_connected
        ):
            self._schedule_trainer_command(self.trainer.set_simulation(grade))

        return grade

    def adjust_sim_grade(self, delta_pct: float) -> float:
        """Adjust SIM grade by a percentage-point delta."""
        return self.set_sim_grade(self._metrics.sim_grade_pct + delta_pct)

    def set_route_profile(self, route_profile: Optional[RouteProfile]) -> None:
        """Attach a distance-indexed route profile for SIM grade control."""
        self._route_profile = route_profile
        self._sync_sim_grade_from_route()

    def handle_bike_sample(self, sample: BikeSample) -> None:
        """Ingest one trainer sample and update live metrics.

        With a route attached, the virtual world is the speed authority:
        speed and distance come from rider dynamics (measured power + route
        grade + rider profile), so terrain, mass, and aerodynamics behave the
        same on every trainer. The trainer's own wheel speed is kept as a
        diagnostic. Without a route there is no world, and the trainer's
        reported speed is used directly.
        """
        if not self.is_active or self.is_paused:
            return

        sample_ts = float(sample["ts"])
        trainer_speed_mps = sample.get("speed_mps")

        self._metrics.elapsed_s = self._elapsed_s(sample_ts)
        self._metrics.power_w = sample.get("power_w")
        self._metrics.cadence_rpm = sample.get("cadence_rpm")
        self._metrics.trainer_speed_mps = trainer_speed_mps

        dt_s = self._sample_dt(sample_ts)
        if self._route_profile is not None:
            # Physics uses the true route grade; the resistance clamp below
            # only limits what is asked of the trainer hardware.
            step = self._dynamics.step(
                power_w=float(self._metrics.power_w or 0),
                grade_pct=self._route_profile.grade_at(self._metrics.distance_m),
                dt_s=dt_s,
            )
            self._metrics.speed_mps = step.speed_mps
            self._metrics.distance_m += step.distance_m
            self._metrics.speed_source = "physics"
        else:
            self._metrics.speed_mps = trainer_speed_mps
            if trainer_speed_mps is not None:
                self._metrics.distance_m += max(0.0, trainer_speed_mps) * dt_s
            self._metrics.speed_source = "trainer"

        self._sync_sim_grade_from_route()
        self._record_sample(sample_ts)

        self._notify_metrics()

    def handle_hr_sample(self, sample: HrSample) -> None:
        """Ingest one heart-rate sample and update live metrics."""
        if not self.is_active or self.is_paused:
            return

        sample_ts = float(sample["ts"])
        self._metrics.elapsed_s = self._elapsed_s(sample_ts)
        self._metrics.hr_bpm = sample.get("hr_bpm")

        self._record_sample(sample_ts)

        self._notify_metrics()

    def _elapsed_s(self, sample_ts: Optional[float] = None) -> float:
        if self._started_monotonic is not None:
            now = time.monotonic()
            if self.is_paused and self._paused_started_monotonic is not None:
                now = self._paused_started_monotonic
            return max(0.0, now - self._started_monotonic - self._total_paused_s)

        started_at = self._state.started_at
        if started_at is None or sample_ts is None:
            return 0.0

        return max(0.0, sample_ts - started_at.timestamp())

    def _sample_dt(self, sample_ts: float) -> float:
        if self._last_sample_ts is None:
            self._last_sample_ts = sample_ts
            return 0.0

        dt_s = max(0.0, sample_ts - self._last_sample_ts)
        self._last_sample_ts = sample_ts
        return dt_s

    @staticmethod
    def _build_dynamics() -> RiderDynamics:
        config = get_config()
        return RiderDynamics(
            SimConfig(
                mass_kg=config.user_mass_kg,
                cda_m2=config.settings.cda_m2,
                crr=config.settings.crr,
            )
        )

    def _sync_sim_grade_from_route(self, notify: bool = True) -> None:
        if (
            self._route_profile is None
            or not self.is_active
            or self._state.mode is not RideMode.SIM
        ):
            return

        grade = self._clamp_sim_grade(
            self._route_profile.grade_at(self._metrics.distance_m)
        )
        if grade == self._metrics.sim_grade_pct:
            return

        self._metrics.sim_grade_pct = grade
        if notify:
            self._notify_metrics()

        if self.trainer.is_connected:
            self._schedule_trainer_command(self.trainer.set_simulation(grade))

    def _clamp_sim_grade(self, grade_pct: float) -> float:
        return min(
            self.MAX_SIM_GRADE_PCT,
            max(self.MIN_SIM_GRADE_PCT, float(grade_pct)),
        )

    def _record_sample(self, sample_ts: float) -> None:
        session_id = self._state.session_id
        if session_id is None:
            return

        self._sample_records.append(
            SampleModel(
                session_id=session_id,
                timestamp=datetime.fromtimestamp(sample_ts, UTC),
                elapsed_s=self._metrics.elapsed_s,
                power_w=self._metrics.power_w,
                cadence_rpm=self._metrics.cadence_rpm,
                speed_mps=self._metrics.speed_mps,
                distance_m=self._metrics.distance_m,
                hr_bpm=self._metrics.hr_bpm,
                erg_target_power_w=self._metrics.erg_target_w,
                sim_grade_pct=self._metrics.sim_grade_pct,
            )
        )

    def _build_session_model(self, session_id: str) -> SessionModel:
        config = get_config()
        start_time = self._state.started_at or datetime.now(UTC)
        end_time = self._state.ended_at or datetime.now(UTC)
        samples = self._sample_records

        power_values = [s.power_w for s in samples if s.power_w is not None]
        cadence_values = [s.cadence_rpm for s in samples if s.cadence_rpm is not None]
        speed_values = [s.speed_mps for s in samples if s.speed_mps is not None]
        hr_values = [s.hr_bpm for s in samples if s.hr_bpm is not None]
        training_metrics = calculate_training_metrics(
            power_samples=power_values,
            duration_seconds=self._metrics.elapsed_s,
            ftp_w=config.user_ftp_w,
            sample_rate_hz=1.0,
        )
        route_id = getattr(self._route_profile, "route_id", None)
        route_title = getattr(self._route_profile, "title", None)

        return SessionModel(
            session_id=session_id,
            mode=TrainingMode((self._state.mode or RideMode.FREE).value),
            start_time=start_time,
            end_time=end_time,
            duration_s=self._metrics.elapsed_s,
            trainer_name=self._state.trainer_name,
            user_mass_kg=config.user_mass_kg,
            user_ftp_w=config.user_ftp_w,
            erg_target_power_w=(
                self._metrics.erg_target_w if self._state.mode is RideMode.ERG else None
            ),
            sim_grade_pct=(
                self._metrics.sim_grade_pct
                if self._state.mode is RideMode.SIM
                else None
            ),
            sim_route_id=(
                str(route_id) if self._state.mode is RideMode.SIM and route_id else None
            ),
            sim_route_title=(
                str(route_title)
                if self._state.mode is RideMode.SIM and route_title
                else None
            ),
            total_distance_m=self._metrics.distance_m,
            avg_power_w=self._mean(power_values),
            max_power_w=max(power_values) if power_values else None,
            avg_cadence_rpm=self._mean(cadence_values),
            avg_speed_mps=self._mean(speed_values),
            avg_hr_bpm=self._mean(hr_values),
            max_hr_bpm=max(hr_values) if hr_values else None,
            normalized_power_w=(
                training_metrics.normalized_power_w if training_metrics else None
            ),
            intensity_factor=(
                training_metrics.intensity_factor if training_metrics else None
            ),
            training_stress_score=(
                training_metrics.training_stress_score if training_metrics else None
            ),
        )

    def _notify_metrics(self) -> None:
        if self.on_metrics_update is None:
            return

        try:
            self.on_metrics_update(self._metrics)
        except Exception as exc:
            logger.debug("Ride metrics callback failed: %s", exc)

    def _notify_state(self) -> None:
        if self.on_state_change is None:
            return

        try:
            self.on_state_change(self._state)
        except Exception as exc:
            logger.debug("Ride state callback failed: %s", exc)

    def _schedule_trainer_command(
        self, command: Coroutine[object, object, None]
    ) -> None:
        try:
            asyncio.get_running_loop().create_task(command)
        except RuntimeError:
            command.close()

    @staticmethod
    def _mean(values: Sequence[int | float]) -> Optional[float]:
        if not values:
            return None
        return float(sum(values) / len(values))


__all__ = ["RideController", "RideMetrics", "RideMode", "RideSnapshot", "RideState"]
