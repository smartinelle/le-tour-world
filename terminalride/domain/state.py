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


@dataclass(frozen=True)
class RideSnapshot:
    """UI-neutral snapshot of the current ride state.

    This is the transport-safe view that browser, terminal, and future 3D
    surfaces can consume without reaching into controller internals.
    """

    session_state: str = "inactive"
    active: bool = False
    paused: bool = False
    session_id: Optional[str] = None
    mode: Optional[RideMode] = None
    elapsed_s: float = 0.0
    power_w: Optional[int] = None
    cadence_rpm: Optional[int] = None
    speed_mps: Optional[float] = None
    distance_m: float = 0.0
    hr_bpm: Optional[int] = None
    erg_target_w: int = 150
    sim_grade_pct: float = 0.0
    trainer_connected: bool = False
    trainer_name: Optional[str] = None
    hr_connected: bool = False
    hr_name: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable snapshot for clients and streams."""
        return {
            "session_state": self.session_state,
            "active": self.active,
            "paused": self.paused,
            "session_id": self.session_id,
            "mode": self.mode.value if self.mode else None,
            "elapsed_s": self.elapsed_s,
            "power_w": self.power_w,
            "cadence_rpm": self.cadence_rpm,
            "speed_mps": self.speed_mps,
            "distance_m": self.distance_m,
            "hr_bpm": self.hr_bpm,
            "erg_target_w": self.erg_target_w,
            "sim_grade_pct": self.sim_grade_pct,
            "trainer_connected": self.trainer_connected,
            "trainer_name": self.trainer_name,
            "hr_connected": self.hr_connected,
            "hr_name": self.hr_name,
        }
