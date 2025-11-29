"""HrService: UI-agnostic facade over the HR client.

This wrapper exposes a stable API and event stream so presentation layers
don't need to depend on bleak or BLE HR protocol details directly.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Any, List, Optional

from terminalride.devices.base import HrSample
from terminalride.devices.hr_client import HrClient
from terminalride.devices.hr_parse import ParsedHrData
from .events import DomainEvent, DeviceConnected, DeviceDisconnected, HrSampleReceived, ErrorEvent


logger = logging.getLogger(__name__)


class HrService:
    """High-level heart rate service wrapping the BLE HR client.

    Provides a clean interface for:
    - Scanning for available HR monitors
    - Connecting to a specific device
    - Subscribing to heart rate data
    - Receiving domain events for UI updates
    """

    def __init__(self) -> None:
        self._client = HrClient()
        self._subscribers: List[Callable[[DomainEvent], None]] = []
        self._last_hr: Optional[int] = None
        self._last_contact: Optional[bool] = None

    # Event subscription -------------------------------------------------
    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        """Subscribe to domain events from this service."""
        self._subscribers.append(handler)

    def unsubscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        """Unsubscribe from domain events."""
        if handler in self._subscribers:
            self._subscribers.remove(handler)

    def _emit(self, event: DomainEvent) -> None:
        """Emit event to all subscribers."""
        for h in list(self._subscribers):
            try:
                h(event)
            except Exception as e:
                logger.debug(f"HrService subscriber error: {e}")

    # Properties ---------------------------------------------------------
    @property
    def is_connected(self) -> bool:
        """True if HR device is connected."""
        return self._client.is_connected

    @property
    def device_info(self) -> Dict[str, Any]:
        """HR device information (name, battery, sensor location, etc.)."""
        return self._client.device_info

    @property
    def last_hr(self) -> Optional[int]:
        """Last received heart rate in BPM, or None if no data yet."""
        return self._last_hr

    @property
    def has_sensor_contact(self) -> Optional[bool]:
        """True if sensor has skin contact, False if not, None if unknown."""
        return self._last_contact

    # Lifecycle ----------------------------------------------------------
    async def scan_available(self, timeout_s: float = 5.0) -> List[Dict[str, Any]]:
        """Scan for available HR monitors without connecting.

        Args:
            timeout_s: Maximum scan time in seconds.

        Returns:
            List of device info dicts with name, address, rssi.
        """
        try:
            return await self._client.scan_available(timeout_s=timeout_s)
        except Exception as e:
            logger.error(f"HR scan failed: {e}")
            self._emit(ErrorEvent(
                code="HR_E_SCAN_FAILED",
                message=str(e),
            ))
            return []

    async def scan_and_connect(
        self,
        timeout_s: float = 10.0,
        device_name: Optional[str] = None,
    ) -> None:
        """Scan for and connect to an HR monitor.

        Args:
            timeout_s: Maximum time to spend scanning/connecting.
            device_name: Optional specific device name to connect to.
        """
        try:
            await self._client.scan_and_connect(
                timeout_s=timeout_s,
                device_name=device_name,
            )
            info = self._client.device_info
            self._emit(DeviceConnected(
                name=info.get("name", "Unknown HR"),
                device_type="hr",
                address=info.get("address"),
                rssi=info.get("rssi"),
            ))
        except Exception as e:
            logger.error(f"HR connection failed: {e}")
            self._emit(ErrorEvent(
                code="HR_E_CONNECTION_FAILED",
                message=str(e),
            ))
            raise

    async def disconnect(self) -> None:
        """Disconnect from HR monitor."""
        await self._client.disconnect()
        self._last_hr = None
        self._last_contact = None
        self._emit(DeviceDisconnected(device_type="hr"))

    async def subscribe_hr_data(self, callback: Callable[[HrSample], None]) -> None:
        """Subscribe to heart rate data notifications.

        Args:
            callback: Function called with each new HrSample.
        """

        def _sample_handler(sample: HrSample) -> None:
            self._last_hr = sample.get("hr_bpm")
            self._emit(HrSampleReceived(sample=sample, sensor_contact=self._last_contact))
            callback(sample)

        def _raw_handler(parsed: ParsedHrData) -> None:
            self._last_contact = parsed.sensor_contact_detected

        await self._client.subscribe_hr_data(_sample_handler, _raw_handler)


# Singleton instance management
_hr_service: Optional[HrService] = None


def get_hr_service() -> HrService:
    """Get (or create) the shared HR service instance."""
    global _hr_service
    if _hr_service is None:
        _hr_service = HrService()
    return _hr_service

