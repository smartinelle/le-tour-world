"""Unit tests for analytics metrics module.

Tests cover:
- Normalized Power calculation
- Intensity Factor calculation
- Training Stress Score calculation
- Power zones
- Time in zones
- Edge cases and error handling
"""

import pytest
from terminalride.analytics import (
    TrainingMetrics,
    calculate_normalized_power,
    calculate_intensity_factor,
    calculate_tss,
    calculate_training_metrics,
    calculate_power_zones,
    calculate_time_in_zones,
    calculate_hr_zones,
    get_hr_zone,
    estimate_max_hr,
)


class TestNormalizedPower:
    """Tests for Normalized Power calculation."""

    def test_constant_power_equals_average(self):
        """NP of constant power equals that power."""
        constant_power = [200] * 100
        np_value = calculate_normalized_power(constant_power, sample_rate_hz=1.0)

        assert np_value is not None
        assert abs(np_value - 200.0) < 0.1

    def test_variable_power_higher_than_average(self):
        """NP of variable power is higher than simple average."""
        # 1 minute at 150W, 1 minute at 250W
        # Simple average = 200W
        variable_power = [150] * 60 + [250] * 60
        np_value = calculate_normalized_power(variable_power, sample_rate_hz=1.0)

        assert np_value is not None
        simple_avg = sum(variable_power) / len(variable_power)
        assert np_value > simple_avg  # NP always >= avg for variable power

    def test_high_variability_increases_np(self):
        """Higher variability increases NP relative to average."""
        # Low variability: 190-210W (±10W)
        low_var = [190] * 30 + [210] * 30 + [190] * 30 + [210] * 30
        np_low = calculate_normalized_power(low_var, sample_rate_hz=1.0)

        # High variability: 100-300W (±100W)
        high_var = [100] * 30 + [300] * 30 + [100] * 30 + [300] * 30
        np_high = calculate_normalized_power(high_var, sample_rate_hz=1.0)

        assert np_low is not None
        assert np_high is not None

        # Both have same average (200W) but high var has higher NP
        avg_low = sum(low_var) / len(low_var)
        avg_high = sum(high_var) / len(high_var)
        assert abs(avg_low - avg_high) < 1  # Same average

        assert np_high > np_low  # Higher variability = higher NP

    def test_empty_samples_returns_none(self):
        """Empty power list returns None."""
        assert calculate_normalized_power([]) is None

    def test_insufficient_samples_uses_average(self):
        """Fewer samples than window size falls back to average."""
        short_samples = [200, 210, 190]  # Only 3 samples, window is 30
        np_value = calculate_normalized_power(short_samples, sample_rate_hz=1.0)

        # Should return simple average for short sessions
        assert np_value is not None
        assert abs(np_value - 200.0) < 1

    def test_different_sample_rates(self):
        """NP calculation works with different sample rates."""
        # 30 samples at 1Hz = 30 samples at 0.5Hz * 2
        power_1hz = [200] * 60
        power_2hz = [200] * 120  # Same duration, 2x samples

        np_1hz = calculate_normalized_power(power_1hz, sample_rate_hz=1.0)
        np_2hz = calculate_normalized_power(power_2hz, sample_rate_hz=2.0)

        assert np_1hz is not None
        assert np_2hz is not None
        # Should give similar results (both constant 200W)
        assert abs(np_1hz - np_2hz) < 1

    def test_zero_power_periods(self):
        """Handles zero power (coasting) correctly."""
        # Intervals: 30s @ 300W, 30s @ 0W (coasting)
        intervals = [300] * 30 + [0] * 30 + [300] * 30 + [0] * 30
        np_value = calculate_normalized_power(intervals, sample_rate_hz=1.0)

        assert np_value is not None
        # NP should be significantly higher than simple avg (150W)
        simple_avg = sum(intervals) / len(intervals)
        assert np_value > simple_avg


class TestIntensityFactor:
    """Tests for Intensity Factor calculation."""

    def test_np_equals_ftp_gives_if_one(self):
        """IF = 1.0 when NP equals FTP."""
        if_value = calculate_intensity_factor(250.0, 250)
        assert abs(if_value - 1.0) < 0.001

    def test_np_below_ftp(self):
        """IF < 1.0 when NP is below FTP."""
        if_value = calculate_intensity_factor(200.0, 250)
        assert if_value == 0.8

    def test_np_above_ftp(self):
        """IF > 1.0 when NP is above FTP."""
        if_value = calculate_intensity_factor(300.0, 250)
        assert if_value == 1.2

    def test_zero_ftp_raises_error(self):
        """Zero FTP raises ValueError."""
        with pytest.raises(ValueError, match="FTP must be positive"):
            calculate_intensity_factor(200.0, 0)

    def test_negative_ftp_raises_error(self):
        """Negative FTP raises ValueError."""
        with pytest.raises(ValueError, match="FTP must be positive"):
            calculate_intensity_factor(200.0, -100)


class TestTSS:
    """Tests for Training Stress Score calculation."""

    def test_one_hour_at_ftp_equals_100(self):
        """1 hour at FTP (IF=1.0) produces TSS = 100."""
        tss = calculate_tss(
            normalized_power_w=250.0,
            intensity_factor=1.0,
            duration_seconds=3600,
            ftp_w=250,
        )
        assert abs(tss - 100.0) < 0.1

    def test_half_hour_at_ftp_equals_50(self):
        """30 minutes at FTP produces TSS = 50."""
        tss = calculate_tss(
            normalized_power_w=250.0,
            intensity_factor=1.0,
            duration_seconds=1800,
            ftp_w=250,
        )
        assert abs(tss - 50.0) < 0.1

    def test_one_hour_at_half_ftp(self):
        """1 hour at 50% FTP (IF=0.5) produces TSS = 25."""
        # TSS = (3600 * 125 * 0.5) / (250 * 3600) * 100 = 25
        tss = calculate_tss(
            normalized_power_w=125.0,
            intensity_factor=0.5,
            duration_seconds=3600,
            ftp_w=250,
        )
        assert abs(tss - 25.0) < 0.1

    def test_high_intensity_short_duration(self):
        """High intensity (IF=1.2) for 30 min produces ~72 TSS."""
        # TSS = (1800 * 300 * 1.2) / (250 * 3600) * 100 = 72
        tss = calculate_tss(
            normalized_power_w=300.0,
            intensity_factor=1.2,
            duration_seconds=1800,
            ftp_w=250,
        )
        assert abs(tss - 72.0) < 0.1

    def test_zero_ftp_raises_error(self):
        """Zero FTP raises ValueError."""
        with pytest.raises(ValueError, match="FTP must be positive"):
            calculate_tss(200.0, 0.8, 3600, 0)


class TestTrainingMetrics:
    """Tests for combined training metrics calculation."""

    def test_complete_metrics_calculation(self):
        """Full metrics calculation returns all expected values."""
        # Steady state ride simulation: ~1 hour at ~200W
        power_samples = [195, 200, 205, 198, 202, 203, 197, 201, 199, 204] * 360
        duration = 3600  # 1 hour
        ftp = 250

        metrics = calculate_training_metrics(
            power_samples=power_samples,
            duration_seconds=duration,
            ftp_w=ftp,
            sample_rate_hz=1.0,
        )

        assert metrics is not None
        assert isinstance(metrics, TrainingMetrics)

        # Check all fields are populated
        assert metrics.normalized_power_w > 0
        assert 0 < metrics.intensity_factor < 2
        assert metrics.training_stress_score > 0
        assert metrics.average_power_w > 0
        assert metrics.max_power_w > 0
        assert metrics.variability_index >= 1.0

    def test_endurance_ride_metrics(self):
        """Endurance ride metrics are in expected range."""
        # Endurance ride: 1 hour at 65% FTP
        ftp = 250
        target_power = int(ftp * 0.65)  # 162W
        power_samples = [target_power + i % 10 - 5 for i in range(3600)]

        metrics = calculate_training_metrics(
            power_samples=power_samples,
            duration_seconds=3600,
            ftp_w=ftp,
        )

        assert metrics is not None
        # IF should be around 0.65
        assert 0.6 < metrics.intensity_factor < 0.75
        # TSS for 1hr endurance should be ~42 (0.65² * 100)
        assert 35 < metrics.training_stress_score < 60

    def test_threshold_intervals_metrics(self):
        """Threshold interval metrics show higher values."""
        ftp = 250

        # 5x5min at FTP with 3min recovery
        power_samples = []
        for _ in range(5):
            power_samples.extend([ftp] * 300)  # 5 min at FTP
            power_samples.extend([int(ftp * 0.5)] * 180)  # 3 min recovery

        duration = len(power_samples)  # ~40 min

        metrics = calculate_training_metrics(
            power_samples=power_samples,
            duration_seconds=duration,
            ftp_w=ftp,
        )

        assert metrics is not None
        # NP should be higher than simple average due to intervals
        simple_avg = sum(power_samples) / len(power_samples)
        assert metrics.normalized_power_w > simple_avg
        # Variability index > 1 for intervals
        assert metrics.variability_index > 1.0

    def test_empty_power_returns_none(self):
        """Empty power samples returns None."""
        metrics = calculate_training_metrics(
            power_samples=[],
            duration_seconds=3600,
            ftp_w=250,
        )
        assert metrics is None

    def test_zero_duration_returns_none(self):
        """Zero duration returns None."""
        metrics = calculate_training_metrics(
            power_samples=[200] * 100,
            duration_seconds=0,
            ftp_w=250,
        )
        assert metrics is None


class TestPowerZones:
    """Tests for power zone calculations."""

    def test_zones_with_standard_ftp(self):
        """Power zones calculated correctly for FTP=250."""
        zones = calculate_power_zones(250)

        assert "Z1 Recovery" in zones
        assert "Z4 Threshold" in zones
        assert "Z7 Neuromuscular" in zones

        # Z4 should be 90-105% FTP = 225-262
        z4_min, z4_max = zones["Z4 Threshold"]
        assert z4_min == int(250 * 0.90) + 1  # 226
        assert z4_max == int(250 * 1.05)  # 262

    def test_zones_coverage(self):
        """All zones cover the full power range without gaps."""
        zones = calculate_power_zones(250)

        # Sort zones by lower bound
        sorted_zones = sorted(zones.values(), key=lambda x: x[0])

        # Check coverage
        assert sorted_zones[0][0] == 0  # Starts at 0
        assert sorted_zones[-1][1] == 9999  # Ends at max

    def test_zones_with_different_ftp(self):
        """Zones scale correctly with different FTP values."""
        zones_200 = calculate_power_zones(200)
        zones_300 = calculate_power_zones(300)

        # Z4 upper bound scales with FTP
        assert zones_200["Z4 Threshold"][1] < zones_300["Z4 Threshold"][1]


class TestTimeInZones:
    """Tests for time-in-zone calculations."""

    def test_all_time_in_one_zone(self):
        """All samples in one zone."""
        ftp = 250
        # All at recovery (< 55% FTP = < 137W)
        power_samples = [100] * 60  # 60 samples at 100W

        times = calculate_time_in_zones(power_samples, ftp, sample_rate_hz=1.0)

        assert times["Z1 Recovery"] == 60.0
        assert times["Z2 Endurance"] == 0.0

    def test_split_between_zones(self):
        """Time split between multiple zones."""
        ftp = 250
        # 30s recovery, 30s endurance
        power_samples = [100] * 30 + [175] * 30

        times = calculate_time_in_zones(power_samples, ftp, sample_rate_hz=1.0)

        assert times["Z1 Recovery"] == 30.0
        assert times["Z2 Endurance"] == 30.0

    def test_sample_rate_affects_time(self):
        """Different sample rates calculate correct time."""
        ftp = 250
        power_samples = [100] * 60

        # At 1Hz: 60 samples = 60 seconds
        times_1hz = calculate_time_in_zones(power_samples, ftp, sample_rate_hz=1.0)
        assert times_1hz["Z1 Recovery"] == 60.0

        # At 2Hz: 60 samples = 30 seconds
        times_2hz = calculate_time_in_zones(power_samples, ftp, sample_rate_hz=2.0)
        assert times_2hz["Z1 Recovery"] == 30.0

    def test_empty_samples(self):
        """Empty samples returns all zeros."""
        times = calculate_time_in_zones([], 250, sample_rate_hz=1.0)

        for zone_time in times.values():
            assert zone_time == 0.0


class TestHrZones:
    """Tests for heart rate zone calculations."""

    def test_hr_zones_structure(self):
        """HR zones have correct structure."""
        zones = calculate_hr_zones(190)

        assert "Z1 Recovery" in zones
        assert "Z2 Easy" in zones
        assert "Z3 Aerobic" in zones
        assert "Z4 Threshold" in zones
        assert "Z5 Max" in zones

    def test_hr_zones_boundaries(self):
        """HR zones have correct boundaries for max HR 200."""
        zones = calculate_hr_zones(200)

        # Z1: 0-60% = 0-120
        assert zones["Z1 Recovery"] == (0, 120)
        # Z2: 60-70% = 121-140
        assert zones["Z2 Easy"] == (121, 140)
        # Z3: 70-80% = 141-160
        assert zones["Z3 Aerobic"] == (141, 160)
        # Z4: 80-90% = 161-180
        assert zones["Z4 Threshold"] == (161, 180)

    def test_get_hr_zone_recovery(self):
        """Low HR returns recovery zone."""
        zone, color = get_hr_zone(100, 190)
        assert zone == "Z1"
        assert color == "dim"

    def test_get_hr_zone_threshold(self):
        """High HR returns threshold zone."""
        zone, color = get_hr_zone(165, 190)  # ~87% of max
        assert zone == "Z4"
        assert color == "yellow"

    def test_get_hr_zone_max(self):
        """Very high HR returns max zone."""
        zone, color = get_hr_zone(180, 190)  # ~95% of max
        assert zone == "Z5"
        assert color == "red"

    def test_estimate_max_hr_age_30(self):
        """Max HR estimate for age 30."""
        max_hr = estimate_max_hr(30)
        assert max_hr == 187  # 208 - 0.7*30 = 187

    def test_estimate_max_hr_age_50(self):
        """Max HR estimate for age 50."""
        max_hr = estimate_max_hr(50)
        assert max_hr == 173  # 208 - 0.7*50 = 173


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_single_sample(self):
        """Single sample returns simple value."""
        np_value = calculate_normalized_power([200], sample_rate_hz=1.0)
        assert np_value == 200.0

    def test_very_high_power_spike(self):
        """Handles very high power spikes."""
        # Sprint: 1500W spike in otherwise steady ride
        power_samples = [200] * 50 + [1500] * 5 + [200] * 50
        np_value = calculate_normalized_power(power_samples, sample_rate_hz=1.0)

        assert np_value is not None
        # NP should be elevated but not extreme
        assert 200 < np_value < 500

    def test_all_zero_power(self):
        """All zero power samples."""
        power_samples = [0] * 100
        np_value = calculate_normalized_power(power_samples, sample_rate_hz=1.0)

        assert np_value is not None
        assert np_value == 0.0

    def test_low_ftp_athlete(self):
        """Metrics work for athletes with low FTP."""
        metrics = calculate_training_metrics(
            power_samples=[80] * 100,
            duration_seconds=100,
            ftp_w=100,  # Low FTP
        )

        assert metrics is not None
        assert metrics.intensity_factor == pytest.approx(0.8, rel=0.1)

    def test_high_ftp_athlete(self):
        """Metrics work for athletes with high FTP."""
        metrics = calculate_training_metrics(
            power_samples=[350] * 100,
            duration_seconds=100,
            ftp_w=400,  # Pro-level FTP
        )

        assert metrics is not None
        assert metrics.intensity_factor < 1.0

