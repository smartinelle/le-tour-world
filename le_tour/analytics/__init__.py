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
from .activity_graphs import (
    ActivityGraphData,
    ActivityGraphPoint,
    ActivityGraphReference,
    ActivityGraphSeries,
    ActivityGraphStat,
    build_history_distance_graph,
    build_session_cadence_graph,
    build_session_hr_graph,
    build_session_power_graph,
    build_session_speed_graph,
    normalize_graph_range,
)

__all__ = [
    "ActivityGraphData",
    "ActivityGraphPoint",
    "ActivityGraphReference",
    "ActivityGraphSeries",
    "ActivityGraphStat",
    "TrainingMetrics",
    "build_history_distance_graph",
    "build_session_cadence_graph",
    "build_session_hr_graph",
    "build_session_power_graph",
    "build_session_speed_graph",
    "calculate_normalized_power",
    "calculate_intensity_factor",
    "calculate_tss",
    "calculate_training_metrics",
    "calculate_power_zones",
    "calculate_time_in_zones",
    "calculate_hr_zones",
    "get_hr_zone",
    "estimate_max_hr",
    "normalize_graph_range",
]
