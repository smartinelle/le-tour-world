"""Development sample source for rides without hardware."""

from __future__ import annotations

import asyncio
import math
import random
import time
from collections.abc import Callable
from typing import Optional

from le_tour.devices.base import BikeSample, HrSample

from .state import RideMode, RideSnapshot


class FakeTrainerSampleSource:
    """Generate plausible indoor cycling samples for no-hardware development.

    The source has no UI dependency. Callers pass the same handlers used for
    real BLE samples, so fake data and hardware data enter the domain through
    the same controller methods.
    """

    def __init__(
        self,
        bike_handler: Callable[[BikeSample], None],
        hr_handler: Callable[[HrSample], None],
        snapshot_provider: Callable[[], RideSnapshot],
        interval_s: float = 1.0,
        seed: Optional[int] = None,
    ) -> None:
        self._bike_handler = bike_handler
        self._hr_handler = hr_handler
        self._snapshot_provider = snapshot_provider
        self._interval_s = interval_s
        self._random = random.Random(seed)
        self._task: Optional[asyncio.Task[None]] = None
        self._started_at_s: Optional[float] = None
        self._power_w = 140.0
        self._cadence_rpm = 82.0
        self._speed_mps = 7.0
        self._hr_bpm = 112.0

    @property
    def is_running(self) -> bool:
        """True while the background generator task is active."""
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        """Start generating samples on the current asyncio loop."""
        if self.is_running:
            return
        self._started_at_s = time.time()
        self._task = asyncio.create_task(self.run())

    def stop(self) -> None:
        """Stop the background generator task."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def run(self) -> None:
        """Generate samples until cancelled."""
        while True:
            self.emit_once()
            await asyncio.sleep(self._interval_s)

    def emit_once(self, now_s: Optional[float] = None) -> None:
        """Generate and publish one bike sample and one HR sample."""
        snapshot = self._snapshot_provider()
        if not snapshot.active or snapshot.paused:
            return

        ts = now_s if now_s is not None else time.time()
        bike_sample = self.next_bike_sample(snapshot, ts)
        hr_sample = self.next_hr_sample(snapshot, ts)

        self._bike_handler(bike_sample)
        self._hr_handler(hr_sample)

    def next_bike_sample(self, snapshot: RideSnapshot, ts: float) -> BikeSample:
        """Return the next deterministic-ish bike sample."""
        elapsed_s = max(0.0, ts - (self._started_at_s or ts))
        wave = math.sin(elapsed_s / 18.0)
        noise = self._random.uniform(-1.0, 1.0)

        if snapshot.mode is RideMode.ERG:
            target_power = float(snapshot.erg_target_w)
            desired_power = target_power + wave * 8.0 + noise * 4.0
        elif snapshot.mode is RideMode.SIM:
            grade_load = snapshot.sim_grade_pct * 10.0
            desired_power = 165.0 + grade_load + wave * 28.0 + noise * 12.0
        else:
            desired_power = 175.0 + wave * 35.0 + noise * 16.0

        self._power_w += (desired_power - self._power_w) * 0.28
        self._cadence_rpm += (
            84.0 + wave * 5.0 + noise * 2.5 - self._cadence_rpm
        ) * 0.22

        grade_drag = (
            snapshot.sim_grade_pct * 0.22 if snapshot.mode is RideMode.SIM else 0
        )
        desired_speed = 3.2 + self._power_w / 38.0 - grade_drag
        self._speed_mps += (desired_speed - self._speed_mps) * 0.18

        return {
            "ts": ts,
            "power_w": max(0, int(round(self._power_w))),
            "cadence_rpm": max(0, int(round(self._cadence_rpm))),
            "speed_mps": max(0.0, min(16.0, self._speed_mps)),
        }

    def next_hr_sample(self, snapshot: RideSnapshot, ts: float) -> HrSample:
        """Return the next heart-rate sample."""
        mode_bias = 6.0 if snapshot.mode in {RideMode.ERG, RideMode.SIM} else 0.0
        target_hr = 95.0 + self._power_w * 0.27 + mode_bias
        self._hr_bpm += (target_hr - self._hr_bpm) * 0.08
        self._hr_bpm += self._random.uniform(-0.6, 0.6)

        return {
            "ts": ts,
            "hr_bpm": max(80, min(190, int(round(self._hr_bpm)))),
        }


__all__ = ["FakeTrainerSampleSource"]
