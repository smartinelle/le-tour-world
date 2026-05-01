"""Minimal Three.js ride prototype."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException, Request
from starlette.responses import FileResponse, HTMLResponse

from terminalride.domain.ride_runtime import RideRuntime
from terminalride.domain.state import RideMode


class RouteApp(Protocol):
    """Minimal route registration surface used by FastAPI/NiceGUI app."""

    def get(
        self, path: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Register a GET route."""
        ...

    def post(
        self, path: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Register a POST route."""
        ...


STATIC_DIR = Path(__file__).parent / "static"


RIDE3D_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TerminalRide 3D</title>
  <style>
    :root {
      --bg: #101412;
      --panel: rgba(250, 250, 250, 0.9);
      --text: #111827;
      --muted: #6b7280;
      --accent: #ea580c;
      --road: #202421;
      --line: #f8fafc;
      --sky: #d9edf7;
      --field: #8fae76;
    }

    * {
      box-sizing: border-box;
    }

    [hidden] {
      display: none !important;
    }

    html,
    body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }

    #scene {
      position: fixed;
      inset: 0;
    }

    .hud {
      position: fixed;
      top: 18px;
      left: 18px;
      right: 18px;
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      pointer-events: none;
    }

    .metric,
    .status {
      min-width: 0;
      border: 1px solid rgba(17, 24, 39, 0.12);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.16);
      padding: 12px 14px;
      backdrop-filter: blur(16px);
    }

    .metric strong {
      display: block;
      color: var(--text);
      font-size: clamp(1.35rem, 3vw, 2.6rem);
      line-height: 1;
      font-weight: 650;
      letter-spacing: 0;
      white-space: nowrap;
    }

    .metric span,
    .status span {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.74rem;
      line-height: 1;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .status {
      position: fixed;
      right: 18px;
      bottom: 18px;
      width: min(360px, calc(100vw - 36px));
      pointer-events: auto;
    }

    .status strong {
      display: block;
      font-size: 0.95rem;
      line-height: 1.35;
      font-weight: 650;
    }

    .status a {
      color: var(--accent);
      font-weight: 650;
      text-decoration: none;
    }

    .start-panel {
      position: fixed;
      left: 18px;
      top: 50%;
      width: min(360px, calc(100vw - 36px));
      transform: translateY(-50%);
      border: 1px solid rgba(17, 24, 39, 0.12);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.16);
      padding: 14px;
      backdrop-filter: blur(16px);
    }

    .start-panel strong {
      display: block;
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.25;
    }

    .start-panel p {
      margin: 7px 0 12px;
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.4;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .action {
      border: 1px solid rgba(17, 24, 39, 0.12);
      border-radius: 8px;
      background: #ffffff;
      color: var(--text);
      cursor: pointer;
      padding: 10px 12px;
      font-size: 0.86rem;
      font-weight: 700;
    }

    .action.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }

    .action:disabled {
      cursor: wait;
      opacity: 0.64;
    }

    .active-controls {
      margin-top: 12px;
    }

    .mode-controls {
      margin-top: 8px;
    }

    .control-value {
      align-items: center;
      color: var(--muted);
      display: inline-flex;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      min-height: 38px;
      text-transform: uppercase;
    }

    .back {
      position: fixed;
      left: 18px;
      bottom: 18px;
      border: 1px solid rgba(17, 24, 39, 0.12);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      padding: 10px 12px;
      font-size: 0.9rem;
      font-weight: 650;
      text-decoration: none;
      backdrop-filter: blur(16px);
    }

    @media (max-width: 760px) {
      .hud {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .metric {
        padding: 10px 11px;
      }

      .status {
        left: 18px;
        right: 18px;
        bottom: 18px;
        width: auto;
      }

      .back {
        bottom: 164px;
      }
    }
  </style>
</head>
<body>
  <canvas id="scene" aria-label="3D road scene"></canvas>

  <section class="hud" aria-label="Ride metrics">
    <div class="metric"><strong id="power">--</strong><span>Watts</span></div>
    <div class="metric"><strong id="speed">--</strong><span>km/h</span></div>
    <div class="metric"><strong id="cadence">--</strong><span>RPM</span></div>
    <div class="metric"><strong id="heart-rate">--</strong><span>BPM</span></div>
    <div class="metric"><strong id="distance">--</strong><span>Distance</span></div>
  </section>

  <section class="status" aria-live="polite">
    <strong id="state">Waiting for ride data</strong>
    <span id="mode">Snapshot stream</span>
    <div id="active-controls" class="active-controls actions" hidden>
      <button id="pause-ride" class="action">Pause</button>
      <button id="stop-ride" class="action">Stop Ride</button>
    </div>
    <div id="erg-controls" class="mode-controls actions" hidden>
      <button class="action" data-erg-delta="-10">-10W</button>
      <span id="erg-target" class="control-value">Target --</span>
      <button class="action" data-erg-delta="10">+10W</button>
    </div>
    <div id="sim-controls" class="mode-controls actions" hidden>
      <button class="action" data-sim-delta="-0.5">-0.5%</button>
      <span id="sim-grade" class="control-value">Grade --</span>
      <button class="action" data-sim-delta="0.5">+0.5%</button>
    </div>
  </section>

  <section id="start-panel" class="start-panel">
    <strong>Start a ride</strong>
    <p>Launch a local session here and the road will move from the same snapshot stream.</p>
    <div class="actions">
      <button class="action primary" data-start-mode="free">Free Ride</button>
      <button class="action" data-start-mode="erg">ERG</button>
      <button class="action" data-start-mode="sim">SIM</button>
    </div>
  </section>

  <a class="back" href="/">Home</a>

  <script type="module" src="/static/ride3d.js"></script>
</body>
</html>
"""


def parse_ride_mode(value: object) -> RideMode:
    """Parse a browser-supplied ride mode."""
    try:
        return RideMode(str(value or RideMode.FREE.value).lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported ride mode") from exc


def parse_delta(value: object, label: str) -> float:
    """Parse a browser-supplied numeric delta."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {label} delta") from exc


def attach_ride3d_routes(
    web_app: RouteApp,
    runtime_provider: Callable[[], RideRuntime],
) -> None:
    """Attach the Three.js prototype route."""

    @web_app.get("/ride3d")
    async def ride3d() -> HTMLResponse:
        return HTMLResponse(RIDE3D_HTML)

    @web_app.get("/static/ride3d.js")
    async def ride3d_script() -> FileResponse:
        return FileResponse(STATIC_DIR / "ride3d.js", media_type="text/javascript")

    @web_app.post("/api/ride/start")
    async def start_ride(request: Request) -> dict[str, object]:
        body = await request.json()
        mode = parse_ride_mode(body.get("mode"))
        return runtime_provider().start_session(mode).to_dict()

    @web_app.post("/api/ride/stop")
    async def stop_ride() -> dict[str, object]:
        return runtime_provider().stop_session().to_dict()

    @web_app.post("/api/ride/toggle-pause")
    async def toggle_pause() -> dict[str, object]:
        return runtime_provider().toggle_pause().to_dict()

    @web_app.post("/api/ride/erg-target")
    async def adjust_erg_target(request: Request) -> dict[str, object]:
        body = await request.json()
        delta = int(parse_delta(body.get("delta"), "ERG target"))
        return runtime_provider().adjust_erg_target(delta).to_dict()

    @web_app.post("/api/ride/sim-grade")
    async def adjust_sim_grade(request: Request) -> dict[str, object]:
        body = await request.json()
        delta = parse_delta(body.get("delta"), "SIM grade")
        return runtime_provider().adjust_sim_grade(delta).to_dict()


__all__ = ["RIDE3D_HTML", "attach_ride3d_routes", "parse_delta", "parse_ride_mode"]
