"""Tests for HrService domain layer."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from le_tour.domain.device_state import DeviceConnectionStatus, DiscoveredDevice
from le_tour.domain.hr_service import HrService, get_hr_service
from le_tour.domain.events import (
    DeviceConnected,
    DeviceDisconnected,
    HrSampleReceived,
    ErrorEvent,
)
from le_tour.devices.base import HrSample


class TestHrServiceBasics:
    """Test HrService basic functionality."""

    def test_initial_state(self):
        """Test service initial state."""
        with patch("le_tour.domain.hr_service.HrClient"):
            service = HrService()

            assert service.last_hr is None
            assert service.has_sensor_contact is None
            assert len(service._subscribers) == 0

    def test_is_connected_delegates_to_client(self):
        """Test is_connected property delegates to client."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = Mock()
            mock_client.is_connected = True
            MockClient.return_value = mock_client

            service = HrService()
            service._client = mock_client

            assert service.is_connected is True

    def test_device_info_delegates_to_client(self):
        """Test device_info property delegates to client."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = Mock()
            mock_client.device_info = {"name": "Polar H10", "battery_percent": 85}
            MockClient.return_value = mock_client

            service = HrService()
            service._client = mock_client

            assert service.device_info == {"name": "Polar H10", "battery_percent": 85}

    def test_connection_status_is_ui_neutral(self):
        """Test HR status exposes connection state without private client access."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = Mock()
            mock_client.is_connected = True
            mock_client.device_info = {
                "name": "Polar H10",
                "address": "AA:BB",
                "rssi": -55,
            }
            MockClient.return_value = mock_client

            service = HrService()
            service._client = mock_client
            service._last_hr = 141
            service._last_contact = True

            status = service.connection_status()

            assert isinstance(status, DeviceConnectionStatus)
            assert status.connected is True
            assert status.device_type == "hr"
            assert status.name == "Polar H10"
            assert status.address == "AA:BB"
            assert status.rssi == -55
            assert status.last_hr_bpm == 141
            assert status.sensor_contact is True

    def test_connection_status_has_no_name_when_disconnected(self):
        """Disconnected HR status should not invent a connected name."""
        service = HrService()

        status = service.connection_status()

        assert status.connected is False
        assert status.name is None
        assert status.address is None


class TestHrServiceSubscription:
    """Test event subscription functionality."""

    def test_subscribe_adds_handler(self):
        """Test subscribing adds handler to list."""
        with patch("le_tour.domain.hr_service.HrClient"):
            service = HrService()
            handler = Mock()

            service.subscribe(handler)

            assert handler in service._subscribers

    def test_unsubscribe_removes_handler(self):
        """Test unsubscribing removes handler from list."""
        with patch("le_tour.domain.hr_service.HrClient"):
            service = HrService()
            handler = Mock()

            service.subscribe(handler)
            service.unsubscribe(handler)

            assert handler not in service._subscribers

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing non-existent handler doesn't raise."""
        with patch("le_tour.domain.hr_service.HrClient"):
            service = HrService()
            handler = Mock()

            # Should not raise
            service.unsubscribe(handler)

    def test_emit_calls_all_subscribers(self):
        """Test _emit calls all subscribed handlers."""
        with patch("le_tour.domain.hr_service.HrClient"):
            service = HrService()
            handler1 = Mock()
            handler2 = Mock()

            service.subscribe(handler1)
            service.subscribe(handler2)

            event = DeviceConnected(name="Test", device_type="hr")
            service._emit(event)

            handler1.assert_called_once_with(event)
            handler2.assert_called_once_with(event)

    def test_emit_handles_subscriber_error(self):
        """Test _emit continues if subscriber raises."""
        with patch("le_tour.domain.hr_service.HrClient"):
            service = HrService()
            handler1 = Mock(side_effect=Exception("Error"))
            handler2 = Mock()

            service.subscribe(handler1)
            service.subscribe(handler2)

            event = DeviceConnected(name="Test", device_type="hr")
            service._emit(event)

            # Second handler should still be called
            handler2.assert_called_once_with(event)


class TestHrServiceScan:
    """Test scanning functionality."""

    @pytest.mark.asyncio
    async def test_scan_available_success(self):
        """Test successful scan returns devices."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_available = AsyncMock(
                return_value=[
                    {"name": "Polar H10", "address": "AA:BB:CC:DD:EE:FF", "rssi": -50}
                ]
            )
            MockClient.return_value = mock_client

            service = HrService()
            devices = await service.scan_available(timeout_s=5.0)

            assert len(devices) == 1
            assert devices[0]["name"] == "Polar H10"

    @pytest.mark.asyncio
    async def test_scan_devices_returns_domain_models(self):
        """Test scans can return UI-neutral HR device models."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_available = AsyncMock(
                return_value=[
                    {
                        "name": "Wahoo TICKR",
                        "address": "CC:DD",
                        "rssi": -62,
                        "battery_percent": 91,
                    }
                ]
            )
            MockClient.return_value = mock_client

            service = HrService()
            devices = await service.scan_devices(timeout_s=3.0)

            assert len(devices) == 1
            assert isinstance(devices[0], DiscoveredDevice)
            assert devices[0].device_type == "hr"
            assert devices[0].name == "Wahoo TICKR"
            assert devices[0].address == "CC:DD"
            assert devices[0].rssi == -62
            assert devices[0].metadata == {"battery_percent": 91}

    @pytest.mark.asyncio
    async def test_scan_available_error_emits_event(self):
        """Test scan error emits ErrorEvent."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_available = AsyncMock(side_effect=Exception("BLE error"))
            MockClient.return_value = mock_client

            service = HrService()
            handler = Mock()
            service.subscribe(handler)

            devices = await service.scan_available()

            assert devices == []
            handler.assert_called_once()
            event = handler.call_args[0][0]
            assert isinstance(event, ErrorEvent)
            assert event.code == "HR_E_SCAN_FAILED"


class TestHrServiceConnect:
    """Test connection functionality."""

    @pytest.mark.asyncio
    async def test_scan_and_connect_success(self):
        """Test successful connection emits DeviceConnected."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_and_connect = AsyncMock()
            mock_client.device_info = {
                "name": "Polar H10",
                "address": "AA:BB:CC:DD:EE:FF",
                "rssi": -50,
            }
            MockClient.return_value = mock_client

            service = HrService()
            handler = Mock()
            service.subscribe(handler)

            await service.scan_and_connect(timeout_s=5.0)

            handler.assert_called_once()
            event = handler.call_args[0][0]
            assert isinstance(event, DeviceConnected)
            assert event.name == "Polar H10"
            assert event.device_type == "hr"

    @pytest.mark.asyncio
    async def test_scan_and_connect_with_name(self):
        """Test connection with device_name parameter."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_and_connect = AsyncMock()
            mock_client.device_info = {"name": "Wahoo TICKR"}
            MockClient.return_value = mock_client

            service = HrService()

            await service.scan_and_connect(timeout_s=10.0, device_name="Wahoo")

            mock_client.scan_and_connect.assert_called_once_with(
                timeout_s=10.0,
                device_name="Wahoo",
            )

    @pytest.mark.asyncio
    async def test_scan_and_connect_failure_emits_error(self):
        """Test connection failure emits ErrorEvent and re-raises."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_and_connect = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            MockClient.return_value = mock_client

            service = HrService()
            handler = Mock()
            service.subscribe(handler)

            with pytest.raises(Exception, match="Connection failed"):
                await service.scan_and_connect()

            handler.assert_called_once()
            event = handler.call_args[0][0]
            assert isinstance(event, ErrorEvent)
            assert event.code == "HR_E_CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_connect_to_device_success(self):
        """Test successful address connection emits DeviceConnected."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.connect_to_device = AsyncMock()
            mock_client.device_info = {
                "name": "Polar H10",
                "address": "AA:BB:CC:DD:EE:FF",
                "rssi": -50,
            }
            MockClient.return_value = mock_client

            service = HrService()
            handler = Mock()
            service.subscribe(handler)

            await service.connect_to_device("AA:BB:CC:DD:EE:FF")

            mock_client.connect_to_device.assert_called_once_with("AA:BB:CC:DD:EE:FF")
            event = handler.call_args[0][0]
            assert isinstance(event, DeviceConnected)
            assert event.name == "Polar H10"
            assert event.device_type == "hr"


class TestHrServiceDisconnect:
    """Test disconnection functionality."""

    @pytest.mark.asyncio
    async def test_disconnect_emits_event(self):
        """Test disconnect emits DeviceDisconnected."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.disconnect = AsyncMock()
            MockClient.return_value = mock_client

            service = HrService()
            service._last_hr = 120
            service._last_contact = True

            handler = Mock()
            service.subscribe(handler)

            await service.disconnect()

            # State should be reset
            assert service.last_hr is None
            assert service.has_sensor_contact is None

            # Event should be emitted
            handler.assert_called_once()
            event = handler.call_args[0][0]
            assert isinstance(event, DeviceDisconnected)
            assert event.device_type == "hr"


class TestHrServiceData:
    """Test HR data subscription functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_hr_data(self):
        """Test subscribing to HR data."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.subscribe_hr_data = AsyncMock()
            MockClient.return_value = mock_client

            service = HrService()
            callback = Mock()

            await service.subscribe_hr_data(callback)

            mock_client.subscribe_hr_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_hr_sample_updates_last_hr(self):
        """Test that HR samples update last_hr property."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            captured_handler = None

            async def capture_handler(handler, raw_handler=None):
                nonlocal captured_handler
                captured_handler = handler

            mock_client.subscribe_hr_data = capture_handler
            MockClient.return_value = mock_client

            service = HrService()
            callback = Mock()

            await service.subscribe_hr_data(callback)

            # Simulate receiving a sample
            sample: HrSample = {"ts": 1234567890.0, "hr_bpm": 145}
            captured_handler(sample)

            assert service.last_hr == 145
            callback.assert_called_once_with(sample)

    @pytest.mark.asyncio
    async def test_hr_sample_emits_event(self):
        """Test that HR samples emit HrSampleReceived events."""
        with patch("le_tour.domain.hr_service.HrClient") as MockClient:
            mock_client = AsyncMock()
            captured_handler = None

            async def capture_handler(handler, raw_handler=None):
                nonlocal captured_handler
                captured_handler = handler

            mock_client.subscribe_hr_data = capture_handler
            MockClient.return_value = mock_client

            service = HrService()
            event_handler = Mock()
            service.subscribe(event_handler)

            await service.subscribe_hr_data(Mock())

            sample: HrSample = {"ts": 1234567890.0, "hr_bpm": 155}
            captured_handler(sample)

            event_handler.assert_called_once()
            event = event_handler.call_args[0][0]
            assert isinstance(event, HrSampleReceived)
            assert event.sample == sample


class TestHrServiceSingleton:
    """Test singleton instance management."""

    def test_get_hr_service_returns_instance(self):
        """Test get_hr_service returns an HrService instance."""
        with patch("le_tour.domain.hr_service.HrClient"):
            # Reset singleton
            import le_tour.domain.hr_service as module

            module._hr_service = None

            service = get_hr_service()

            assert isinstance(service, HrService)

    def test_get_hr_service_returns_same_instance(self):
        """Test get_hr_service returns the same instance."""
        with patch("le_tour.domain.hr_service.HrClient"):
            # Reset singleton
            import le_tour.domain.hr_service as module

            module._hr_service = None

            service1 = get_hr_service()
            service2 = get_hr_service()

            assert service1 is service2
