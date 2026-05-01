"""Tests for TrainerService domain layer."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from terminalride.domain.trainer_service import TrainerService
from terminalride.domain.events import (
    DeviceConnected,
    DeviceDisconnected,
    SampleReceived,
    ControlGranted,
)
from terminalride.devices.base import BikeSample


class TestTrainerServiceBasics:
    """Test TrainerService basic functionality."""

    def test_initial_state(self):
        """Test service initial state."""
        with patch("terminalride.domain.trainer_service.FtmsClient"):
            service = TrainerService()

            assert len(service._subscribers) == 0

    def test_is_connected_delegates_to_client(self):
        """Test is_connected property delegates to client."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = Mock()
            mock_client.is_connected = True
            MockClient.return_value = mock_client

            service = TrainerService()
            service._client = mock_client

            assert service.is_connected is True

    def test_has_control_delegates_to_client(self):
        """Test has_control property delegates to client."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = Mock()
            mock_client.has_control = True
            MockClient.return_value = mock_client

            service = TrainerService()
            service._client = mock_client

            assert service.has_control is True

    def test_device_info_delegates_to_client(self):
        """Test device_info property delegates to client."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = Mock()
            mock_client.device_info = {"name": "Wahoo KICKR", "power_range": (0, 2000)}
            MockClient.return_value = mock_client

            service = TrainerService()
            service._client = mock_client

            assert service.device_info == {
                "name": "Wahoo KICKR",
                "power_range": (0, 2000),
            }


class TestTrainerServiceSubscription:
    """Test event subscription functionality."""

    def test_subscribe_adds_handler(self):
        """Test subscribing adds handler to list."""
        with patch("terminalride.domain.trainer_service.FtmsClient"):
            service = TrainerService()
            handler = Mock()

            service.subscribe(handler)

            assert handler in service._subscribers

    def test_emit_calls_all_subscribers(self):
        """Test _emit calls all subscribed handlers."""
        with patch("terminalride.domain.trainer_service.FtmsClient"):
            service = TrainerService()
            handler1 = Mock()
            handler2 = Mock()

            service.subscribe(handler1)
            service.subscribe(handler2)

            event = DeviceConnected(name="Test", device_type="trainer")
            service._emit(event)

            handler1.assert_called_once_with(event)
            handler2.assert_called_once_with(event)

    def test_emit_handles_subscriber_error(self):
        """Test _emit continues if subscriber raises."""
        with patch("terminalride.domain.trainer_service.FtmsClient"):
            service = TrainerService()
            handler1 = Mock(side_effect=Exception("Error"))
            handler2 = Mock()

            service.subscribe(handler1)
            service.subscribe(handler2)

            event = DeviceConnected(name="Test", device_type="trainer")
            service._emit(event)

            # Second handler should still be called
            handler2.assert_called_once_with(event)


class TestTrainerServiceConnect:
    """Test connection functionality."""

    @pytest.mark.asyncio
    async def test_scan_available_success(self):
        """Test successful scan returns trainer devices."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_available = AsyncMock(
                return_value=[{"name": "Wahoo KICKR", "address": "12:34", "rssi": -45}]
            )
            MockClient.return_value = mock_client

            service = TrainerService()
            devices = await service.scan_available(timeout_s=5.0)

            assert len(devices) == 1
            assert devices[0]["name"] == "Wahoo KICKR"
            mock_client.scan_available.assert_called_once_with(timeout_s=5.0)

    @pytest.mark.asyncio
    async def test_scan_available_error_emits_event(self):
        """Test scan failure emits ErrorEvent and returns no devices."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_available = AsyncMock(side_effect=Exception("BLE error"))
            MockClient.return_value = mock_client

            service = TrainerService()
            service._client = mock_client
            handler = Mock()
            service.subscribe(handler)

            devices = await service.scan_available()

            assert devices == []
            handler.assert_called_once()
            assert handler.call_args[0][0].code == "TRAINER_E_SCAN_FAILED"

    @pytest.mark.asyncio
    async def test_scan_and_connect_success(self):
        """Test successful connection emits DeviceConnected."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_and_connect = AsyncMock()
            mock_client.device_info = {
                "name": "Wahoo KICKR",
                "address": "12:34:56:78:90:AB",
                "rssi": -45,
            }
            MockClient.return_value = mock_client

            service = TrainerService()
            service._client = mock_client
            handler = Mock()
            service.subscribe(handler)

            await service.scan_and_connect(timeout_s=10.0)

            mock_client.scan_and_connect.assert_called_once_with(timeout_s=10.0)
            handler.assert_called_once()

            event = handler.call_args[0][0]
            assert isinstance(event, DeviceConnected)
            assert event.name == "Wahoo KICKR"
            assert event.address == "12:34:56:78:90:AB"

    @pytest.mark.asyncio
    async def test_scan_and_connect_with_timeout(self):
        """Test connection with custom timeout."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.scan_and_connect = AsyncMock()
            mock_client.device_info = {"name": "Trainer"}
            MockClient.return_value = mock_client

            service = TrainerService()

            await service.scan_and_connect(timeout_s=30.0)

            mock_client.scan_and_connect.assert_called_once_with(timeout_s=30.0)

    @pytest.mark.asyncio
    async def test_connect_to_device_success(self):
        """Test connecting by address emits DeviceConnected."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.connect_to_device = AsyncMock()
            mock_client.device_info = {
                "name": "Wahoo KICKR",
                "address": "12:34:56:78:90:AB",
                "rssi": -45,
            }
            MockClient.return_value = mock_client

            service = TrainerService()
            handler = Mock()
            service.subscribe(handler)

            await service.connect_to_device("12:34:56:78:90:AB")

            mock_client.connect_to_device.assert_called_once_with("12:34:56:78:90:AB")
            event = handler.call_args[0][0]
            assert isinstance(event, DeviceConnected)
            assert event.name == "Wahoo KICKR"


class TestTrainerServiceDisconnect:
    """Test disconnection functionality."""

    @pytest.mark.asyncio
    async def test_disconnect_emits_event(self):
        """Test disconnect emits DeviceDisconnected."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.disconnect = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()
            service._client = mock_client
            handler = Mock()
            service.subscribe(handler)

            await service.disconnect()

            mock_client.disconnect.assert_called_once()
            handler.assert_called_once()

            event = handler.call_args[0][0]
            assert isinstance(event, DeviceDisconnected)


class TestTrainerServiceSamples:
    """Test bike data subscription functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_samples(self):
        """Test subscribing to bike data samples."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.subscribe_bike_data = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()
            handler = Mock()

            await service.subscribe_samples(handler)

            mock_client.subscribe_bike_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_sample_emits_event_and_calls_handler(self):
        """Test that samples emit SampleReceived and call handler."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            captured_bridge = None

            async def capture_bridge(bridge):
                nonlocal captured_bridge
                captured_bridge = bridge

            mock_client.subscribe_bike_data = capture_bridge
            MockClient.return_value = mock_client

            service = TrainerService()
            sample_handler = Mock()
            event_handler = Mock()
            service.subscribe(event_handler)

            await service.subscribe_samples(sample_handler)

            # Simulate receiving a sample
            sample: BikeSample = {
                "ts": 1234567890.0,
                "power_w": 200,
                "cadence_rpm": 90,
                "speed_mps": 8.5,
            }
            captured_bridge(sample)

            # Handler should be called
            sample_handler.assert_called_once_with(sample)

            # Event should be emitted
            event_handler.assert_called_once()
            event = event_handler.call_args[0][0]
            assert isinstance(event, SampleReceived)
            assert event.sample == sample


class TestTrainerServiceControl:
    """Test trainer control functionality."""

    @pytest.mark.asyncio
    async def test_request_control(self):
        """Test requesting trainer control."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request_control = AsyncMock()
            mock_client.has_control = True
            MockClient.return_value = mock_client

            service = TrainerService()
            handler = Mock()
            service.subscribe(handler)

            await service.request_control()

            mock_client.request_control.assert_called_once()
            handler.assert_called_once()

            event = handler.call_args[0][0]
            assert isinstance(event, ControlGranted)
            assert event.granted is True

    @pytest.mark.asyncio
    async def test_request_control_denied(self):
        """Test control request denied."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.request_control = AsyncMock()
            mock_client.has_control = False
            MockClient.return_value = mock_client

            service = TrainerService()
            handler = Mock()
            service.subscribe(handler)

            await service.request_control()

            event = handler.call_args[0][0]
            assert isinstance(event, ControlGranted)
            assert event.granted is False

    @pytest.mark.asyncio
    async def test_start_session(self):
        """Test starting a training session."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.start_session = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()

            await service.start()

            mock_client.start_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_session(self):
        """Test stopping a training session."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.stop_session = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()

            await service.stop()

            mock_client.stop_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_target_power(self):
        """Test setting ERG target power."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.set_target_power = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()

            await service.set_target_power(250)

            mock_client.set_target_power.assert_called_once_with(250)

    @pytest.mark.asyncio
    async def test_set_simulation(self):
        """Test setting simulation grade."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.set_simulation_params = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()

            await service.set_simulation(5.5)

            mock_client.set_simulation_params.assert_called_once_with(5.5)

    @pytest.mark.asyncio
    async def test_set_simulation_negative_grade(self):
        """Test setting negative simulation grade (downhill)."""
        with patch("terminalride.domain.trainer_service.FtmsClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.set_simulation_params = AsyncMock()
            MockClient.return_value = mock_client

            service = TrainerService()

            await service.set_simulation(-3.0)

            mock_client.set_simulation_params.assert_called_once_with(-3.0)
