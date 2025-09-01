"""Domain event definitions for TerminalRide.

These events are UI-agnostic and can be consumed by any presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal
from terminalride.devices.base import BikeSample


@dataclass(frozen=True)
class DeviceConnected:
    name: str
    address: Optional[str] = None
    rssi: Optional[int] = None


@dataclass(frozen=True)
class DeviceDisconnected:
    reason: Optional[str] = None


@dataclass(frozen=True)
class ControlGranted:
    granted: bool


@dataclass(frozen=True)
class SampleReceived:
    sample: BikeSample


@dataclass(frozen=True)
class ErrorEvent:
    code: str
    message: str
    context: Optional[dict] = None


DomainEvent = DeviceConnected | DeviceDisconnected | ControlGranted | SampleReceived | ErrorEvent

