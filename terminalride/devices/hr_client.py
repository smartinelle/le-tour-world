"""BLE Heart Rate client implementation using bleak.

Connects to standard BLE Heart Rate Profile devices including:
- Wahoo TICKR / TICKR X / TICKR Fit
- Garmin HRM-Pro / HRM-Dual / HRM-Run / HRM-Tri
- Polar H10 / H9 / OH1
- Any device implementing BLE Heart Rate Service (0x180D)
"""

import asyncio
import time
from typing import Callable, Optional, Dict, Any, List
import logging

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .base import (
    HrSample,
    DeviceNotFoundError,
    ConnectionError,
)
from .hr_parse import parse_heart_rate_measurement, ParsedHrData


logger = logging.getLogger(__name__)


class HrClient:
    """BLE Heart Rate client for HR monitor communication.

    Implements HrDevice protocol for standard BLE Heart Rate monitors.
    Handles scanning, connection, and heart rate data subscription.

    Example:
        >>> client = HrClient()
        >>> await client.scan_and_connect()
        >>> await client.subscribe_hr_data(lambda s: print(f"HR: {s['hr_bpm']}"))
    """

    # Standard BLE Heart Rate Service UUIDs
    HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
    HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
    BODY_SENSOR_LOCATION_UUID = "00002a38-0000-1000-8000-00805f9b34fb"

    # Device Information Service (optional)
    DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
    MANUFACTURER_NAME_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
    MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"

    # Battery Service (optional)
    BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
    BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

    # Body sensor location mapping
    SENSOR_LOCATIONS = {
        0: "Other",
        1: "Chest",
        2: "Wrist",
        3: "Finger",
        4: "Hand",
        5: "Ear Lobe",
        6: "Foot",
    }

    def __init__(self) -> None:
        self._client: Optional[BleakClient] = None
        self._device: Optional[BLEDevice] = None
        self._device_info: Dict[str, Any] = {}
        self._hr_callback: Optional[Callable[[HrSample], None]] = None
        self._raw_callback: Optional[Callable[[ParsedHrData], None]] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self._reconnect_delay = 1.0
        self._notify_count = 0

    @property
    def is_connected(self) -> bool:
        """True if device is connected."""
        return self._client is not None and self._client.is_connected

    @property
    def device_info(self) -> Dict[str, Any]:
        """Device information (name, manufacturer, battery, etc.)."""
        return self._device_info.copy()

    async def scan_and_connect(
        self,
        timeout_s: float = 10.0,
        device_name: Optional[str] = None,
    ) -> None:
        """Scan for HR device and connect.

        Args:
            timeout_s: Maximum time to spend scanning/connecting.
            device_name: Optional specific device name to connect to.
                If None, connects to first HR device found.

        Raises:
            DeviceNotFoundError: If no HR device found.
            ConnectionError: If connection fails.
        """
        logger.info(f"Scanning for HR monitors (timeout: {timeout_s}s)")

        # Scan for devices advertising HR service
        devices = await BleakScanner.discover(
            timeout=timeout_s,
            service_uuids=[self.HR_SERVICE_UUID],
        )

        if not devices:
            raise DeviceNotFoundError("No heart rate monitors found")

        # Filter by name if specified
        if device_name:
            matching = [d for d in devices if d.name and device_name.lower() in d.name.lower()]
            if not matching:
                available = [d.name for d in devices if d.name]
                raise DeviceNotFoundError(
                    f"No HR device matching '{device_name}'. Available: {available}"
                )
            device = matching[0]
        else:
            device = devices[0]

        logger.info(f"Found HR monitor: {device.name} ({device.address})")

        try:
            self._client = BleakClient(device, disconnected_callback=self._on_disconnect)
            await self._client.connect()
            self._device = device

            # Store basic device info
            self._device_info = {
                "name": device.name,
                "address": device.address,
                "rssi": getattr(device, "rssi", None),
            }

            # Read additional device characteristics
            await self._read_device_info()

            logger.info(f"Connected to {device.name}")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to {device.name}: {e}")

    async def scan_available(self, timeout_s: float = 5.0) -> List[Dict[str, Any]]:
        """Scan for available HR devices without connecting.

        Args:
            timeout_s: Maximum time to spend scanning.

        Returns:
            List of device info dicts with name, address, rssi.
        """
        logger.info(f"Scanning for available HR monitors (timeout: {timeout_s}s)")

        devices = await BleakScanner.discover(
            timeout=timeout_s,
            service_uuids=[self.HR_SERVICE_UUID],
        )

        return [
            {
                "name": d.name or "Unknown",
                "address": d.address,
                "rssi": getattr(d, "rssi", None),
            }
            for d in devices
        ]

    async def disconnect(self) -> None:
        """Disconnect from HR device."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self._client and self._client.is_connected:
            logger.info("Disconnecting from HR monitor")
            await self._client.disconnect()

        self._client = None
        self._device = None
        self._device_info = {}
        self._hr_callback = None
        self._raw_callback = None

    async def subscribe_hr_data(
        self,
        callback: Callable[[HrSample], None],
        raw_callback: Optional[Callable[[ParsedHrData], None]] = None,
    ) -> None:
        """Subscribe to heart rate notifications.

        Args:
            callback: Function called with each new HrSample (simplified).
            raw_callback: Optional function called with full ParsedHrData
                including RR intervals and sensor contact status.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to HR monitor")

        self._hr_callback = callback
        self._raw_callback = raw_callback

        async def notification_handler(sender: int, data: bytearray) -> None:
            try:
                parsed = parse_heart_rate_measurement(bytes(data))

                # Create simplified HrSample
                sample: HrSample = {
                    "ts": time.time(),
                    "hr_bpm": parsed.hr_bpm,
                }

                # Debug logging
                self._notify_count += 1
                if self._notify_count <= 3:
                    logger.info(
                        "HR notify #%d: %d BPM, contact=%s, RR=%s",
                        self._notify_count,
                        parsed.hr_bpm,
                        parsed.sensor_contact_detected,
                        parsed.rr_intervals_ms,
                    )
                elif self._notify_count % 60 == 0:
                    logger.debug(
                        "HR notify #%d: %d BPM",
                        self._notify_count,
                        parsed.hr_bpm,
                    )

                # Call callbacks
                callback(sample)
                if raw_callback:
                    raw_callback(parsed)

            except Exception as e:
                logger.error(f"Error parsing HR data: {e}; hex={data.hex()}")

        # Subscribe to HR Measurement characteristic
        await self._client.start_notify(self.HR_MEASUREMENT_UUID, notification_handler)
        logger.info("Subscribed to HR notifications")

    async def _read_device_info(self) -> None:
        """Read optional device characteristics."""
        try:
            # Read body sensor location
            try:
                location_data = await self._client.read_gatt_char(self.BODY_SENSOR_LOCATION_UUID)
                location_code = location_data[0] if location_data else 0
                self._device_info["sensor_location"] = self.SENSOR_LOCATIONS.get(
                    location_code, f"Unknown ({location_code})"
                )
            except Exception:
                pass  # Optional characteristic

            # Read manufacturer name
            try:
                manufacturer_data = await self._client.read_gatt_char(self.MANUFACTURER_NAME_UUID)
                self._device_info["manufacturer"] = manufacturer_data.decode("utf-8").strip("\x00")
            except Exception:
                pass

            # Read model number
            try:
                model_data = await self._client.read_gatt_char(self.MODEL_NUMBER_UUID)
                self._device_info["model"] = model_data.decode("utf-8").strip("\x00")
            except Exception:
                pass

            # Read battery level
            try:
                battery_data = await self._client.read_gatt_char(self.BATTERY_LEVEL_UUID)
                self._device_info["battery_percent"] = battery_data[0] if battery_data else None
            except Exception:
                pass

            logger.debug(f"HR device info: {self._device_info}")

        except Exception as e:
            logger.debug(f"Could not read all device info: {e}")

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle unexpected disconnection."""
        logger.warning("HR monitor disconnected")
        if self._hr_callback and not self._reconnect_task:
            # Start reconnection if we had an active subscription
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        max_delay = 30.0

        while not self.is_connected:
            try:
                await asyncio.sleep(self._reconnect_delay)
                logger.info(f"HR reconnection attempt (delay: {self._reconnect_delay:.1f}s)")

                if self._device:
                    self._client = BleakClient(
                        self._device,
                        disconnected_callback=self._on_disconnect,
                    )
                    await self._client.connect()

                    # Re-subscribe if callback exists
                    if self._hr_callback:
                        await self.subscribe_hr_data(self._hr_callback, self._raw_callback)

                    self._reconnect_delay = 1.0
                    logger.info("HR reconnection successful")
                    break

            except Exception as e:
                logger.debug(f"HR reconnection failed: {e}")
                self._reconnect_delay = min(self._reconnect_delay * 2, max_delay)

        self._reconnect_task = None

