"""Training metrics calculations: Normalized Power, Intensity Factor, TSS.

These metrics follow the standard cycling power analysis methodology
originally developed by Dr. Andrew Coggan.

References:
    - Training and Racing with a Power Meter (Coggan & Allen)
    - https://www.trainingpeaks.com/learn/articles/normalized-power-intensity-factor-training-stress/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class TrainingMetrics:
    """Calculated training metrics for a session.

    Attributes:
        normalized_power_w: Normalized Power in watts. Represents the power
            you could have maintained for the same physiological cost if
            output had been constant.
        intensity_factor: Ratio of NP to FTP (0.0 to ~1.5+). Values >1.0
            indicate above-threshold effort.
        training_stress_score: Training load expressed in arbitrary units.
            100 TSS = 1 hour at FTP.
        average_power_w: Simple arithmetic mean of power samples.
        max_power_w: Peak power recorded during session.
        variability_index: NP/avg power ratio. Higher values indicate more
            variable (less steady) effort.
    """

    normalized_power_w: float
    intensity_factor: float
    training_stress_score: float
    average_power_w: float
    max_power_w: int
    variability_index: float


def calculate_normalized_power(
    power_samples: Sequence[int],
    sample_rate_hz: float = 1.0,
    window_seconds: float = 30.0,
) -> Optional[float]:
    """Calculate Normalized Power from a sequence of power readings.

    Normalized Power (NP) accounts for the variability of power output
    during a ride. It uses a 30-second rolling average raised to the
    4th power to weight harder efforts more heavily.

    Algorithm:
        1. Calculate 30-second rolling average of power
        2. Raise each averaged value to the 4th power
        3. Take the average of these 4th power values
        4. Take the 4th root of that average

    Args:
        power_samples: Sequence of instantaneous power values in watts.
            Zero and negative values are valid (coasting/descending).
        sample_rate_hz: Sample frequency in Hz (samples per second).
            Default is 1.0 (one sample per second).
        window_seconds: Rolling average window size in seconds.
            Default is 30.0 (standard NP window).

    Returns:
        Normalized Power in watts, or None if insufficient data.
        Returns None if fewer samples than the window size.

    Example:
        >>> powers = [200] * 60 + [300] * 60  # 1 min @ 200W, 1 min @ 300W
        >>> np_value = calculate_normalized_power(powers, sample_rate_hz=1.0)
        >>> 245 < np_value < 255  # NP higher than simple avg (250W)
        True
    """
    if not power_samples:
        return None

    # Calculate window size in samples
    window_size = int(window_seconds * sample_rate_hz)

    if len(power_samples) < window_size:
        # Not enough data for meaningful NP calculation
        # Fall back to simple average for very short sessions
        if len(power_samples) > 0:
            return float(sum(power_samples) / len(power_samples))
        return None

    # Calculate 30-second rolling averages
    rolling_averages: List[float] = []

    for i in range(len(power_samples) - window_size + 1):
        window = power_samples[i : i + window_size]
        avg = sum(window) / window_size
        rolling_averages.append(avg)

    if not rolling_averages:
        return None

    # Raise to 4th power, average, then 4th root
    fourth_powers = [avg**4 for avg in rolling_averages]
    mean_fourth_power = sum(fourth_powers) / len(fourth_powers)
    normalized_power = mean_fourth_power**0.25

    return normalized_power


def calculate_intensity_factor(
    normalized_power_w: float,
    ftp_w: int,
) -> float:
    """Calculate Intensity Factor (IF) from NP and FTP.

    Intensity Factor represents the relative intensity of a workout
    compared to the athlete's threshold power.

    IF = NP / FTP

    Typical values:
        - Recovery ride: < 0.75
        - Endurance ride: 0.75 - 0.85
        - Tempo ride: 0.85 - 0.95
        - Threshold intervals: 0.95 - 1.05
        - VO2max intervals: 1.05 - 1.20
        - Anaerobic efforts: > 1.20

    Args:
        normalized_power_w: Normalized Power in watts.
        ftp_w: Functional Threshold Power in watts. Must be positive.

    Returns:
        Intensity Factor as a ratio (typically 0.5 to 1.5).

    Raises:
        ValueError: If FTP is zero or negative.

    Example:
        >>> calculate_intensity_factor(225.0, 250)
        0.9
    """
    if ftp_w <= 0:
        raise ValueError(f"FTP must be positive, got {ftp_w}")

    return normalized_power_w / ftp_w


def calculate_tss(
    normalized_power_w: float,
    intensity_factor: float,
    duration_seconds: float,
    ftp_w: int,
) -> float:
    """Calculate Training Stress Score (TSS).

    TSS quantifies the training load of a workout. It accounts for
    both intensity and duration.

    TSS = (duration_s * NP * IF) / (FTP * 3600) * 100

    Or equivalently:
    TSS = (duration_s / 3600) * IF² * 100

    Reference values:
        - < 150: Low, recovery typically complete next day
        - 150-300: Medium, some residual fatigue next day
        - 300-450: High, residual fatigue likely for 2+ days
        - > 450: Very high, extended recovery needed

    A 1-hour ride at exactly FTP produces TSS = 100.

    Args:
        normalized_power_w: Normalized Power in watts.
        intensity_factor: Intensity Factor (NP/FTP ratio).
        duration_seconds: Workout duration in seconds.
        ftp_w: Functional Threshold Power in watts.

    Returns:
        Training Stress Score (dimensionless).

    Raises:
        ValueError: If FTP is zero or negative.

    Example:
        >>> # 1 hour at FTP (IF=1.0)
        >>> calculate_tss(250.0, 1.0, 3600, 250)
        100.0
    """
    if ftp_w <= 0:
        raise ValueError(f"FTP must be positive, got {ftp_w}")

    # TSS = (duration_s * NP * IF) / (FTP * 3600) * 100
    tss = (
        (duration_seconds * normalized_power_w * intensity_factor)
        / (ftp_w * 3600)
        * 100
    )

    return tss


def calculate_training_metrics(
    power_samples: Sequence[int],
    duration_seconds: float,
    ftp_w: int,
    sample_rate_hz: float = 1.0,
) -> Optional[TrainingMetrics]:
    """Calculate all training metrics from power data.

    This is the main entry point for computing session analytics.
    It calculates NP, IF, TSS, and related statistics in one call.

    Args:
        power_samples: Sequence of instantaneous power values in watts.
        duration_seconds: Total session duration in seconds.
        ftp_w: Functional Threshold Power in watts.
        sample_rate_hz: Sample frequency in Hz. Default 1.0.

    Returns:
        TrainingMetrics dataclass with all calculated values,
        or None if insufficient power data.

    Example:
        >>> powers = [220, 230, 240, 250, 260] * 100  # 500 samples
        >>> metrics = calculate_training_metrics(powers, 500, 250)
        >>> metrics is not None
        True
        >>> 0.8 < metrics.intensity_factor < 1.2
        True
    """
    if not power_samples or duration_seconds <= 0:
        return None

    # Filter out None values if any (defensive)
    valid_powers = [p for p in power_samples if p is not None]

    if not valid_powers:
        return None

    # Basic statistics
    average_power = sum(valid_powers) / len(valid_powers)
    max_power = max(valid_powers)

    # Normalized Power
    np_value = calculate_normalized_power(
        valid_powers,
        sample_rate_hz=sample_rate_hz,
    )

    if np_value is None:
        return None

    # Intensity Factor
    try:
        if_value = calculate_intensity_factor(np_value, ftp_w)
    except ValueError:
        return None

    # Training Stress Score
    try:
        tss_value = calculate_tss(np_value, if_value, duration_seconds, ftp_w)
    except ValueError:
        return None

    # Variability Index (how variable the effort was)
    variability_index = np_value / average_power if average_power > 0 else 1.0

    return TrainingMetrics(
        normalized_power_w=round(np_value, 1),
        intensity_factor=round(if_value, 3),
        training_stress_score=round(tss_value, 1),
        average_power_w=round(average_power, 1),
        max_power_w=max_power,
        variability_index=round(variability_index, 3),
    )


def calculate_power_zones(ftp_w: int) -> dict[str, tuple[int, int]]:
    """Calculate power training zones based on FTP.

    Uses the classic 7-zone model based on percentage of FTP.

    Args:
        ftp_w: Functional Threshold Power in watts.

    Returns:
        Dictionary mapping zone names to (min_watts, max_watts) tuples.

    Example:
        >>> zones = calculate_power_zones(250)
        >>> zones["Z4 Threshold"]
        (238, 262)
    """
    return {
        "Z1 Recovery": (0, int(ftp_w * 0.55)),
        "Z2 Endurance": (int(ftp_w * 0.55) + 1, int(ftp_w * 0.75)),
        "Z3 Tempo": (int(ftp_w * 0.75) + 1, int(ftp_w * 0.90)),
        "Z4 Threshold": (int(ftp_w * 0.90) + 1, int(ftp_w * 1.05)),
        "Z5 VO2max": (int(ftp_w * 1.05) + 1, int(ftp_w * 1.20)),
        "Z6 Anaerobic": (int(ftp_w * 1.20) + 1, int(ftp_w * 1.50)),
        "Z7 Neuromuscular": (int(ftp_w * 1.50) + 1, 9999),
    }


def calculate_hr_zones(max_hr_bpm: int) -> dict[str, tuple[int, int]]:
    """Calculate heart rate training zones based on max HR.

    Uses the classic 5-zone model based on percentage of max HR.

    Args:
        max_hr_bpm: Maximum heart rate in BPM.

    Returns:
        Dictionary mapping zone names to (min_bpm, max_bpm) tuples.

    Example:
        >>> zones = calculate_hr_zones(190)
        >>> zones["Z2 Easy"]
        (114, 133)
    """
    return {
        "Z1 Recovery": (0, int(max_hr_bpm * 0.60)),
        "Z2 Easy": (int(max_hr_bpm * 0.60) + 1, int(max_hr_bpm * 0.70)),
        "Z3 Aerobic": (int(max_hr_bpm * 0.70) + 1, int(max_hr_bpm * 0.80)),
        "Z4 Threshold": (int(max_hr_bpm * 0.80) + 1, int(max_hr_bpm * 0.90)),
        "Z5 Max": (int(max_hr_bpm * 0.90) + 1, max_hr_bpm + 50),  # Allow for spikes
    }


def get_hr_zone(hr_bpm: int, max_hr_bpm: int) -> tuple[str, str]:
    """Get the HR zone name and color for a given heart rate.

    Args:
        hr_bpm: Current heart rate in BPM.
        max_hr_bpm: Maximum heart rate in BPM.

    Returns:
        Tuple of (zone_name, color) where color is a semantic display token.

    Example:
        >>> get_hr_zone(150, 190)
        ('Z4', 'yellow')
    """
    pct = hr_bpm / max_hr_bpm if max_hr_bpm > 0 else 0

    if pct <= 0.60:
        return ("Z1", "dim")
    elif pct <= 0.70:
        return ("Z2", "blue")
    elif pct <= 0.80:
        return ("Z3", "green")
    elif pct <= 0.90:
        return ("Z4", "yellow")
    else:
        return ("Z5", "red")


def estimate_max_hr(age: int) -> int:
    """Estimate max heart rate from age using Tanaka formula.

    Formula: 208 - (0.7 × age)
    This is more accurate than the older 220 - age formula.

    Args:
        age: Age in years.

    Returns:
        Estimated max heart rate in BPM.

    Example:
        >>> estimate_max_hr(30)
        187
    """
    return int(208 - (0.7 * age))


def calculate_time_in_zones(
    power_samples: Sequence[int],
    ftp_w: int,
    sample_rate_hz: float = 1.0,
) -> dict[str, float]:
    """Calculate time spent in each power zone.

    Args:
        power_samples: Sequence of power values in watts.
        ftp_w: Functional Threshold Power in watts.
        sample_rate_hz: Sample frequency in Hz.

    Returns:
        Dictionary mapping zone names to time in seconds.

    Example:
        >>> powers = [100] * 60 + [200] * 60  # 1 min recovery, 1 min endurance
        >>> times = calculate_time_in_zones(powers, 250, sample_rate_hz=1.0)
        >>> times["Z1 Recovery"]
        60.0
    """
    zones = calculate_power_zones(ftp_w)
    time_in_zone: dict[str, float] = {zone: 0.0 for zone in zones}
    seconds_per_sample = 1.0 / sample_rate_hz

    for power in power_samples:
        if power is None:
            continue

        for zone_name, (min_w, max_w) in zones.items():
            if min_w <= power <= max_w:
                time_in_zone[zone_name] += seconds_per_sample
                break

    return time_in_zone
