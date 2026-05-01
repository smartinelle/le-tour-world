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
        "scenery": "fields",
    }


def test_default_demo_route_supports_distance_lookup():
    """Route profiles expose grade and section lookup by distance."""
    route = default_demo_route()

    assert route.grade_at(0) == 0.4
    assert route.segment_at(421).name == "Pine Rise"
    assert route.grade_at(421) == 3.2
    assert route.segment_at(route.distance_m + 1).name == "Valley Rollers"


def test_default_demo_route_returns_upcoming_points():
    """Route profiles expose coarse upcoming samples for previews."""
    route = default_demo_route()
    points = route.upcoming(400, 100)

    assert points[0].segment_name == "Valley Rollers"
    assert any(point.segment_name == "Pine Rise" for point in points)
