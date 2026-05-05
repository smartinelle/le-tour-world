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


def segmented_control(
    options: list[tuple[str, str, Callable[[], Any]]],
    *,
    active_key: str,
) -> dict[str, Any]:
    """Render a segmented control containing N inline options.

    `options` is a list of (key, label, on_click) tuples. Returns a dict
    mapping option key → button element so callers can toggle .active.
    """
    cols = len(options)
    buttons: dict[str, Any] = {}
    with ui.element("div").classes("tr-segmented").style(f"--seg-cols: {cols}"):
        for key, label, on_click in options:
            classes = "tr-seg active" if key == active_key else "tr-seg"
            buttons[key] = (
                ui.button(label, on_click=on_click, color=None)
                .classes(classes)
                .props("flat unelevated no-caps")
            )
    return buttons


def hero_button(text: str, on_click: Callable[[], Any]) -> Any:
    """Render the page's primary call-to-action — taller, fills its grid cell."""
    return ui.button(text, on_click=on_click, color=None).classes(
        "tr-btn-primary tr-btn-hero"
    )
