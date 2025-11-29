"""BLE FTMS client implementation using bleak."""

import asyncio
import time
import struct
from typing import Callable, Optional, Dict, Any
import logging

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .base import (
    BikeSample,
    DeviceNotFoundError,
    ConnectionError,
    ControlNotAvailableError,
)
from .ftms_parse import parse_indoor_bike_data


logger = logging.getLogger(__name__)


class FtmsClient:
    """BLE FTMS client for trainer communication.

    Implements TrainerDevice protocol for BLE FTMS trainers like Wahoo KICKR.
    Handles scanning, connection, data subscription, and control commands.
    """

    # FTMS Service and Characteristic UUIDs
    FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
    INDOOR_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb"
    FITNESS_MACHINE_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb"
    FITNESS_MACHINE_STATUS_UUID = "00002ada-0000-1000-8000-00805f9b34fb"
    FITNESS_MACHINE_FEATURE_UUID = "00002acc-0000-1000-8000-00805f9b34fb"

    # FTMS Control Point Opcodes
    # TODO(FTMS: confirm opcodes from official spec)
    OP_REQUEST_CONTROL = 0x00
    OP_RESET = 0x01
    OP_SET_TARGET_POWER = 0x05
    OP_START_RESUME = 0x07
    OP_STOP_PAUSE = 0x08
    OP_SET_INDOOR_BIKE_SIMULATION = 0x11

    def __init__(self) -> None:
        self._client: Optional[BleakClient] = None
        self._device: Optional[BLEDevice] = None
        self._has_control = False
        self._device_info: Dict[str, Any] = {}
        self._bike_data_callback: Optional[Callable[[BikeSample], None]] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self._reconnect_delay = 1.0  # Start with 1s, exponential backoff
        self._notify_count = 0

    @property
    def is_connected(self) -> bool:
        """True if device is connected."""
        return self._client is not None and self._client.is_connected

    @property
    def has_control(self) -> bool:
        """True if we have control of the trainer."""
        return self._has_control

    @property
    def device_info(self) -> Dict[str, Any]:
        """Device information (model, firmware, etc.)."""
        return self._device_info.copy()

    async def scan_and_connect(self, timeout_s: float = 10.0) -> None:
        """Scan for FTMS trainer and connect.

        Args:
            timeout_s: Maximum time to spend scanning/connecting

        Raises:
            DeviceNotFoundError: If no FTMS trainer found
            ConnectionError: If connection fails
        """
        logger.info(f"Scanning for FTMS trainers (timeout: {timeout_s}s)")

        # Scan for devices advertising FTMS service
        devices = await BleakScanner.discover(
            timeout=timeout_s, service_uuids=[self.FTMS_SERVICE_UUID]
        )

        if not devices:
            raise DeviceNotFoundError("No FTMS trainers found")

        # Try to connect to first compatible device
        # TODO: Add device filtering/selection logic
        device = devices[0]
        logger.info(f"Found trainer: {device.name} ({device.address})")

        try:
            self._client = BleakClient(device)
            await self._client.connect()
            self._device = device

            # Store device info
            self._device_info = {
                "name": device.name,
                "address": device.address,
                "rssi": getattr(device, "rssi", None),
            }

            # Read device characteristics for more info
            await self._read_device_characteristics()

            logger.info(f"Connected to {device.name}")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to {device.name}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from trainer device."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self._client and self._client.is_connected:
            logger.info("Disconnecting from trainer")
            await self._client.disconnect()

        self._client = None
        self._device = None
        self._has_control = False
        self._device_info = {}

    async def subscribe_bike_data(self, callback: Callable[[BikeSample], None]) -> None:
        """Subscribe to live bike data notifications.

        Args:
            callback: Function called with each new BikeSample
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to trainer")

        self._bike_data_callback = callback

        async def notification_handler(sender: int, data: bytearray) -> None:
            try:
                # Parse FTMS Indoor Bike Data
                parsed = parse_indoor_bike_data(bytes(data))

                # Convert to BikeSample
                sample: BikeSample = {
                    "ts": time.time(),
                    "power_w": parsed.power_w,
                    "cadence_rpm": parsed.cadence_rpm,
                    "speed_mps": parsed.speed_mps,
                }

                # Debug logging of first frames to verify stream
                self._notify_count += 1
                if self._notify_count <= 5:
                    logger.info(
                        "FTMS notify #%d len=%d flags=0x%04x sample: power=%sW cad=%srpm speed=%sm/s hex=%s",
                        self._notify_count,
                        len(data),
                        parsed.flags,
                        str(parsed.power_w),
                        str(parsed.cadence_rpm),
                        f"{parsed.speed_mps:.3f}" if parsed.speed_mps is not None else "None",
                        data.hex(),
                    )
                elif self._notify_count % 100 == 0:
                    logger.debug(
                        "FTMS notify #%d flags=0x%04x power=%s cad=%s speed=%s",
                        self._notify_count,
                        parsed.flags,
                        str(parsed.power_w),
                        str(parsed.cadence_rpm),
                        f"{parsed.speed_mps:.3f}" if parsed.speed_mps is not None else "None",
                    )

                # Call user callback
                callback(sample)

            except Exception as e:
                try:
                    hex_data = bytes(data).hex()
                except Exception:
                    hex_data = "<unavailable>"
                logger.error(f"Error parsing bike data: {e}; hex={hex_data}")

        # Subscribe to Indoor Bike Data characteristic
        await self._client.start_notify(
            self.INDOOR_BIKE_DATA_UUID, notification_handler
        )
        logger.info("Subscribed to bike data notifications")

    async def request_control(self) -> None:
        """Request control of trainer for ERG/SIM modes.

        Raises:
            ControlNotGrantedError: If trainer rejects control request
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to trainer")

        # Send Request Control command
        command = struct.pack("<B", self.OP_REQUEST_CONTROL)
        await self._write_control_point(command)

        # TODO(FTMS: confirm response handling and timeout)
        # For now, assume control is granted immediately
        self._has_control = True
        logger.info("Trainer control granted")

    async def start_session(self) -> None:
        """Start training session on trainer."""
        if not self.has_control:
            raise ControlNotAvailableError("Control not granted")

        command = struct.pack("<B", self.OP_START_RESUME)
        await self._write_control_point(command)
        logger.info("Training session started")

    async def stop_session(self) -> None:
        """Stop training session on trainer."""
        if not self.has_control:
            raise ControlNotAvailableError("Control not granted")

        command = struct.pack("<B", self.OP_STOP_PAUSE)
        await self._write_control_point(command)
        logger.info("Training session stopped")

    async def set_target_power(self, watts: int) -> None:
        """Set target power for ERG mode.

        Args:
            watts: Target power in watts [100-400]

        Raises:
            ControlNotAvailableError: If control not granted
            ValueError: If watts outside valid range
        """
        if not self.has_control:
            raise ControlNotAvailableError("Control not granted")

        if not (100 <= watts <= 400):
            raise ValueError(f"Power {watts}W outside valid range [100-400]")

        # TODO(FTMS: confirm command format for Set Target Power)
        # Assuming: opcode (1 byte) + power (2 bytes, little-endian)
        command = struct.pack("<BH", self.OP_SET_TARGET_POWER, watts)
        await self._write_control_point(command)
        logger.debug(f"Set target power: {watts}W")

    async def set_simulation_params(
        self,
        grade_pct: float,
        wind_speed_mps: float = 0.0,
        rolling_resistance: float = 0.0045,
    ) -> None:
        """Set simulation parameters for SIM mode.

        Args:
            grade_pct: Road grade as percentage (positive = uphill)
            wind_speed_mps: Wind speed in m/s (positive = headwind)
            rolling_resistance: Rolling resistance coefficient

        Raises:
            ControlNotAvailableError: If control not granted
        """
        if not self.has_control:
            raise ControlNotAvailableError("Control not granted")

        # TODO(FTMS: confirm command format for Indoor Bike Simulation)
        # This is a complex command with multiple parameters
        # Need to check FTMS spec for exact format

        # For now, implement basic grade setting
        # Assuming grade is sent as signed 16-bit int in 0.01% units
        grade_raw = int(grade_pct * 100)  # Convert to 0.01% units

        # Simplified command (may need more parameters)
        command = struct.pack("<Bh", self.OP_SET_INDOOR_BIKE_SIMULATION, grade_raw)
        await self._write_control_point(command)
        logger.debug(f"Set simulation grade: {grade_pct:.1f}%")

    async def _write_control_point(self, command: bytes) -> None:
        """Write command to Fitness Machine Control Point.

        Args:
            command: Command bytes to send
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to trainer")

        try:
            await self._client.write_gatt_char(
                self.FITNESS_MACHINE_CONTROL_POINT_UUID, command
            )
        except Exception as e:
            logger.error(f"Failed to write control point: {e}")
            # Try to reconnect on communication failure
            asyncio.create_task(self._handle_disconnection())
            raise ConnectionError(f"Control point write failed: {e}")

    async def _read_device_characteristics(self) -> None:
        """Read device characteristics to populate device info."""
        try:
            # Try to read Fitness Machine Features
            features_data = await self._client.read_gatt_char(
                self.FITNESS_MACHINE_FEATURE_UUID
            )
            # TODO: Parse features data according to FTMS spec
            self._device_info["features_raw"] = features_data.hex()

        except Exception as e:
            logger.debug(f"Could not read device characteristics: {e}")

    async def _handle_disconnection(self) -> None:
        """Handle unexpected disconnection with reconnection attempts."""
        if self._reconnect_task:
            return  # Already handling reconnection

        logger.warning("Trainer disconnected, attempting reconnection...")
        self._has_control = False

        # Start reconnection with exponential backoff
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        max_delay = 30.0  # Maximum 30s between attempts

        while not self.is_connected:
            try:
                await asyncio.sleep(self._reconnect_delay)
                logger.info(
                    f"Reconnection attempt (delay: {self._reconnect_delay:.1f}s)"
                )

                if self._device:
                    self._client = BleakClient(self._device)
                    await self._client.connect()

                    # Re-subscribe to notifications if callback exists
                    if self._bike_data_callback:
                        await self.subscribe_bike_data(self._bike_data_callback)

                    # Reset delay on successful reconnection
                    self._reconnect_delay = 1.0
                    logger.info("Reconnection successful")
                    break

            except Exception as e:
                logger.debug(f"Reconnection failed: {e}")
                # Exponential backoff
                self._reconnect_delay = min(self._reconnect_delay * 2, max_delay)

        self._reconnect_task = None
