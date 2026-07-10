"""Shared Playwright harness for end-to-end ride checks (M6).

This is the scaffold the generative plan's eval loop (Experiment 3) runs
on: launch the real web app with the demo sample source, drive a real
browser over it, and read `window.__rideDebug` for renderer ground truth.

The browser tests are opt-in (`LE_TOUR_E2E=1`) because they need a
Chromium binary; everything else in the suite stays hardware- and
browser-free.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Containers (and this repo's dev sandbox) ship a Chromium at a fixed path;
# fall back to Playwright's own managed browser elsewhere.
DEFAULT_CHROMIUM = "/opt/pw-browsers/chromium"

# Software-GL flags so the harness renders the same way with or without a
# GPU. Real-GPU numbers (the 60 FPS check) need a run without SwiftShader.
CHROMIUM_ARGS = ["--use-gl=swiftshader", "--no-sandbox"]


def chromium_executable() -> str | None:
    """Return an explicit Chromium path, or None for Playwright's default."""
    override = os.environ.get("LE_TOUR_CHROMIUM")
    if override:
        return override
    if Path(DEFAULT_CHROMIUM).exists():
        return DEFAULT_CHROMIUM
    return None


def free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def fetch_json(url: str, timeout_s: float = 5.0) -> dict[str, object]:
    """GET a JSON endpoint (stdlib only, no client dependency)."""
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return json.loads(response.read())


def post_json(
    url: str, payload: dict[str, object] | None = None, timeout_s: float = 5.0
) -> dict[str, object]:
    """POST a JSON body and return the JSON response."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.loads(response.read())


@contextmanager
def ride_server(
    port: int | None = None, startup_timeout_s: float = 30.0
) -> Iterator[str]:
    """Run the real web app as a subprocess and yield its base URL.

    The app starts with no hardware connected, so sessions ride the demo
    sample source — exactly the no-hardware path the virtual rider drives.
    """
    port = port or free_port()
    base_url = f"http://127.0.0.1:{port}"
    # Strip pytest's env vars: NiceGUI sniffs them and switches ui.run into
    # its own screen-test mode, which expects a NiceGUI-managed port.
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("PYTEST")
    }
    env.update(LE_TOUR_PORT=str(port), LE_TOUR_HOST="127.0.0.1")
    process = subprocess.Popen(
        [sys.executable, "run_web.py"],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + startup_timeout_s
        while True:
            if process.poll() is not None:
                output = (process.stdout.read() if process.stdout else b"").decode(
                    errors="replace"
                )
                raise RuntimeError(f"web app exited during startup:\n{output}")
            try:
                if fetch_json(f"{base_url}/api/health")["status"] == "ok":
                    break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError("web app did not become healthy in time")
            time.sleep(0.25)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def wait_for(predicate, timeout_s: float, interval_s: float = 0.25, label: str = ""):
    """Poll `predicate` until it returns a truthy value, or fail."""
    deadline = time.monotonic() + timeout_s
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() > deadline:
            raise TimeoutError(f"timed out waiting for {label or 'condition'}")
        time.sleep(interval_s)


def hide_ride_ui(page) -> None:
    """Hide DOM overlays for clean world screenshots."""
    page.evaluate("""() => {
          document
            .querySelectorAll(".hud, .status, .start-panel, .back")
            .forEach((node) => (node.style.visibility = "hidden"));
        }""")


def ride_debug(page) -> dict[str, object]:
    """Return the renderer's live diagnostics object."""
    return page.evaluate("() => window.__rideDebug") or {}
