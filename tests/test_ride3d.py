"""Tests for the Three.js ride prototype page."""

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from terminalride.domain.state import RideMode
from terminalride.web.ride3d import (
    RIDE3D_HTML,
    attach_ride3d_routes,
    parse_delta,
    parse_ride_mode,
)

RIDE3D_JS = Path("terminalride/web/static/ride3d.js").read_text()
RIDE_CLIENT_JS = Path("terminalride/web/static/ride_client.js").read_text()
RIDE_MOTION_JS = Path("terminalride/web/static/ride_motion.js").read_text()


def test_ride3d_route_endpoint_returns_default_route():
    """3D route API exposes route data as a browser contract."""
    app = FastAPI()
    attach_ride3d_routes(app, lambda: None)  # type: ignore[arg-type]
    response = TestClient(app).get("/api/ride/route")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "demo_rolling_route"
    assert payload["segments"][0]["name"] == "Valley Rollers"
    assert payload["segments"][0]["length_m"] == 420


def test_ride3d_route_endpoint_selects_route_by_id():
    """3D route API can serve a selected bundled route."""
    app = FastAPI()
    attach_ride3d_routes(app, lambda: None)  # type: ignore[arg-type]
    response = TestClient(app).get("/api/ride/route?route_id=forest_climb_loop")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "forest_climb_loop"
    assert payload["segments"][1]["name"] == "Switchback One"


def test_ride3d_routes_endpoint_lists_bundled_routes():
    """Browser clients can populate route selection without hardcoded maps."""
    app = FastAPI()
    attach_ride3d_routes(app, lambda: None)  # type: ignore[arg-type]
    response = TestClient(app).get("/api/ride/routes")

    assert response.status_code == 200
    payload = response.json()
    assert [route["id"] for route in payload] == [
        "demo_rolling_route",
        "forest_climb_loop",
    ]
    assert payload[0]["segment_count"] == 5


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
    assert '"/api/ride/route"' in RIDE_CLIENT_JS
    assert '"/api/ride/routes"' in RIDE_CLIENT_JS
    assert "getRoute(routeId = null)" in RIDE_CLIENT_JS
    assert "getRoutes()" in RIDE_CLIENT_JS


def test_ride3d_page_has_route_selection_controls():
    """Route choice is UI state that is sent to the start endpoint."""
    assert 'id="route-select"' in RIDE3D_HTML
    assert 'id="route-hud"' in RIDE3D_HTML
    assert "populateRouteSelect(routes)" in RIDE3D_JS
    assert "await loadRoute(routes[0]?.id ?? null)" in RIDE3D_JS
    assert 'hud.routeSelect.addEventListener("change"' in RIDE3D_JS
    assert "selectedRouteId" in RIDE3D_JS
    assert "startRide(mode, routeId = null)" in RIDE_CLIENT_JS
    assert "route_id: routeId" in RIDE_CLIENT_JS


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
    assert "DEFAULT_ROUTE_SEGMENTS" not in RIDE_MOTION_JS
    assert "routeSegments = []" in RIDE_MOTION_JS
    assert "segmentForDistance(distanceM)" in RIDE_MOTION_JS
    assert "routeSegmentName" in RIDE_MOTION_JS
    assert "routeSegmentKind" in RIDE_MOTION_JS
    assert "routeSurface" in RIDE_MOTION_JS
    assert "routeHeadingDeg" in RIDE_MOTION_JS
    assert "routeCurveStrength" in RIDE_MOTION_JS
    assert "roadWidthM" in RIDE_MOTION_JS
    assert "routeSegmentProgress" in RIDE_MOTION_JS
    assert "routeSegmentRemainingM" in RIDE_MOTION_JS
    assert "routeGradePct" in RIDE_MOTION_JS
    assert "nextSegmentName" in RIDE_MOTION_JS
    assert "nextSegmentGradePct" in RIDE_MOTION_JS
    assert "segmentGateAlpha" in RIDE_MOTION_JS
    assert "scenery" in RIDE_MOTION_JS


def test_ride3d_hud_and_scene_use_route_segment_state():
    """Route segment state feeds HUD text and scene variation."""
    assert "const route = await rideClient.getRoute(routeId)" in RIDE3D_JS
    assert "routeSegments: route.segments" in RIDE3D_JS
    assert "sceneState.routeSegmentName" in RIDE3D_JS
    assert "sceneState.gradePct.toFixed(1)" in RIDE3D_JS
    assert "sceneState.routeSegmentProgress" in RIDE3D_JS
    assert "hills.rotation.y = sceneState.routeSegmentProgress" in RIDE3D_JS


def test_ride3d_uses_route_geometry_for_road_shape():
    """Route geometry affects road width, yaw, camera look, and curve signage."""
    assert "turnDeg" in RIDE_MOTION_JS
    assert "roadWidthM" in RIDE_MOTION_JS
    assert "headingDeg" in RIDE_MOTION_JS
    assert "curveStrength" in RIDE_MOTION_JS
    assert "function buildRoutePath(route)" in RIDE3D_JS
    assert "function visibleRouteSamples(routePath, distanceM)" in RIDE3D_JS
    assert "function ribbonGeometry(samples" in RIDE3D_JS
    assert "activeRoutePath = buildRoutePath(route)" in RIDE3D_JS
    assert "replaceGeometry(" in RIDE3D_JS
    assert "camera.lookAt(sceneState.cameraLookX" in RIDE3D_JS
    assert "camera.rotation.z += sceneState.cameraRoll" in RIDE3D_JS


def test_ride3d_generates_live_road_ribbon_from_route_path():
    """The visible road mesh is rebuilt from sampled route centerline data."""
    assert "sampleRoutePath(routePath, distanceM)" in RIDE3D_JS
    assert "ribbonGeometry(samples, (widthM) => -widthM / 2" in RIDE3D_JS
    assert "updateLaneMarkers(samples)" in RIDE3D_JS
    assert "sample.roadWidthM / 2 + 2.3" in RIDE3D_JS
    assert "roadGroup.rotation.y = 0" in RIDE3D_JS


def test_ride3d_renders_curve_chevrons_from_route_geometry():
    """Curve metadata produces a visible route cue without BLE coupling."""
    assert "const curveChevronGroup = new THREE.Group()" in RIDE3D_JS
    assert "function updateCurveChevrons(sceneState)" in RIDE3D_JS
    assert "sceneState.routeCurveStrength" in RIDE3D_JS
    assert "chevronMaterial.opacity" in RIDE3D_JS
    assert "updateCurveChevrons(sceneState)" in RIDE3D_JS


def test_ride3d_renders_pacer_riders_from_motion_state():
    """A small rider pack gives the route a Zwift-like sense of scale."""
    assert "const pacerGroup = new THREE.Group()" in RIDE3D_JS
    assert "new THREE.CapsuleGeometry" in RIDE3D_JS
    assert "function updatePacerRiders(sceneState, now)" in RIDE3D_JS
    assert "pacerGroup.visible = sceneState.active" in RIDE3D_JS
    assert "updatePacerRiders(sceneState, now)" in RIDE3D_JS


def test_ride3d_renders_player_cockpit_from_motion_state():
    """Foreground cockpit gives the ride a first-person anchor."""
    assert "const cockpitGroup = new THREE.Group()" in RIDE3D_JS
    assert "camera.add(cockpitGroup)" in RIDE3D_JS
    assert "function updateCockpit(sceneState, now)" in RIDE3D_JS
    assert "cockpitGroup.visible = sceneState.active" in RIDE3D_JS
    assert "frontWheel.rotation.x" in RIDE3D_JS
    assert "updateCockpit(sceneState, now)" in RIDE3D_JS


def test_ride3d_renders_scenery_props_from_route_samples():
    """Roadside objects use the same route samples as the road ribbon."""
    assert "const roadsidePropGroup = new THREE.Group()" in RIDE3D_JS
    assert 'scenery: String(segment.scenery || "fields")' in RIDE3D_JS
    assert "scenery: sample.scenery" in RIDE3D_JS
    assert "function activePropVariant(scenery)" in RIDE3D_JS
    assert "function updateRoadsideProps(sceneState, samples)" in RIDE3D_JS
    assert "activePropVariant(sample.scenery || sceneState.scenery)" in RIDE3D_JS
    assert "sample.roadWidthM / 2 + 3.5" in RIDE3D_JS
    assert "updateRoadsideProps(sceneState, roadSamples)" in RIDE3D_JS


def test_ride3d_renders_river_ribbon_for_river_segments():
    """River scenery gets a lightweight water ribbon alongside the route."""
    assert "const riverRibbon = new THREE.Mesh(" in RIDE3D_JS
    assert "propMaterials.water" in RIDE3D_JS
    assert 'samples.some((sample) => sample.scenery === "river")' in RIDE3D_JS
    assert "near.roadWidthM / 2 + 5.8" in RIDE3D_JS


def test_ride3d_scenery_palette_tracks_route_segment():
    """Segment scenery updates the lightweight world palette."""
    assert "const sceneryPalettes" in RIDE3D_JS
    assert "function applyScenery(scenery)" in RIDE3D_JS
    assert "applyScenery(sceneState.scenery)" in RIDE3D_JS
    assert "renderer.setClearColor(palette.sky, 1)" in RIDE3D_JS
    assert "groundMaterial.color.setHex(palette.ground)" in RIDE3D_JS
    assert "hillMaterial.color.setHex(palette.hills)" in RIDE3D_JS


def test_ride3d_surface_palette_tracks_route_segment():
    """Segment surface updates the lightweight road material."""
    assert "const surfaceColors" in RIDE3D_JS
    assert "function applySurface(surface)" in RIDE3D_JS
    assert "applySurface(sceneState.routeSurface)" in RIDE3D_JS
    assert "roadMaterial.color.setHex" in RIDE3D_JS


def test_ride3d_builds_route_profile_hud_from_motion_state():
    """Route profile HUD stays browser-side and uses render state."""
    assert "function createRouteProfile(parent)" in RIDE3D_JS
    assert "routeProfile = createRouteProfile(hud.routeHud)" in RIDE3D_JS
    assert "routeProfile.update(sceneState, snapshot.active)" in RIDE3D_JS
    assert "sceneState.routeSegmentProgress * 100" in RIDE3D_JS
    assert "sceneState.routeSegmentName" in RIDE3D_JS
    assert "sceneState.nextSegmentName" in RIDE3D_JS
    assert "sceneState.routeSegmentRemainingM" in RIDE3D_JS
    assert "sceneState.nextSegmentGradePct.toFixed(1)" in RIDE3D_JS


def test_ride3d_builds_elevation_profile_from_route_spec():
    """Elevation profile is generated from route data, not hardcoded DOM."""
    assert "function createElevationProfile(parent, route)" in RIDE3D_JS
    assert "route.segments.forEach((segment)" in RIDE3D_JS
    assert "Number(segment.grade_pct)" in RIDE3D_JS
    assert 'document.createElementNS(ns, "polyline")' in RIDE3D_JS
    assert "elevationProfile.update(sceneState, snapshot.active)" in RIDE3D_JS
    assert "elevationProfile = createElevationProfile(hud.routeHud, route)" in RIDE3D_JS


def test_ride3d_renders_segment_gate_from_route_state():
    """Upcoming segment state drives a lightweight route gate."""
    assert "const segmentGate = new THREE.Group()" in RIDE3D_JS
    assert "function updateSegmentGate(sceneState, samples)" in RIDE3D_JS
    assert "sceneState.segmentGateAlpha" in RIDE3D_JS
    assert "sceneState.nextSegmentGradePct >= 0" in RIDE3D_JS
    assert "sceneState.routeSegmentRemainingM / 5.2" in RIDE3D_JS
    assert "segmentGate.position.set(sample.x, sample.y, sample.z)" in RIDE3D_JS
    assert "updateSegmentGate(sceneState, roadSamples)" in RIDE3D_JS


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
