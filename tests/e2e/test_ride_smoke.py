"""M6 browser smoke test: a real ride on the flagship map, end to end.

Run with:

    LE_TOUR_E2E=1 uv run --group e2e pytest tests/e2e -q

Launches the real web app (demo sample source), rides Col du Rivelet in a
real Chromium, and asserts the renderer contract: world builds, canvas
takes over from the CSS fallback, HUD updates from the snapshot stream,
zero frame errors, and the frame stays inside the performance budget
documented in docs/development.md. Also captures a screenshot artifact at
a fixed route distance — the same capture the future eval loop compares
against docs/screenshots/.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from harness import (
    CHROMIUM_ARGS,
    chromium_executable,
    hide_ride_ui,
    post_json,
    ride_debug,
    ride_server,
    wait_for,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("LE_TOUR_E2E") != "1",
    reason="browser smoke test; set LE_TOUR_E2E=1 (needs Chromium)",
)
playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright not installed (uv sync --group e2e)"
)

FLAGSHIP_ROUTE_ID = "col_du_rivelet"
SCREENSHOT_AT_M = 400  # matches the first docs/screenshots baseline frame

# Perf budget (docs/development.md): static world + instanced props must
# stay well under what mid-range GPUs rasterize at 60 FPS.
MAX_TRIANGLES = 500_000
MAX_DRAW_CALLS = 200


@pytest.fixture(scope="module")
def base_url():
    with ride_server() as url:
        yield url


@pytest.fixture(scope="module")
def page(base_url):
    with playwright_api.sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=chromium_executable(), args=CHROMIUM_ARGS
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page_errors: list[str] = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(f"{base_url}/ride3d?route_id={FLAGSHIP_ROUTE_ID}", wait_until="load")
        page.page_errors = page_errors  # type: ignore[attr-defined]
        yield page
        browser.close()


def test_flagship_ride_smoke(base_url, page, tmp_path_factory):
    # World compiles and the WebGL canvas takes over from the CSS fallback.
    wait_for(
        lambda: (ride_debug(page).get("pathLengthM") or 0) > 17_000,
        timeout_s=30,
        label="flagship path compile",
    )
    assert page.eval_on_selector(".scene-fallback", "(node) => node.hidden")
    assert page.eval_on_selector("#route-select", "(node) => node.value") == (
        FLAGSHIP_ROUTE_ID
    )

    # Start a SIM ride and hold a steady virtual effort.
    page.click('[data-start-mode="sim"]')
    wait_for(
        lambda: page.eval_on_selector("#start-panel", "(node) => node.hidden"),
        timeout_s=10,
        label="session start",
    )
    post_json(f"{base_url}/api/ride/virtual-rider", {"action": "hold", "watts": 300})

    # The snapshot stream drives the HUD and the world moves.
    wait_for(
        lambda: (ride_debug(page).get("serverDistanceM") or 0) > 60,
        timeout_s=60,
        label="ride distance",
    )
    debug = ride_debug(page)
    assert debug["frameErrorCount"] == 0
    assert debug["renderDistanceM"] > 0
    assert debug["speedMps"] > 1.0
    power_text = page.text_content("#power")
    assert re.fullmatch(r"\d+", power_text or ""), power_text
    assert re.fullmatch(r"\d+:\d{2}", page.text_content("#ride-time") or "")
    assert re.fullmatch(
        r"-?\d+\.\d%", page.text_content("#grade") or ""
    ), page.text_content("#grade")

    # Frame cost stays inside the documented budget.
    assert debug["triangles"] <= MAX_TRIANGLES, debug["triangles"]
    assert debug["drawCalls"] <= MAX_DRAW_CALLS, debug["drawCalls"]

    # Deterministic capture point: same distance as the baseline's first
    # frame (docs/screenshots/flagship_00400m.png).
    wait_for(
        lambda: (ride_debug(page).get("serverDistanceM") or 0) >= SCREENSHOT_AT_M,
        timeout_s=120,
        label="screenshot distance",
    )
    hide_ride_ui(page)
    artifact_dir = Path(
        os.environ.get("LE_TOUR_E2E_ARTIFACTS", tmp_path_factory.mktemp("ride-smoke"))
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(artifact_dir / "ride_smoke_00400m.png"))

    # Stop ends cleanly: post-ride summary appears with real numbers.
    page.evaluate("""() => {
          document
            .querySelectorAll(".hud, .status, .start-panel, .back")
            .forEach((node) => (node.style.visibility = ""));
        }""")
    page.click("#stop-ride")
    wait_for(
        lambda: not page.eval_on_selector("#ride-summary", "(node) => node.hidden"),
        timeout_s=10,
        label="ride summary",
    )
    assert re.fullmatch(r"\d+:\d{2}", page.text_content("#summary-duration") or "")
    assert re.fullmatch(r"\d+", page.text_content("#summary-avg") or "")

    assert page.page_errors == [], page.page_errors
