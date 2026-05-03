"""Tests for BLE Heart Rate client."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from le_tour.devices.hr_client import HrClient
from le_tour.devices.base import DeviceNotFoundError, ConnectionError


class TestHrClient:
    """Test HR BLE client protocol compliance."""

    def test_initial_state(self):
        """Test client initial state."""
        client = HrClient()

        assert not client.is_connected
        assert client.device_info == {}

    def test_device_info_returns_copy(self):
        """Test that device_info returns a copy, not reference."""
        client = HrClient()
        client._device_info = {"name": "Test HR", "address": "AA:BB:CC:DD:EE:FF"}

        info = client.device_info
        info["name"] = "Modified"

        assert client.device_info["name"] == "Test HR"

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    async def test_scan_no_devices_found(self, mock_scanner):
        """Test scan when no HR devices are found."""
        mock_scanner.discover = AsyncMock(return_value=[])

        client = HrClient()

        with pytest.raises(DeviceNotFoundError, match="No heart rate monitors found"):
            await client.scan_and_connect(timeout_s=5.0)

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    @patch("le_tour.devices.hr_client.BleakClient")
    async def test_scan_and_connect_success(self, mock_client_class, mock_scanner):
        """Test successful scan and connect."""
        # Mock discovered device
        mock_device = Mock()
        mock_device.name = "Polar H10"
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_device.rssi = -55

        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        # Mock BLE client
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=b"\x01")  # Chest location
        mock_client_class.return_value = mock_client

        client = HrClient()
        await client.scan_and_connect(timeout_s=5.0)

        assert client.is_connected
        assert client.device_info["name"] == "Polar H10"
        assert client.device_info["address"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    @patch("le_tour.devices.hr_client.BleakClient")
    async def test_scan_and_connect_by_name(self, mock_client_class, mock_scanner):
        """Test scan and connect with specific device name."""
        # Mock multiple discovered devices
        device1 = Mock()
        device1.name = "Wahoo TICKR"
        device1.address = "11:22:33:44:55:66"

        device2 = Mock()
        device2.name = "Polar H10"
        device2.address = "AA:BB:CC:DD:EE:FF"

        mock_scanner.discover = AsyncMock(return_value=[device1, device2])

        # Mock BLE client
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=b"\x01")
        mock_client_class.return_value = mock_client

        client = HrClient()
        await client.scan_and_connect(device_name="Polar")

        # Should connect to Polar, not Wahoo
        assert client.device_info["name"] == "Polar H10"

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    async def test_scan_and_connect_name_not_found(self, mock_scanner):
        """Test scan when specified device name not found."""
        mock_device = Mock()
        mock_device.name = "Wahoo TICKR"

        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        client = HrClient()

        with pytest.raises(DeviceNotFoundError, match="No HR device matching"):
            await client.scan_and_connect(device_name="Polar")

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    @patch("le_tour.devices.hr_client.BleakClient")
    async def test_connect_failure(self, mock_client_class, mock_scanner):
        """Test connection failure handling."""
        mock_device = Mock()
        mock_device.name = "Polar H10"
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        # Mock client that fails to connect
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(side_effect=Exception("BLE error"))
        mock_client_class.return_value = mock_client

        client = HrClient()

        with pytest.raises(ConnectionError, match="Failed to connect"):
            await client.scan_and_connect()

    @pytest.mark.asyncio
    async def test_subscribe_without_connection(self):
        """Test that subscription fails when not connected."""
        client = HrClient()

        with pytest.raises(ConnectionError, match="Not connected"):
            await client.subscribe_hr_data(lambda x: None)

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    async def test_scan_available(self, mock_scanner):
        """Test scanning for available devices without connecting."""
        device1 = Mock()
        device1.name = "Polar H10"
        device1.address = "AA:BB:CC:DD:EE:FF"
        device1.rssi = -50

        device2 = Mock()
        device2.name = "Wahoo TICKR"
        device2.address = "11:22:33:44:55:66"
        device2.rssi = -65

        mock_scanner.discover = AsyncMock(return_value=[device1, device2])

        client = HrClient()
        devices = await client.scan_available(timeout_s=5.0)

        assert len(devices) == 2
        assert devices[0]["name"] == "Polar H10"
        assert devices[0]["address"] == "AA:BB:CC:DD:EE:FF"
        assert devices[1]["name"] == "Wahoo TICKR"

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    async def test_scan_available_empty(self, mock_scanner):
        """Test scanning when no devices found."""
        mock_scanner.discover = AsyncMock(return_value=[])

        client = HrClient()
        devices = await client.scan_available(timeout_s=5.0)

        assert devices == []

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected doesn't raise."""
        client = HrClient()

        # Should not raise
        await client.disconnect()

        assert not client.is_connected
        assert client.device_info == {}

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    @patch("le_tour.devices.hr_client.BleakClient")
    async def test_disconnect(self, mock_client_class, mock_scanner):
        """Test successful disconnection."""
        mock_device = Mock()
        mock_device.name = "Polar H10"
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=b"\x01")
        mock_client_class.return_value = mock_client

        client = HrClient()
        await client.scan_and_connect()

        assert client.is_connected

        await client.disconnect()

        mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    @patch("le_tour.devices.hr_client.BleakClient")
    async def test_connect_to_device_success(self, mock_client_class, mock_scanner):
        """Test connecting to a specific device by address."""
        mock_device = Mock()
        mock_device.name = "Polar H10"
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_device.rssi = -55

        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=b"\x01")
        mock_client_class.return_value = mock_client

        client = HrClient()
        await client.connect_to_device("AA:BB:CC:DD:EE:FF")

        assert client.is_connected
        assert client.device_info["address"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    @patch("le_tour.devices.hr_client.BleakScanner")
    async def test_connect_to_device_not_found(self, mock_scanner):
        """Test connecting to device that's not found."""
        mock_scanner.discover = AsyncMock(return_value=[])

        client = HrClient()

        with pytest.raises(DeviceNotFoundError, match="not found"):
            await client.connect_to_device("AA:BB:CC:DD:EE:FF")


class TestHrClientSensorLocations:
    """Test sensor location mapping."""

    def test_sensor_locations_mapping(self):
        """Test all standard sensor locations are mapped."""
        locations = HrClient.SENSOR_LOCATIONS

        assert locations[0] == "Other"
        assert locations[1] == "Chest"
        assert locations[2] == "Wrist"
        assert locations[3] == "Finger"
        assert locations[4] == "Hand"
        assert locations[5] == "Ear Lobe"
        assert locations[6] == "Foot"


class TestHrClientUUIDs:
    """Test BLE service and characteristic UUIDs."""

    def test_hr_service_uuid(self):
        """Test HR service UUID is correct."""
        assert HrClient.HR_SERVICE_UUID == "0000180d-0000-1000-8000-00805f9b34fb"

    def test_hr_measurement_uuid(self):
        """Test HR measurement characteristic UUID."""
        assert HrClient.HR_MEASUREMENT_UUID == "00002a37-0000-1000-8000-00805f9b34fb"

    def test_battery_service_uuid(self):
        """Test battery service UUID."""
        assert HrClient.BATTERY_SERVICE_UUID == "0000180f-0000-1000-8000-00805f9b34fb"
