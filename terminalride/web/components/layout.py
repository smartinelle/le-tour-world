"""Shared layout primitives for NiceGUI pages."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from terminalride.web.theme import WEB_STYLES

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    ("Home", "/"),
    ("Devices", "/devices"),
    ("Ride 3D", "/ride3d"),
    ("History", "/history"),
    ("Settings", "/settings"),
)


def apply_theme() -> None:
    """Inject the shared theme and NiceGUI color overrides."""
    ui.html(WEB_STYLES, sanitize=False)
    ui.colors(primary="#e85d04", secondary="#181b1f", accent="#e85d04")


def page_container(classes: str = "gap-5 fade-in") -> Any:
    """Return the standard page container."""
    return ui.column().classes(f"tr-shell tr-page {classes}".strip())


def render_page_title(kicker: str, title: str, subtitle: str) -> None:
    """Render the common page title block."""
    with ui.column().classes("gap-2"):
        ui.label(kicker).classes("tr-eyebrow")
        ui.label(title).classes("tr-title")
        ui.label(subtitle).classes("tr-subtitle")


def panel_header(title: str, detail: str, *, badge: str | None = None) -> None:
    """Render a compact panel heading with optional state badge."""
    with ui.element("div").classes("tr-panel-header"):
        with ui.column().classes("gap-1"):
            ui.label(title).classes("tr-panel-title")
            ui.label(detail).classes("tr-status-meta")
        if badge:
            ui.html(f'<span class="tr-state-badge">{badge}</span>', sanitize=False)


def render_app_header(
    current: str,
    *,
    user: dict[str, Any] | None = None,
    logout_path: str = "/logout",
) -> None:
    """Render the app header and optional authenticated user controls."""
    with ui.header().classes("tr-header px-0 py-3"):
        with ui.row().classes("tr-shell w-full items-center justify-between"):
            with ui.link("", "/").classes("tr-brand"):
                ui.html('<span class="tr-brand-mark">TR</span>', sanitize=False)
                ui.label("TerminalRide")

            with ui.row().classes("gap-3 items-center"):
                with ui.row().classes("gap-1"):
                    for name, path in NAV_ITEMS:
                        active = "active" if current == name else ""
                        ui.link(name, path).classes(f"nav-link {active}")

                if user:
                    with ui.row().classes(
                        "gap-2 items-center ml-2 pl-3 border-l border-gray-200"
                    ):
                        avatar_url = user.get("avatar_url", "")
                        if avatar_url:
                            ui.image(str(avatar_url)).classes(
                                "w-8 h-8 rounded-full object-cover"
                            )
                        else:
                            initial = str(user.get("name", "U"))[0].upper()
                            ui.element("div").classes(
                                "w-8 h-8 rounded-full bg-orange-100 text-orange-600 "
                                "flex items-center justify-center font-medium text-sm"
                            ).text(initial)

                        ui.label(str(user.get("name", "User"))).classes(
                            "text-sm font-semibold text-gray-600 hidden md:block"
                        )
                        ui.link("Logout", logout_path).classes(
                            "text-sm font-semibold text-gray-500 hover:text-orange-700 ml-2"
                        )
