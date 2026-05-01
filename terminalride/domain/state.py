"""UI-agnostic ride state models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RideMode(str, Enum):
    """Supported ride modes."""

    FREE = "free"
    ERG = "erg"
    SIM = "sim"


@dataclass
class RideMetrics:
    """Live ride metrics exposed to presentation layers.

    All values use SI units unless the field name says otherwise.
    """

    elapsed_s: float = 0.0
    power_w: Optional[int] = None
    cadence_rpm: Optional[int] = None
    speed_mps: Optional[float] = None
    distance_m: float = 0.0
    hr_bpm: Optional[int] = None
    erg_target_w: int = 150
    sim_grade_pct: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Return a stable serializable snapshot for UIs and transports."""
        return {
            "time_s": self.elapsed_s,
            "power_w": self.power_w,
            "cadence_rpm": self.cadence_rpm,
            "speed_mps": self.speed_mps,
            "distance_m": self.distance_m,
            "hr_bpm": self.hr_bpm,
            "erg_target_w": self.erg_target_w,
            "sim_grade_pct": self.sim_grade_pct,
        }


@dataclass
class RideState:
    """Current ride/session lifecycle state."""

    mode: Optional[RideMode] = None
    active: bool = False
    paused: bool = False
    session_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    trainer_name: Optional[str] = None
