// Static world construction for the /ride3d surface.
//
// Everything here is built ONCE per route load from the compiled route path.
// The per-frame loop only moves the camera and a handful of actors; no
// geometry is rebuilt while riding. Long static runs (dashes, posts, props,
// chevrons) are baked into a few merged vertex-colored meshes so the whole
// world stays within a small draw-call budget until M2 introduces instancing.

import * as THREE from "/static/vendor/three.module.js";

export const sceneryPalettes = {
  fields: { sky: 0xd9edf7, ground: 0x8fae76, shoulder: 0xb7c5ac, hills: 0x6f8b61 },
  forest: { sky: 0xcfe3df, ground: 0x496d45, shoulder: 0x6f825f, hills: 0x2f5d38 },
  village: { sky: 0xd7e5e8, ground: 0x9aa174, shoulder: 0xc0b69d, hills: 0x7b855d },
  ridge: { sky: 0xdce6ef, ground: 0x6d8060, shoulder: 0xa8aa9a, hills: 0x64715a },
  river: { sky: 0xc9e6f1, ground: 0x78a875, shoulder: 0x9ebea7, hills: 0x598261 },
};

export const surfaceColors = {
  asphalt: 0x202421,
  gravel: 0x6f6758,
  dirt: 0x72543e,
};

const propColors = {
  trunk: 0x5b3b24,
  foliage: 0x1f6b3b,
  wall: 0xd8c3a5,
  roof: 0x8f3c2e,
  rock: 0x7b8176,
  field: 0xd8b35c,
};

const DASH_SPACING_M = 7.8;
const POST_SPACING_M = 8.5;
const CHEVRON_SPACING_M = 30;
const PROP_CHUNK_M = 400;
const GROUND_HALF_WIDTH_M = 80;
const COLOR_BLEND_SAMPLES = 5;

// Shared materials that applyScenery retunes as the rider crosses scenery.
const baseGroundMaterial = new THREE.MeshLambertMaterial({ color: 0x8fae76 });
const hillMaterial = new THREE.MeshLambertMaterial({ color: 0x6f8b61 });
const vertexColorMaterial = new THREE.MeshLambertMaterial({ vertexColors: true });
const dashMaterial = new THREE.MeshBasicMaterial({ color: 0xf8fafc });
const waterMaterial = new THREE.MeshLambertMaterial({
  color: 0x1d8db8,
  transparent: true,
  opacity: 0.82,
});
const gateMaterial = new THREE.MeshLambertMaterial({ color: 0xf8fafc });
const gateUphillMaterial = new THREE.MeshLambertMaterial({ color: 0xea580c });
const gateDownhillMaterial = new THREE.MeshLambertMaterial({ color: 0x38bdf8 });

let activeScenery = null;

export function applyScenery(renderer, scene, scenery) {
  if (scenery === activeScenery) return;
  const palette = sceneryPalettes[scenery] || sceneryPalettes.fields;
  activeScenery = scenery;
  renderer.setClearColor(palette.sky, 1);
  scene.fog.color.setHex(palette.sky);
  baseGroundMaterial.color.setHex(palette.ground);
  hillMaterial.color.setHex(palette.hills);
}

function pseudoRandom(seed) {
  const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return value - Math.floor(value);
}

// Merge already-transformed, vertex-colored geometries into one buffer.
function mergeGeometries(geometries) {
  let vertexCount = 0;
  geometries.forEach((geometry) => {
    vertexCount += geometry.getAttribute("position").count;
  });
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const colors = new Float32Array(vertexCount * 3);
  let offset = 0;
  geometries.forEach((geometry) => {
    positions.set(geometry.getAttribute("position").array, offset * 3);
    normals.set(geometry.getAttribute("normal").array, offset * 3);
    colors.set(geometry.getAttribute("color").array, offset * 3);
    offset += geometry.getAttribute("position").count;
    geometry.dispose();
  });
  const merged = new THREE.BufferGeometry();
  merged.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  merged.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  merged.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return merged;
}

// Flatten a template geometry: apply a world transform and bake a flat color.
const bakeColor = new THREE.Color();
function bakeGeometry(geometry, matrix, colorHex) {
  const baked = geometry.index ? geometry.toNonIndexed() : geometry.clone();
  baked.applyMatrix4(matrix);
  const count = baked.getAttribute("position").count;
  const colors = new Float32Array(count * 3);
  bakeColor.setHex(colorHex);
  for (let index = 0; index < count; index += 1) {
    colors[index * 3] = bakeColor.r;
    colors[index * 3 + 1] = bakeColor.g;
    colors[index * 3 + 2] = bakeColor.b;
  }
  baked.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return baked;
}

const bakeMatrix = new THREE.Matrix4();
const bakePosition = new THREE.Vector3();
const bakeQuaternion = new THREE.Quaternion();
const bakeEuler = new THREE.Euler();
const bakeScale = new THREE.Vector3();
function transformMatrix({ x = 0, y = 0, z = 0, rotationX = 0, rotationY = 0, rotationZ = 0, scale = 1 }) {
  bakePosition.set(x, y, z);
  bakeEuler.set(rotationX, rotationY, rotationZ);
  bakeQuaternion.setFromEuler(bakeEuler);
  bakeScale.setScalar(scale);
  return bakeMatrix.compose(bakePosition, bakeQuaternion, bakeScale).clone();
}

// Ribbon along the whole path with per-sample width offsets and colors.
function ribbonGeometry(samples, innerOffset, outerOffset, yLift, colorAt) {
  const positions = [];
  const colors = [];
  const indices = [];
  const color = new THREE.Color();

  samples.forEach((sample, index) => {
    const rightX = Math.cos(sample.headingRad);
    const rightZ = Math.sin(sample.headingRad);
    color.setHex(colorAt(index));
    [innerOffset(sample.roadWidthM), outerOffset(sample.roadWidthM)].forEach(
      (offset) => {
        positions.push(
          sample.x + rightX * offset,
          sample.y + yLift,
          sample.z + rightZ * offset,
        );
        colors.push(color.r, color.g, color.b);
      },
    );
    if (index < samples.length - 1) {
      const vertex = index * 2;
      indices.push(vertex, vertex + 1, vertex + 2);
      indices.push(vertex + 1, vertex + 3, vertex + 2);
    }
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

// Average a palette color over neighboring samples so scenery transitions
// paint gradually across the ground instead of switching on a hard line.
function blendedPaletteColor(samples, index, pick) {
  let r = 0;
  let g = 0;
  let b = 0;
  const color = new THREE.Color();
  for (let tap = -COLOR_BLEND_SAMPLES; tap <= COLOR_BLEND_SAMPLES; tap += 1) {
    const neighbor =
      samples[(index + tap + samples.length * 8) % samples.length];
    const palette = sceneryPalettes[neighbor.scenery] || sceneryPalettes.fields;
    color.setHex(pick(palette));
    r += color.r;
    g += color.g;
    b += color.b;
  }
  const taps = COLOR_BLEND_SAMPLES * 2 + 1;
  color.setRGB(r / taps, g / taps, b / taps);
  return color.getHex();
}

function createTreeProp() {
  const prop = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 0.7, 7));
  trunk.userData.colorHex = propColors.trunk;
  const crown = new THREE.Mesh(new THREE.ConeGeometry(0.52, 1.25, 7));
  crown.userData.colorHex = propColors.foliage;
  trunk.position.y = 0.35;
  crown.position.y = 1.18;
  prop.add(trunk, crown);
  return prop;
}

function createVillageProp() {
  const prop = new THREE.Group();
  const wall = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.62, 0.8));
  wall.userData.colorHex = propColors.wall;
  const roof = new THREE.Mesh(new THREE.ConeGeometry(0.72, 0.42, 4));
  roof.userData.colorHex = propColors.roof;
  wall.position.y = 0.31;
  roof.position.y = 0.83;
  roof.rotation.y = Math.PI / 4;
  prop.add(wall, roof);
  return prop;
}

function createRockProp() {
  const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.42, 0));
  rock.userData.colorHex = propColors.rock;
  rock.position.y = 0.38;
  rock.scale.set(1.25, 0.72, 0.9);
  const prop = new THREE.Group();
  prop.add(rock);
  return prop;
}

function createFieldProp() {
  const bale = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.56, 14));
  bale.userData.colorHex = propColors.field;
  bale.position.y = 0.34;
  bale.rotation.z = Math.PI / 2;
  const prop = new THREE.Group();
  prop.add(bale);
  return prop;
}

const propBuilders = {
  fields: createFieldProp,
  forest: createTreeProp,
  village: createVillageProp,
  ridge: createRockProp,
  river: createTreeProp,
};

const propSpacingM = {
  fields: 40,
  forest: 18,
  village: 30,
  ridge: 35,
  river: 30,
};

function bakePropAt(prop, pose, side, offsetM, scale) {
  const rightX = Math.cos(pose.headingRad);
  const rightZ = Math.sin(pose.headingRad);
  prop.position.set(
    pose.x + rightX * side * offsetM,
    pose.y,
    pose.z + rightZ * side * offsetM,
  );
  prop.rotation.y = -pose.headingRad + side * 0.18;
  prop.scale.setScalar(scale);
  prop.updateMatrixWorld(true);
  const baked = [];
  prop.traverse((node) => {
    if (node.isMesh) {
      baked.push(bakeGeometry(node.geometry, node.matrixWorld, node.userData.colorHex));
      node.geometry.dispose();
    }
  });
  return baked;
}

function buildRoadSurfaces(path, group) {
  const samples = path.samples;
  const road = new THREE.Mesh(
    ribbonGeometry(
      samples,
      (widthM) => -widthM / 2,
      (widthM) => widthM / 2,
      0.02,
      (index) => surfaceColors[samples[index].surface] || surfaceColors.asphalt,
    ),
    vertexColorMaterial,
  );
  group.add(road);

  [-1, 1].forEach((side) => {
    const shoulder = new THREE.Mesh(
      ribbonGeometry(
        samples,
        (widthM) => side * (widthM / 2),
        (widthM) => side * (widthM / 2 + 1.8),
        0.012,
        (index) => blendedPaletteColor(samples, index, (palette) => palette.shoulder),
      ),
      vertexColorMaterial,
    );
    group.add(shoulder);
  });

  const corridor = new THREE.Mesh(
    ribbonGeometry(
      samples,
      () => -GROUND_HALF_WIDTH_M,
      () => GROUND_HALF_WIDTH_M,
      -0.06,
      (index) => blendedPaletteColor(samples, index, (palette) => palette.ground),
    ),
    vertexColorMaterial,
  );
  group.add(corridor);
}

function buildLaneDashes(path, group) {
  const template = new THREE.PlaneGeometry(0.16, 3.4);
  const baked = [];
  for (let distanceM = 0; distanceM < path.lengthM; distanceM += DASH_SPACING_M) {
    const pose = path.poseAt(distanceM);
    baked.push(
      bakeGeometry(
        template,
        transformMatrix({
          x: pose.x,
          y: pose.y + 0.045,
          z: pose.z,
          rotationX: -Math.PI / 2,
          rotationZ: -pose.headingRad,
        }),
        0xf8fafc,
      ),
    );
  }
  template.dispose();
  const dashes = new THREE.Mesh(mergeGeometries(baked), dashMaterial);
  group.add(dashes);
}

function buildRailPosts(path, group) {
  const template = new THREE.BoxGeometry(0.12, 0.9, 0.12);
  const baked = [];
  for (let distanceM = 0; distanceM < path.lengthM; distanceM += POST_SPACING_M) {
    const pose = path.poseAt(distanceM);
    const rightX = Math.cos(pose.headingRad);
    const rightZ = Math.sin(pose.headingRad);
    const edgeM = pose.roadWidthM / 2 + 2.3;
    [-1, 1].forEach((side) => {
      baked.push(
        bakeGeometry(
          template,
          transformMatrix({
            x: pose.x + rightX * side * edgeM,
            y: pose.y + 0.48,
            z: pose.z + rightZ * side * edgeM,
          }),
          0x566052,
        ),
      );
    });
  }
  template.dispose();
  const posts = new THREE.Mesh(mergeGeometries(baked), vertexColorMaterial);
  group.add(posts);
}

function buildCurveChevrons(path, group) {
  const barTemplate = new THREE.BoxGeometry(0.95, 0.2, 0.08);
  const baked = [];
  path.segmentBoundaries.forEach(({ startM, endM, segment }) => {
    if (Math.abs(segment.turnDeg) < 20) return;
    const side = segment.turnDeg >= 0 ? 1 : -1;
    for (
      let distanceM = startM + CHEVRON_SPACING_M / 2;
      distanceM < endM;
      distanceM += CHEVRON_SPACING_M
    ) {
      const pose = path.poseAt(distanceM);
      const rightX = Math.cos(pose.headingRad);
      const rightZ = Math.sin(pose.headingRad);
      const offsetM = pose.roadWidthM / 2 + 2.9;
      [0.55, -0.55].forEach((tilt, tiltIndex) => {
        baked.push(
          bakeGeometry(
            barTemplate,
            transformMatrix({
              x: pose.x + rightX * side * offsetM,
              y: pose.y + 1.2 + (tiltIndex === 0 ? 0.16 : -0.16),
              z: pose.z + rightZ * side * offsetM,
              rotationY: -pose.headingRad,
              rotationZ: side * tilt,
            }),
            0xf97316,
          ),
        );
      });
    }
  });
  barTemplate.dispose();
  if (baked.length === 0) return;
  const chevrons = new THREE.Mesh(mergeGeometries(baked), vertexColorMaterial);
  group.add(chevrons);
}

function buildSegmentGates(path, group) {
  const postGeometry = new THREE.BoxGeometry(0.16, 2.4, 0.16);
  const barGeometry = new THREE.BoxGeometry(8.4, 0.16, 0.16);
  path.segmentBoundaries.forEach(({ endM }, index) => {
    const nextSegment =
      path.segmentBoundaries[(index + 1) % path.segmentBoundaries.length].segment;
    const pose = path.poseAt(endM);
    const gate = new THREE.Group();
    [-4.7, 4.7].forEach((offset) => {
      const post = new THREE.Mesh(postGeometry, gateMaterial);
      post.position.x = offset;
      post.position.y = 1.2;
      gate.add(post);
    });
    const bar = new THREE.Mesh(
      barGeometry,
      nextSegment.gradePct >= 0 ? gateUphillMaterial : gateDownhillMaterial,
    );
    bar.position.y = 2.4;
    gate.add(bar);
    gate.position.set(pose.x, pose.y, pose.z);
    gate.rotation.y = -pose.headingRad;
    gate.scale.x = Math.max(0.68, pose.roadWidthM / 8.6);
    gate.updateMatrixWorld(true);
    gate.matrixAutoUpdate = false;
    group.add(gate);
  });
}

function buildProps(path, group) {
  const chunks = new Map();
  let distanceM = 0;
  let placementIndex = 0;
  while (distanceM < path.lengthM) {
    const pose = path.poseAt(distanceM);
    const builder = propBuilders[pose.scenery] || createFieldProp;
    const side = placementIndex % 2 === 0 ? -1 : 1;
    const jitter = pseudoRandom(placementIndex);
    const offsetM = pose.roadWidthM / 2 + 3.5 + jitter * 3.4;
    const scale = 0.72 + pseudoRandom(placementIndex + 57) * 0.4;
    const baked = bakePropAt(builder(), pose, side, offsetM, scale);
    const chunkKey = Math.floor(distanceM / PROP_CHUNK_M);
    if (!chunks.has(chunkKey)) chunks.set(chunkKey, []);
    chunks.get(chunkKey).push(...baked);
    distanceM += propSpacingM[pose.scenery] || 35;
    placementIndex += 1;
  }
  chunks.forEach((baked) => {
    const chunk = new THREE.Mesh(mergeGeometries(baked), vertexColorMaterial);
    chunk.matrixAutoUpdate = false;
    group.add(chunk);
  });
}

function buildRiverRibbons(path, group) {
  const samples = path.samples;
  let spanStart = null;
  const spans = [];
  samples.forEach((sample, index) => {
    const isRiver = sample.scenery === "river";
    if (isRiver && spanStart === null) spanStart = index;
    if ((!isRiver || index === samples.length - 1) && spanStart !== null) {
      spans.push([spanStart, isRiver ? index : index - 1]);
      spanStart = null;
    }
  });
  spans.forEach(([startIndex, endIndex]) => {
    if (endIndex - startIndex < 2) return;
    const spanSamples = samples.slice(startIndex, endIndex + 1);
    const river = new THREE.Mesh(
      ribbonGeometry(
        spanSamples,
        (widthM) => widthM / 2 + 4.6,
        (widthM) => widthM / 2 + 8.4,
        -0.35,
        () => 0x1d8db8,
      ),
      waterMaterial,
    );
    group.add(river);
  });
}

function buildBasePlaneAndHills(path, group) {
  const bounds = new THREE.Box3();
  path.samples.forEach((sample) => {
    bounds.expandByPoint(new THREE.Vector3(sample.x, sample.y, sample.z));
  });
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());

  const base = new THREE.Mesh(
    new THREE.PlaneGeometry(size.x + 1600, size.z + 1600),
    baseGroundMaterial,
  );
  base.rotation.x = -Math.PI / 2;
  base.position.set(center.x, bounds.min.y - 0.35, center.z);
  group.add(base);

  const hillCount = 14;
  const radiusX = size.x / 2 + 130;
  const radiusZ = size.z / 2 + 130;
  for (let index = 0; index < hillCount; index += 1) {
    const angle = (index / hillCount) * Math.PI * 2;
    const hill = new THREE.Mesh(
      new THREE.ConeGeometry(26 + pseudoRandom(index) * 22, 14 + pseudoRandom(index + 9) * 16, 5),
      hillMaterial,
    );
    hill.position.set(
      center.x + Math.cos(angle) * radiusX,
      bounds.min.y - 0.3,
      center.z + Math.sin(angle) * radiusZ,
    );
    hill.rotation.y = index * 0.37;
    hill.matrixAutoUpdate = false;
    hill.updateMatrix();
    group.add(hill);
  }
}

export function buildWorld(path) {
  const group = new THREE.Group();
  buildRoadSurfaces(path, group);
  buildLaneDashes(path, group);
  buildRailPosts(path, group);
  buildCurveChevrons(path, group);
  buildSegmentGates(path, group);
  buildProps(path, group);
  buildRiverRibbons(path, group);
  buildBasePlaneAndHills(path, group);

  return {
    group,
    dispose() {
      group.traverse((node) => {
        if (node.isMesh) node.geometry.dispose();
      });
    },
  };
}
