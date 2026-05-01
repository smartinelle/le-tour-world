"""UI-neutral route profile models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RouteSegment:
    """A route section with constant grade and world metadata."""

    name: str
    length_m: float
    grade_pct: float
    scenery: str = "fields"

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "name": self.name,
            "length_m": self.length_m,
            "grade_pct": self.grade_pct,
            "scenery": self.scenery,
        }


@dataclass(frozen=True)
class RoutePoint:
    """A distance-indexed grade sample."""

    distance_m: float
    grade_pct: float
    segment_name: str

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "distance_m": self.distance_m,
            "grade_pct": self.grade_pct,
            "segment_name": self.segment_name,
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
        if not self.segments:
            raise ValueError("Route has no segments")

        route_distance_m = distance_m % self.distance_m if self.distance_m else 0
        for segment in self.segments:
            if route_distance_m < segment.length_m:
                return segment
            route_distance_m -= segment.length_m
        return self.segments[-1]

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


def default_demo_route() -> RideRoute:
    """Return the built-in route used by local demos and the 3D prototype."""
    return RideRoute(
        route_id="demo_rolling_route",
        title="Rolling Demo Route",
        description="A compact loop with rolling terrain, one climb, and varied scenery.",
        segments=(
            RouteSegment(
                name="Valley Rollers",
                length_m=420,
                grade_pct=0.4,
                scenery="fields",
            ),
            RouteSegment(
                name="Pine Rise",
                length_m=360,
                grade_pct=3.2,
                scenery="forest",
            ),
            RouteSegment(
                name="Mill Descent",
                length_m=320,
                grade_pct=-2.1,
                scenery="village",
            ),
            RouteSegment(
                name="Ridge Steps",
                length_m=460,
                grade_pct=5.6,
                scenery="ridge",
            ),
            RouteSegment(
                name="River Run",
                length_m=520,
                grade_pct=-0.6,
                scenery="river",
            ),
        ),
    )


__all__ = [
    "RideRoute",
    "RoutePoint",
    "RouteProfile",
    "RouteSegment",
    "default_demo_route",
]
