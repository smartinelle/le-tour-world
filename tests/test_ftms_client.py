"""Tests for FTMS BLE client."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from le_tour.devices.ftms_client import FtmsClient
from le_tour.devices.base import (
    DeviceNotFoundError,
    ConnectionError,
    ControlNotAvailableError,
)


class TestFtmsClient:
    """Test FTMS BLE client protocol compliance."""

    def test_implements_trainer_device_protocol(self):
        """Test that FtmsClient implements TrainerDevice protocol."""
        from le_tour.devices.base import TrainerDevice

        client = FtmsClient()
        assert isinstance(client, TrainerDevice)

    def test_initial_state(self):
        """Test client initial state."""
        client = FtmsClient()

        assert not client.is_connected
        assert not client.has_control
        assert client.device_info == {}

    @pytest.mark.asyncio
    @patch("le_tour.devices.ftms_client.BleakScanner")
    async def test_scan_no_devices_found(self, mock_scanner):
        """Test scan when no FTMS devices are found."""
        mock_scanner.discover = AsyncMock(return_value=[])

        client = FtmsClient()

        with pytest.raises(DeviceNotFoundError, match="No FTMS trainers found"):
            await client.scan_and_connect(timeout_s=5.0)

    @pytest.mark.asyncio
    @patch("le_tour.devices.ftms_client.BleakScanner")
    @patch("le_tour.devices.ftms_client.BleakClient")
    async def test_scan_and_connect_success(self, mock_client_class, mock_scanner):
        """Test successful scan and connect."""
        # Mock discovered device
        mock_device = Mock()
        mock_device.name = "Wahoo KICKR"
        mock_device.address = "12:34:56:78:90:AB"
        mock_device.rssi = -45

        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        # Mock BLE client
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=b"\\x00\\x01")
        mock_client_class.return_value = mock_client

        client = FtmsClient()
        await client.scan_and_connect(timeout_s=5.0)

        assert client.is_connected
        assert client.device_info["name"] == "Wahoo KICKR"
        assert client.device_info["address"] == "12:34:56:78:90:AB"

    @pytest.mark.asyncio
    @patch("le_tour.devices.ftms_client.BleakScanner")
    @patch("le_tour.devices.ftms_client.BleakClient")
    async def test_connect_failure(self, mock_client_class, mock_scanner):
        """Test connection failure handling."""
        mock_device = Mock()
        mock_device.name = "Wahoo KICKR"
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        # Mock client that fails to connect
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(side_effect=Exception("BLE error"))
        mock_client_class.return_value = mock_client

        client = FtmsClient()

        with pytest.raises(ConnectionError, match="Failed to connect"):
            await client.scan_and_connect()

    @pytest.mark.asyncio
    async def test_operations_without_connection(self):
        """Test that operations fail when not connected."""
        client = FtmsClient()

        with pytest.raises(ConnectionError, match="Not connected"):
            await client.subscribe_bike_data(lambda x: None)

        with pytest.raises(ConnectionError, match="Not connected"):
            await client.request_control()

    @pytest.mark.asyncio
    async def test_subscribe_bike_data_is_idempotent(self):
        """Repeated subscriptions update the callback without duplicate notifies."""
        client = FtmsClient()
        mock_ble = AsyncMock()
        mock_ble.is_connected = True
        client._client = mock_ble

        first_callback = Mock()
        second_callback = Mock()

        await client.subscribe_bike_data(first_callback)
        await client.subscribe_bike_data(second_callback)

        mock_ble.start_notify.assert_awaited_once()
        assert client._bike_data_callback is second_callback

    @pytest.mark.asyncio
    async def test_disconnect_clears_bike_data_subscription_state(self):
        """Explicit disconnect allows a future connection to subscribe again."""
        client = FtmsClient()
        mock_ble = AsyncMock()
        mock_ble.is_connected = True
        client._client = mock_ble
        client._bike_data_callback = Mock()
        client._bike_data_notify_active = True

        await client.disconnect()

        assert client._bike_data_callback is None
        assert client._bike_data_notify_active is False

    @pytest.mark.asyncio
    async def test_control_operations_without_control(self):
        """Test that control operations fail without control."""
        client = FtmsClient()
        # Simulate connected but no control
        client._client = Mock()
        client._client.is_connected = True

        with pytest.raises(ControlNotAvailableError, match="Control not granted"):
            await client.start_session()

        with pytest.raises(ControlNotAvailableError, match="Control not granted"):
            await client.set_target_power(200)

    def test_power_validation(self):
        """Test power range validation."""
        client = FtmsClient()
        # Simulate having control
        client._has_control = True
        client._client = Mock()
        client._client.is_connected = True

        # Test invalid power values
        with pytest.raises(ValueError, match="outside valid range"):
            asyncio.run(client.set_target_power(50))  # Too low

        with pytest.raises(ValueError, match="outside valid range"):
            asyncio.run(client.set_target_power(500))  # Too high
