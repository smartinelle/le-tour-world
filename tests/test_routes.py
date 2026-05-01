"""Tests for route profile domain models."""

import json

import pytest

from terminalride.domain.routes import (
    RouteSpecError,
    available_route_specs,
    default_demo_route,
    load_route_spec,
    route_from_spec,
)


def test_default_demo_route_serializes_segments():
    """Default route is UI-neutral structured data."""
    route = default_demo_route()
    payload = route.to_dict()

    assert payload["id"] == "demo_rolling_route"
    assert payload["distance_m"] == 2080
    assert payload["segments"][0] == {
        "name": "Valley Rollers",
        "length_m": 420,
        "grade_pct": 0.4,
        "kind": "warmup",
        "surface": "asphalt",
        "scenery": "fields",
    }
    assert payload["start"]["segment"]["name"] == "Valley Rollers"
    assert payload["upcoming"][0]["segment_kind"] == "warmup"


def test_default_demo_route_is_loaded_from_bundled_spec():
    """Default route comes from the external route spec package asset."""
    assert available_route_specs() == ("demo_rolling_route.json",)

    route = default_demo_route()

    assert route.title == "Rolling Demo Route"
    assert route.segments[-1].surface == "gravel"


def test_route_spec_loader_accepts_file_specs(tmp_path):
    """Route specs can be loaded from disk without touching UI code."""
    route_file = tmp_path / "route.json"
    route_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "test_route",
                "title": "Test Route",
                "description": "A test route.",
                "segments": [
                    {
                        "name": "Start",
                        "length_m": 100,
                        "grade_pct": 1.5,
                        "kind": "rolling",
                        "surface": "asphalt",
                        "scenery": "fields",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    route = load_route_spec(route_file)

    assert route.route_id == "test_route"
    assert route.grade_at(10) == 1.5


def test_route_spec_rejects_empty_segments():
    """Invalid map specs fail before they can drive SIM or renderers."""
    with pytest.raises(RouteSpecError, match="segments"):
        route_from_spec(
            {
                "schema_version": 1,
                "id": "empty",
                "title": "Empty",
                "description": "No route.",
                "segments": [],
            }
        )


def test_route_spec_rejects_non_positive_segment_length():
    """Segment distances must remain usable for route progress math."""
    with pytest.raises(RouteSpecError, match="length_m"):
        route_from_spec(
            {
                "schema_version": 1,
                "id": "bad_length",
                "title": "Bad Length",
                "description": "Invalid segment length.",
                "segments": [
                    {
                        "name": "Broken",
                        "length_m": 0,
                        "grade_pct": 0,
                        "kind": "rolling",
                        "surface": "asphalt",
                        "scenery": "fields",
                    }
                ],
            }
        )


def test_route_spec_rejects_unknown_surface():
    """Renderer-facing metadata is constrained to supported values."""
    with pytest.raises(RouteSpecError, match="surface"):
        route_from_spec(
            {
                "schema_version": 1,
                "id": "bad_surface",
                "title": "Bad Surface",
                "description": "Invalid segment surface.",
                "segments": [
                    {
                        "name": "Broken",
                        "length_m": 100,
                        "grade_pct": 0,
                        "kind": "rolling",
                        "surface": "snow",
                        "scenery": "fields",
                    }
                ],
            }
        )


def test_default_demo_route_supports_distance_lookup():
    """Route profiles expose grade and section lookup by distance."""
    route = default_demo_route()

    assert route.grade_at(0) == 0.4
    assert route.segment_at(421).name == "Pine Rise"
    assert route.grade_at(421) == 3.2
    assert route.segment_at(route.distance_m + 1).name == "Valley Rollers"


def test_default_demo_route_returns_route_position():
    """Route position serializes current and next segment state."""
    route = default_demo_route()
    position = route.position_at(421)

    assert position.segment.name == "Pine Rise"
    assert position.segment.kind == "climb"
    assert position.segment.surface == "asphalt"
    assert position.next_segment.name == "Mill Descent"
    assert position.segment_remaining_m == 359
    assert position.to_dict()["route_progress"] > 0


def test_default_demo_route_returns_upcoming_points():
    """Route profiles expose coarse upcoming samples for previews."""
    route = default_demo_route()
    points = route.upcoming(400, 100)

    assert points[0].segment_name == "Valley Rollers"
    assert points[0].segment_kind == "warmup"
    assert any(point.segment_name == "Pine Rise" for point in points)
