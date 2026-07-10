"""Tests for RideRuntime."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from le_tour.domain.ride_controller import RideController
from le_tour.domain.ride_runtime import RideRuntime
from le_tour.domain.routes import default_demo_route
from le_tour.domain.state import RideMode


def make_controller(
    trainer_connected: bool = False,
    hr_connected: bool = False,
) -> RideController:
    """Create a controller with mocked services."""
    trainer = MagicMock()
    trainer.is_connected = trainer_connected
    trainer.device_info = {"name": "KICKR"} if trainer_connected else {}
    trainer.subscribe_samples = AsyncMock()
    trainer.request_control = AsyncMock()
    trainer.set_target_power = AsyncMock()
    trainer.set_simulation = AsyncMock()
    hr_service = MagicMock()
    hr_service.is_connected = hr_connected
    hr_service.device_info = {"name": "Polar H10"} if hr_connected else {}
    hr_service.subscribe_hr_data = AsyncMock()
    return RideController(trainer=trainer, hr_service=hr_service)


def test_start_session_uses_fake_source_when_trainer_disconnected():
    """Runtime starts fake samples for no-hardware rides."""
    controller = make_controller(trainer_connected=False)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        snapshot = runtime.start_session(RideMode.FREE)

    assert snapshot.active is True
    assert snapshot.mode is RideMode.FREE
    assert snapshot.trainer_name == "Simulated Trainer"
    source.return_value.start.assert_called_once()


def test_start_session_skips_fake_source_when_trainer_connected():
    """Runtime does not start fake samples when trainer hardware is connected."""
    controller = make_controller(trainer_connected=True)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        snapshot = runtime.start_session(RideMode.ERG)

    assert snapshot.active is True
    assert snapshot.trainer_name == "KICKR"
    source.assert_not_called()


@pytest.mark.asyncio
async def test_prepare_hardware_session_attaches_trainer_stream():
    """Runtime attaches connected trainer samples outside any UI layer."""
    controller = make_controller(trainer_connected=True)
    runtime = RideRuntime(controller)
    runtime.start_session(RideMode.FREE)

    await runtime.prepare_hardware_session(RideMode.FREE)

    controller.trainer.subscribe_samples.assert_awaited_once_with(
        controller.handle_bike_sample
    )
    controller.trainer.request_control.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_hardware_session_configures_erg_control():
    """ERG sessions request trainer control and send the initial target."""
    controller = make_controller(trainer_connected=True)
    runtime = RideRuntime(controller)
    runtime.start_session(RideMode.ERG)

    await runtime.prepare_hardware_session(RideMode.ERG)

    controller.trainer.request_control.assert_awaited_once()
    controller.trainer.set_target_power.assert_awaited_once_with(150)
    controller.trainer.set_simulation.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_hardware_session_configures_sim_control_from_route():
    """SIM sessions send the current route grade to the trainer."""
    controller = make_controller(trainer_connected=True)
    runtime = RideRuntime(controller, route_profile=default_demo_route())
    runtime.start_session(RideMode.SIM)

    await runtime.prepare_hardware_session(RideMode.SIM)

    controller.trainer.request_control.assert_awaited_once()
    controller.trainer.set_simulation.assert_awaited_once_with(0.0)


@pytest.mark.asyncio
async def test_prepare_hardware_session_attaches_hr_without_trainer():
    """A real HR strap can be used while trainer samples remain simulated."""
    controller = make_controller(trainer_connected=False, hr_connected=True)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)
        await runtime.prepare_hardware_session(RideMode.FREE)

    source.return_value.start.assert_called_once()
    controller.hr_service.subscribe_hr_data.assert_awaited_once_with(
        controller.handle_hr_sample
    )
    controller.trainer.subscribe_samples.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_hardware_session_does_not_duplicate_subscriptions():
    """Runtime avoids duplicate BLE subscriptions across repeated prepares."""
    controller = make_controller(trainer_connected=True, hr_connected=True)
    runtime = RideRuntime(controller)
    runtime.start_session(RideMode.FREE)

    await runtime.prepare_hardware_session(RideMode.FREE)
    await runtime.prepare_hardware_session(RideMode.FREE)

    controller.trainer.subscribe_samples.assert_awaited_once()
    controller.hr_service.subscribe_hr_data.assert_awaited_once()


def test_stop_session_stops_fake_source():
    """Runtime stops its fake source when the ride stops."""
    controller = make_controller(trainer_connected=False)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)
        snapshot = runtime.stop_session()

    source.return_value.stop.assert_called_once()
    assert snapshot.active is False


def test_request_stop_confirmation_stops_fake_source_and_pauses():
    """Runtime freezes rides before the UI asks to save or delete."""
    controller = make_controller(trainer_connected=False)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)
        snapshot = runtime.request_stop_confirmation()

    source.return_value.stop.assert_called_once()
    assert snapshot.active is True
    assert snapshot.paused is True


def test_stop_session_result_reports_unsaved_empty_rides():
    """Runtime exposes no-sample stop results for UI summary flows."""
    controller = make_controller(trainer_connected=False)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource"):
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)
        result = runtime.stop_session_result()

    assert result.snapshot.active is False
    assert result.session_id is not None
    assert result.saved_session_id is None
    assert result.sample_count == 0
    assert result.saved is False


def test_discard_session_stops_without_saving():
    """Runtime can end rides without persisting or showing a summary."""
    service = MagicMock()
    controller = RideController(session_service=service)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource"):
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)
        result = runtime.discard_session()

    assert result.snapshot.active is False
    assert result.saved_session_id is None
    assert result.saved is False
    service.save_session.assert_not_called()
    service.save_sample.assert_not_called()


def test_runtime_controls_return_snapshots():
    """Runtime control methods mutate controller state and return snapshots."""
    controller = make_controller(trainer_connected=False)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource"):
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.ERG)
        paused = runtime.toggle_pause()
        erg = runtime.adjust_erg_target(20)
        runtime.start_session(RideMode.SIM)
        sim = runtime.adjust_sim_grade(1.5)

    assert paused.paused is True
    assert erg.erg_target_w == 170
    assert sim.sim_grade_pct == 1.5


def test_runtime_can_attach_route_profile():
    """Runtime can attach a route profile without UI coupling."""
    controller = make_controller(trainer_connected=False)
    runtime = RideRuntime(controller)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource"):
        runtime.set_route_profile(default_demo_route())
        snapshot = runtime.start_session(RideMode.SIM)

    # Seam-blended smoothed grade at the start line.
    assert snapshot.sim_grade_pct == 0.0


def test_fake_source_ignores_fake_hr_when_hr_hardware_connected():
    """Fake trainer source should not overwrite a connected HR strap."""
    controller = make_controller(trainer_connected=False, hr_connected=True)

    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)

    kwargs = source.call_args.kwargs
    kwargs["hr_handler"]({"ts": 1.0, "hr_bpm": 155})
    assert controller.metrics.hr_bpm is None


def test_set_virtual_power_reaches_running_fake_source():
    """Live rider-set watts are forwarded to the running virtual trainer."""
    controller = RideController()
    runtime = RideRuntime(controller)
    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        source.return_value.is_running = True
        runtime.start_session(RideMode.FREE)

        snapshot = runtime.set_virtual_power(250)

        source.return_value.set_effort.assert_called_once_with(
            "hold", power_w=250, duration_s=None
        )
        assert runtime.virtual_power_w == 250
        assert snapshot.active is True


def test_virtual_power_set_before_start_applies_on_fake_source_creation():
    """Virtual power chosen before the ride starts sticks to the new source."""
    controller = RideController()
    runtime = RideRuntime(controller)
    runtime.set_virtual_power(180)
    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource") as source:
        source.return_value.is_running = True

        runtime.start_session(RideMode.FREE)

        source.return_value.set_effort.assert_called_once_with(
            "hold", power_w=180, duration_s=None
        )


def test_disconnect_event_resets_sample_attachment():
    """After a manual disconnect, the next session must re-subscribe.

    Manual disconnects clear the BLE clients' notify state, so a sticky
    attached-flag would leave the next session with a connected trainer
    and no samples until app restart.
    """
    from le_tour.domain.events import DeviceDisconnected

    controller = make_controller(trainer_connected=True, hr_connected=True)
    runtime = RideRuntime(controller)
    runtime._trainer_samples_attached = True
    runtime._hr_samples_attached = True

    runtime._on_trainer_event(DeviceDisconnected())
    runtime._on_hr_event(DeviceDisconnected())

    assert runtime._trainer_samples_attached is False
    assert runtime._hr_samples_attached is False


@pytest.mark.asyncio
async def test_reconnect_then_new_session_resubscribes_samples():
    """Disconnect + reconnect + new ride ends with live samples again."""
    from le_tour.domain.events import DeviceDisconnected

    controller = make_controller(trainer_connected=True)
    runtime = RideRuntime(controller)
    await runtime.prepare_hardware_session(RideMode.FREE)
    assert controller.trainer.subscribe_samples.await_count == 1

    runtime._on_trainer_event(DeviceDisconnected())
    await runtime.prepare_hardware_session(RideMode.FREE)

    assert controller.trainer.subscribe_samples.await_count == 2


@pytest.mark.asyncio
async def test_trainer_connect_mid_session_takes_over_from_demo_source():
    """Pairing during an active ride hands the session to hardware."""
    controller = make_controller(trainer_connected=False)
    with patch("le_tour.domain.ride_runtime.FakeTrainerSampleSource"):
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.SIM)
        assert runtime._fake_source is not None

        controller.trainer.is_connected = True
        await runtime._attach_trainer_mid_session()

    assert runtime._fake_source is None
    controller.trainer.subscribe_samples.assert_awaited_once()
    controller.trainer.request_control.assert_awaited_once()
    controller.trainer.set_simulation.assert_awaited_once()


def test_connect_event_when_inactive_does_not_attach():
    """Auto-connect at startup (no session) must not start hardware prep."""
    from le_tour.domain.events import DeviceConnected

    controller = make_controller(trainer_connected=True)
    runtime = RideRuntime(controller)

    runtime._on_trainer_event(DeviceConnected(name="KICKR"))

    controller.trainer.subscribe_samples.assert_not_awaited()
