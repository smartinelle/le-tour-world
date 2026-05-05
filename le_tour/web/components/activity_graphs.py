"""Activity graph components for NiceGUI pages."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from math import ceil
from collections.abc import Callable
from typing import Sequence

from nicegui import ui

from le_tour.analytics.activity_graphs import (
    ActivityGraphData,
    ActivityGraphPoint,
    ActivityGraphSeries,
)


@dataclass(frozen=True)
class GraphControl:
    """One small graph control link."""

    label: str
    href: str
    active: bool = False


def activity_graph(
    graph: ActivityGraphData,
    *,
    controls: Sequence[GraphControl] = (),
    collapsible: bool = False,
    initially_open: bool = False,
) -> None:
    """Render an activity graph panel."""
    if collapsible:
        details = ui.element("details").classes(
            "tr-activity-graph tr-activity-graph-collapsible tr-panel"
        )
        if initially_open:
            details.props("open")
        with details:
            with ui.element("summary").classes("tr-activity-graph-summary"):
                with ui.column().classes("gap-1"):
                    ui.label(graph.title).classes("tr-panel-title")
                    ui.label(graph.detail).classes("tr-status-meta")
                ui.icon("expand_more").classes("tr-activity-graph-summary-icon")
            _render_graph_body(graph, controls)
        return

    with ui.element("section").classes("tr-activity-graph tr-panel"):
        _render_graph_header(graph, controls)
        _render_graph_body(graph, controls=())


def _render_graph_header(
    graph: ActivityGraphData,
    controls: Sequence[GraphControl],
) -> None:
    with ui.element("div").classes("tr-activity-graph-header"):
        with ui.column().classes("gap-1"):
            ui.label(graph.title).classes("tr-panel-title")
            ui.label(graph.detail).classes("tr-status-meta")
        if controls:
            with ui.element("nav").classes("tr-activity-graph-controls"):
                for control in controls:
                    active = "active" if control.active else ""
                    ui.link(control.label, control.href).classes(
                        f"tr-activity-graph-control {active}".strip()
                    )


def _render_graph_body(
    graph: ActivityGraphData,
    controls: Sequence[GraphControl],
) -> None:
    if controls:
        with ui.element("nav").classes("tr-activity-graph-controls"):
            for control in controls:
                active = "active" if control.active else ""
                ui.link(control.label, control.href).classes(
                    f"tr-activity-graph-control {active}".strip()
                )

    if not graph.has_points:
        with ui.element("div").classes("tr-activity-graph-empty"):
            ui.label(graph.empty_title).classes("tr-panel-title")
            ui.label(graph.empty_detail).classes("tr-status-meta")
        return

    ui.html(_render_svg(graph), sanitize=False)


def _render_svg(graph: ActivityGraphData) -> str:
    width = 960.0
    height = 320.0
    margin_left = 58.0
    margin_right = 28.0
    margin_top = 24.0
    margin_bottom = 50.0
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    points = [point for series in graph.series for point in series.points]
    references = [reference.value for reference in graph.references]

    x_min = min((point.x for point in points), default=0.0)
    x_max = max((point.x for point in points), default=1.0)
    if graph.kind == "bar":
        x_min -= 0.5
        x_max += 0.5
    y_values = [point.y for point in points] + references + [0.0]
    y_min = 0.0 if graph.kind == "bar" else min(y_values, default=0.0)
    y_max = max(y_values, default=1.0)
    if y_max == y_min:
        y_max += 1.0
    y_pad = (y_max - y_min) * 0.08
    y_min = max(0.0, y_min - y_pad)
    y_max += y_pad

    def map_x(value: float) -> float:
        if x_max == x_min:
            return margin_left + plot_width / 2.0
        return margin_left + ((value - x_min) / (x_max - x_min)) * plot_width

    def map_y(value: float) -> float:
        return margin_top + (1.0 - ((value - y_min) / (y_max - y_min))) * plot_height

    y_ticks = _nice_ticks(y_min, y_max)
    x_ticks = _x_ticks(graph.series[0].points if graph.series else ())
    chunks: list[str] = [
        '<div class="tr-activity-graph-viewport">',
        '<svg class="tr-activity-graph-svg" viewBox="0 0 960 320" '
        'role="img" aria-label="'
        f'{escape(graph.title)} graph">',
        '<g class="tr-activity-graph-grid">',
    ]

    for tick in y_ticks:
        y = map_y(tick)
        chunks.append(
            f'<line x1="{margin_left:.1f}" y1="{y:.1f}" '
            f'x2="{(width - margin_right):.1f}" y2="{y:.1f}" />'
        )
        chunks.append(
            f'<text x="{(margin_left - 12):.1f}" y="{(y + 4):.1f}" '
            f'text-anchor="end">{escape(_format_axis_value(tick, graph.y_unit))}</text>'
        )

    chunks.append("</g>")
    chunks.append('<g class="tr-activity-graph-axis">')
    chunks.append(
        f'<line x1="{margin_left:.1f}" y1="{(height - margin_bottom):.1f}" '
        f'x2="{(width - margin_right):.1f}" y2="{(height - margin_bottom):.1f}" />'
    )
    for point in x_ticks:
        x = map_x(point.x)
        chunks.append(
            f'<text x="{x:.1f}" y="{(height - 18):.1f}" '
            f'text-anchor="middle">{escape(point.label)}</text>'
        )
    chunks.append("</g>")

    for reference in graph.references:
        y = map_y(reference.value)
        chunks.append('<g class="tr-activity-graph-reference">')
        chunks.append(
            f'<line x1="{margin_left:.1f}" y1="{y:.1f}" '
            f'x2="{(width - margin_right):.1f}" y2="{y:.1f}" />'
        )
        chunks.append(
            f'<text x="{(width - margin_right):.1f}" y="{(y - 7):.1f}" '
            f'text-anchor="end">{escape(reference.label)}</text>'
        )
        chunks.append("</g>")

    for series in graph.series:
        if not series.points:
            continue
        chunks.append(_render_series(series, graph.kind, map_x, map_y, plot_width))

    chunks.append(_render_legend(graph.series, margin_left, height - 4.0))
    chunks.append("</svg></div>")
    return "".join(chunks)


def _render_series(
    series: ActivityGraphSeries,
    kind: str,
    map_x: Callable[[float], float],
    map_y: Callable[[float], float],
    plot_width: float,
) -> str:
    tone = "secondary" if series.tone == "secondary" else "primary"
    if kind == "bar":
        bar_count = max(1, len(series.points))
        bar_width = max(
            5.0,
            min(34.0, (plot_width / (bar_count + 1)) * 0.62),
        )
        bars = []
        base_y = map_y(0.0)
        for point in series.points:
            x = map_x(point.x)
            y = map_y(point.y)
            height = max(1.0, base_y - y)
            bar = (
                f'<rect class="tr-activity-graph-bar {tone}" '
                f'x="{(x - bar_width / 2):.1f}" y="{y:.1f}" '
                f'width="{bar_width:.1f}" height="{height:.1f}" rx="3" />'
            )
            if tone == "primary":
                bars.append(
                    '<g class="tr-activity-graph-hover">'
                    f"{bar}"
                    f'<rect class="tr-activity-graph-hit" '
                    f'x="{(x - bar_width / 2 - 4):.1f}" y="{y:.1f}" '
                    f'width="{(bar_width + 8):.1f}" height="{height:.1f}" />'
                    f"{_render_tooltip(x, y, point, series)}"
                    "</g>"
                )
            else:
                bars.append(bar)
        return "".join(bars)

    path = " ".join(
        f'{"M" if index == 0 else "L"} ' f"{map_x(point.x):.1f} {map_y(point.y):.1f}"
        for index, point in enumerate(series.points)
    )
    marker_radius = 2.6 if tone == "secondary" else 3.0
    markers = "".join(
        f'<circle class="tr-activity-graph-point {tone}" '
        f'cx="{map_x(point.x):.1f}" cy="{map_y(point.y):.1f}" '
        f'r="{marker_radius:.1f}" />'
        for point in _marker_points(series.points)
    )
    hover_points = ""
    if tone == "primary":
        hover_points = "".join(
            '<g class="tr-activity-graph-hover">'
            f'<circle class="tr-activity-graph-hit" '
            f'cx="{map_x(point.x):.1f}" cy="{map_y(point.y):.1f}" r="8" />'
            f"{_render_tooltip(map_x(point.x), map_y(point.y), point, series)}"
            "</g>"
            for point in series.points
        )
    return (
        f'<path class="tr-activity-graph-line {tone}" d="{path}" />'
        f"{markers}"
        f"{hover_points}"
    )


def _render_tooltip(
    x: float,
    y: float,
    point: ActivityGraphPoint,
    series: ActivityGraphSeries,
) -> str:
    label = escape(point.label)
    value = escape(_format_tooltip_value(point.y, series))
    tooltip_x = min(858.0, max(64.0, x - 48.0))
    tooltip_y = max(22.0, y - 42.0)
    return (
        '<g class="tr-activity-graph-tooltip">'
        f'<rect x="{tooltip_x:.1f}" y="{tooltip_y:.1f}" '
        'width="96" height="34" rx="8" />'
        f'<text x="{(tooltip_x + 10):.1f}" y="{(tooltip_y + 13):.1f}">'
        f"{label}</text>"
        f'<text x="{(tooltip_x + 10):.1f}" y="{(tooltip_y + 27):.1f}" '
        'class="value">'
        f"{value}</text>"
        "</g>"
    )


def _render_legend(
    series: Sequence[ActivityGraphSeries],
    x: float,
    y: float,
) -> str:
    visible_series = [item for item in series if item.points]
    if not visible_series:
        return ""

    chunks = ['<g class="tr-activity-graph-legend">']
    cursor = x
    for item in visible_series:
        tone = "secondary" if item.tone == "secondary" else "primary"
        chunks.append(f'<circle class="{tone}" cx="{cursor:.1f}" cy="{y:.1f}" r="4" />')
        chunks.append(
            f'<text x="{(cursor + 10):.1f}" y="{(y + 4):.1f}">'
            f"{escape(item.label)}</text>"
        )
        cursor += 112.0
    chunks.append("</g>")
    return "".join(chunks)


def _x_ticks(points: Sequence[ActivityGraphPoint]) -> tuple[ActivityGraphPoint, ...]:
    if len(points) <= 5:
        return tuple(points)

    step = max(1, ceil(len(points) / 5))
    ticks = [point for index, point in enumerate(points) if index % step == 0]
    if ticks[-1] != points[-1]:
        ticks.append(points[-1])
    return tuple(ticks)


def _nice_ticks(min_value: float, max_value: float) -> tuple[float, ...]:
    span = max_value - min_value
    if span <= 0:
        return (min_value,)

    raw_step = span / 4.0
    magnitude = 10 ** max(0, len(str(int(raw_step))) - 1)
    step = max(1.0, round(raw_step / magnitude) * magnitude)
    start = 0.0 if min_value >= 0 else min_value
    return tuple(start + index * step for index in range(5))


def _marker_points(
    points: Sequence[ActivityGraphPoint],
) -> tuple[ActivityGraphPoint, ...]:
    if len(points) <= 12:
        return tuple(points)
    return (points[0], points[-1])


def _format_axis_value(value: float, unit: str) -> str:
    if unit == "km/h":
        return f"{value:.1f}"
    return f"{value:.0f}"


def _format_tooltip_value(value: float, series: ActivityGraphSeries) -> str:
    if series.key == "distance_km":
        return f"{value:.2f} km"
    if series.key == "speed_kph":
        return f"{value:.1f} km/h"
    if series.key == "hr_bpm":
        return f"{value:.0f} bpm"
    if series.key == "cadence_rpm":
        return f"{value:.0f} rpm"
    return f"{value:.0f} W"
