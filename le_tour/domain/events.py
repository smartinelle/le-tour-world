"""Domain event definitions for le-tour.

These events are UI-agnostic and can be consumed by any presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from le_tour.devices.base import BikeSample, HrSample


@dataclass(frozen=True)
class DeviceConnected:
    """Emitted when a device (trainer or HR monitor) connects."""

    name: str
    device_type: str = "trainer"  # "trainer" or "hr"
    address: Optional[str] = None
    rssi: Optional[int] = None


@dataclass(frozen=True)
class DeviceDisconnected:
    """Emitted when a device disconnects."""

    device_type: str = "trainer"  # "trainer" or "hr"
    reason: Optional[str] = None


@dataclass(frozen=True)
class ControlGranted:
    """Emitted when trainer control is granted or denied."""

    granted: bool


@dataclass(frozen=True)
class SampleReceived:
    """Emitted when new bike data sample is received from trainer."""

    sample: BikeSample


@dataclass(frozen=True)
class HrSampleReceived:
    """Emitted when new heart rate sample is received."""

    sample: HrSample
    sensor_contact: Optional[bool] = None


@dataclass(frozen=True)
class ErrorEvent:
    """Emitted when an error occurs."""

    code: str
    message: str
    context: Optional[dict] = None


DomainEvent = (
    DeviceConnected
    | DeviceDisconnected
    | ControlGranted
    | SampleReceived
    | HrSampleReceived
    | ErrorEvent
)
