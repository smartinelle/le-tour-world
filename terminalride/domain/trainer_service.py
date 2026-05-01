"""TrainerService: UI-agnostic facade over the FTMS client.

This wrapper exposes a stable API and event stream so presentation layers
don't need to depend on bleak or FTMS details directly.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Any, List, Optional

from terminalride.devices.base import BikeSample
from .events import (
    DomainEvent,
    DeviceConnected,
    DeviceDisconnected,
    SampleReceived,
    ControlGranted,
    ErrorEvent,
)

logger = logging.getLogger(__name__)
FtmsClient: Optional[type[Any]] = None


class TrainerService:
    """High-level trainer service wrapping the BLE FTMS client."""

    def __init__(self) -> None:
        self._client: Optional[Any] = None
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
        return self._client is not None and bool(self._client.is_connected)

    @property
    def has_control(self) -> bool:
        return self._client is not None and bool(self._client.has_control)

    @property
    def device_info(self) -> Dict[str, Any]:
        if self._client is None:
            return {}
        return self._client.device_info

    # Lifecycle ----------------------------------------------------------
    async def scan_and_connect(self, timeout_s: float = 10.0) -> None:
        client = self._get_client()
        await client.scan_and_connect(timeout_s=timeout_s)
        info = client.device_info
        self._emit(
            DeviceConnected(
                name=info.get("name", "Unknown"),
                address=info.get("address"),
                rssi=info.get("rssi"),
            )
        )

    async def scan_available(self, timeout_s: float = 5.0) -> List[Dict[str, Any]]:
        """Scan for available trainers without connecting."""
        try:
            return await self._get_client().scan_available(timeout_s=timeout_s)
        except Exception as e:
            logger.error(f"Trainer scan failed: {e}")
            self._emit(
                ErrorEvent(
                    code="TRAINER_E_SCAN_FAILED",
                    message=str(e),
                )
            )
            return []

    async def connect_to_device(self, address: str) -> None:
        """Connect to a trainer by BLE address."""
        try:
            client = self._get_client()
            await client.connect_to_device(address)
            info = client.device_info
            self._emit(
                DeviceConnected(
                    name=info.get("name", "Unknown"),
                    address=info.get("address"),
                    rssi=info.get("rssi"),
                )
            )
        except Exception as e:
            logger.error(f"Trainer connection failed: {e}")
            self._emit(
                ErrorEvent(
                    code="TRAINER_E_CONNECTION_FAILED",
                    message=str(e),
                )
            )
            raise

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
        self._emit(DeviceDisconnected())

    async def subscribe_samples(self, handler: Callable[[BikeSample], None]) -> None:
        def _bridge(sample: BikeSample) -> None:
            self._emit(SampleReceived(sample=sample))
            handler(sample)

        await self._get_client().subscribe_bike_data(_bridge)

    # Control ------------------------------------------------------------
    async def request_control(self) -> None:
        client = self._get_client()
        await client.request_control()
        self._emit(ControlGranted(granted=client.has_control))

    async def start(self) -> None:
        await self._get_client().start_session()

    async def stop(self) -> None:
        await self._get_client().stop_session()

    async def set_target_power(self, watts: int) -> None:
        await self._get_client().set_target_power(watts)

    async def set_simulation(self, grade_pct: float) -> None:
        await self._get_client().set_simulation_params(grade_pct)

    def _get_client(self) -> Any:
        """Return the BLE client, importing bleak only when hardware is used."""
        global FtmsClient
        if self._client is None:
            if FtmsClient is None:
                from terminalride.devices.ftms_client import FtmsClient as Client

                FtmsClient = Client
            self._client = FtmsClient()
        return self._client
