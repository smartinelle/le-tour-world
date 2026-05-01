import * as THREE from "https://esm.sh/three@0.164.1";

const canvas = document.querySelector("#scene");
const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0xd9edf7, 1);

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

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(220, 260),
  new THREE.MeshLambertMaterial({ color: 0x8fae76 }),
);
ground.rotation.x = -Math.PI / 2;
ground.position.z = -54;
scene.add(ground);

const road = new THREE.Mesh(
  new THREE.PlaneGeometry(8.6, 260),
  new THREE.MeshLambertMaterial({ color: 0x202421 }),
);
road.rotation.x = -Math.PI / 2;
road.position.y = 0.015;
road.position.z = -54;
scene.add(road);

const shoulderMaterial = new THREE.MeshLambertMaterial({ color: 0xb7c5ac });
for (const x of [-5.4, 5.4]) {
  const shoulder = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 260),
    shoulderMaterial,
  );
  shoulder.rotation.x = -Math.PI / 2;
  shoulder.position.set(x, 0.02, -54);
  scene.add(shoulder);
}

const laneGroup = new THREE.Group();
const dashMaterial = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
for (let i = 0; i < 34; i += 1) {
  const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 3.4), dashMaterial);
  dash.rotation.x = -Math.PI / 2;
  dash.position.set(0, 0.035, 8 - i * 7.8);
  laneGroup.add(dash);
}
scene.add(laneGroup);

const railMaterial = new THREE.MeshLambertMaterial({ color: 0x566052 });
const postGeometry = new THREE.BoxGeometry(0.12, 0.9, 0.12);
for (const x of [-6.75, 6.75]) {
  for (let i = 0; i < 30; i += 1) {
    const post = new THREE.Mesh(postGeometry, railMaterial);
    post.position.set(x, 0.48, 9 - i * 8.5);
    scene.add(post);
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
  power: document.querySelector("#power"),
  speed: document.querySelector("#speed"),
  cadence: document.querySelector("#cadence"),
  hr: document.querySelector("#heart-rate"),
  distance: document.querySelector("#distance"),
  state: document.querySelector("#state"),
  mode: document.querySelector("#mode"),
  startPanel: document.querySelector("#start-panel"),
  activeControls: document.querySelector("#active-controls"),
};

let ride = {
  active: false,
  paused: false,
  mode: null,
  speed_mps: 0,
  power_w: null,
  cadence_rpm: null,
  hr_bpm: null,
  distance_m: 0,
  session_state: "inactive",
};

function formatValue(value, fallback = "--") {
  return value === null || value === undefined ? fallback : String(value);
}

function updateHud(snapshot) {
  ride = snapshot;
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
    ? `${snapshot.mode || "free"} mode · ${snapshot.trainer_name || "demo source"}`
    : "Start a session to drive the road";

  hud.startPanel.hidden = Boolean(snapshot.active);
  hud.activeControls.hidden = !snapshot.active;
}

async function postRideAction(path, payload = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  updateHud(await response.json());
}

function attachControls() {
  document.querySelectorAll("[data-start-mode]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await postRideAction("/api/ride/start", {
          mode: button.dataset.startMode,
        });
      } finally {
        button.disabled = false;
      }
    });
  });

  const stopButton = document.querySelector("#stop-ride");
  stopButton.addEventListener("click", async () => {
    await postRideAction("/api/ride/stop");
    stopButton.blur();
  });
}

function connectSnapshots() {
  const source = new EventSource("/api/ride/snapshots");
  source.addEventListener("snapshot", (event) => {
    updateHud(JSON.parse(event.data));
  });
  source.onerror = () => {
    hud.state.textContent = "Snapshot stream disconnected";
  };
}

function resize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

let last = performance.now();
let roadOffset = 0;

function frame(now) {
  const dt = Math.min(0.06, (now - last) / 1000);
  last = now;

  const speed = ride.active && !ride.paused ? Math.max(0, ride.speed_mps || 0) : 0;
  roadOffset = (roadOffset + speed * dt) % 7.8;
  laneGroup.children.forEach((dash, index) => {
    dash.position.z = 8 - index * 7.8 + roadOffset;
    if (dash.position.z > 12) dash.position.z -= 34 * 7.8;
  });

  camera.position.y = 3.6 + Math.sin(now * 0.004) * 0.03 * Math.min(speed, 10);
  camera.lookAt(0, 0.35, -22);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

window.addEventListener("resize", resize);
attachControls();
resize();
connectSnapshots();
requestAnimationFrame(frame);
