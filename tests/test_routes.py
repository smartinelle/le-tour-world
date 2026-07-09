"""Tests for route profile domain models."""

import json

import pytest

from le_tour.domain.routes import (
    RouteSpecError,
    available_routes,
    available_route_specs,
    default_demo_route,
    load_route_spec,
    route_by_id,
    route_from_spec,
)


def test_default_demo_route_serializes_segments():
    """Default route is UI-neutral structured data."""
    route = default_demo_route()
    payload = route.to_dict()

    assert payload["id"] == "demo_rolling_route"
    assert payload["distance_m"] == 2080
    assert payload["elevation_gain_m"] == pytest.approx(38.96)
    assert payload["max_grade_pct"] == 5.6
    assert payload["difficulty"] == "Moderate"
    assert payload["segments"][0] == {
        "name": "Valley Rollers",
        "length_m": 420,
        "grade_pct": 0.4,
        "turn_deg": 18,
        "road_width_m": 8.8,
        "kind": "warmup",
        "surface": "asphalt",
        "scenery": "fields",
    }
    assert payload["start"]["segment"]["name"] == "Valley Rollers"
    assert payload["upcoming"][0]["segment_kind"] == "warmup"


def test_default_demo_route_is_loaded_from_bundled_spec():
    """Default route comes from the external route spec package asset."""
    assert available_route_specs() == (
        "demo_rolling_route.json",
        "forest_climb_loop.json",
    )

    route = default_demo_route()

    assert route.title == "Rolling Demo Route"
    assert route.segments[-1].surface == "gravel"


def test_bundled_routes_can_be_selected_by_route_id():
    """Route selection uses stable route ids rather than UI state."""
    routes = available_routes()

    assert [route.route_id for route in routes] == [
        "demo_rolling_route",
        "forest_climb_loop",
    ]
    assert route_by_id("forest_climb_loop").title == "Forest Climb Loop"
    assert route_by_id(None).route_id == "demo_rolling_route"


def test_route_by_id_rejects_unknown_routes():
    """Unknown browser route ids fail before runtime starts."""
    with pytest.raises(RouteSpecError, match="Unknown route id"):
        route_by_id("missing_route")


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
                        "turn_deg": 12,
                        "road_width_m": 8,
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
    assert route.position_at(50).heading_deg == 6


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
                        "turn_deg": 0,
                        "road_width_m": 8,
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
                        "turn_deg": 0,
                        "road_width_m": 8,
                        "kind": "rolling",
                        "surface": "snow",
                        "scenery": "fields",
                    }
                ],
            }
        )


def test_route_spec_rejects_impossible_turns():
    """Map geometry keeps turns within plausible renderable bounds."""
    with pytest.raises(RouteSpecError, match="turn_deg"):
        route_from_spec(
            {
                "schema_version": 1,
                "id": "bad_turn",
                "title": "Bad Turn",
                "description": "Invalid segment geometry.",
                "segments": [
                    {
                        "name": "Hairpin Spiral",
                        "length_m": 100,
                        "grade_pct": 0,
                        "turn_deg": 180,
                        "road_width_m": 8,
                        "kind": "rolling",
                        "surface": "asphalt",
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
    assert position.heading_deg < 18
    assert position.curve_strength < 0
    assert position.to_dict()["route_progress"] > 0


def test_default_demo_route_returns_upcoming_points():
    """Route profiles expose coarse upcoming samples for previews."""
    route = default_demo_route()
    points = route.upcoming(400, 100)

    assert points[0].segment_name == "Valley Rollers"
    assert points[0].segment_kind == "warmup"
    assert any(point.segment_name == "Pine Rise" for point in points)


def test_smoothed_grade_matches_segment_grade_away_from_boundaries():
    """Deep inside a segment the smoothed grade is the segment grade."""
    route = default_demo_route()

    assert route.smoothed_grade_at(200) == pytest.approx(0.4)
    assert route.smoothed_grade_at(600) == pytest.approx(3.2)


def test_smoothed_grade_ramps_across_segment_boundaries():
    """Boundaries blend between grades instead of stepping."""
    route = default_demo_route()

    # Valley Rollers (0.4%) ends at 420 m, Pine Rise (3.2%) begins.
    at_boundary = route.smoothed_grade_at(420)
    assert 0.4 < at_boundary < 3.2
    # Approaching from both sides moves monotonically through the blend.
    before = route.smoothed_grade_at(410)
    after = route.smoothed_grade_at(430)
    assert 0.4 <= before < at_boundary < after <= 3.2


def test_smoothed_grade_wraps_across_the_lap_seam():
    """The last segment blends into the first across the wrap."""
    route = default_demo_route()

    # River Run (-0.6%) wraps into Valley Rollers (0.4%).
    near_end = route.smoothed_grade_at(route.distance_m - 1)
    assert -0.6 < near_end < 0.4
    just_after_start = route.smoothed_grade_at(1)
    assert -0.6 < just_after_start < 0.4
