"""Shared layout primitives for NiceGUI pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from le_tour.web.theme import WEB_STYLES

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    ("Ride", "/"),
    ("History", "/history"),
    ("Settings", "/settings"),
)


def apply_theme() -> None:
    """Inject the shared theme and NiceGUI color overrides."""
    ui.html(WEB_STYLES, sanitize=False)
    ui.colors(primary="#f43e01", secondary="#2d2f33", accent="#f43e01")


def page_container(classes: str = "gap-5 fade-in") -> Any:
    """Return the standard page container."""
    return ui.column().classes(f"tr-shell tr-page {classes}".strip())


def render_page_title(kicker: str, title: str, subtitle: str) -> None:
    """Render the common page title block."""
    with ui.column().classes("gap-2"):
        ui.label(kicker).classes("tr-eyebrow")
        ui.label(title).classes("tr-title")
        ui.label(subtitle).classes("tr-subtitle")


def panel_header(
    title: str,
    detail: str,
    *,
    badge: str | None = None,
    action: tuple[str, str | Callable[[], Any]] | None = None,
) -> None:
    """Render a compact panel heading.

    `badge` is used only for stateful indicators (Ready/Demo, Saved/Review).
    `action` is a (label, href_or_callback) tuple for a right-aligned
    navigation/action affordance. Pass at most one of badge/action.
    """
    with ui.element("div").classes("tr-panel-header"):
        with ui.column().classes("gap-1"):
            ui.label(title).classes("tr-panel-title")
            ui.label(detail).classes("tr-status-meta")
        if badge:
            ui.html(f'<span class="tr-state-badge">{badge}</span>', sanitize=False)
        elif action:
            label, target = action
            if callable(target):
                with (
                    ui.element("button")
                    .props("type=button")
                    .classes("tr-panel-action tr-panel-action-button")
                    .on("click", target)
                ):
                    ui.label(label)
            else:
                ui.link(label, target).classes("tr-panel-action")


def render_app_header(
    current: str,
    *,
    user: dict[str, Any] | None = None,
    logout_path: str = "/logout",
    statuses: tuple[tuple[str, bool], ...] = (),
) -> None:
    """Render the app header and optional authenticated user controls.

    `statuses` is a tuple of (label, connected) pairs rendered as pill chips
    next to the nav. Pass an empty tuple on pages that don't surface device
    state (e.g. settings sub-pages).
    """
    with ui.header().classes("tr-header px-0 py-3"):
        with ui.row().classes("tr-shell w-full items-center justify-between"):
            with ui.link("", "/").classes("tr-brand"):
                ui.html('<span class="tr-brand-mark">LT</span>', sanitize=False)
                ui.label("le-tour")

            with ui.row().classes("gap-3 items-center"):
                with ui.row().classes("gap-1"):
                    for name, path in NAV_ITEMS:
                        active = "active" if current == name else ""
                        ui.link(name, path).classes(f"nav-link {active}")

                for label, connected in statuses:
                    dot_class = "connected" if connected else "disconnected"
                    ui.html(
                        f'<span class="tr-header-status">'
                        f'<span class="status-dot {dot_class}"></span>'
                        f"{label}</span>",
                        sanitize=False,
                    )

                if user:
                    with ui.row().classes("tr-user-cluster"):
                        avatar_url = user.get("avatar_url", "")
                        if avatar_url:
                            ui.image(str(avatar_url)).classes("tr-avatar-img")
                        else:
                            initial = str(user.get("name", "U"))[0].upper()
                            ui.element("div").classes("tr-avatar").text(initial)

                        ui.label(str(user.get("name", "User"))).classes(
                            "tr-user-name hidden md:block"
                        )
                        ui.link("Logout", logout_path).classes("tr-logout-link")
