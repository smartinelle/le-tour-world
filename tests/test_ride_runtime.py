"""Tests for RideRuntime."""

from unittest.mock import MagicMock, patch

from terminalride.domain.ride_controller import RideController
from terminalride.domain.ride_runtime import RideRuntime
from terminalride.domain.state import RideMode


def make_controller(trainer_connected: bool = False) -> RideController:
    """Create a controller with mocked services."""
    trainer = MagicMock()
    trainer.is_connected = trainer_connected
    trainer.device_info = {"name": "KICKR"} if trainer_connected else {}
    hr_service = MagicMock()
    hr_service.is_connected = False
    hr_service.device_info = {}
    return RideController(trainer=trainer, hr_service=hr_service)


def test_start_session_uses_fake_source_when_trainer_disconnected():
    """Runtime starts fake samples for no-hardware rides."""
    controller = make_controller(trainer_connected=False)

    with patch("terminalride.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        snapshot = runtime.start_session(RideMode.FREE)

    assert snapshot.active is True
    assert snapshot.mode is RideMode.FREE
    assert snapshot.trainer_name == "Simulated Trainer"
    source.return_value.start.assert_called_once()


def test_start_session_skips_fake_source_when_trainer_connected():
    """Runtime does not start fake samples when trainer hardware is connected."""
    controller = make_controller(trainer_connected=True)

    with patch("terminalride.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        snapshot = runtime.start_session(RideMode.ERG)

    assert snapshot.active is True
    assert snapshot.trainer_name == "KICKR"
    source.assert_not_called()


def test_stop_session_stops_fake_source():
    """Runtime stops its fake source when the ride stops."""
    controller = make_controller(trainer_connected=False)

    with patch("terminalride.domain.ride_runtime.FakeTrainerSampleSource") as source:
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.FREE)
        snapshot = runtime.stop_session()

    source.return_value.stop.assert_called_once()
    assert snapshot.active is False


def test_runtime_controls_return_snapshots():
    """Runtime control methods mutate controller state and return snapshots."""
    controller = make_controller(trainer_connected=False)

    with patch("terminalride.domain.ride_runtime.FakeTrainerSampleSource"):
        runtime = RideRuntime(controller)
        runtime.start_session(RideMode.ERG)
        paused = runtime.toggle_pause()
        erg = runtime.adjust_erg_target(20)
        runtime.start_session(RideMode.SIM)
        sim = runtime.adjust_sim_grade(1.5)

    assert paused.paused is True
    assert erg.erg_target_w == 170
    assert sim.sim_grade_pct == 1.5
