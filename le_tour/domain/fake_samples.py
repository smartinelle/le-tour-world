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
        # Virtual rider effort state machine (see set_effort).
        self._effort_mode = "auto"
        self._hold_power_w = 150.0
        self._ramp: Optional[dict[str, float]] = None
        self._sprint: Optional[dict[str, float]] = None
        self._resume_mode = "auto"
        self._pedal_phase = self._random.uniform(0.0, math.tau)

    # -- Virtual rider effort -------------------------------------------------
    #
    # A real trainer never reports a flat line: rider power approaches a
    # target over a second or two, every pedal stroke wobbles a few percent,
    # and cadence follows effort. The effort modes mirror how a rider is
    # actually driven in testing:
    #   auto   - wandering demo effort (the original behavior)
    #   hold   - settle onto a target wattage and sit on it
    #   ramp   - build progressively from current power to a target
    #   sprint - out-of-the-saddle burst: fast attack, fatigue decay, sit up

    MAX_POWER_W = 1500.0
    RIDER_RESPONSE = 0.55  # per-sample approach toward desired power
    SPRINT_RESPONSE = 0.85
    SPRINT_ATTACK_S = 1.2
    SPRINT_FATIGUE = 0.18  # fraction of peak lost across the sprint
    PEDAL_FLUCTUATION = 0.03  # stroke-to-stroke power wobble

    @property
    def effort(self) -> dict[str, object]:
        """Current virtual rider effort for API echo and UIs."""
        target: Optional[float] = None
        if self._effort_mode == "hold":
            target = self._hold_power_w
        elif self._effort_mode == "ramp" and self._ramp is not None:
            target = self._ramp["target_w"]
        elif self._effort_mode == "sprint" and self._sprint is not None:
            target = self._sprint["peak_w"]
        return {"action": self._effort_mode, "target_w": target}

    @property
    def manual_power_w(self) -> Optional[float]:
        """Rider-controlled hold target, or None outside hold mode."""
        return self._hold_power_w if self._effort_mode == "hold" else None

    def set_manual_power(self, power_w: Optional[float]) -> Optional[float]:
        """Back-compat wrapper: hold a wattage, or None for auto."""
        if power_w is None:
            self.set_effort("auto")
            return None
        self.set_effort("hold", power_w=power_w)
        return self._hold_power_w

    def set_effort(
        self,
        action: str,
        power_w: Optional[float] = None,
        duration_s: Optional[float] = None,
    ) -> dict[str, object]:
        """Steer the virtual rider. Returns the resulting effort state."""
        clamped = (
            None if power_w is None else max(0.0, min(self.MAX_POWER_W, float(power_w)))
        )
        if action == "auto":
            self._effort_mode = "auto"
            self._ramp = None
            self._sprint = None
        elif action == "hold":
            self._effort_mode = "hold"
            self._hold_power_w = clamped if clamped is not None else self._hold_power_w
            self._ramp = None
            self._sprint = None
        elif action == "ramp":
            self._effort_mode = "ramp"
            self._ramp = {
                "start_w": self._power_w,
                "target_w": clamped if clamped is not None else self._hold_power_w,
                "started_s": -1.0,  # initialized from the first sample timestamp
                "duration_s": max(5.0, min(600.0, float(duration_s or 60.0))),
            }
            self._sprint = None
        elif action == "sprint":
            self._resume_mode = (
                "hold" if self._effort_mode in {"hold", "ramp", "sprint"} else "auto"
            )
            self._effort_mode = "sprint"
            self._sprint = {
                "peak_w": clamped if clamped is not None else 650.0,
                "started_s": -1.0,
                "duration_s": max(3.0, min(30.0, float(duration_s or 10.0))),
                "from_w": self._power_w,
            }
            self._ramp = None
        else:
            raise ValueError(f"Unknown virtual rider action: {action}")
        return self.effort

    def _desired_power(self, ts: float) -> tuple[float, float]:
        """Return (desired watts, response rate) for the manual effort modes."""
        if self._effort_mode == "ramp" and self._ramp is not None:
            ramp = self._ramp
            if ramp["started_s"] < 0:
                ramp["started_s"] = ts
            progress = (ts - ramp["started_s"]) / ramp["duration_s"]
            if progress >= 1.0:
                self._hold_power_w = ramp["target_w"]
                self._effort_mode = "hold"
                self._ramp = None
                return self._hold_power_w, self.RIDER_RESPONSE
            desired = ramp["start_w"] + (ramp["target_w"] - ramp["start_w"]) * progress
            return desired, self.RIDER_RESPONSE

        if self._effort_mode == "sprint" and self._sprint is not None:
            sprint = self._sprint
            if sprint["started_s"] < 0:
                sprint["started_s"] = ts
            elapsed = ts - sprint["started_s"]
            if elapsed >= sprint["duration_s"]:
                self._effort_mode = self._resume_mode
                self._sprint = None
                return self._hold_power_w, self.RIDER_RESPONSE
            if elapsed < self.SPRINT_ATTACK_S:
                rise = elapsed / self.SPRINT_ATTACK_S
                desired = (
                    sprint["from_w"] + (sprint["peak_w"] - sprint["from_w"]) * rise
                )
            else:
                fatigue = (elapsed - self.SPRINT_ATTACK_S) / max(
                    0.1, sprint["duration_s"] - self.SPRINT_ATTACK_S
                )
                desired = sprint["peak_w"] * (1.0 - self.SPRINT_FATIGUE * fatigue)
            return desired, self.SPRINT_RESPONSE

        return self._hold_power_w, self.RIDER_RESPONSE

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
        if self._effort_mode != "auto":
            return self._rider_bike_sample(ts)

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

    def _rider_bike_sample(self, ts: float) -> BikeSample:
        """One sample of steered rider effort, shaped like real trainer data:
        power approaches the desired effort over ~1-2 s and every sample
        carries stroke-to-stroke wobble; cadence tracks effort."""
        desired_w, response = self._desired_power(ts)
        if desired_w <= 1.0:
            # Stopping pedaling reads as ~0 W within a sample or two - much
            # faster than effort builds.
            response = max(response, 0.9)
        self._power_w += (desired_w - self._power_w) * response

        # Pedal-stroke fluctuation: multiplicative so 0 W stays exactly 0.
        self._pedal_phase += 2.3 + self._random.uniform(-0.3, 0.3)
        wobble = self.PEDAL_FLUCTUATION * math.sin(
            self._pedal_phase
        ) + self._random.uniform(-0.02, 0.02)
        emitted_w = max(0.0, self._power_w * (1.0 + wobble))

        sprinting = self._effort_mode == "sprint"
        if emitted_w < 15.0:
            desired_cadence = 0.0
        else:
            desired_cadence = min(104.0, 58.0 + 30.0 * emitted_w / 300.0)
            if sprinting:
                desired_cadence = min(118.0, desired_cadence + 12.0)
        # Legs stop instantly; effort changes settle over a couple of strokes.
        cadence_response = 1.0 if desired_cadence == 0.0 else 0.45
        self._cadence_rpm += (
            desired_cadence
            + (self._random.uniform(-1.5, 1.5) if desired_cadence else 0.0)
            - self._cadence_rpm
        ) * cadence_response

        desired_speed = 0.0 if emitted_w <= 0 else 3.2 + emitted_w / 38.0
        self._speed_mps += (desired_speed - self._speed_mps) * 0.18

        return {
            "ts": ts,
            "power_w": max(0, int(round(emitted_w))),
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
