"""Tests for the Three.js ride prototype page."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from terminalride.domain.state import RideMode
from terminalride.web.ride3d import RIDE3D_HTML, parse_delta, parse_ride_mode

RIDE3D_JS = Path("terminalride/web/static/ride3d.js").read_text()
RIDE_CLIENT_JS = Path("terminalride/web/static/ride_client.js").read_text()
RIDE_MOTION_JS = Path("terminalride/web/static/ride_motion.js").read_text()


def test_ride3d_page_consumes_snapshot_stream():
    """3D prototype is a browser-only snapshot stream consumer."""
    assert '<script type="module" src="/static/ride3d.js"></script>' in RIDE3D_HTML
    assert 'import { RideApiClient } from "/static/ride_client.js"' in RIDE3D_JS
    assert 'import { RideMotionModel } from "/static/ride_motion.js"' in RIDE3D_JS
    assert "new EventSource(this.snapshotUrl)" in RIDE_CLIENT_JS
    assert '"/api/ride/snapshots"' in RIDE_CLIENT_JS
    assert "export class RideMotionModel" in RIDE_MOTION_JS
    assert "https://esm.sh/three" in RIDE3D_JS
    assert "speed_mps" in RIDE3D_JS
    assert "canvas" in RIDE3D_HTML
    assert "fetch(" not in RIDE3D_JS
    assert "EventSource(" not in RIDE3D_JS


def test_ride3d_page_has_session_controls():
    """3D prototype can start and stop local ride sessions."""
    assert 'data-start-mode="free"' in RIDE3D_HTML
    assert 'data-start-mode="erg"' in RIDE3D_HTML
    assert 'data-start-mode="sim"' in RIDE3D_HTML
    assert 'id="stop-ride"' in RIDE3D_HTML
    assert 'id="pause-ride"' in RIDE3D_HTML
    assert 'id="erg-controls"' in RIDE3D_HTML
    assert 'id="sim-controls"' in RIDE3D_HTML
    assert "rideClient.startRide" in RIDE3D_JS
    assert "rideClient.stopRide" in RIDE3D_JS
    assert "rideClient.togglePause" in RIDE3D_JS
    assert "rideClient.adjustErgTarget" in RIDE3D_JS
    assert "rideClient.adjustSimGrade" in RIDE3D_JS
    assert '"/api/ride/start"' in RIDE_CLIENT_JS
    assert '"/api/ride/stop"' in RIDE_CLIENT_JS
    assert '"/api/ride/toggle-pause"' in RIDE_CLIENT_JS
    assert '"/api/ride/erg-target"' in RIDE_CLIENT_JS
    assert '"/api/ride/sim-grade"' in RIDE_CLIENT_JS


def test_ride3d_motion_model_owns_scene_motion():
    """3D scene reads render-friendly motion state, not raw snapshots."""
    assert "motion.updateFromSnapshot(snapshot)" in RIDE3D_JS
    assert "const sceneState = motion.advance(dt, now)" in RIDE3D_JS
    assert "sceneState.roadOffset" in RIDE3D_JS
    assert "sceneState.cameraBob" in RIDE3D_JS
    assert "sceneState.cameraPitch" in RIDE3D_JS
    assert "targetSpeedMps" in RIDE_MOTION_JS
    assert "cameraPitch" in RIDE_MOTION_JS


def test_parse_ride_mode():
    """Browser-supplied ride mode strings map to domain modes."""
    assert parse_ride_mode("free") is RideMode.FREE
    assert parse_ride_mode("ERG") is RideMode.ERG
    assert parse_ride_mode(None) is RideMode.FREE


def test_parse_ride_mode_rejects_unknown_mode():
    """Unsupported ride mode strings return a 400 response."""
    with pytest.raises(HTTPException) as exc_info:
        parse_ride_mode("climb")

    assert exc_info.value.status_code == 400


def test_parse_delta():
    """Browser-supplied numeric deltas are parsed as floats."""
    assert parse_delta("10", "test") == 10.0
    assert parse_delta("-0.5", "test") == -0.5


def test_parse_delta_rejects_invalid_values():
    """Invalid deltas return a 400 response."""
    with pytest.raises(HTTPException) as exc_info:
        parse_delta("watts", "test")

    assert exc_info.value.status_code == 400
