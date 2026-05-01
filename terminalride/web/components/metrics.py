"""Shared ride metric components."""

from __future__ import annotations

from typing import Any

from nicegui import ui


def metric_cell(value: str, label: str) -> Any:
    """Render a fixed metric cell and return the value label."""
    with ui.element("div").classes("tr-metric-cell"):
        value_label = ui.label(value).classes("tr-metric-value")
        ui.label(label).classes("tr-metric-label")
    return value_label


def meta_stat(value: str, label: str) -> Any:
    """Render a compact stat used in setup and preview panels."""
    with ui.element("div").classes("tr-meta-row"):
        value_label = ui.label(value).classes("tr-meta-value")
        ui.label(label).classes("tr-meta-label")
    return value_label


def power_panel(initial_value: str = "---") -> Any:
    """Render primary power contents and return the power value label."""
    power_label = ui.label(initial_value).classes("tr-power-value")
    ui.label("Watts").classes("tr-power-unit")
    return power_label
