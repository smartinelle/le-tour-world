"""Tests for activity graph data builders."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from le_tour.analytics.activity_graphs import (
    build_history_distance_graph,
    build_session_power_graph,
    normalize_graph_range,
)
from le_tour.store.models import SampleModel, SessionModel, TrainingMode


def _session(
    day_offset: int,
    *,
    distance_m: float,
    start: datetime,
) -> SessionModel:
    return SessionModel(
        mode=TrainingMode.FREE,
        start_time=start + timedelta(days=day_offset),
        duration_s=1800.0,
        total_distance_m=distance_m,
    )


def test_normalize_graph_range_defaults_to_30_days() -> None:
    assert normalize_graph_range(None) == "30d"
    assert normalize_graph_range("bad") == "30d"
    assert normalize_graph_range("7d") == "7d"
    assert normalize_graph_range("all") == "all"


def test_history_distance_graph_buckets_latest_7_days() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    sessions = [
        _session(0, distance_m=10_000.0, start=start),
        _session(7, distance_m=12_000.0, start=start),
        _session(8, distance_m=3_000.0, start=start),
    ]

    graph = build_history_distance_graph(
        sessions,
        "7d",
        today=date(2026, 1, 9),
        local_tz=UTC,
    )

    points = graph.series[0].points
    assert len(points) == 7
    assert sum(point.y for point in points) == 15.0
    assert points[0].label == "03.01"
    assert points[-1].label == "09.01"
    assert graph.stats[0].value == "15.0 km"
    assert graph.stats[1].value == "2"


def test_history_distance_graph_all_uses_available_span_through_today() -> None:
    start = datetime(2026, 5, 2, tzinfo=UTC)
    sessions = [
        _session(0, distance_m=4_000.0, start=start),
        _session(2, distance_m=6_000.0, start=start),
    ]

    graph = build_history_distance_graph(
        sessions,
        "all",
        today=date(2026, 5, 15),
        local_tz=UTC,
    )

    points = graph.series[0].points
    assert len(points) == 14
    assert [point.y for point in points[:3]] == [4.0, 0.0, 6.0]
    assert points[0].label == "02.05"
    assert points[-1].label == "15.05"
    assert points[-1].y == 0.0
    assert graph.detail == "Distance by day since your first saved ride through today."


def test_session_power_graph_adds_target_series_and_ftp_reference() -> None:
    samples = [
        SampleModel(
            session_id="s1",
            elapsed_s=float(index * 60),
            power_w=180 + index * 10,
            erg_target_power_w=220,
        )
        for index in range(3)
    ]

    graph = build_session_power_graph(samples, ftp_w=250)

    assert [series.key for series in graph.series] == [
        "power_w",
        "erg_target_power_w",
    ]
    assert graph.series[0].points[-1].label == "2m"
    assert graph.references[0].label == "FTP"
    assert graph.references[0].value == 250.0
    assert graph.stats[0].value == "190 W"
    assert graph.stats[1].value == "200 W"
