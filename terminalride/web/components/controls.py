"""Shared action controls for NiceGUI pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from nicegui import ui

ButtonVariant = Literal["primary", "secondary"]


def action_button(
    text: str,
    on_click: Callable[[], Any],
    *,
    variant: ButtonVariant = "secondary",
    classes: str = "",
    min_width: str | None = None,
) -> Any:
    """Render a themed action button."""
    button_class = "tr-btn-primary" if variant == "primary" else "tr-btn-secondary"
    button = ui.button(text, on_click=on_click, color=None).classes(
        f"{button_class} {classes}".strip()
    )
    if min_width:
        button.style(f"min-width: {min_width}")
    return button


def mode_button(
    text: str,
    on_click: Callable[[], Any],
    *,
    active: bool = False,
) -> Any:
    """Render a segmented ride-mode button."""
    classes = "tr-mode-button active" if active else "tr-mode-button"
    return ui.button(text, on_click=on_click, color=None).classes(classes)
