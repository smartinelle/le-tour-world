"""Regenerate the flagship screenshot baseline in docs/screenshots/.

Usage:

    uv run --group e2e python tests/e2e/capture_flagship_screenshots.py

Launches the app, rides Col du Rivelet on the virtual rider (450 W hold,
matching the original baseline), and captures a clean-world frame as the
ride passes each fixed distance. Riding the whole 17.2 km takes roughly
20 minutes — this is a baseline tool, not a smoke test (that's
test_ride_smoke.py).

Note: on SwiftShader (software GL) the output differs subtly from real
GPUs — compare like with like.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import (  # noqa: E402
    CHROMIUM_ARGS,
    PROJECT_ROOT,
    chromium_executable,
    hide_ride_ui,
    post_json,
    ride_debug,
    ride_server,
    wait_for,
)

FLAGSHIP_ROUTE_ID = "col_du_rivelet"
CAPTURE_DISTANCES_M = (400, 2400, 3600, 5200, 7600, 9000, 11500, 14200, 15800)
HOLD_WATTS = 450
OUTPUT_DIR = PROJECT_ROOT / "docs" / "screenshots"


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shots: list[dict[str, object]] = []

    with ride_server() as base_url, sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=chromium_executable(), args=CHROMIUM_ARGS
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{base_url}/ride3d?route_id={FLAGSHIP_ROUTE_ID}", wait_until="load")
        wait_for(
            lambda: (ride_debug(page).get("pathLengthM") or 0) > 17_000,
            timeout_s=30,
            label="flagship path compile",
        )

        page.click('[data-start-mode="free"]')
        wait_for(
            lambda: page.eval_on_selector("#start-panel", "(node) => node.hidden"),
            timeout_s=10,
            label="session start",
        )
        post_json(
            f"{base_url}/api/ride/virtual-rider",
            {"action": "hold", "watts": HOLD_WATTS},
        )
        hide_ride_ui(page)

        started = time.monotonic()
        for target_m in CAPTURE_DISTANCES_M:
            wait_for(
                lambda: (ride_debug(page).get("serverDistanceM") or 0) >= target_m,
                timeout_s=600,
                interval_s=1.0,
                label=f"distance {target_m} m",
            )
            name = f"flagship_{target_m:05d}m.png"
            page.screenshot(path=str(OUTPUT_DIR / name))
            debug = ride_debug(page)
            shots.append(
                {
                    "name": name,
                    "at_m": round(float(debug["serverDistanceM"])),
                    "frame_errors": debug["frameErrorCount"],
                }
            )
            print(
                f"captured {name} at {shots[-1]['at_m']} m "
                f"({time.monotonic() - started:.0f} s elapsed)",
                flush=True,
            )

        # Stopping persists a ~20-minute session; give it time, and don't
        # let a slow save invalidate captures that are already on disk.
        try:
            post_json(f"{base_url}/api/ride/stop", timeout_s=60.0)
        except OSError as exc:
            print(f"warning: stop/persist did not finish cleanly: {exc}")
        browser.close()

    print(json.dumps(shots, indent=2))
    failed = [shot for shot in shots if shot["frame_errors"]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
