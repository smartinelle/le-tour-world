"""Shared status and empty-state components."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from .controls import action_button


def status_dot(connected: bool) -> Any:
    """Render a connected/disconnected status dot."""
    dot_class = "connected" if connected else "disconnected"
    return ui.html(f'<span class="status-dot {dot_class}"></span>', sanitize=False)


def status_tile(title: str, detail: str, *, connected: bool) -> dict[str, Any]:
    """Render a compact readiness tile."""
    with ui.element("div").classes("tr-status-tile") as tile:
        dot = status_dot(connected)
        with ui.column().classes("gap-1"):
            ui.label(title).classes("tr-status-name")
            detail_label = ui.label(detail).classes("tr-status-meta")
    return {"tile": tile, "dot": dot, "detail": detail_label}


def empty_state(
    title: str,
    detail: str,
    *,
    action_label: str | None = None,
    on_action: Callable[[], Any] | None = None,
    action_variant: str = "secondary",
) -> Any:
    """Render an honest empty state with an optional action."""
    with ui.element("div").classes("tr-empty") as element:
        with ui.column().classes("gap-1"):
            ui.label(title).classes("tr-cell-strong")
            ui.label(detail).classes("tr-cell-soft")
        if action_label and on_action:
            action_button(
                action_label,
                on_action,
                variant="primary" if action_variant == "primary" else "secondary",
            )
    return element
