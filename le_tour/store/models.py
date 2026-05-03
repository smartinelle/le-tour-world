"""Data models for training sessions and samples."""

from datetime import datetime, UTC
from typing import Optional, List
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, computed_field, field_serializer


class TrainingMode(str, Enum):
    """Training mode enumeration."""

    FREE = "free"
    ERG = "erg"
    SIM = "sim"


class SessionModel(BaseModel):
    """Training session model."""

    # Session identification
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Session info
    mode: TrainingMode
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_s: Optional[float] = None

    # Device info
    trainer_name: Optional[str] = None
    trainer_model: Optional[str] = None
    hr_device_name: Optional[str] = None

    # User settings at session start
    user_mass_kg: float = 75.0
    user_ftp_w: int = 250

    # Mode-specific settings
    erg_target_power_w: Optional[int] = None
    sim_grade_pct: Optional[float] = None
    sim_route_id: Optional[str] = None
    sim_route_title: Optional[str] = None

    # Session statistics (calculated)
    total_distance_m: Optional[float] = None
    avg_power_w: Optional[float] = None
    max_power_w: Optional[int] = None
    avg_cadence_rpm: Optional[float] = None
    avg_speed_mps: Optional[float] = None
    avg_hr_bpm: Optional[float] = None
    max_hr_bpm: Optional[int] = None

    # Training metrics (calculated)
    normalized_power_w: Optional[float] = None
    intensity_factor: Optional[float] = None
    training_stress_score: Optional[float] = None

    # Additional metadata
    notes: str = ""
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict()

    @field_serializer("created_at", "start_time", "end_time")
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None


class SampleModel(BaseModel):
    """Training data sample model."""

    # Sample identification
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    elapsed_s: float  # Seconds since session start

    # Core bike metrics
    power_w: Optional[int] = None
    cadence_rpm: Optional[int] = None
    speed_mps: Optional[float] = None
    distance_m: Optional[float] = None  # Cumulative distance

    # Heart rate
    hr_bpm: Optional[int] = None

    # Mode-specific data
    erg_target_power_w: Optional[int] = None
    sim_grade_pct: Optional[float] = None

    model_config = ConfigDict()

    @field_serializer("timestamp")
    def _serialize_timestamp(self, ts: datetime) -> str:
        return ts.isoformat()

    @computed_field
    def speed_kph(self) -> Optional[float]:
        """Speed in km/h calculated from speed_mps."""
        if self.speed_mps is not None:
            return self.speed_mps * 3.6
        return None


@dataclass
class SessionSummary:
    """Summary statistics for a training session."""

    # Basic info
    session_id: str
    mode: str
    duration_s: float
    start_time: datetime

    # Distance and time
    total_distance_m: float
    total_distance_km: float = field(init=False)

    # Power statistics
    avg_power_w: Optional[float] = None
    max_power_w: Optional[int] = None
    normalized_power_w: Optional[float] = None

    # Cadence statistics
    avg_cadence_rpm: Optional[float] = None
    max_cadence_rpm: Optional[int] = None

    # Speed statistics
    avg_speed_mps: Optional[float] = None
    avg_speed_kph: Optional[float] = field(init=False, default=None)
    max_speed_mps: Optional[float] = None

    # Heart rate statistics
    avg_hr_bpm: Optional[float] = None
    max_hr_bpm: Optional[int] = None

    # Training metrics
    intensity_factor: Optional[float] = None
    training_stress_score: Optional[float] = None

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        self.total_distance_km = self.total_distance_m / 1000.0

        if self.avg_speed_mps is not None:
            self.avg_speed_kph = self.avg_speed_mps * 3.6
