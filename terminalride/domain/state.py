"""Domain state models.

These provide UI-agnostic snapshots of the current ride/train state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class RideMode(str, Enum):
    FREE = "free"
    ERG = "erg"
    SIM = "sim"


@dataclass
class RideState:
    mode: RideMode = RideMode.FREE
    active: bool = False
    paused: bool = False
    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

