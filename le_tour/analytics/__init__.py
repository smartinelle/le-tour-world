"""Analytics module for training metrics calculations.

This module provides functions for computing standard cycling power metrics:
- Normalized Power (NP)
- Intensity Factor (IF)
- Training Stress Score (TSS)
- Power zones and time-in-zone analysis
"""

from .metrics import (
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

__all__ = [
    "TrainingMetrics",
    "calculate_normalized_power",
    "calculate_intensity_factor",
    "calculate_tss",
    "calculate_training_metrics",
    "calculate_power_zones",
    "calculate_time_in_zones",
    "calculate_hr_zones",
    "get_hr_zone",
    "estimate_max_hr",
]
