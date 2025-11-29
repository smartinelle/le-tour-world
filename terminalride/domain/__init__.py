"""Domain services and models for TerminalRide.

This package provides UI-agnostic services for:
- Trainer control (TrainerService)
- Heart rate monitoring (HrService)
- Session persistence (SessionService)
- Domain events for reactive UI updates
"""

from .events import (
    DomainEvent,
    DeviceConnected,
    DeviceDisconnected,
    ControlGranted,
    SampleReceived,
    HrSampleReceived,
    ErrorEvent,
)
from .state import RideMode, RideState
from .trainer_service import TrainerService
from .hr_service import HrService, get_hr_service
from .session_service import SessionService, get_session_service
from .ride_controller import (
    RideController,
    RideMode,
    RideMetrics,
    RideState,
    get_ride_controller,
)

__all__ = [
    # Events
    "DomainEvent",
    "DeviceConnected",
    "DeviceDisconnected",
    "ControlGranted",
    "SampleReceived",
    "HrSampleReceived",
    "ErrorEvent",
    # State
    "RideMode",
    "RideState",
    # Services
    "TrainerService",
    "HrService",
    "get_hr_service",
    "SessionService",
    "get_session_service",
    # Ride Controller
    "RideController",
    "RideMode",
    "RideMetrics",
    "RideState",
    "get_ride_controller",
]
