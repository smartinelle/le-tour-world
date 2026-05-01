import * as THREE from "https://esm.sh/three@0.164.1";
import { RideApiClient } from "/static/ride_client.js";
import { RideMotionModel } from "/static/ride_motion.js";

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0xd9edf7, 1);

const sceneryPalettes = {
  fields: {
    sky: 0xd9edf7,
    ground: 0x8fae76,
    shoulder: 0xb7c5ac,
    hills: 0x6f8b61,
  },
  forest: {
    sky: 0xcfe3df,
    ground: 0x496d45,
    shoulder: 0x6f825f,
    hills: 0x2f5d38,
  },
  village: {
    sky: 0xd7e5e8,
    ground: 0x9aa174,
    shoulder: 0xc0b69d,
    hills: 0x7b855d,
  },
  ridge: {
    sky: 0xdce6ef,
    ground: 0x6d8060,
    shoulder: 0xa8aa9a,
    hills: 0x64715a,
  },
  river: {
    sky: 0xc9e6f1,
    ground: 0x78a875,
    shoulder: 0x9ebea7,
    hills: 0x598261,
  },
};

const surfaceColors = {
  asphalt: 0x202421,
  gravel: 0x6f6758,
  dirt: 0x72543e,
};

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

const roadGroup = new THREE.Group();
scene.add(roadGroup);

const groundMaterial = new THREE.MeshLambertMaterial({ color: 0x8fae76 });
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(220, 260),
  groundMaterial,
);
ground.rotation.x = -Math.PI / 2;
ground.position.z = -54;
roadGroup.add(ground);

const roadMaterial = new THREE.MeshLambertMaterial({ color: 0x202421 });
const road = new THREE.Mesh(
  new THREE.PlaneGeometry(8.6, 260),
  roadMaterial,
);
road.rotation.x = -Math.PI / 2;
road.position.y = 0.015;
road.position.z = -54;
roadGroup.add(road);

const shoulderMaterial = new THREE.MeshLambertMaterial({ color: 0xb7c5ac });
const shoulders = [];
for (const x of [-5.4, 5.4]) {
  const shoulder = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 260),
    shoulderMaterial,
  );
  shoulder.rotation.x = -Math.PI / 2;
  shoulder.position.set(x, 0.02, -54);
  shoulder.userData.side = x < 0 ? -1 : 1;
  shoulders.push(shoulder);
  roadGroup.add(shoulder);
}

const laneGroup = new THREE.Group();
const dashMaterial = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
for (let i = 0; i < 34; i += 1) {
  const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 3.4), dashMaterial);
  dash.rotation.x = -Math.PI / 2;
  dash.position.set(0, 0.035, 8 - i * 7.8);
  laneGroup.add(dash);
}
roadGroup.add(laneGroup);

const railMaterial = new THREE.MeshLambertMaterial({ color: 0x566052 });
const postGeometry = new THREE.BoxGeometry(0.12, 0.9, 0.12);
const railPosts = [];
for (const x of [-6.75, 6.75]) {
  for (let i = 0; i < 30; i += 1) {
    const post = new THREE.Mesh(postGeometry, railMaterial);
    post.position.set(x, 0.48, 9 - i * 8.5);
    post.userData.side = x < 0 ? -1 : 1;
    railPosts.push(post);
    roadGroup.add(post);
  }
}

const curveChevronGroup = new THREE.Group();
const chevronMaterial = new THREE.MeshLambertMaterial({
  color: 0xf97316,
  transparent: true,
  opacity: 0,
});
const chevronGeometry = new THREE.BoxGeometry(0.95, 0.2, 0.08);
for (let i = 0; i < 7; i += 1) {
  const chevron = new THREE.Group();
  const top = new THREE.Mesh(chevronGeometry, chevronMaterial);
  const bottom = new THREE.Mesh(chevronGeometry, chevronMaterial);
  top.rotation.z = 0.55;
  bottom.rotation.z = -0.55;
  top.position.y = 0.16;
  bottom.position.y = -0.16;
  chevron.add(top, bottom);
  chevron.position.set(5.9, 1.2, -16 - i * 8);
  curveChevronGroup.add(chevron);
}
roadGroup.add(curveChevronGroup);

const segmentGate = new THREE.Group();
const gateMaterial = new THREE.MeshLambertMaterial({
  color: 0xf8fafc,
  transparent: true,
  opacity: 0,
});
const gateAccentMaterial = new THREE.MeshLambertMaterial({
  color: 0xea580c,
  transparent: true,
  opacity: 0,
});
const gatePostGeometry = new THREE.BoxGeometry(0.16, 2.4, 0.16);
const gateBarGeometry = new THREE.BoxGeometry(8.4, 0.16, 0.16);
for (const x of [-4.7, 4.7]) {
  const gatePost = new THREE.Mesh(gatePostGeometry, gateMaterial);
  gatePost.position.set(x, 1.2, -23);
  segmentGate.add(gatePost);
}
const gateBar = new THREE.Mesh(gateBarGeometry, gateAccentMaterial);
gateBar.position.set(0, 2.4, -23);
segmentGate.add(gateBar);
segmentGate.visible = false;
roadGroup.add(segmentGate);

const hills = new THREE.Group();
const hillMaterial = new THREE.MeshLambertMaterial({ color: 0x6f8b61 });
for (let i = 0; i < 9; i += 1) {
  const hill = new THREE.Mesh(
    new THREE.ConeGeometry(14 + i * 1.4, 8 + i, 5),
    hillMaterial,
  );
  hill.position.set(
    i % 2 === 0 ? -22 - i * 4 : 22 + i * 4,
    3.5,
    -38 - i * 12,
  );
  hill.rotation.y = i * 0.37;
  hills.add(hill);
}
scene.add(hills);

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
  rider.userData.depth = -18 - i * 9;
  rider.userData.phase = i * 0.8;
  pacerGroup.add(rider);
}
roadGroup.add(pacerGroup);

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
  routeHud: document.querySelector("#route-hud"),
  routeSelect: document.querySelector("#route-select"),
};

const rideClient = new RideApiClient();
let motion = new RideMotionModel({ dashSpacing: 7.8 });
let activeScenery = "fields";
let routeProfile = { update() {} };
let elevationProfile = { update() {} };
let selectedRouteId = null;

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

function applyScenery(scenery) {
  if (scenery === activeScenery) return;

  const palette = sceneryPalettes[scenery] || sceneryPalettes.fields;
  activeScenery = scenery;
  renderer.setClearColor(palette.sky, 1);
  scene.fog.color.setHex(palette.sky);
  groundMaterial.color.setHex(palette.ground);
  shoulderMaterial.color.setHex(palette.shoulder);
  hillMaterial.color.setHex(palette.hills);
}

function applySurface(surface) {
  roadMaterial.color.setHex(surfaceColors[surface] || surfaceColors.asphalt);
}

function updateSegmentGate(sceneState) {
  const opacity = sceneState.segmentGateAlpha;
  segmentGate.visible = opacity > 0.02;
  gateMaterial.opacity = opacity * 0.75;
  gateAccentMaterial.opacity = opacity;
  gateAccentMaterial.color.setHex(
    sceneState.nextSegmentGradePct >= 0 ? 0xea580c : 0x38bdf8,
  );
  segmentGate.position.z = (1 - opacity) * -8;
}

function updateRoadGeometry(sceneState) {
  road.scale.x = sceneState.roadScaleX;
  shoulders.forEach((shoulder) => {
    shoulder.position.x = shoulder.userData.side * sceneState.shoulderSpreadM;
  });
  railPosts.forEach((post) => {
    post.position.x = post.userData.side * (sceneState.shoulderSpreadM + 1.35);
  });
}

function updateCurveChevrons(sceneState) {
  const curve = sceneState.routeCurveStrength;
  const side = curve >= 0 ? 1 : -1;
  const opacity = Math.min(Math.abs(curve) * 1.25, 0.9);
  chevronMaterial.opacity = opacity;
  curveChevronGroup.visible = opacity > 0.04;
  curveChevronGroup.children.forEach((chevron, index) => {
    chevron.position.x = side * (sceneState.shoulderSpreadM + 1.45);
    chevron.position.z = -16 - index * 8 + sceneState.roadOffset * 0.45;
    chevron.rotation.y = side > 0 ? -0.45 : 0.45;
    chevron.scale.setScalar(1 + opacity * 0.25);
  });
}

function updatePacerRiders(sceneState, now) {
  pacerGroup.visible = sceneState.active;
  pacerGroup.children.forEach((rider, index) => {
    const lane = rider.userData.lane;
    const phase = rider.userData.phase;
    const depth =
      rider.userData.depth +
      Math.sin(now * 0.001 + phase) * 1.4 +
      sceneState.routeCurveStrength * index;
    rider.position.set(
      lane + sceneState.routeCurveStrength * 0.9,
      0,
      depth + sceneState.roadOffset * 0.28,
    );
    rider.rotation.y = sceneState.worldYaw * 0.5;
    rider.rotation.z = Math.sin(now * 0.006 + phase) * 0.035;
  });
}

function formatValue(value, fallback = "--") {
  return value === null || value === undefined ? fallback : String(value);
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
  laneGroup.children.forEach((dash, index) => {
    dash.position.z = 8 - index * 7.8 + sceneState.roadOffset;
    if (dash.position.z > 12) dash.position.z -= 34 * 7.8;
  });

  roadGroup.rotation.x = sceneState.roadPitch;
  roadGroup.rotation.y = sceneState.worldYaw;
  updateRoadGeometry(sceneState);
  hills.position.y = sceneState.horizonLift;
  hills.position.x = sceneState.sceneryDrift;
  hills.rotation.y = sceneState.routeSegmentProgress * 0.08;
  applyScenery(sceneState.scenery);
  applySurface(sceneState.routeSurface);
  updateSegmentGate(sceneState);
  updateCurveChevrons(sceneState);
  updatePacerRiders(sceneState, now);
  camera.position.y = 3.6 + sceneState.cameraBob;
  camera.lookAt(sceneState.cameraLookX, 0.35 + sceneState.cameraPitch, -22);
  camera.rotation.z += sceneState.cameraRoll;
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
    dashSpacing: 7.8,
    routeSegments: route.segments,
  });
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
  attachControls();
  resize();
  connectSnapshots();
  requestAnimationFrame(frame);
}

initializeRide3d().catch((error) => {
  hud.state.textContent = "Route data unavailable";
  throw error;
});
