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


def test_ride3d_uses_grade_aware_render_state():
    """SIM grade changes visibly affect the scene through motion state."""
    assert "const roadGroup = new THREE.Group()" in RIDE3D_JS
    assert "roadGroup.add(road)" in RIDE3D_JS
    assert "roadGroup.rotation.x = sceneState.roadPitch" in RIDE3D_JS
    assert "hills.position.y = sceneState.horizonLift" in RIDE3D_JS
    assert "roadPitch" in RIDE_MOTION_JS
    assert "horizonLift" in RIDE_MOTION_JS


def test_ride3d_motion_model_defines_distance_route_segments():
    """Route segments turn distance into render state for the browser scene."""
    assert "export const DEFAULT_ROUTE_SEGMENTS" in RIDE_MOTION_JS
    assert "segmentForDistance(distanceM)" in RIDE_MOTION_JS
    assert "routeSegmentName" in RIDE_MOTION_JS
    assert "routeSegmentProgress" in RIDE_MOTION_JS
    assert "routeSegmentRemainingM" in RIDE_MOTION_JS
    assert "routeGradePct" in RIDE_MOTION_JS
    assert "nextSegmentName" in RIDE_MOTION_JS
    assert "nextSegmentGradePct" in RIDE_MOTION_JS
    assert "scenery" in RIDE_MOTION_JS


def test_ride3d_hud_and_scene_use_route_segment_state():
    """Route segment state feeds HUD text and scene variation."""
    assert "sceneState.routeSegmentName" in RIDE3D_JS
    assert "sceneState.gradePct.toFixed(1)" in RIDE3D_JS
    assert "sceneState.routeSegmentProgress" in RIDE3D_JS
    assert "hills.rotation.y = sceneState.routeSegmentProgress" in RIDE3D_JS


def test_ride3d_scenery_palette_tracks_route_segment():
    """Segment scenery updates the lightweight world palette."""
    assert "const sceneryPalettes" in RIDE3D_JS
    assert "function applyScenery(scenery)" in RIDE3D_JS
    assert "applyScenery(sceneState.scenery)" in RIDE3D_JS
    assert "renderer.setClearColor(palette.sky, 1)" in RIDE3D_JS
    assert "groundMaterial.color.setHex(palette.ground)" in RIDE3D_JS
    assert "hillMaterial.color.setHex(palette.hills)" in RIDE3D_JS


def test_ride3d_builds_route_profile_hud_from_motion_state():
    """Route profile HUD stays browser-side and uses render state."""
    assert "function createRouteProfile(parent)" in RIDE3D_JS
    assert "const routeProfile = createRouteProfile(hud.statusPanel)" in RIDE3D_JS
    assert "routeProfile.update(sceneState, snapshot.active)" in RIDE3D_JS
    assert "sceneState.routeSegmentProgress * 100" in RIDE3D_JS
    assert "sceneState.routeSegmentName" in RIDE3D_JS
    assert "sceneState.nextSegmentName" in RIDE3D_JS
    assert "sceneState.routeSegmentRemainingM" in RIDE3D_JS
    assert "sceneState.nextSegmentGradePct.toFixed(1)" in RIDE3D_JS


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
