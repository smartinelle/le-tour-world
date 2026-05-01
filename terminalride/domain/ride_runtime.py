"""UI-neutral ride runtime helpers."""

from __future__ import annotations

import logging
from typing import Optional

from terminalride.devices.base import HrSample

from .fake_samples import FakeTrainerSampleSource
from .ride_controller import RideController
from .state import RideMode, RideSnapshot

logger = logging.getLogger(__name__)


class RideRuntime:
    """Own ride actions and local sample-source lifecycle for one controller."""

    def __init__(self, controller: RideController) -> None:
        self.controller = controller
        self._fake_source: Optional[FakeTrainerSampleSource] = None

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

    def stop_session(self) -> RideSnapshot:
        """Stop the ride and any runtime-owned sample source."""
        self.stop_fake_source()
        self.controller.stop_session()
        return self.controller.snapshot()

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

    def _trainer_name(self) -> str:
        if not self.controller.trainer.is_connected:
            return "Simulated Trainer"

        return str(self.controller.trainer.device_info.get("name", "Connected Trainer"))


__all__ = ["RideRuntime"]
