"""UI-neutral device connection models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class DiscoveredDevice:
    """A BLE device discovered by a domain service scan."""

    name: str
    address: str
    rssi: Optional[int] = None
    device_type: str = "trainer"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_scan_result(
        cls,
        result: dict[str, Any],
        *,
        device_type: str,
        fallback_name: str,
    ) -> "DiscoveredDevice":
        """Normalize a raw BLE scan result into a stable service contract."""
        name = str(result.get("name") or fallback_name)
        address = str(result.get("address") or "")
        rssi_value = result.get("rssi")
        rssi = int(rssi_value) if isinstance(rssi_value, int | float) else None
        metadata = {
            key: value
            for key, value in result.items()
            if key not in {"name", "address", "rssi"}
        }
        return cls(
            name=name,
            address=address,
            rssi=rssi,
            device_type=device_type,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable device description."""
        data: dict[str, Any] = {
            "name": self.name,
            "address": self.address,
            "rssi": self.rssi,
            "device_type": self.device_type,
        }
        data.update(self.metadata)
        return data


@dataclass(frozen=True)
class DeviceConnectionStatus:
    """Current connection state for a domain device service."""

    device_type: str
    connected: bool
    name: Optional[str] = None
    address: Optional[str] = None
    rssi: Optional[int] = None
    has_control: Optional[bool] = None
    last_hr_bpm: Optional[int] = None
    sensor_contact: Optional[bool] = None

    @classmethod
    def from_device_info(
        cls,
        info: dict[str, Any],
        *,
        device_type: str,
        connected: bool,
        fallback_name: Optional[str] = None,
        has_control: Optional[bool] = None,
        last_hr_bpm: Optional[int] = None,
        sensor_contact: Optional[bool] = None,
    ) -> "DeviceConnectionStatus":
        """Create status from a client device_info dict."""
        rssi_value = info.get("rssi")
        rssi = int(rssi_value) if isinstance(rssi_value, int | float) else None
        name_value = info.get("name") or (fallback_name if connected else None)
        address_value = info.get("address")
        return cls(
            device_type=device_type,
            connected=connected,
            name=str(name_value) if name_value else None,
            address=str(address_value) if address_value else None,
            rssi=rssi,
            has_control=has_control,
            last_hr_bpm=last_hr_bpm,
            sensor_contact=sensor_contact,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a stable serializable connection status."""
        return {
            "device_type": self.device_type,
            "connected": self.connected,
            "name": self.name,
            "address": self.address,
            "rssi": self.rssi,
            "has_control": self.has_control,
            "last_hr_bpm": self.last_hr_bpm,
            "sensor_contact": self.sensor_contact,
        }
