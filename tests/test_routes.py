"""Tests for route profile domain models."""

from terminalride.domain.routes import default_demo_route


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
