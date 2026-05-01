"""Minimal Three.js ride prototype."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from starlette.responses import HTMLResponse


class RouteApp(Protocol):
    """Minimal route registration surface used by FastAPI/NiceGUI app."""

    def get(
        self, path: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Register a GET route."""
        ...


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
        bottom: 112px;
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
  </section>

  <a class="back" href="/">Home</a>

  <script type="module">
    import * as THREE from "https://esm.sh/three@0.164.1";

    const canvas = document.querySelector("#scene");
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      preserveDrawingBuffer: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0xd9edf7, 1);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0xd9edf7, 42, 150);

    const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 240);
    camera.position.set(0, 3.6, 7.6);
    camera.lookAt(0, 0.35, -22);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x5d6b4f, 2.4);
    scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(-10, 18, 8);
    scene.add(sun);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(220, 260),
      new THREE.MeshLambertMaterial({ color: 0x8fae76 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.z = -54;
    scene.add(ground);

    const road = new THREE.Mesh(
      new THREE.PlaneGeometry(8.6, 260),
      new THREE.MeshLambertMaterial({ color: 0x202421 })
    );
    road.rotation.x = -Math.PI / 2;
    road.position.y = 0.015;
    road.position.z = -54;
    scene.add(road);

    const shoulderMaterial = new THREE.MeshLambertMaterial({ color: 0xb7c5ac });
    for (const x of [-5.4, 5.4]) {
      const shoulder = new THREE.Mesh(new THREE.PlaneGeometry(2, 260), shoulderMaterial);
      shoulder.rotation.x = -Math.PI / 2;
      shoulder.position.set(x, 0.02, -54);
      scene.add(shoulder);
    }

    const laneGroup = new THREE.Group();
    const dashMaterial = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
    for (let i = 0; i < 34; i += 1) {
      const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 3.4), dashMaterial);
      dash.rotation.x = -Math.PI / 2;
      dash.position.set(0, 0.035, 8 - i * 7.8);
      laneGroup.add(dash);
    }
    scene.add(laneGroup);

    const railMaterial = new THREE.MeshLambertMaterial({ color: 0x566052 });
    const postGeometry = new THREE.BoxGeometry(0.12, 0.9, 0.12);
    for (const x of [-6.75, 6.75]) {
      for (let i = 0; i < 30; i += 1) {
        const post = new THREE.Mesh(postGeometry, railMaterial);
        post.position.set(x, 0.48, 9 - i * 8.5);
        scene.add(post);
      }
    }

    const hills = new THREE.Group();
    const hillMaterial = new THREE.MeshLambertMaterial({ color: 0x6f8b61 });
    for (let i = 0; i < 9; i += 1) {
      const hill = new THREE.Mesh(new THREE.ConeGeometry(14 + i * 1.4, 8 + i, 5), hillMaterial);
      hill.position.set(i % 2 === 0 ? -22 - i * 4 : 22 + i * 4, 3.5, -38 - i * 12);
      hill.rotation.y = i * 0.37;
      hills.add(hill);
    }
    scene.add(hills);

    const hud = {
      power: document.querySelector("#power"),
      speed: document.querySelector("#speed"),
      cadence: document.querySelector("#cadence"),
      hr: document.querySelector("#heart-rate"),
      distance: document.querySelector("#distance"),
      state: document.querySelector("#state"),
      mode: document.querySelector("#mode"),
    };

    let ride = {
      active: false,
      paused: false,
      mode: null,
      speed_mps: 0,
      power_w: null,
      cadence_rpm: null,
      hr_bpm: null,
      distance_m: 0,
      session_state: "inactive",
    };

    function formatValue(value, fallback = "--") {
      return value === null || value === undefined ? fallback : String(value);
    }

    function updateHud(snapshot) {
      ride = snapshot;
      hud.power.textContent = formatValue(snapshot.power_w);
      hud.speed.textContent = snapshot.speed_mps ? (snapshot.speed_mps * 3.6).toFixed(1) : "--";
      hud.cadence.textContent = formatValue(snapshot.cadence_rpm);
      hud.hr.textContent = formatValue(snapshot.hr_bpm);
      hud.distance.textContent = snapshot.distance_m ? `${(snapshot.distance_m / 1000).toFixed(2)} km` : "--";

      const state = snapshot.session_state || "inactive";
      hud.state.textContent = state === "active"
        ? "Live ride stream"
        : state === "paused"
          ? "Ride paused"
          : "Waiting for ride data";
      hud.mode.textContent = snapshot.active
        ? `${snapshot.mode || "free"} mode · ${snapshot.trainer_name || "demo source"}`
        : "Start a session to drive the road";
    }

    function connectSnapshots() {
      const source = new EventSource("/api/ride/snapshots");
      source.addEventListener("snapshot", event => {
        updateHud(JSON.parse(event.data));
      });
      source.onerror = () => {
        hud.state.textContent = "Snapshot stream disconnected";
      };
    }

    function resize() {
      const width = window.innerWidth;
      const height = window.innerHeight;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    let last = performance.now();
    let roadOffset = 0;

    function frame(now) {
      const dt = Math.min(0.06, (now - last) / 1000);
      last = now;

      const speed = ride.active && !ride.paused ? Math.max(0, ride.speed_mps || 0) : 0;
      roadOffset = (roadOffset + speed * dt) % 7.8;
      laneGroup.children.forEach((dash, index) => {
        dash.position.z = 8 - index * 7.8 + roadOffset;
        if (dash.position.z > 12) dash.position.z -= 34 * 7.8;
      });

      camera.position.y = 3.6 + Math.sin(now * 0.004) * 0.03 * Math.min(speed, 10);
      camera.lookAt(0, 0.35, -22);
      renderer.render(scene, camera);
      requestAnimationFrame(frame);
    }

    window.addEventListener("resize", resize);
    resize();
    connectSnapshots();
    requestAnimationFrame(frame);
  </script>
</body>
</html>
"""


def attach_ride3d_routes(web_app: RouteApp) -> None:
    """Attach the Three.js prototype route."""

    @web_app.get("/ride3d")
    async def ride3d() -> HTMLResponse:
        return HTMLResponse(RIDE3D_HTML)


__all__ = ["RIDE3D_HTML", "attach_ride3d_routes"]
