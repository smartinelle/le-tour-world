import * as THREE from "/static/vendor/three.module.js";
import { RideApiClient } from "/static/ride_client.js?v=device-pairing";
import { RideMotionModel } from "/static/ride_motion.js?v=world-fixed";
import { buildRoutePath } from "/static/route_path.js?v=world-fixed";
import { applyScenery, buildWorld } from "/static/world_builder.js?v=world-fixed";

const CAMERA_HEIGHT_M = 3.6;
const LOOK_AHEAD_M = 22;

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0xd9edf7, 1);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xd9edf7, 80, 460);

const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 560);
camera.position.set(0, CAMERA_HEIGHT_M, 7.6);
camera.lookAt(0, 0.35, -22);
scene.add(camera);

const hemi = new THREE.HemisphereLight(0xffffff, 0x5d6b4f, 2.4);
scene.add(hemi);

const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(-10, 18, 8);
scene.add(sun);

// The world (road, ground, props, gates) is compiled once per route load by
// world_builder; the frame loop only moves the camera and the actors below.
let activePath = null;
let world = null;

const pacerGroup = new THREE.Group();
const pacerColors = [0xf97316, 0x2563eb, 0x16a34a, 0xe11d48, 0x9333ea];
for (let i = 0; i < 5; i += 1) {
  const rider = new THREE.Group();
  const body = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.16, 0.42, 5, 10),
    new THREE.MeshLambertMaterial({ color: pacerColors[i] }),
  );
  const helmet = new THREE.Mesh(
    new THREE.SphereGeometry(0.13, 12, 8),
    new THREE.MeshLambertMaterial({ color: 0xf8fafc }),
  );
  const bikeMaterial = new THREE.MeshLambertMaterial({ color: 0x111827 });
  const wheelGeometry = new THREE.TorusGeometry(0.18, 0.025, 6, 16);
  const frontWheel = new THREE.Mesh(wheelGeometry, bikeMaterial);
  const rearWheel = new THREE.Mesh(wheelGeometry, bikeMaterial);
  const frame = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.055, 0.055), bikeMaterial);
  body.position.y = 0.88;
  helmet.position.y = 1.28;
  frontWheel.rotation.y = Math.PI / 2;
  rearWheel.rotation.y = Math.PI / 2;
  frontWheel.position.set(0.34, 0.28, 0);
  rearWheel.position.set(-0.34, 0.28, 0);
  frame.position.y = 0.54;
  rider.add(body, helmet, frontWheel, rearWheel, frame);
  rider.userData.lane = (i - 2) * 0.58;
  rider.userData.gapM = 12 + i * 9;
  rider.userData.phase = i * 0.8;
  pacerGroup.add(rider);
}
scene.add(pacerGroup);

const cockpitGroup = new THREE.Group();
cockpitGroup.position.set(0, -1.72, -3.25);
const cockpitMaterial = new THREE.MeshLambertMaterial({ color: 0x111827 });
const cockpitAccentMaterial = new THREE.MeshLambertMaterial({ color: 0xf97316 });
const frontWheel = new THREE.Mesh(
  new THREE.TorusGeometry(0.42, 0.025, 8, 36),
  cockpitMaterial,
);
frontWheel.rotation.y = Math.PI / 2;
frontWheel.position.set(0, -0.16, -0.38);
const handlebar = new THREE.Mesh(
  new THREE.BoxGeometry(1.35, 0.055, 0.055),
  cockpitMaterial,
);
handlebar.position.set(0, 0.52, 0.1);
const stem = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.08, 0.72), cockpitMaterial);
stem.position.set(0, 0.26, -0.18);
stem.rotation.x = -0.48;
const headTube = new THREE.Mesh(
  new THREE.CapsuleGeometry(0.055, 0.46, 5, 10),
  cockpitAccentMaterial,
);
headTube.position.set(0, 0.1, -0.22);
headTube.rotation.x = -0.28;
cockpitGroup.add(frontWheel, handlebar, stem, headTube);
camera.add(cockpitGroup);

const hud = {
  statusPanel: document.querySelector(".status"),
  power: document.querySelector("#power"),
  speed: document.querySelector("#speed"),
  cadence: document.querySelector("#cadence"),
  hr: document.querySelector("#heart-rate"),
  distance: document.querySelector("#distance"),
  state: document.querySelector("#state"),
  mode: document.querySelector("#mode"),
  startPanel: document.querySelector("#start-panel"),
  activeControls: document.querySelector("#active-controls"),
  pauseButton: document.querySelector("#pause-ride"),
  ergControls: document.querySelector("#erg-controls"),
  ergTarget: document.querySelector("#erg-target"),
  simControls: document.querySelector("#sim-controls"),
  simGrade: document.querySelector("#sim-grade"),
  deviceStatus: document.querySelector("#device-status"),
  trainerDeviceLabel: document.querySelector("#trainer-device-label"),
  trainerDeviceAction: document.querySelector("#trainer-device-action"),
  hrDeviceLabel: document.querySelector("#hr-device-label"),
  hrDeviceAction: document.querySelector("#hr-device-action"),
  deviceResults: document.querySelector("#device-results"),
  routeHud: document.querySelector("#route-hud"),
  routeSelect: document.querySelector("#route-select"),
};

const rideClient = new RideApiClient();
let motion = new RideMotionModel({});
let routeProfile = { update() {} };
let elevationProfile = { update() {} };
let selectedRouteId = null;
let deviceState = { trainer: null, hr: null };

function createRouteProfile(parent) {
  const profile = document.createElement("div");
  const label = document.createElement("span");
  const detail = document.createElement("span");
  const track = document.createElement("div");
  const fill = document.createElement("div");

  profile.hidden = true;
  Object.assign(profile.style, {
    marginTop: "10px",
  });
  Object.assign(label.style, {
    display: "block",
    fontSize: "0.74rem",
    fontWeight: "800",
    letterSpacing: "0.08em",
    lineHeight: "1",
    marginBottom: "7px",
    textTransform: "uppercase",
  });
  Object.assign(track.style, {
    background: "rgba(17, 24, 39, 0.14)",
    borderRadius: "999px",
    height: "5px",
    overflow: "hidden",
  });
  Object.assign(fill.style, {
    background: "var(--accent)",
    borderRadius: "999px",
    height: "100%",
    transition: "width 160ms linear",
    width: "0%",
  });
  Object.assign(detail.style, {
    display: "block",
    fontSize: "0.68rem",
    fontWeight: "750",
    letterSpacing: "0.06em",
    lineHeight: "1",
    marginTop: "7px",
    opacity: "0.72",
    textTransform: "uppercase",
  });

  track.append(fill);
  profile.append(label, track, detail);
  parent.append(profile);

  return {
    update(sceneState, active) {
      profile.hidden = !active;
      label.textContent = `${sceneState.routeSegmentName} · ${sceneState.gradePct.toFixed(1)}%`;
      fill.style.width = `${Math.round(sceneState.routeSegmentProgress * 100)}%`;
      detail.textContent = `Next ${sceneState.nextSegmentName} in ${Math.round(sceneState.routeSegmentRemainingM)} m · ${sceneState.nextSegmentGradePct.toFixed(1)}%`;
    },
  };
}

function createElevationProfile(parent, route) {
  const ns = "http://www.w3.org/2000/svg";
  const panel = document.createElement("div");
  const label = document.createElement("span");
  const svg = document.createElementNS(ns, "svg");
  const elevationLine = document.createElementNS(ns, "polyline");
  const segmentLineGroup = document.createElementNS(ns, "g");
  const cursor = document.createElementNS(ns, "circle");

  const routeLengthM = Math.max(1, Number(route.distance_m) || 1);
  const elevationPoints = [{ distanceM: 0, elevationM: 0 }];
  let cursorDistanceM = 0;
  let elevationM = 0;
  route.segments.forEach((segment) => {
    const lengthM = Number(segment.length_m) || 0;
    elevationM += (lengthM * (Number(segment.grade_pct) || 0)) / 100;
    cursorDistanceM += lengthM;
    elevationPoints.push({ distanceM: cursorDistanceM, elevationM });
  });

  const minElevationM = Math.min(
    ...elevationPoints.map((point) => point.elevationM),
  );
  const maxElevationM = Math.max(
    ...elevationPoints.map((point) => point.elevationM),
  );
  const elevationRangeM = Math.max(1, maxElevationM - minElevationM);
  const xForDistance = (distanceM) => 10 + (distanceM / routeLengthM) * 300;
  const yForElevation = (valueM) =>
    58 - ((valueM - minElevationM) / elevationRangeM) * 42;
  const pointString = elevationPoints
    .map((point) => `${xForDistance(point.distanceM)},${yForElevation(point.elevationM)}`)
    .join(" ");

  panel.hidden = true;
  Object.assign(panel.style, {
    marginTop: "12px",
  });
  Object.assign(label.style, {
    display: "block",
    fontSize: "0.68rem",
    fontWeight: "800",
    letterSpacing: "0.08em",
    lineHeight: "1",
    marginBottom: "6px",
    opacity: "0.72",
    textTransform: "uppercase",
  });
  svg.setAttribute("viewBox", "0 0 320 72");
  svg.setAttribute("aria-hidden", "true");
  Object.assign(svg.style, {
    display: "block",
    height: "72px",
    width: "100%",
  });
  elevationLine.setAttribute("points", pointString);
  elevationLine.setAttribute("fill", "none");
  elevationLine.setAttribute("stroke", "var(--accent)");
  elevationLine.setAttribute("stroke-linecap", "round");
  elevationLine.setAttribute("stroke-linejoin", "round");
  elevationLine.setAttribute("stroke-width", "4");
  cursor.setAttribute("r", "4.5");
  cursor.setAttribute("fill", "#111827");
  cursor.setAttribute("stroke", "#ffffff");
  cursor.setAttribute("stroke-width", "2");

  cursorDistanceM = 0;
  route.segments.slice(0, -1).forEach((segment) => {
    cursorDistanceM += Number(segment.length_m) || 0;
    const marker = document.createElementNS(ns, "line");
    const markerX = xForDistance(cursorDistanceM);
    marker.setAttribute("x1", String(markerX));
    marker.setAttribute("x2", String(markerX));
    marker.setAttribute("y1", "14");
    marker.setAttribute("y2", "62");
    marker.setAttribute("stroke", "rgba(17, 24, 39, 0.18)");
    marker.setAttribute("stroke-width", "1");
    segmentLineGroup.append(marker);
  });

  svg.append(segmentLineGroup, elevationLine, cursor);
  panel.append(label, svg);
  parent.append(panel);

  return {
    update(sceneState, active) {
      panel.hidden = false;
      label.textContent = route.title;
      const routeDistanceM =
        ((sceneState.distanceM % routeLengthM) + routeLengthM) % routeLengthM;
      const currentElevationM =
        elevationPoints.reduce((current, point) => {
          return point.distanceM <= routeDistanceM ? point.elevationM : current;
        }, 0) || 0;
      cursor.setAttribute("cx", String(xForDistance(routeDistanceM)));
      cursor.setAttribute("cy", String(yForElevation(currentElevationM)));
      cursor.style.opacity = active ? "1" : "0.38";
    },
  };
}

function updateCamera(sceneState) {
  const pose = activePath.poseAt(sceneState.renderDistanceM);
  const ahead = activePath.poseAt(sceneState.renderDistanceM + LOOK_AHEAD_M);
  camera.position.set(
    pose.x,
    pose.y + CAMERA_HEIGHT_M + sceneState.cameraBob,
    pose.z,
  );
  camera.lookAt(ahead.x, ahead.y + 0.9, ahead.z);
  camera.rotation.z += sceneState.cameraRoll;
}

function updatePacerRiders(sceneState, now) {
  pacerGroup.visible = sceneState.active;
  if (!pacerGroup.visible) return;
  pacerGroup.children.forEach((rider) => {
    const pacerDistanceM =
      sceneState.renderDistanceM +
      rider.userData.gapM +
      Math.sin(now * 0.001 + rider.userData.phase) * 1.4;
    const pose = activePath.poseAt(pacerDistanceM);
    const rightX = Math.cos(pose.headingRad);
    const rightZ = Math.sin(pose.headingRad);
    rider.position.set(
      pose.x + rightX * rider.userData.lane,
      pose.y,
      pose.z + rightZ * rider.userData.lane,
    );
    rider.rotation.y = -pose.headingRad;
    rider.rotation.z = Math.sin(now * 0.006 + rider.userData.phase) * 0.035;
  });
}

function updateCockpit(sceneState, now) {
  cockpitGroup.visible = sceneState.active;
  cockpitGroup.rotation.z = sceneState.cameraRoll * 1.8;
  cockpitGroup.position.x = -sceneState.cameraLookX * 0.018;
  frontWheel.rotation.x = now * 0.012 * Math.max(0.2, sceneState.speedMps);
  handlebar.rotation.z = sceneState.routeCurveStrength * -0.08;
}

function formatValue(value, fallback = "--") {
  return value === null || value === undefined ? fallback : String(value);
}

function deviceNameForStatus(type, status) {
  if (status?.connected) {
    return status.name || (type === "trainer" ? "Trainer live" : "HR live");
  }
  return type === "trainer" ? "No trainer" : "No HR";
}

function sourceLabelForStatus(type, status) {
  if (status?.connected) return deviceNameForStatus(type, status);
  return type === "trainer" ? "No trainer · demo source" : "No HR · demo source";
}

function updateDeviceStatusLine(status = deviceState) {
  const trainerLabel = sourceLabelForStatus("trainer", status.trainer);
  const hrLabel = sourceLabelForStatus("hr", status.hr);
  hud.deviceStatus.textContent = `${trainerLabel} · ${hrLabel}`;
}

function updateDeviceControls(status = deviceState) {
  hud.trainerDeviceLabel.textContent = deviceNameForStatus("trainer", status.trainer);
  hud.hrDeviceLabel.textContent = deviceNameForStatus("hr", status.hr);
  hud.trainerDeviceAction.textContent = status.trainer?.connected ? "Disconnect" : "Scan";
  hud.hrDeviceAction.textContent = status.hr?.connected ? "Disconnect" : "Scan";
  updateDeviceStatusLine(status);
}

async function refreshDeviceStatus() {
  deviceState = await rideClient.getDeviceStatus();
  updateDeviceControls(deviceState);
  return deviceState;
}

function setDeviceResults(message, devices = [], type = "trainer") {
  hud.deviceResults.hidden = false;
  hud.deviceResults.replaceChildren();
  if (message) {
    const label = document.createElement("span");
    label.className = "control-value";
    label.textContent = message;
    hud.deviceResults.append(label);
  }

  devices.forEach((device) => {
    const button = document.createElement("button");
    const name = document.createElement("span");
    const signal = document.createElement("span");
    button.className = "action device-result";
    button.type = "button";
    name.textContent = device.name || "Unknown device";
    signal.textContent = device.rssi === null || device.rssi === undefined
      ? "Signal --"
      : `${device.rssi} dBm`;
    button.append(name, signal);
    button.addEventListener("click", async () => {
      await connectDevice(type, device.address, button);
    });
    hud.deviceResults.append(button);
  });
}

async function connectDevice(type, address, button) {
  if (!address) {
    setDeviceResults("Device address unavailable");
    return;
  }
  button.disabled = true;
  setDeviceResults("Connecting...");
  try {
    await rideClient.connectDevice(type, address);
    hud.deviceResults.hidden = true;
    await refreshDeviceStatus();
  } catch (error) {
    setDeviceResults(`Connection failed: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function handleDeviceAction(type, button) {
  const status = deviceState[type];
  button.disabled = true;
  try {
    if (status?.connected) {
      setDeviceResults(`Disconnecting ${deviceNameForStatus(type, status)}...`);
      await rideClient.disconnectDevice(type);
      hud.deviceResults.hidden = true;
      await refreshDeviceStatus();
      return;
    }

    const label = type === "trainer" ? "trainers" : "heart-rate monitors";
    setDeviceResults(`Scanning for ${label}...`);
    const result = await rideClient.scanDevices(type);
    const devices = result.devices || [];
    if (devices.length === 0) {
      setDeviceResults(`No ${label} found`);
    } else {
      setDeviceResults(`Found ${devices.length} ${label}`, devices, type);
    }
  } catch (error) {
    setDeviceResults(`Device action failed: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

function updateHud(snapshot) {
  const sceneState = motion.updateFromSnapshot(snapshot);
  hud.power.textContent = snapshot.active ? formatValue(snapshot.power_w) : "--";
  hud.speed.textContent =
    snapshot.active && snapshot.speed_mps
      ? (snapshot.speed_mps * 3.6).toFixed(1)
      : "--";
  hud.cadence.textContent = snapshot.active
    ? formatValue(snapshot.cadence_rpm)
    : "--";
  hud.hr.textContent = snapshot.active ? formatValue(snapshot.hr_bpm) : "--";
  hud.distance.textContent =
    snapshot.active && snapshot.distance_m
      ? `${(snapshot.distance_m / 1000).toFixed(2)} km`
      : "--";

  const state = snapshot.session_state || "inactive";
  hud.state.textContent =
    state === "active"
      ? "Live ride stream"
      : state === "paused"
        ? "Ride paused"
        : "Ready to ride";
  hud.mode.textContent = snapshot.active
    ? `${snapshot.mode || "free"} mode · ${sceneState.routeSegmentName} · ${sceneState.gradePct.toFixed(1)}%`
    : "Start a session to drive the road";
  updateDeviceStatusLine({
    trainer: {
      connected: snapshot.trainer_connected,
      name: snapshot.trainer_name,
    },
    hr: {
      connected: snapshot.hr_connected,
      name: snapshot.hr_name,
    },
  });
  routeProfile.update(sceneState, snapshot.active);
  elevationProfile.update(sceneState, snapshot.active);

  hud.startPanel.hidden = Boolean(snapshot.active);
  hud.activeControls.hidden = !snapshot.active;
  hud.pauseButton.textContent = snapshot.paused ? "Resume" : "Pause";
  hud.ergControls.hidden = !snapshot.active || snapshot.mode !== "erg";
  hud.simControls.hidden = !snapshot.active || snapshot.mode !== "sim";
  hud.routeSelect.disabled = Boolean(snapshot.active);
  hud.ergTarget.textContent = `Target ${snapshot.erg_target_w ?? "--"}W`;
  hud.simGrade.textContent = `Grade ${
    snapshot.sim_grade_pct === null || snapshot.sim_grade_pct === undefined
      ? "--"
      : snapshot.sim_grade_pct.toFixed(1)
  }%`;
}

function attachControls() {
  document.querySelectorAll("[data-start-mode]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        updateHud(
          await rideClient.startRide(button.dataset.startMode, selectedRouteId),
        );
      } finally {
        button.disabled = false;
      }
    });
  });

  const stopButton = document.querySelector("#stop-ride");
  stopButton.addEventListener("click", async () => {
    updateHud(await rideClient.stopRide());
    stopButton.blur();
  });

  const pauseButton = document.querySelector("#pause-ride");
  pauseButton.addEventListener("click", async () => {
    updateHud(await rideClient.togglePause());
    pauseButton.blur();
  });

  document.querySelectorAll("[data-erg-delta]").forEach((button) => {
    button.addEventListener("click", async () => {
      updateHud(await rideClient.adjustErgTarget(button.dataset.ergDelta));
      button.blur();
    });
  });

  document.querySelectorAll("[data-sim-delta]").forEach((button) => {
    button.addEventListener("click", async () => {
      updateHud(await rideClient.adjustSimGrade(button.dataset.simDelta));
      button.blur();
    });
  });

  hud.routeSelect.addEventListener("change", async () => {
    await loadRoute(hud.routeSelect.value);
  });

  hud.trainerDeviceAction.addEventListener("click", async () => {
    await handleDeviceAction("trainer", hud.trainerDeviceAction);
    hud.trainerDeviceAction.blur();
  });

  hud.hrDeviceAction.addEventListener("click", async () => {
    await handleDeviceAction("hr", hud.hrDeviceAction);
    hud.hrDeviceAction.blur();
  });
}

function connectSnapshots() {
  rideClient.connectSnapshots({
    onSnapshot: updateHud,
    onError: () => {
      hud.state.textContent = "Snapshot stream disconnected";
    },
  });
}

function resize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

let last = performance.now();

function frame(now) {
  const dt = Math.min(0.06, (now - last) / 1000);
  last = now;

  const sceneState = motion.advance(dt, now);
  if (activePath) {
    updateCamera(sceneState);
    updatePacerRiders(sceneState, now);
  }
  updateCockpit(sceneState, now);
  applyScenery(renderer, scene, sceneState.scenery);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

window.addEventListener("resize", resize);

function populateRouteSelect(routes) {
  hud.routeSelect.replaceChildren();
  routes.forEach((route) => {
    const option = document.createElement("option");
    option.value = route.id;
    option.textContent = `${route.title} · ${(route.distance_m / 1000).toFixed(1)} km`;
    hud.routeSelect.append(option);
  });
}

async function loadRoute(routeId) {
  const route = await rideClient.getRoute(routeId);
  selectedRouteId = route.id;
  hud.routeSelect.value = route.id;
  motion = new RideMotionModel({
    routeSegments: route.segments,
  });

  if (world) {
    scene.remove(world.group);
    world.dispose();
  }
  activePath = buildRoutePath(route);
  world = buildWorld(activePath);
  scene.add(world.group);
  console.info(
    `route path compiled: ${route.id}, ${activePath.samples.length} samples, ` +
      `loop closed with ${activePath.closure.extraTurns} extra turn(s), ` +
      `${activePath.closure.driftM.toFixed(1)} m horizontal / ` +
      `${activePath.closure.elevationDriftM.toFixed(1)} m vertical drift redistributed`,
  );

  hud.routeHud.replaceChildren();
  routeProfile = createRouteProfile(hud.routeHud);
  elevationProfile = createElevationProfile(hud.routeHud, route);
  updateHud({
    active: false,
    paused: false,
    mode: null,
    distance_m: 0,
    power_w: null,
    speed_mps: null,
    cadence_rpm: null,
    hr_bpm: null,
    session_state: "inactive",
    erg_target_w: null,
    sim_grade_pct: null,
  });
}

async function initializeRide3d() {
  const routes = await rideClient.getRoutes();
  populateRouteSelect(routes);
  await loadRoute(routes[0]?.id ?? null);
  await refreshDeviceStatus();
  attachControls();
  resize();
  connectSnapshots();
  requestAnimationFrame(frame);
}

initializeRide3d().catch((error) => {
  hud.state.textContent = "Route data unavailable";
  throw error;
});
