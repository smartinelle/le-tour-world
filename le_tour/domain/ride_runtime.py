"""UI-neutral ride runtime helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from le_tour.devices.base import HrSample

from .fake_samples import FakeTrainerSampleSource
from .ride_controller import RideController
from .routes import RouteProfile
from .state import RideMode, RideSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RideStopResult:
    """UI-neutral result of ending a ride."""

    snapshot: RideSnapshot
    session_id: Optional[str]
    saved_session_id: Optional[str]
    sample_count: int
    persistence_error: Optional[str] = None

    @property
    def saved(self) -> bool:
        """True when the stopped ride was persisted."""
        return self.saved_session_id is not None and self.persistence_error is None


class RideRuntime:
    """Own ride actions and local sample-source lifecycle for one controller."""

    def __init__(
        self,
        controller: RideController,
        route_profile: Optional[RouteProfile] = None,
    ) -> None:
        self.controller = controller
        self.route_profile = route_profile
        if route_profile is not None:
            self.controller.set_route_profile(route_profile)
        self._fake_source: Optional[FakeTrainerSampleSource] = None
        self._trainer_samples_attached = False
        self._hr_samples_attached = False

    def set_route_profile(self, route_profile: Optional[RouteProfile]) -> None:
        """Attach the route profile used by route-aware ride modes."""
        self.route_profile = route_profile
        self.controller.set_route_profile(route_profile)

    @property
    def using_fake_source(self) -> bool:
        """True when the no-hardware fake source is running."""
        return self._fake_source is not None and self._fake_source.is_running

    def start_session(
        self,
        mode: RideMode,
        trainer_name: Optional[str] = None,
    ) -> RideSnapshot:
        """Start a ride and attach the local fake source when needed."""
        resolved_trainer_name = trainer_name or self._trainer_name()
        self.stop_fake_source()
        self.controller.start_session(mode, resolved_trainer_name)

        if not self.controller.trainer.is_connected:
            self.start_fake_source()

        return self.controller.snapshot()

    async def prepare_hardware_session(self, mode: RideMode) -> None:
        """Attach connected hardware streams and apply mode-specific control."""
        try:
            await self._attach_hr_stream()
            if not self.controller.trainer.is_connected:
                return

            if not self._trainer_samples_attached:
                await self.controller.trainer.subscribe_samples(
                    self.controller.handle_bike_sample
                )
                self._trainer_samples_attached = True

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

            logger.info("Hardware streams attached to active session")
        except Exception as exc:
            logger.warning("Failed to prepare hardware session: %s", exc)

    def stop_session(self) -> RideSnapshot:
        """Stop the ride and any runtime-owned sample source."""
        return self.stop_session_result().snapshot

    def stop_session_result(self) -> RideStopResult:
        """Stop the ride and return persistence details for presentation layers."""
        session_id = self.controller.state.session_id
        sample_count = self.controller.recorded_sample_count
        self.stop_fake_source()
        saved_session_id = self.controller.stop_session()
        snapshot = self.controller.snapshot()
        return RideStopResult(
            snapshot=snapshot,
            session_id=session_id,
            saved_session_id=saved_session_id,
            sample_count=sample_count,
            persistence_error=self.controller.last_persistence_error,
        )

    def toggle_pause(self) -> RideSnapshot:
        """Toggle pause state and return the latest snapshot."""
        self.controller.toggle_pause()
        return self.controller.snapshot()

    def adjust_erg_target(self, delta_w: int) -> RideSnapshot:
        """Adjust ERG target power and return the latest snapshot."""
        self.controller.adjust_erg_target(delta_w)
        return self.controller.snapshot()

    def adjust_sim_grade(self, delta_pct: float) -> RideSnapshot:
        """Adjust SIM grade and return the latest snapshot."""
        self.controller.adjust_sim_grade(delta_pct)
        return self.controller.snapshot()

    def start_fake_source(self) -> None:
        """Start no-hardware development samples for the active session."""
        if not self.controller.is_active or self.controller.trainer.is_connected:
            return

        self.stop_fake_source()

        hr_handler = self.controller.handle_hr_sample
        if self.controller.hr_service.is_connected:

            def ignore_hr_sample(sample: HrSample) -> None:
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

    def stop_fake_source(self) -> None:
        """Stop the no-hardware development sample source if running."""
        if self._fake_source is None:
            return
        self._fake_source.stop()
        self._fake_source = None

    async def _attach_hr_stream(self) -> None:
        if not self.controller.hr_service.is_connected or self._hr_samples_attached:
            return

        await self.controller.hr_service.subscribe_hr_data(
            self.controller.handle_hr_sample
        )
        self._hr_samples_attached = True

    def _trainer_name(self) -> str:
        if not self.controller.trainer.is_connected:
            return "Simulated Trainer"

        return str(self.controller.trainer.device_info.get("name", "Connected Trainer"))


__all__ = ["RideRuntime", "RideStopResult"]
