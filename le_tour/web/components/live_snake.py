"""Live ride snake visualization component."""

from __future__ import annotations

from typing import Any

from nicegui import ui


def live_snake_panel(ftp_w: int) -> Any:
    """Render the calibrated live-screen snake surface.

    The browser module owns animation, watt smoothing, and snapshot streaming.
    Python keeps rendering the surrounding session chrome and secondary metrics.
    """
    with (
        ui.element("div")
        .classes("tr-snake-canvas is-warming")
        .props(
            f'data-le-tour-snake data-ftp="{int(ftp_w)}" '
            'data-snapshot-url="/api/ride/snapshots"'
        )
    ) as canvas:
        ui.html(
            """
            <svg class="tr-snake-svg" viewBox="0 0 1344 704"
                preserveAspectRatio="xMidYMid meet" role="presentation"
                aria-hidden="true"></svg>
            <div class="tr-snake-loader" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
                <span></span><span></span><span></span><span></span>
            </div>
            """,
            sanitize=False,
        )
        with ui.element("div").classes("tr-snake-watts-island"):
            with ui.element("div").classes("tr-snake-readout"):
                ui.html(
                    """
                    <div class="tr-snake-power-value" data-snake-watts>---</div>
                    <div class="tr-power-unit">Watts</div>
                    """,
                    sanitize=False,
                )
    return canvas


def load_live_snake_script() -> None:
    """Load and boot the browser-side live snake module."""
    ui.add_body_html("""
        <script type="module">
          import { bootLiveSnake } from "/static/live_snake.js?v=calibrated-2";
          bootLiveSnake();
        </script>
        """)
