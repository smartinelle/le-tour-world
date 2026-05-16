"""UI-neutral activity graph data builders."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo
from typing import Literal, Sequence

from le_tour.store.models import SampleModel, SessionModel

ActivityGraphRange = Literal["7d", "30d", "all"]
ActivityGraphKind = Literal["bar", "line"]


@dataclass(frozen=True)
class ActivityGraphPoint:
    """One graph point in numeric chart coordinates."""

    x: float
    y: float
    label: str


@dataclass(frozen=True)
class ActivityGraphSeries:
    """One named graph series."""

    key: str
    label: str
    points: tuple[ActivityGraphPoint, ...]
    tone: Literal["primary", "secondary"] = "primary"


@dataclass(frozen=True)
class ActivityGraphReference:
    """Horizontal reference line, such as FTP or an ERG target."""

    label: str
    value: float


@dataclass(frozen=True)
class ActivityGraphStat:
    """Compact stat displayed alongside a graph."""

    label: str
    value: str


@dataclass(frozen=True)
class ActivityGraphData:
    """Presentation-ready graph data without any NiceGUI dependency."""

    title: str
    detail: str
    kind: ActivityGraphKind
    x_label: str
    y_label: str
    y_unit: str
    series: tuple[ActivityGraphSeries, ...]
    stats: tuple[ActivityGraphStat, ...] = field(default_factory=tuple)
    references: tuple[ActivityGraphReference, ...] = field(default_factory=tuple)
    empty_title: str = "No graph data"
    empty_detail: str = "Complete a ride to populate this graph."

    @property
    def has_points(self) -> bool:
        """Return true when any series has at least one point."""
        return any(series.points for series in self.series)


@dataclass(frozen=True)
class ActivityCalendarDay:
    """One day in a year-style activity calendar."""

    day: date
    activity_count: int
    total_distance_m: float
    total_duration_s: float
    label: str
    is_future: bool = False

    @property
    def is_active(self) -> bool:
        """Return true when at least one activity happened on this day."""
        return self.activity_count > 0 and not self.is_future


@dataclass(frozen=True)
class ActivityCalendarWeek:
    """One Monday-starting week in the activity calendar."""

    days: tuple[ActivityCalendarDay, ...]


@dataclass(frozen=True)
class ActivityCalendarData:
    """Presentation-ready 52-week activity calendar data."""

    title: str
    weeks: tuple[ActivityCalendarWeek, ...]


def normalize_graph_range(value: str | None) -> ActivityGraphRange:
    """Normalize user-facing range input for history graphs."""
    if value == "7d":
        return "7d"
    if value == "all":
        return "all"
    return "30d"


def build_history_distance_graph(
    sessions: Sequence[SessionModel],
    graph_range: ActivityGraphRange = "30d",
    *,
    today: date | None = None,
    local_tz: tzinfo | None = None,
) -> ActivityGraphData:
    """Build a day-bucketed history graph for distance over time."""
    local_tz = _resolve_local_timezone(local_tz)
    anchor_day = today or _local_today(local_tz)
    ordered_sessions = sorted(sessions, key=lambda session: session.start_time)
    filtered_sessions = _filter_sessions_by_range(
        ordered_sessions,
        graph_range,
        anchor_day=anchor_day,
        local_tz=local_tz,
    )
    buckets = _distance_buckets(
        filtered_sessions,
        graph_range,
        anchor_day=anchor_day,
        local_tz=local_tz,
    )

    points = tuple(
        ActivityGraphPoint(
            x=float(index),
            y=distance_m / 1000.0,
            label=_format_bucket_label(day, graph_range),
        )
        for index, (day, distance_m) in enumerate(buckets)
    )
    total_km = sum(point.y for point in points)
    active_days = sum(1 for point in points if point.y > 0)
    best_day_km = max((point.y for point in points), default=0.0)

    return ActivityGraphData(
        title="Distance",
        detail=_history_detail(graph_range),
        kind="bar",
        x_label="Date",
        y_label="Kilometers",
        y_unit="km",
        series=(
            ActivityGraphSeries(
                key="distance_km",
                label="Distance",
                points=points,
            ),
        ),
        stats=(
            ActivityGraphStat("Total", f"{total_km:.1f} km"),
            ActivityGraphStat("Active days", str(active_days)),
            ActivityGraphStat("Best day", f"{best_day_km:.1f} km"),
        ),
        empty_title="No rides in this range",
        empty_detail="Try another range or complete a ride.",
    )


def build_history_activity_calendar(
    sessions: Sequence[SessionModel],
    *,
    weeks: int = 52,
    today: date | None = None,
    local_tz: tzinfo | None = None,
) -> ActivityCalendarData:
    """Build a 7-row, week-column activity calendar from saved rides."""
    local_tz = _resolve_local_timezone(local_tz)
    anchor_day = today or _local_today(local_tz)
    week_count = max(1, weeks)
    current_week_start = anchor_day - timedelta(days=anchor_day.weekday())
    first_day = current_week_start - timedelta(weeks=week_count - 1)

    sessions_by_day: defaultdict[date, list[SessionModel]] = defaultdict(list)
    for session in sessions:
        session_day = _session_local_date(session, local_tz)
        if first_day <= session_day <= anchor_day:
            sessions_by_day[session_day].append(session)

    calendar_weeks: list[ActivityCalendarWeek] = []
    for week_index in range(week_count):
        week_start = first_day + timedelta(weeks=week_index)
        days = tuple(
            _activity_calendar_day(
                week_start + timedelta(days=day_offset),
                anchor_day=anchor_day,
                sessions_by_day=sessions_by_day,
            )
            for day_offset in range(7)
        )
        calendar_weeks.append(ActivityCalendarWeek(days=days))

    return ActivityCalendarData(title="Activity", weeks=tuple(calendar_weeks))


def build_session_power_graph(
    samples: Sequence[SampleModel],
    *,
    ftp_w: int | None = None,
) -> ActivityGraphData:
    """Build a power-over-time graph for a single session."""
    power_points = _sample_points(
        samples,
        value_getter=lambda sample: (
            float(sample.power_w) if sample.power_w is not None else None
        ),
    )
    target_points = _sample_points(
        samples,
        value_getter=lambda sample: (
            float(sample.erg_target_power_w)
            if sample.erg_target_power_w is not None
            else None
        ),
    )
    series: list[ActivityGraphSeries] = [
        ActivityGraphSeries("power_w", "Power", power_points)
    ]
    if target_points:
        series.append(
            ActivityGraphSeries(
                "erg_target_power_w",
                "ERG target",
                target_points,
                tone="secondary",
            )
        )

    values = [point.y for point in power_points]
    references = (
        (ActivityGraphReference("FTP", float(ftp_w)),)
        if ftp_w is not None and ftp_w > 0
        else ()
    )

    return ActivityGraphData(
        title="Power",
        detail="Watts across the ride.",
        kind="line",
        x_label="Time",
        y_label="Watts",
        y_unit="W",
        series=tuple(series),
        stats=_metric_stats(values, "W"),
        references=references,
        empty_title="No power samples",
        empty_detail="Power data will appear here after a recorded ride.",
    )


def build_session_hr_graph(samples: Sequence[SampleModel]) -> ActivityGraphData:
    """Build a heart-rate-over-time graph for a single session."""
    points = _sample_points(
        samples,
        value_getter=lambda sample: (
            float(sample.hr_bpm) if sample.hr_bpm is not None else None
        ),
    )
    return ActivityGraphData(
        title="Heart rate",
        detail="Heart rate response across the ride.",
        kind="line",
        x_label="Time",
        y_label="BPM",
        y_unit="bpm",
        series=(ActivityGraphSeries("hr_bpm", "Heart rate", points),),
        stats=_metric_stats([point.y for point in points], "bpm"),
        empty_title="No heart-rate samples",
        empty_detail="Connect a heart-rate monitor to record this graph.",
    )


def build_session_cadence_graph(samples: Sequence[SampleModel]) -> ActivityGraphData:
    """Build a cadence-over-time graph for a single session."""
    points = _sample_points(
        samples,
        value_getter=lambda sample: (
            float(sample.cadence_rpm) if sample.cadence_rpm is not None else None
        ),
    )
    return ActivityGraphData(
        title="Cadence",
        detail="Pedaling rhythm across the ride.",
        kind="line",
        x_label="Time",
        y_label="RPM",
        y_unit="rpm",
        series=(ActivityGraphSeries("cadence_rpm", "Cadence", points),),
        stats=_metric_stats([point.y for point in points], "rpm"),
        empty_title="No cadence samples",
        empty_detail="Cadence data will appear when the trainer reports it.",
    )


def build_session_speed_graph(samples: Sequence[SampleModel]) -> ActivityGraphData:
    """Build a speed-over-time graph for a single session."""
    points = _sample_points(
        samples,
        value_getter=lambda sample: (
            sample.speed_mps * 3.6 if sample.speed_mps is not None else None
        ),
    )
    return ActivityGraphData(
        title="Speed",
        detail="Speed across the ride.",
        kind="line",
        x_label="Time",
        y_label="Speed",
        y_unit="km/h",
        series=(ActivityGraphSeries("speed_kph", "Speed", points),),
        stats=_metric_stats([point.y for point in points], "km/h"),
        empty_title="No speed samples",
        empty_detail="Speed data will appear when the trainer reports it.",
    )


def _filter_sessions_by_range(
    sessions: Sequence[SessionModel],
    graph_range: ActivityGraphRange,
    *,
    anchor_day: date,
    local_tz: tzinfo | None,
) -> list[SessionModel]:
    if graph_range == "all" or not sessions:
        return list(sessions)

    days = 7 if graph_range == "7d" else 30
    start_day = anchor_day - timedelta(days=days - 1)
    return [
        session
        for session in sessions
        if start_day <= _session_local_date(session, local_tz) <= anchor_day
    ]


def _distance_buckets(
    sessions: Sequence[SessionModel],
    graph_range: ActivityGraphRange,
    *,
    anchor_day: date,
    local_tz: tzinfo | None,
) -> list[tuple[date, float]]:
    if not sessions:
        return []

    distances_by_day: defaultdict[date, float] = defaultdict(float)
    for session in sessions:
        distances_by_day[_session_local_date(session, local_tz)] += (
            session.total_distance_m or 0.0
        )

    first_day = min(distances_by_day)
    last_day = max(max(distances_by_day), anchor_day)

    if graph_range in {"7d", "30d"}:
        days = 7 if graph_range == "7d" else 30
        first_day = anchor_day - timedelta(days=days - 1)
        last_day = anchor_day

    bucket_count = (last_day - first_day).days + 1
    return [
        (
            first_day + timedelta(days=offset),
            distances_by_day[first_day + timedelta(days=offset)],
        )
        for offset in range(bucket_count)
    ]


def _format_bucket_label(day: date, graph_range: ActivityGraphRange) -> str:
    return day.strftime("%d.%m")


def _history_detail(graph_range: ActivityGraphRange) -> str:
    if graph_range == "7d":
        return "Distance by day for the last 7 days."
    if graph_range == "30d":
        return "Distance by day for the last 30 days."
    return "Distance by day since your first saved ride through today."


def _activity_calendar_day(
    day: date,
    *,
    anchor_day: date,
    sessions_by_day: dict[date, list[SessionModel]],
) -> ActivityCalendarDay:
    is_future = day > anchor_day
    sessions = [] if is_future else sessions_by_day.get(day, [])
    activity_count = len(sessions)
    total_distance_m = sum(session.total_distance_m or 0.0 for session in sessions)
    total_duration_s = sum(session.duration_s or 0.0 for session in sessions)
    return ActivityCalendarDay(
        day=day,
        activity_count=activity_count,
        total_distance_m=total_distance_m,
        total_duration_s=total_duration_s,
        label=_activity_calendar_label(
            day,
            activity_count,
            total_distance_m,
            total_duration_s,
            is_future,
        ),
        is_future=is_future,
    )


def _activity_calendar_label(
    day: date,
    activity_count: int,
    total_distance_m: float,
    total_duration_s: float,
    is_future: bool,
) -> str:
    date_label = day.strftime("%A, %d %b %Y")
    if is_future:
        return f"{date_label}: upcoming"
    if activity_count == 0:
        return f"{date_label}: no rides"

    ride_label = "1 ride" if activity_count == 1 else f"{activity_count} rides"
    distance_label = _format_activity_distance(total_distance_m)
    duration_label = _format_activity_duration(total_duration_s)
    return f"{date_label}: {ride_label} · {distance_label} · {duration_label}"


def _format_activity_distance(distance_m: float) -> str:
    return f"{distance_m / 1000.0:.1f} km"


def _format_activity_duration(duration_s: float) -> str:
    total_seconds = int(duration_s)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours} h {minutes:02d} min"
    return f"{minutes} min"


def _resolve_local_timezone(local_tz: tzinfo | None) -> tzinfo | None:
    if local_tz is not None:
        return local_tz
    return datetime.now().astimezone().tzinfo


def _local_today(local_tz: tzinfo | None) -> date:
    if local_tz is None:
        return datetime.now().astimezone().date()
    return datetime.now(local_tz).date()


def _session_local_date(session: SessionModel, local_tz: tzinfo | None) -> date:
    start_time = session.start_time
    if start_time.tzinfo is None or start_time.utcoffset() is None:
        return start_time.date()
    if local_tz is None:
        return start_time.astimezone().date()
    return start_time.astimezone(local_tz).date()


def _sample_points(
    samples: Sequence[SampleModel],
    *,
    value_getter: Callable[[SampleModel], float | None],
    max_points: int = 240,
) -> tuple[ActivityGraphPoint, ...]:
    points: list[ActivityGraphPoint] = []
    for sample in samples:
        value = value_getter(sample)
        if value is None:
            continue
        minutes = sample.elapsed_s / 60.0
        points.append(
            ActivityGraphPoint(
                x=minutes,
                y=float(value),
                label=_format_elapsed(minutes),
            )
        )

    return tuple(_downsample(points, max_points=max_points))


def _downsample(
    points: Sequence[ActivityGraphPoint],
    *,
    max_points: int,
) -> list[ActivityGraphPoint]:
    if len(points) <= max_points:
        return list(points)

    step = max(1, len(points) // max_points)
    sampled = [point for index, point in enumerate(points) if index % step == 0]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled


def _format_elapsed(minutes: float) -> str:
    if minutes < 1:
        return "0m"
    return f"{minutes:.0f}m"


def _metric_stats(values: Sequence[float], unit: str) -> tuple[ActivityGraphStat, ...]:
    if not values:
        return ()

    average = sum(values) / len(values)
    peak = max(values)
    return (
        ActivityGraphStat("Avg", _format_metric_value(average, unit)),
        ActivityGraphStat("Max", _format_metric_value(peak, unit)),
    )


def _format_metric_value(value: float, unit: str) -> str:
    if unit == "km/h":
        return f"{value:.1f} {unit}"
    return f"{value:.0f} {unit}"
