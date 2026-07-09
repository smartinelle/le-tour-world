"""Tests for the Three.js ride surface (world-fixed renderer)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from le_tour.domain.state import RideMode, RideSnapshot
from le_tour.web.ride3d import (
    RIDE3D_HTML,
    attach_ride3d_routes,
    parse_delta,
    parse_ride_mode,
)

RIDE3D_JS = Path("le_tour/web/static/ride3d.js").read_text()
RIDE_CLIENT_JS = Path("le_tour/web/static/ride_client.js").read_text()
RIDE_MOTION_JS = Path("le_tour/web/static/ride_motion.js").read_text()
ROUTE_PATH_JS = Path("le_tour/web/static/route_path.js").read_text()
WORLD_BUILDER_JS = Path("le_tour/web/static/world_builder.js").read_text()
WEB_APP_PY = Path("le_tour/web/app.py").read_text()


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
        "col_du_rivelet",
        "demo_rolling_route",
        "forest_climb_loop",
    ]
    assert payload[0]["segment_count"] == 18


def test_ride3d_serves_renderer_modules():
    """The world-fixed renderer modules are served as static assets."""
    app = FastAPI()
    attach_ride3d_routes(app, lambda: None)  # type: ignore[arg-type]
    client = TestClient(app)

    for name in (
        "route_path.js",
        "world_builder.js",
        "ride3d.js",
        "vendor/three.module.js",
    ):
        response = client.get(f"/static/{name}")
        assert response.status_code == 200, name
        assert "javascript" in response.headers["content-type"], name


def test_ride3d_start_endpoint_prepares_hardware_session():
    """3D start uses the same runtime hardware preparation as other UIs."""
    runtime = MagicMock()
    runtime.controller.snapshot.return_value = RideSnapshot(
        session_state="active",
        active=True,
        mode=RideMode.ERG,
        trainer_connected=True,
        trainer_name="KICKR Core",
    )
    runtime.prepare_hardware_session = AsyncMock()
    app = FastAPI()
    attach_ride3d_routes(app, lambda: runtime)

    response = TestClient(app).post(
        "/api/ride/start",
        json={"mode": "erg", "route_id": "demo_rolling_route"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trainer_connected"] is True
    runtime.start_session.assert_called_once_with(RideMode.ERG)
    runtime.prepare_hardware_session.assert_awaited_once_with(RideMode.ERG)


def test_health_endpoint_identifies_server_process():
    """Clients can tell which server process (and session) they talk to."""
    runtime = MagicMock()
    runtime.controller.snapshot.return_value = RideSnapshot(
        session_state="active", active=True, distance_m=1234.5
    )
    app = FastAPI()
    attach_ride3d_routes(app, lambda: runtime)

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["pid"] > 0
    assert payload["session_state"] == "active"
    assert payload["distance_m"] == 1234.5


def test_motion_model_coasts_to_stop_when_stream_goes_stale():
    """A dead server must not leave the browser world riding forever."""
    assert "staleSnapshotMs" in RIDE_MOTION_JS
    assert "lastSnapshotAtMs" in RIDE_MOTION_JS
    assert "this.targetSpeedMps = 0" in RIDE_MOTION_JS


def test_ride3d_surfaces_failed_session_controls():
    """Start/stop failures show in the HUD instead of failing silently."""
    assert "async function runRideAction(label, action)" in RIDE3D_JS
    assert "failed: ${error.message || error}" in RIDE3D_JS
    assert 'runRideAction("Start"' in RIDE3D_JS
    assert 'runRideAction("Stop"' in RIDE3D_JS


def test_ride3d_virtual_power_endpoint_sets_rider_watts():
    """The virtual trainer endpoint forwards live rider-set watts."""
    runtime = MagicMock()
    runtime.set_virtual_power.return_value = RideSnapshot(
        session_state="active", active=True
    )
    app = FastAPI()
    attach_ride3d_routes(app, lambda: runtime)

    response = TestClient(app).post("/api/ride/virtual-power", json={"watts": 250})

    assert response.status_code == 200
    runtime.set_virtual_power.assert_called_once_with(250.0)


def test_ride3d_virtual_power_endpoint_accepts_auto_mode():
    """A null wattage returns the virtual trainer to auto demo power."""
    runtime = MagicMock()
    runtime.set_virtual_power.return_value = RideSnapshot(session_state="inactive")
    app = FastAPI()
    attach_ride3d_routes(app, lambda: runtime)

    response = TestClient(app).post("/api/ride/virtual-power", json={"watts": None})

    assert response.status_code == 200
    runtime.set_virtual_power.assert_called_once_with(None)


def test_ride3d_page_has_virtual_trainer_controls():
    """Ride feel is testable without hardware: live watts from the browser."""
    assert 'id="virtual-trainer"' in RIDE3D_HTML
    assert 'id="virtual-power-slider"' in RIDE3D_HTML
    assert 'id="virtual-power-auto"' in RIDE3D_HTML
    assert 'data-virtual-power="300"' in RIDE3D_HTML
    assert "sendVirtualPower" in RIDE3D_JS
    assert "updateVirtualTrainerPanel(snapshot)" in RIDE3D_JS
    assert "rideClient.setVirtualPower" in RIDE3D_JS
    assert '"/api/ride/virtual-power"' in RIDE_CLIENT_JS
    assert "setVirtualPower(watts)" in RIDE_CLIENT_JS
    # Panel only appears while riding the demo source, never with hardware.
    assert "!snapshot.active || snapshot.trainer_connected" in RIDE3D_JS


def test_ride3d_page_consumes_snapshot_stream():
    """3D surface is a browser-only snapshot stream consumer."""
    assert '<script type="module" src="/static/ride3d.js?v=' in RIDE3D_HTML
    assert 'import { RideApiClient } from "/static/ride_client.js?v=' in RIDE3D_JS
    assert 'import { RideMotionModel } from "/static/ride_motion.js?v=' in RIDE3D_JS
    assert "new EventSource(this.snapshotUrl)" in RIDE_CLIENT_JS
    assert '"/api/ride/snapshots"' in RIDE_CLIENT_JS
    assert "export class RideMotionModel" in RIDE_MOTION_JS
    # three.js is vendored so the local-first ride surface works offline.
    assert 'import * as THREE from "/static/vendor/three.module.js"' in RIDE3D_JS
    assert 'import * as THREE from "/static/vendor/three.module.js"' in WORLD_BUILDER_JS
    assert "speed_mps" in RIDE3D_JS
    assert "canvas" in RIDE3D_HTML
    assert "fetch(" not in RIDE3D_JS
    assert "EventSource(" not in RIDE3D_JS
    # The CSS fallback yields to the canvas once WebGL actually renders.
    assert "scene-fallback" in RIDE3D_HTML
    assert 'document.querySelector(".scene-fallback")' in RIDE3D_JS


def test_ride3d_page_has_session_controls():
    """3D surface can start and stop local ride sessions."""
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
    assert '"/api/devices/status"' in RIDE_CLIENT_JS
    assert "getDeviceStatus()" in RIDE_CLIENT_JS
    assert "scanDevices(deviceType)" in RIDE_CLIENT_JS
    assert "connectDevice(deviceType, address)" in RIDE_CLIENT_JS
    assert "disconnectDevice(deviceType)" in RIDE_CLIENT_JS


def test_ride3d_hud_shows_hardware_connection_source():
    """3D HUD exposes whether samples are hardware-backed or demo-backed."""
    assert 'id="device-status"' in RIDE3D_HTML
    assert "No trainer · demo source" in RIDE3D_HTML
    assert "trainer_connected" in RIDE3D_JS
    assert "trainer_name" in RIDE3D_JS
    assert "hr_connected" in RIDE3D_JS
    assert "hr_name" in RIDE3D_JS
    assert "No trainer · demo source" in RIDE3D_JS
    assert "No HR · demo source" in RIDE3D_JS
    assert "hud.deviceStatus.textContent" in RIDE3D_JS


def test_ride3d_page_has_device_pairing_controls():
    """3D page can scan and connect hardware without returning to NiceGUI."""
    assert 'aria-label="Devices"' in RIDE3D_HTML
    assert 'id="trainer-device-action"' in RIDE3D_HTML
    assert 'id="hr-device-action"' in RIDE3D_HTML
    assert 'id="device-results"' in RIDE3D_HTML
    assert "refreshDeviceStatus()" in RIDE3D_JS
    assert 'handleDeviceAction("trainer"' in RIDE3D_JS
    assert 'handleDeviceAction("hr"' in RIDE3D_JS
    assert "rideClient.scanDevices(type)" in RIDE3D_JS
    assert "rideClient.connectDevice(type, address)" in RIDE3D_JS
    assert "rideClient.disconnectDevice(type)" in RIDE3D_JS


def test_web_app_uses_device_services_not_private_clients():
    """Web UI should stay behind domain service APIs for hardware flows."""
    assert "._client" not in WEB_APP_PY
    assert "connection_status()" in WEB_APP_PY
    assert "scan_devices(timeout_s=8.0)" in WEB_APP_PY


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
    assert "sceneState.cameraBob" in RIDE3D_JS
    assert "sceneState.cameraRoll" in RIDE3D_JS
    assert "targetSpeedMps" in RIDE_MOTION_JS
    assert "cameraPitch" in RIDE_MOTION_JS


def test_ride3d_motion_model_tracks_continuous_render_distance():
    """The camera needs a continuous distance between 4 Hz snapshots."""
    assert "renderDistanceM" in RIDE_MOTION_JS
    assert "this.renderDistanceM += this.speedMps * boundedDt" in RIDE_MOTION_JS
    assert "distanceErrorM" in RIDE_MOTION_JS
    assert "sceneState.renderDistanceM" in RIDE3D_JS


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
    assert "scenery" in RIDE_MOTION_JS


def test_route_path_compiles_world_fixed_centerline():
    """Routes compile once into an arc-length-indexed world-fixed centerline."""
    assert "export function buildRoutePath(route)" in ROUTE_PATH_JS
    assert "SAMPLE_SPACING_M" in ROUTE_PATH_JS
    assert "TRANSITION_WINDOW_M" in ROUTE_PATH_JS
    assert "poseAt" in ROUTE_PATH_JS
    assert "segmentBoundaries" in ROUTE_PATH_JS
    assert 'import { buildRoutePath } from "/static/route_path.js?v=' in RIDE3D_JS
    assert "activePath = buildRoutePath(route)" in RIDE3D_JS


def test_route_path_closes_the_loop():
    """Rides wrap modulo route length, so the compiled path must close."""
    assert "headingResidualRad" in ROUTE_PATH_JS
    assert "turnCorrectionRadPerM" in ROUTE_PATH_JS
    assert "elevationDriftM" in ROUTE_PATH_JS
    assert "closure" in ROUTE_PATH_JS
    # Drift correction bends tangents, so headings are recomputed from
    # corrected positions and unwrapped for interpolation.
    assert "wrapToPi" in ROUTE_PATH_JS
    assert "Math.atan2" in ROUTE_PATH_JS


def test_world_is_built_once_not_per_frame():
    """World geometry is compiled at route load; frames only move the camera."""
    assert "export function buildWorld(path)" in WORLD_BUILDER_JS
    assert (
        "import { applyScenery, buildWorld, createSkydome } from "
        '"/static/world_builder.js?v=' in RIDE3D_JS
    )
    assert "world = buildWorld(activePath)" in RIDE3D_JS
    assert "scene.add(world.group)" in RIDE3D_JS
    assert "world.dispose()" in RIDE3D_JS
    # The treadmill-era per-frame geometry churn must stay gone.
    assert "replaceGeometry" not in RIDE3D_JS
    assert "visibleRouteSamples" not in RIDE3D_JS
    assert "updateRoadGeometry" not in RIDE3D_JS


def test_world_builder_builds_static_road_from_path():
    """Road, shoulders, and ground ride the compiled centerline."""
    assert "function ribbonGeometry(" in WORLD_BUILDER_JS
    assert "function buildRoadSurfaces(path, group)" in WORLD_BUILDER_JS
    assert "computeVertexNormals" in WORLD_BUILDER_JS
    assert "GROUND_HALF_WIDTH_M" in WORLD_BUILDER_JS


def test_world_builder_bakes_surface_and_scenery_colors():
    """Surface and scenery are painted per-vertex along the world, not swapped
    globally as the rider crosses segments."""
    assert "export const surfaceColors" in WORLD_BUILDER_JS
    assert "export const sceneryPalettes" in WORLD_BUILDER_JS
    assert "vertexColors: true" in WORLD_BUILDER_JS
    assert "blendedPaletteColor" in WORLD_BUILDER_JS
    assert "applySurface" not in RIDE3D_JS


def test_world_builder_merges_static_runs_into_few_meshes():
    """Dashes, posts, and chevrons are merged; props ride InstancedMesh -
    the whole world stays within a small draw-call budget."""
    assert "function mergeGeometries(geometries)" in WORLD_BUILDER_JS
    assert "function buildLaneDashes(path, group)" in WORLD_BUILDER_JS
    assert "function buildRailPosts(path, group)" in WORLD_BUILDER_JS
    assert "function buildCurveChevrons(path, group)" in WORLD_BUILDER_JS
    assert "function buildProps(path, terrain, group)" in WORLD_BUILDER_JS
    assert "new THREE.InstancedMesh(" in WORLD_BUILDER_JS
    assert "setMatrixAt" in WORLD_BUILDER_JS
    assert "matrixAutoUpdate = false" in WORLD_BUILDER_JS


def test_world_builder_builds_terrain_deformed_to_the_road():
    """Corridor terrain: seeded noise blended into road elevation with a
    cubic falloff, per-scenery character, crossfaded along the route."""
    assert "function buildTerrainModel(path)" in WORLD_BUILDER_JS
    assert "function buildTerrainMesh(path, terrain, group)" in WORLD_BUILDER_JS
    assert "function terrainNoise(x, z)" in WORLD_BUILDER_JS
    assert "smoothstep" in WORLD_BUILDER_JS
    assert "terrainProfiles" in WORLD_BUILDER_JS
    assert "ROAD_FLAT_HALF_WIDTH_M" in WORLD_BUILDER_JS
    assert "TERRAIN_BLEND_END_M" in WORLD_BUILDER_JS
    # Props sample the same height function as the terrain mesh.
    assert "terrain.heightAt(rowIndex, side * offsetM)" in WORLD_BUILDER_JS


def test_world_builder_provides_atmosphere():
    """Camera-anchored skydome and per-scenery fog depth."""
    assert "export function createSkydome()" in WORLD_BUILDER_JS
    assert "fogProfiles" in WORLD_BUILDER_JS
    assert "scene.fog.near = fog.nearM" in WORLD_BUILDER_JS
    assert "camera.add(createSkydome())" in RIDE3D_JS


def test_world_builder_places_scenery_props_along_route():
    """Roadside props are placed deterministically by segment scenery."""
    assert "propBuilders" in WORLD_BUILDER_JS
    assert "propSpacingM" in WORLD_BUILDER_JS
    assert "createTreeProp" in WORLD_BUILDER_JS
    assert "createVillageProp" in WORLD_BUILDER_JS
    assert "createRockProp" in WORLD_BUILDER_JS
    assert "createFieldProp" in WORLD_BUILDER_JS
    assert "pseudoRandom" in WORLD_BUILDER_JS


def test_world_builder_renders_river_ribbons_for_river_segments():
    """River scenery gets static water ribbons alongside the route."""
    assert "function buildRiverRibbons(path, group)" in WORLD_BUILDER_JS
    assert 'scenery === "river"' in WORLD_BUILDER_JS
    assert "waterMaterial" in WORLD_BUILDER_JS


def test_world_builder_renders_segment_gates_at_boundaries():
    """Segment boundaries get static gates colored by the next grade."""
    assert "function buildSegmentGates(path, group)" in WORLD_BUILDER_JS
    assert "gradePct >= 0" in WORLD_BUILDER_JS
    assert "gateUphillMaterial" in WORLD_BUILDER_JS
    assert "gateDownhillMaterial" in WORLD_BUILDER_JS


def test_ride3d_scenery_palette_tracks_rider_position():
    """Sky, fog, and distant terrain follow the rider's current scenery."""
    assert "export function applyScenery(renderer, scene, scenery)" in WORLD_BUILDER_JS
    assert "renderer.setClearColor(palette.sky, 1)" in WORLD_BUILDER_JS
    assert "scene.fog.color.setHex(palette.sky)" in WORLD_BUILDER_JS
    assert "applyScenery(renderer, scene, sceneState.scenery)" in RIDE3D_JS


def test_ride3d_camera_follows_route_path():
    """The camera moves through a fixed world along the compiled path."""
    assert "function updateCamera(sceneState)" in RIDE3D_JS
    assert "activePath.poseAt(distanceM)" in RIDE3D_JS
    assert "activePath.poseAt(distanceM + LOOK_AHEAD_M)" in RIDE3D_JS
    assert "camera.lookAt(ahead.x" in RIDE3D_JS
    assert "camera.rotation.z += sceneState.cameraRoll" in RIDE3D_JS


def test_ride3d_render_loop_is_self_healing():
    """One bad frame must not kill the animation or strand the camera."""
    # Next frame is scheduled before the frame body can throw.
    assert RIDE3D_JS.index("requestAnimationFrame(frame);") < RIDE3D_JS.index(
        "const sceneState = motion.advance(dt, now)"
    )
    assert "catch (error)" in RIDE3D_JS
    assert "frameErrorCount" in RIDE3D_JS
    assert "__rideDebug" in RIDE3D_JS
    # Camera recovers from non-finite distances and degenerate look targets.
    assert "Number.isFinite(distanceM)" in RIDE3D_JS
    assert "pose.headingRad" in RIDE3D_JS


def test_ride3d_renders_pacer_riders_on_route_path():
    """The pacer pack rides the same world-fixed path as the camera."""
    assert "const pacerGroup = new THREE.Group()" in RIDE3D_JS
    assert "new THREE.CapsuleGeometry" in RIDE3D_JS
    assert "function updatePacerRiders(sceneState, now)" in RIDE3D_JS
    assert "pacerGroup.visible = sceneState.active" in RIDE3D_JS
    assert "activePath.poseAt(pacerDistanceM)" in RIDE3D_JS
    assert "updatePacerRiders(sceneState, now)" in RIDE3D_JS


def test_ride3d_renders_player_cockpit_from_motion_state():
    """Foreground cockpit gives the ride a first-person anchor."""
    assert "const cockpitGroup = new THREE.Group()" in RIDE3D_JS
    assert "camera.add(cockpitGroup)" in RIDE3D_JS
    assert "function updateCockpit(sceneState, now)" in RIDE3D_JS
    assert "cockpitGroup.visible = sceneState.active" in RIDE3D_JS
    assert "frontWheel.rotation.x" in RIDE3D_JS
    assert "updateCockpit(sceneState, now)" in RIDE3D_JS


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
