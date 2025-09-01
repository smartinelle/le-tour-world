"""TrainerService: UI-agnostic facade over the FTMS client.

This wrapper exposes a stable API and event stream so presentation layers
don't need to depend on bleak or FTMS details directly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional, Dict, Any, List

from terminalride.devices.base import BikeSample
from terminalride.devices.ftms_client import FtmsClient
from .events import DomainEvent, DeviceConnected, DeviceDisconnected, SampleReceived, ControlGranted, ErrorEvent


logger = logging.getLogger(__name__)


class TrainerService:
    """High-level trainer service wrapping the BLE FTMS client."""

    def __init__(self) -> None:
        self._client = FtmsClient()
        self._subscribers: List[Callable[[DomainEvent], None]] = []

    # Event subscription -------------------------------------------------
    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        self._subscribers.append(handler)

    def _emit(self, event: DomainEvent) -> None:
        for h in list(self._subscribers):
            try:
                h(event)
            except Exception as e:
                logger.debug(f"TrainerService subscriber error: {e}")

    # Properties ---------------------------------------------------------
    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    @property
    def has_control(self) -> bool:
        return self._client.has_control

    @property
    def device_info(self) -> Dict[str, Any]:
        return self._client.device_info

    # Lifecycle ----------------------------------------------------------
    async def scan_and_connect(self, timeout_s: float = 10.0) -> None:
        await self._client.scan_and_connect(timeout_s=timeout_s)
        info = self._client.device_info
        self._emit(DeviceConnected(name=info.get("name", "Unknown"), address=info.get("address"), rssi=info.get("rssi")))

    async def disconnect(self) -> None:
        await self._client.disconnect()
        self._emit(DeviceDisconnected())

    async def subscribe_samples(self, handler: Callable[[BikeSample], None]) -> None:
        def _bridge(sample: BikeSample) -> None:
            self._emit(SampleReceived(sample=sample))
            handler(sample)

        await self._client.subscribe_bike_data(_bridge)

    # Control ------------------------------------------------------------
    async def request_control(self) -> None:
        await self._client.request_control()
        self._emit(ControlGranted(granted=self._client.has_control))

    async def start(self) -> None:
        await self._client.start_session()

    async def stop(self) -> None:
        await self._client.stop_session()

    async def set_target_power(self, watts: int) -> None:
        await self._client.set_target_power(watts)

    async def set_simulation(self, grade_pct: float) -> None:
        await self._client.set_simulation_params(grade_pct)

