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
    kind: str = "rolling"
    surface: str = "asphalt"
    scenery: str = "fields"

    def to_dict(self) -> dict[str, object]:
        """Serialize for browser and API clients."""
        return {
            "name": self.name,
            "length_m": self.length_m,
            "grade_pct": self.grade_pct,
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
        for index, segment in enumerate(self.segments):
            next_segment = self.segments[(index + 1) % len(self.segments)]
            if route_distance_m < segment.length_m:
                return RoutePosition(
                    distance_m=distance_m,
                    route_distance_m=distance_cursor_m,
                    route_progress=(
                        distance_cursor_m / self.distance_m if self.distance_m else 0.0
                    ),
                    segment=segment,
                    segment_progress=route_distance_m / segment.length_m,
                    segment_remaining_m=segment.length_m - route_distance_m,
                    next_segment=next_segment,
                )
            route_distance_m -= segment.length_m

        last_segment = self.segments[-1]
        return RoutePosition(
            distance_m=distance_m,
            route_distance_m=distance_cursor_m,
            route_progress=1.0,
            segment=last_segment,
            segment_progress=1.0,
            segment_remaining_m=0.0,
            next_segment=self.segments[0],
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
                kind="warmup",
                surface="asphalt",
                scenery="fields",
            ),
            RouteSegment(
                name="Pine Rise",
                length_m=360,
                grade_pct=3.2,
                kind="climb",
                surface="asphalt",
                scenery="forest",
            ),
            RouteSegment(
                name="Mill Descent",
                length_m=320,
                grade_pct=-2.1,
                kind="descent",
                surface="asphalt",
                scenery="village",
            ),
            RouteSegment(
                name="Ridge Steps",
                length_m=460,
                grade_pct=5.6,
                kind="climb",
                surface="asphalt",
                scenery="ridge",
            ),
            RouteSegment(
                name="River Run",
                length_m=520,
                grade_pct=-0.6,
                kind="recovery",
                surface="gravel",
                scenery="river",
            ),
        ),
    )


__all__ = [
    "RideRoute",
    "RoutePoint",
    "RoutePosition",
    "RouteProfile",
    "RouteSegment",
    "default_demo_route",
]
