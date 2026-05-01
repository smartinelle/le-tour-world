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
for (const x of [-5.4, 5.4]) {
  const shoulder = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 260),
    shoulderMaterial,
  );
  shoulder.rotation.x = -Math.PI / 2;
  shoulder.position.set(x, 0.02, -54);
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
for (const x of [-6.75, 6.75]) {
  for (let i = 0; i < 30; i += 1) {
    const post = new THREE.Mesh(postGeometry, railMaterial);
    post.position.set(x, 0.48, 9 - i * 8.5);
    roadGroup.add(post);
  }
}

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
};

const rideClient = new RideApiClient();
const motion = new RideMotionModel({ dashSpacing: 7.8 });
let activeScenery = "fields";

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

const routeProfile = createRouteProfile(hud.statusPanel);

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

  hud.startPanel.hidden = Boolean(snapshot.active);
  hud.activeControls.hidden = !snapshot.active;
  hud.pauseButton.textContent = snapshot.paused ? "Resume" : "Pause";
  hud.ergControls.hidden = !snapshot.active || snapshot.mode !== "erg";
  hud.simControls.hidden = !snapshot.active || snapshot.mode !== "sim";
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
        updateHud(await rideClient.startRide(button.dataset.startMode));
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
  hills.position.y = sceneState.horizonLift;
  hills.rotation.y = sceneState.routeSegmentProgress * 0.08;
  applyScenery(sceneState.scenery);
  camera.position.y = 3.6 + sceneState.cameraBob;
  camera.lookAt(0, 0.35 + sceneState.cameraPitch, -22);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

window.addEventListener("resize", resize);
attachControls();
resize();
connectSnapshots();
requestAnimationFrame(frame);
