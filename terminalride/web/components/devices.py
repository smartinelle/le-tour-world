"""Shared device presentation components."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from .controls import action_button
from .status import status_dot


def device_row(
    title: str,
    detail: str,
    *,
    connected: bool,
    action_label: str,
    on_action: Callable[[], Any],
    action_variant: str = "primary",
    signal_bars: int | None = None,
    state_label: str | None = None,
) -> Any:
    """Render a hardware bay row."""
    with ui.element("div").classes("tr-device-row") as row:
        with ui.row().classes("items-center gap-3"):
            status_dot(connected)
            with ui.column().classes("gap-1"):
                ui.label(title).classes("tr-status-name")
                ui.label(detail).classes("tr-status-meta")
        with ui.element("div").classes("tr-device-meta"):
            badge_class = "ready" if connected else "demo"
            ui.html(
                f'<span class="tr-state-badge {badge_class}">'
                f"{state_label or ('Paired' if connected else 'Demo')}</span>",
                sanitize=False,
            )
            if signal_bars is not None:
                bars = max(0, min(4, signal_bars))
                bar_html = "".join(
                    f'<span class="{"active" if index <= bars else ""}"></span>'
                    for index in range(1, 5)
                )
                ui.html(
                    f'<span class="tr-signal-bars">{bar_html}</span>',
                    sanitize=False,
                )
        action_button(
            action_label,
            on_action,
            variant="primary" if action_variant == "primary" else "secondary",
            min_width="120px",
        )
    return row
