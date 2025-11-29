"""Device communication modules for trainers and sensors.

This package provides BLE clients for:
- FTMS trainers (Wahoo KICKR, etc.)
- Heart rate monitors (Wahoo TICKR, Garmin HRM, Polar, etc.)
"""

from .base import (
    BikeSample,
    HrSample,
    TrainerDevice,
    HrDevice,
    DeviceError,
    DeviceNotFoundError,
    ConnectionError,
    ControlNotGrantedError,
    ControlNotAvailableError,
)
from .ftms_client import FtmsClient
from .ftms_parse import parse_indoor_bike_data, ParsedBikeData
from .hr_client import HrClient
from .hr_parse import parse_heart_rate_measurement, ParsedHrData

__all__ = [
    # Base types and protocols
    "BikeSample",
    "HrSample",
    "TrainerDevice",
    "HrDevice",
    # Exceptions
    "DeviceError",
    "DeviceNotFoundError",
    "ConnectionError",
    "ControlNotGrantedError",
    "ControlNotAvailableError",
    # FTMS (trainer)
    "FtmsClient",
    "parse_indoor_bike_data",
    "ParsedBikeData",
    # Heart Rate
    "HrClient",
    "parse_heart_rate_measurement",
    "ParsedHrData",
]
