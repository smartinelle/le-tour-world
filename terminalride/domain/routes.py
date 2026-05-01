"""UI-neutral route profile models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Protocol

ROUTE_SPEC_VERSION = 1
DEFAULT_ROUTE_SPEC = "demo_rolling_route.json"
ALLOWED_SEGMENT_KINDS = frozenset({"warmup", "rolling", "climb", "descent", "recovery"})
ALLOWED_SURFACES = frozenset({"asphalt", "gravel", "dirt"})
ALLOWED_SCENERY = frozenset({"fields", "forest", "village", "ridge", "river"})


class RouteSpecError(ValueError):
    """Raised when a route spec cannot be converted into a route."""


@dataclass(frozen=True)
class RouteSegment:
    """A route section with constant grade and world metadata."""

    name: str
    length_m: float
    grade_pct: float
    turn_deg: float = 0.0
    road_width_m: float = 8.6
    kind: str = "rolling"
    surface: str = "asphalt"
    scenery: str = "fields"

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "name": self.name,
            "length_m": self.length_m,
            "grade_pct": self.grade_pct,
            "turn_deg": self.turn_deg,
            "road_width_m": self.road_width_m,
            "kind": self.kind,
            "surface": self.surface,
            "scenery": self.scenery,
        }


@dataclass(frozen=True)
class RoutePoint:
    """A distance-indexed grade sample."""

    distance_m: float
    grade_pct: float
    segment_name: str
    segment_kind: str = "rolling"

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "distance_m": self.distance_m,
            "grade_pct": self.grade_pct,
            "segment_name": self.segment_name,
            "segment_kind": self.segment_kind,
        }


@dataclass(frozen=True)
class RoutePosition:
    """Resolved route state at one rider distance."""

    distance_m: float
    route_distance_m: float
    route_progress: float
    segment: RouteSegment
    segment_progress: float
    segment_remaining_m: float
    next_segment: RouteSegment
    heading_deg: float
    curve_strength: float

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "distance_m": self.distance_m,
            "route_distance_m": self.route_distance_m,
            "route_progress": self.route_progress,
            "segment": self.segment.to_dict(),
            "segment_progress": self.segment_progress,
            "segment_remaining_m": self.segment_remaining_m,
            "next_segment": self.next_segment.to_dict(),
            "heading_deg": self.heading_deg,
            "curve_strength": self.curve_strength,
        }


@dataclass(frozen=True)
class RideRoute:
    """A deterministic route profile that can drive SIM and renderers."""

    route_id: str
    title: str
    description: str
    segments: tuple[RouteSegment, ...]

    @property
    def distance_m(self) -> float:
        """Total route length in meters."""
        return sum(segment.length_m for segment in self.segments)

    def segment_at(self, distance_m: float) -> RouteSegment:
        """Return the segment at a route-relative distance."""
        return self.position_at(distance_m).segment

    def position_at(self, distance_m: float) -> RoutePosition:
        """Return resolved route state at a route-relative distance."""
        if not self.segments:
            raise ValueError("Route has no segments")

        route_distance_m = distance_m % self.distance_m if self.distance_m else 0
        distance_cursor_m = route_distance_m
        heading_deg = 0.0
        for index, segment in enumerate(self.segments):
            next_segment = self.segments[(index + 1) % len(self.segments)]
            if route_distance_m < segment.length_m:
                segment_progress = route_distance_m / segment.length_m
                curve_strength = _clamp(segment.turn_deg / 60.0, -1.0, 1.0)
                return RoutePosition(
                    distance_m=distance_m,
                    route_distance_m=distance_cursor_m,
                    route_progress=(
                        distance_cursor_m / self.distance_m if self.distance_m else 0.0
                    ),
                    segment=segment,
                    segment_progress=segment_progress,
                    segment_remaining_m=segment.length_m - route_distance_m,
                    next_segment=next_segment,
                    heading_deg=heading_deg + segment.turn_deg * segment_progress,
                    curve_strength=curve_strength,
                )
            route_distance_m -= segment.length_m
            heading_deg += segment.turn_deg

        last_segment = self.segments[-1]
        return RoutePosition(
            distance_m=distance_m,
            route_distance_m=distance_cursor_m,
            route_progress=1.0,
            segment=last_segment,
            segment_progress=1.0,
            segment_remaining_m=0.0,
            next_segment=self.segments[0],
            heading_deg=heading_deg,
            curve_strength=0.0,
        )

    def grade_at(self, distance_m: float) -> float:
        """Return the grade at a route-relative distance."""
        return self.segment_at(distance_m).grade_pct

    def upcoming(self, distance_m: float, horizon_m: float) -> list[RoutePoint]:
        """Return coarse upcoming route points for a distance horizon."""
        if horizon_m <= 0:
            return []

        spacing_m = min(100.0, max(10.0, horizon_m / 8.0))
        points: list[RoutePoint] = []
        cursor_m = 0.0
        while cursor_m <= horizon_m:
            sample_distance_m = distance_m + cursor_m
            segment = self.segment_at(sample_distance_m)
            points.append(
                RoutePoint(
                    distance_m=sample_distance_m,
                    grade_pct=segment.grade_pct,
                    segment_name=segment.name,
                    segment_kind=segment.kind,
                )
            )
            cursor_m += spacing_m
        return points

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "id": self.route_id,
            "title": self.title,
            "description": self.description,
            "distance_m": self.distance_m,
            "segments": [segment.to_dict() for segment in self.segments],
            "start": self.position_at(0).to_dict() if self.segments else None,
            "upcoming": [
                point.to_dict() for point in self.upcoming(0, min(500, self.distance_m))
            ],
        }


class RouteProfile(Protocol):
    """Distance-indexed route interface for SIM and renderers."""

    def grade_at(self, distance_m: float) -> float:
        """Return current grade."""
        ...

    def upcoming(self, distance_m: float, horizon_m: float) -> list[RoutePoint]:
        """Return upcoming route samples."""
        ...

    def segment_at(self, distance_m: float) -> RouteSegment:
        """Return the active segment."""
        ...

    def position_at(self, distance_m: float) -> RoutePosition:
        """Return resolved route state."""
        ...


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _required_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RouteSpecError(f"Route spec field '{key}' must be a non-empty string")
    return value


def _number(data: dict[str, object], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RouteSpecError(f"Route spec field '{key}' must be a number")
    return value


def _optional_number(data: dict[str, object], key: str, default: float) -> float:
    if key not in data:
        return default
    return _number(data, key)


def _choice(data: dict[str, object], key: str, allowed: frozenset[str]) -> str:
    value = _required_string(data, key)
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise RouteSpecError(
            f"Route spec field '{key}' must be one of: {allowed_values}"
        )
    return value


def route_from_spec(data: dict[str, object]) -> RideRoute:
    """Build and validate a route from a JSON-compatible spec."""
    schema_version = data.get("schema_version", ROUTE_SPEC_VERSION)
    if schema_version != ROUTE_SPEC_VERSION:
        raise RouteSpecError(
            f"Unsupported route spec schema_version: {schema_version!r}"
        )

    segments_data = data.get("segments")
    if not isinstance(segments_data, list) or not segments_data:
        raise RouteSpecError("Route spec field 'segments' must be a non-empty list")

    segments: list[RouteSegment] = []
    for index, segment_data in enumerate(segments_data):
        if not isinstance(segment_data, dict):
            raise RouteSpecError(f"Route segment {index} must be an object")

        segment = RouteSegment(
            name=_required_string(segment_data, "name"),
            length_m=_number(segment_data, "length_m"),
            grade_pct=_number(segment_data, "grade_pct"),
            turn_deg=_optional_number(segment_data, "turn_deg", 0.0),
            road_width_m=_optional_number(segment_data, "road_width_m", 8.6),
            kind=_choice(segment_data, "kind", ALLOWED_SEGMENT_KINDS),
            surface=_choice(segment_data, "surface", ALLOWED_SURFACES),
            scenery=_choice(segment_data, "scenery", ALLOWED_SCENERY),
        )
        if segment.length_m <= 0:
            raise RouteSpecError(f"Route segment {index} length_m must be positive")
        if not -120 <= segment.turn_deg <= 120:
            raise RouteSpecError(
                f"Route segment {index} turn_deg must be between -120 and 120"
            )
        if not 4 <= segment.road_width_m <= 14:
            raise RouteSpecError(
                f"Route segment {index} road_width_m must be between 4 and 14"
            )
        segments.append(segment)

    return RideRoute(
        route_id=_required_string(data, "id"),
        title=_required_string(data, "title"),
        description=_required_string(data, "description"),
        segments=tuple(segments),
    )


def load_route_spec(path: Path | str) -> RideRoute:
    """Load a route spec from disk."""
    route_path = Path(path)
    try:
        with route_path.open(encoding="utf-8") as route_file:
            data = json.load(route_file)
    except OSError as exc:
        raise RouteSpecError(f"Could not read route spec: {route_path}") from exc
    except json.JSONDecodeError as exc:
        raise RouteSpecError(f"Route spec is not valid JSON: {route_path}") from exc

    if not isinstance(data, dict):
        raise RouteSpecError("Route spec root must be an object")
    return route_from_spec(data)


def load_bundled_route_spec(spec_name: str) -> RideRoute:
    """Load one packaged route spec by filename."""
    if spec_name not in available_route_specs():
        raise RouteSpecError(f"Unknown bundled route spec: {spec_name}")
    route_file = files("terminalride.assets.routes").joinpath(spec_name)
    return load_route_spec(str(route_file))


def available_route_specs() -> tuple[str, ...]:
    """Return bundled route spec names."""
    route_files = files("terminalride.assets.routes")
    return tuple(
        sorted(
            route_file.name
            for route_file in route_files.iterdir()
            if route_file.name.endswith(".json")
        )
    )


def available_routes() -> tuple[RideRoute, ...]:
    """Return all bundled route specs as domain routes."""
    return tuple(
        load_bundled_route_spec(spec_name) for spec_name in available_route_specs()
    )


def route_by_id(route_id: str | None) -> RideRoute:
    """Return a bundled route by route id."""
    if route_id is None or not route_id.strip():
        return default_demo_route()

    for route in available_routes():
        if route.route_id == route_id:
            return route
    raise RouteSpecError(f"Unknown route id: {route_id}")


def default_demo_route() -> RideRoute:
    """Return the built-in route used by local demos and the 3D prototype."""
    return load_bundled_route_spec(DEFAULT_ROUTE_SPEC)


__all__ = [
    "ALLOWED_SCENERY",
    "ALLOWED_SEGMENT_KINDS",
    "ALLOWED_SURFACES",
    "DEFAULT_ROUTE_SPEC",
    "RideRoute",
    "RoutePoint",
    "RoutePosition",
    "RouteProfile",
    "ROUTE_SPEC_VERSION",
    "RouteSpecError",
    "RouteSegment",
    "available_routes",
    "available_route_specs",
    "default_demo_route",
    "load_bundled_route_spec",
    "load_route_spec",
    "route_by_id",
    "route_from_spec",
]
