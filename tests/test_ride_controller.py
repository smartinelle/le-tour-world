"""Unit tests for RideController."""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock
from terminalride.domain.ride_controller import (
    RideController,
    RideMode,
    RideMetrics,
    RideState,
)


class TestRideControllerBasics:
    """Basic RideController tests."""

    def test_initial_state(self):
        """Controller starts with inactive state."""
        controller = RideController()
        
        assert not controller.is_active
        assert not controller.is_paused
        assert controller.state.mode is None
        assert controller.state.session_id is None

    def test_start_session_free(self, tmp_path):
        """Start a FREE mode session."""
        controller = RideController()
        
        session_id = controller.start_session(RideMode.FREE, "Test Trainer")
        
        assert session_id is not None
        assert controller.is_active
        assert not controller.is_paused
        assert controller.state.mode == RideMode.FREE
        assert controller.state.session_id == session_id

    def test_start_session_erg(self):
        """Start an ERG mode session with default target."""
        controller = RideController()
        
        controller.start_session(RideMode.ERG)
        
        assert controller.state.mode == RideMode.ERG
        assert controller.metrics.erg_target_w == 150  # Default

    def test_start_session_sim(self):
        """Start a SIM mode session with default grade."""
        controller = RideController()
        
        controller.start_session(RideMode.SIM)
        
        assert controller.state.mode == RideMode.SIM
        assert controller.metrics.sim_grade_pct == 0.0  # Default

    def test_stop_session_no_samples(self):
        """Stop session with no samples returns None."""
        controller = RideController()
        
        controller.start_session(RideMode.FREE)
        result = controller.stop_session()
        
        assert result is None
        assert not controller.is_active


class TestPauseResume:
    """Pause and resume tests."""

    def test_pause(self):
        """Pause active session."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        
        controller.pause()
        
        assert controller.is_paused
        assert controller.is_active

    def test_resume(self):
        """Resume paused session."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        controller.pause()
        
        controller.resume()
        
        assert not controller.is_paused
        assert controller.is_active

    def test_toggle_pause(self):
        """Toggle pause state."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        
        result1 = controller.toggle_pause()
        assert result1 is True
        assert controller.is_paused
        
        result2 = controller.toggle_pause()
        assert result2 is False
        assert not controller.is_paused


class TestErgControl:
    """ERG mode control tests."""

    def test_set_erg_target(self):
        """Set ERG target power."""
        controller = RideController()
        controller.start_session(RideMode.ERG)
        
        controller.set_erg_target(200)
        
        assert controller.metrics.erg_target_w == 200

    def test_erg_target_bounds(self):
        """ERG target respects bounds."""
        controller = RideController()
        controller.start_session(RideMode.ERG)
        
        controller.set_erg_target(50)  # Below minimum
        assert controller.metrics.erg_target_w == 100
        
        controller.set_erg_target(500)  # Above maximum
        assert controller.metrics.erg_target_w == 400

    def test_adjust_erg_target(self):
        """Adjust ERG target incrementally."""
        controller = RideController()
        controller.start_session(RideMode.ERG)
        controller.set_erg_target(200)
        
        result = controller.adjust_erg_target(10)
        
        assert result == 210
        assert controller.metrics.erg_target_w == 210


class TestSimControl:
    """SIM mode control tests."""

    def test_set_sim_grade(self):
        """Set SIM grade percentage."""
        controller = RideController()
        controller.start_session(RideMode.SIM)
        
        controller.set_sim_grade(5.0)
        
        assert controller.metrics.sim_grade_pct == 5.0

    def test_sim_grade_bounds(self):
        """SIM grade respects bounds."""
        controller = RideController()
        controller.start_session(RideMode.SIM)
        
        controller.set_sim_grade(-15.0)  # Below minimum
        assert controller.metrics.sim_grade_pct == -10.0
        
        controller.set_sim_grade(20.0)  # Above maximum
        assert controller.metrics.sim_grade_pct == 15.0

    def test_adjust_sim_grade(self):
        """Adjust SIM grade incrementally."""
        controller = RideController()
        controller.start_session(RideMode.SIM)
        controller.set_sim_grade(3.0)
        
        result = controller.adjust_sim_grade(0.5)
        
        assert result == 3.5
        assert controller.metrics.sim_grade_pct == 3.5


class TestSampleHandling:
    """Sample handling tests."""

    def test_handle_bike_sample_updates_metrics(self):
        """Bike sample updates live metrics."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        
        sample = {
            "ts": time.time(),
            "power_w": 200,
            "cadence_rpm": 90,
            "speed_mps": 8.5,
        }
        
        controller.handle_bike_sample(sample)
        
        assert controller.metrics.power_w == 200
        assert controller.metrics.cadence_rpm == 90
        assert controller.metrics.speed_mps == 8.5

    def test_handle_bike_sample_accumulates_distance(self):
        """Bike samples accumulate distance."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        
        # First sample
        sample1 = {"ts": time.time(), "power_w": 200, "cadence_rpm": 90, "speed_mps": 10.0}
        controller.handle_bike_sample(sample1)
        
        # Wait a bit and send another
        time.sleep(0.1)
        sample2 = {"ts": time.time(), "power_w": 200, "cadence_rpm": 90, "speed_mps": 10.0}
        controller.handle_bike_sample(sample2)
        
        # Should have accumulated ~1m of distance (10 m/s * 0.1s)
        assert controller.metrics.distance_m > 0

    def test_handle_hr_sample(self):
        """HR sample updates heart rate."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        
        sample = {"ts": time.time(), "hr_bpm": 145}
        
        controller.handle_hr_sample(sample)
        
        assert controller.metrics.hr_bpm == 145

    def test_paused_does_not_accumulate(self):
        """Paused session doesn't accumulate data."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        controller.pause()
        
        sample = {"ts": time.time(), "power_w": 200, "cadence_rpm": 90, "speed_mps": 10.0}
        controller.handle_bike_sample(sample)
        
        # Live metrics update but distance doesn't accumulate
        assert controller.metrics.power_w == 200
        assert controller.metrics.distance_m == 0.0


class TestCallbacks:
    """Event callback tests."""

    def test_metrics_callback(self):
        """Metrics callback is called on sample."""
        controller = RideController()
        callback = MagicMock()
        controller.on_metrics_update = callback
        
        controller.start_session(RideMode.FREE)
        sample = {"ts": time.time(), "power_w": 200, "cadence_rpm": 90, "speed_mps": 8.5}
        controller.handle_bike_sample(sample)
        
        assert callback.called
        metrics = callback.call_args[0][0]
        assert metrics.power_w == 200

    def test_state_callback(self):
        """State callback is called on state change."""
        controller = RideController()
        callback = MagicMock()
        controller.on_state_change = callback
        
        controller.start_session(RideMode.FREE)
        
        assert callback.called
        state = callback.call_args[0][0]
        assert state.active is True


class TestMetricsToDict:
    """RideMetrics serialization tests."""

    def test_to_dict(self):
        """Metrics can be converted to dict."""
        metrics = RideMetrics(
            elapsed_s=120.0,
            power_w=200,
            cadence_rpm=90,
            speed_mps=8.5,
            distance_m=1000.0,
            hr_bpm=145,
        )
        
        d = metrics.to_dict()
        
        assert d["time_s"] == 120.0
        assert d["power_w"] == 200
        assert d["cadence_rpm"] == 90
        assert d["speed_mps"] == 8.5
        assert d["distance_m"] == 1000.0
        assert d["hr_bpm"] == 145

