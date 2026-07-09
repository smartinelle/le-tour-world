"""Unit tests for RideController."""

import time
from unittest.mock import MagicMock
from le_tour.domain.ride_controller import (
    RideController,
    RideMode,
    RideMetrics,
)
from le_tour.domain.routes import default_demo_route


class TestRideControllerBasics:
    """Basic RideController tests."""

    def test_initial_state(self):
        """Controller starts with inactive state."""
        controller = RideController()

        assert not controller.is_active
        assert not controller.is_paused
        assert controller.state.mode is None
        assert controller.state.session_id is None

    def test_snapshot_inactive(self):
        """Inactive snapshot exposes default state and connection flags."""
        trainer = MagicMock()
        trainer.is_connected = False
        trainer.device_info = {}
        hr_service = MagicMock()
        hr_service.is_connected = False
        hr_service.device_info = {}
        controller = RideController(trainer=trainer, hr_service=hr_service)

        snapshot = controller.snapshot()

        assert snapshot.session_state == "inactive"
        assert snapshot.active is False
        assert snapshot.paused is False
        assert snapshot.mode is None
        assert snapshot.elapsed_s == 0.0
        assert snapshot.trainer_connected is False
        assert snapshot.hr_connected is False

    def test_snapshot_active(self):
        """Active snapshot includes lifecycle state and trainer connection."""
        trainer = MagicMock()
        trainer.is_connected = True
        trainer.device_info = {"name": "KICKR Core"}
        hr_service = MagicMock()
        hr_service.is_connected = False
        hr_service.device_info = {}
        controller = RideController(trainer=trainer, hr_service=hr_service)

        session_id = controller.start_session(RideMode.FREE, "Fallback Trainer")
        snapshot = controller.snapshot()

        assert snapshot.session_state == "active"
        assert snapshot.active is True
        assert snapshot.session_id == session_id
        assert snapshot.mode == RideMode.FREE
        assert snapshot.trainer_connected is True
        assert snapshot.trainer_name == "KICKR Core"
        assert snapshot.elapsed_s >= 0.0

    def test_snapshot_paused(self):
        """Paused snapshot reflects paused session state."""
        controller = RideController()
        controller.start_session(RideMode.FREE)

        controller.pause()
        snapshot = controller.snapshot()

        assert snapshot.session_state == "paused"
        assert snapshot.active is True
        assert snapshot.paused is True

    def test_snapshot_erg(self):
        """ERG snapshot includes target power."""
        controller = RideController()
        controller.start_session(RideMode.ERG)
        controller.set_erg_target(225)

        snapshot = controller.snapshot()

        assert snapshot.mode == RideMode.ERG
        assert snapshot.erg_target_w == 225

    def test_snapshot_sim(self):
        """SIM snapshot includes road grade."""
        controller = RideController()
        controller.start_session(RideMode.SIM)
        controller.set_sim_grade(4.5)

        snapshot = controller.snapshot()

        assert snapshot.mode == RideMode.SIM
        assert snapshot.sim_grade_pct == 4.5

    def test_snapshot_live_sample_updates(self):
        """Snapshot reflects latest bike and HR samples."""
        trainer = MagicMock()
        trainer.is_connected = False
        trainer.device_info = {}
        hr_service = MagicMock()
        hr_service.is_connected = True
        hr_service.device_info = {"name": "Polar H10"}
        controller = RideController(trainer=trainer, hr_service=hr_service)
        controller.start_session(RideMode.FREE)

        controller.handle_bike_sample(
            {
                "ts": time.time(),
                "power_w": 210,
                "cadence_rpm": 88,
                "speed_mps": 9.2,
            }
        )
        controller.handle_hr_sample({"ts": time.time(), "hr_bpm": 147})
        snapshot = controller.snapshot()

        assert snapshot.power_w == 210
        assert snapshot.cadence_rpm == 88
        assert snapshot.speed_mps == 9.2
        assert snapshot.hr_bpm == 147
        assert snapshot.hr_connected is True
        assert snapshot.hr_name == "Polar H10"

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
        assert controller.recorded_sample_count == 0

    def test_sim_session_persists_route_metadata(self):
        """Saved SIM sessions carry selected route metadata."""
        service = MagicMock()
        controller = RideController(session_service=service)
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.SIM)
        controller.handle_bike_sample(
            {
                "ts": time.time(),
                "power_w": 180,
                "cadence_rpm": 86,
                "speed_mps": 8.0,
            }
        )

        saved_session_id = controller.stop_session()

        assert saved_session_id is not None
        saved_session = service.save_session.call_args.args[0]
        assert saved_session.sim_route_id == "demo_rolling_route"
        assert saved_session.sim_route_title == "Rolling Demo Route"

    def test_stop_session_persists_training_metrics(self):
        """Saved sessions include analytics needed by history without samples."""
        service = MagicMock()
        controller = RideController(session_service=service)
        controller.start_session(RideMode.ERG)
        controller._started_monotonic = time.monotonic() - 120.0

        for power_w in (200, 220, 240):
            controller.handle_bike_sample(
                {
                    "ts": time.time(),
                    "power_w": power_w,
                    "cadence_rpm": 86,
                    "speed_mps": 8.0,
                }
            )

        saved_session_id = controller.stop_session()

        assert saved_session_id is not None
        saved_session = service.save_session.call_args.args[0]
        assert saved_session.normalized_power_w is not None
        assert saved_session.intensity_factor is not None
        assert saved_session.training_stress_score is not None


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

    def test_route_profile_sets_initial_sim_grade(self):
        """SIM mode can take grade from a distance-indexed route profile."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())

        controller.start_session(RideMode.SIM)

        # Distance 0 sits on the lap seam, so the smoothed grade blends the
        # last segment (-0.6%) into the first (0.4%).
        assert controller.metrics.sim_grade_pct == 0.0

    def test_route_profile_updates_sim_grade_from_distance(self):
        """Route profile updates SIM grade as physics distance crosses segments."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.SIM)
        start = time.time()

        # Ride hard at 1 Hz until physics distance crosses the 420 m Valley
        # Rollers / Pine Rise boundary (300 W flat sustains ~11.5 m/s).
        for second in range(75):
            controller.handle_bike_sample(
                {
                    "ts": start + second,
                    "power_w": 300,
                    "cadence_rpm": 90,
                    "speed_mps": 10.0,
                }
            )

        assert controller.metrics.distance_m > 420.0
        assert controller.metrics.sim_grade_pct == 3.2

    def test_sim_grade_ramps_across_segment_boundaries(self):
        """Resistance transitions in steps bounded by the smoothing window,
        never as one jolt from segment grade to segment grade."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.SIM)
        start = time.time()

        grades: list[float] = []
        for second in range(120):
            controller.handle_bike_sample(
                {
                    "ts": start + second,
                    "power_w": 300,
                    "cadence_rpm": 90,
                    "speed_mps": 10.0,
                }
            )
            grades.append(controller.metrics.sim_grade_pct)

        # The ride crossed segment boundaries up to the -2.1% -> 5.6% step
        # (7.7 grade points raw). Ramped, no sample may jump more than the
        # window allows (step size x speed/window ~= 0.4 x step) - assert
        # well under half the raw step, with intermediate values present.
        assert max(grades) == 3.2
        deltas = [abs(b - a) for a, b in zip(grades, grades[1:])]
        assert max(deltas) < 3.5
        assert any(0.4 < grade < 3.2 for grade in grades)


class TestPhysicsSpeedAuthority:
    """With a route attached, the virtual world computes speed from power."""

    def _sample(self, ts: float, power_w: int = 200) -> dict[str, object]:
        return {
            "ts": ts,
            "power_w": power_w,
            "cadence_rpm": 90,
            "speed_mps": 99.0,  # implausible trainer speed: must be ignored
        }

    def test_route_ride_uses_physics_speed_not_trainer_speed(self):
        """Speed comes from rider dynamics; trainer speed stays diagnostic."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.SIM)
        start = time.time()

        for second in range(30):
            controller.handle_bike_sample(self._sample(start + second))

        assert controller.metrics.speed_source == "physics"
        assert controller.metrics.trainer_speed_mps == 99.0
        assert controller.metrics.speed_mps is not None
        # 200 W on the flat warmup sustains ~9-10 m/s, nowhere near 99.
        assert 5.0 < controller.metrics.speed_mps < 15.0

    def test_route_ride_accumulates_physics_distance(self):
        """Distance integrates the physics speed, not the trainer speed."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.SIM)
        start = time.time()

        for second in range(10):
            controller.handle_bike_sample(self._sample(start + second))

        # 9 seconds of riding from a standstill at 200 W: well under the
        # 891 m the bogus 99 m/s trainer speed would have produced.
        assert 0.0 < controller.metrics.distance_m < 100.0

    def test_speed_ramps_with_inertia_not_instantly(self):
        """Speed builds over seconds from a standing start."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.FREE)
        start = time.time()

        speeds: list[float] = []
        for second in range(12):
            controller.handle_bike_sample(self._sample(start + second))
            speeds.append(float(controller.metrics.speed_mps or 0.0))

        assert speeds[1] < speeds[5] < speeds[-1]
        assert speeds[1] < 5.0  # still accelerating early on

    def test_no_route_keeps_trainer_speed_authority(self):
        """Without a world, the trainer's reported speed is used directly."""
        controller = RideController()
        controller.start_session(RideMode.FREE)

        controller.handle_bike_sample(
            {
                "ts": time.time(),
                "power_w": 200,
                "cadence_rpm": 90,
                "speed_mps": 8.5,
            }
        )

        assert controller.metrics.speed_source == "trainer"
        assert controller.metrics.speed_mps == 8.5
        assert controller.metrics.trainer_speed_mps == 8.5

    def test_snapshot_exposes_speed_source_and_trainer_speed(self):
        """Clients can observe both speeds for calibration benches."""
        controller = RideController()
        controller.set_route_profile(default_demo_route())
        controller.start_session(RideMode.SIM)
        start = time.time()
        controller.handle_bike_sample(self._sample(start))
        controller.handle_bike_sample(self._sample(start + 1))

        snapshot = controller.snapshot().to_dict()

        assert snapshot["speed_source"] == "physics"
        assert snapshot["trainer_speed_mps"] == 99.0
        assert snapshot["speed_mps"] != 99.0


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
        sample1 = {
            "ts": time.time(),
            "power_w": 200,
            "cadence_rpm": 90,
            "speed_mps": 10.0,
        }
        controller.handle_bike_sample(sample1)

        # Wait a bit and send another
        time.sleep(0.1)
        sample2 = {
            "ts": time.time(),
            "power_w": 200,
            "cadence_rpm": 90,
            "speed_mps": 10.0,
        }
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

    def test_paused_freezes_live_metrics(self):
        """Paused session freezes displayed metrics and accumulated data."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        controller.handle_bike_sample(
            {
                "ts": time.time(),
                "power_w": 150,
                "cadence_rpm": 82,
                "speed_mps": 7.0,
            }
        )
        controller.pause()
        paused_elapsed_s = controller.metrics.elapsed_s

        sample = {
            "ts": time.time(),
            "power_w": 200,
            "cadence_rpm": 90,
            "speed_mps": 10.0,
        }
        controller.handle_bike_sample(sample)

        assert controller.metrics.power_w == 150
        assert controller.metrics.elapsed_s == paused_elapsed_s
        assert controller.metrics.distance_m == 0.0

    def test_discard_session_does_not_persist_samples(self):
        """Discarding stops the ride without saving captured samples."""
        service = MagicMock()
        controller = RideController(session_service=service)
        controller.start_session(RideMode.FREE)
        controller.handle_bike_sample(
            {
                "ts": time.time(),
                "power_w": 200,
                "cadence_rpm": 90,
                "speed_mps": 10.0,
            }
        )

        controller.discard_session()

        assert not controller.is_active
        service.save_session.assert_not_called()
        service.save_sample.assert_not_called()


class TestLivePowerAnalytics:
    """Live in-ride avg power / normalized power for the HUD (M4)."""

    @staticmethod
    def _feed(controller, powers, start_ts):
        for i, power in enumerate(powers):
            controller.handle_bike_sample(
                {
                    "ts": start_ts + i,
                    "power_w": power,
                    "cadence_rpm": 90,
                    "speed_mps": 8.0,
                }
            )

    def test_constant_power_avg_and_np_match_power(self):
        """Steady effort: avg equals the power and NP converges onto it."""
        controller = RideController()
        controller.start_session(RideMode.FREE)

        self._feed(controller, [200] * 40, time.time())

        assert controller.metrics.avg_power_w == 200.0
        assert abs(controller.metrics.normalized_power_w - 200.0) < 1.0

    def test_variable_power_np_exceeds_avg(self):
        """NP weights hard efforts: surges push NP above average power."""
        controller = RideController()
        controller.start_session(RideMode.FREE)

        self._feed(controller, [100] * 60 + [500] * 60, time.time())

        avg = controller.metrics.avg_power_w
        np_w = controller.metrics.normalized_power_w
        assert abs(avg - 300.0) < 1.0
        assert np_w > avg + 20.0

    def test_snapshot_exposes_live_power_analytics_and_ftp(self):
        """Snapshot carries avg/NP and the configured FTP for zone coloring."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        self._feed(controller, [250] * 5, time.time())

        snapshot = controller.snapshot().to_dict()

        assert snapshot["avg_power_w"] == 250.0
        assert snapshot["normalized_power_w"] is not None
        assert isinstance(snapshot["ftp_w"], int)
        assert snapshot["ftp_w"] > 0

    def test_new_session_resets_live_power_stats(self):
        """A fresh session must not inherit the previous ride's analytics."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        self._feed(controller, [400] * 10, time.time())

        controller.stop_session()
        controller.start_session(RideMode.FREE)

        assert controller.metrics.avg_power_w is None
        assert controller.metrics.normalized_power_w is None
        self._feed(controller, [100] * 3, time.time() + 100)
        assert controller.metrics.avg_power_w == 100.0

    def test_powerless_samples_do_not_skew_stats(self):
        """Samples without power (e.g. cadence-only) leave analytics alone."""
        controller = RideController()
        controller.start_session(RideMode.FREE)
        start = time.time()
        self._feed(controller, [200] * 3, start)
        controller.handle_bike_sample(
            {"ts": start + 3, "cadence_rpm": 90, "speed_mps": 8.0}
        )

        assert controller.metrics.avg_power_w == 200.0


class TestCallbacks:
    """Event callback tests."""

    def test_metrics_callback(self):
        """Metrics callback is called on sample."""
        controller = RideController()
        callback = MagicMock()
        controller.on_metrics_update = callback

        controller.start_session(RideMode.FREE)
        sample = {
            "ts": time.time(),
            "power_w": 200,
            "cadence_rpm": 90,
            "speed_mps": 8.5,
        }
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
