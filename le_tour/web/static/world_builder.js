// Static world construction for the /ride3d surface.
//
// Everything here is built ONCE per route load from the compiled route path.
// The per-frame loop only moves the camera and a handful of actors; no
// geometry is rebuilt while riding. The ground is a corridor terrain grid:
// seeded value-noise blended into the road elevation with a cubic falloff
// (architecture.md's deformation, precomputed instead of chunk-streamed).
// Props ride InstancedMesh - one draw call per template part - and sample
// the same terrain height function, so nothing floats or sinks.

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

// Terrain character per scenery: noise amplitude and how hard the ground
// falls away laterally (the ridge crest drops on both sides).
const terrainProfiles = {
  fields: { amplitudeM: 4.0, lateralDropPerM: 0.02 },
  forest: { amplitudeM: 9.0, lateralDropPerM: 0.05 },
  village: { amplitudeM: 3.0, lateralDropPerM: 0.01 },
  ridge: { amplitudeM: 6.0, lateralDropPerM: 0.3 },
  river: { amplitudeM: 2.5, lateralDropPerM: 0.04 },
};

// Fog per scenery: forests close in, the ridge opens up.
const fogProfiles = {
  fields: { nearM: 90, farM: 520 },
  forest: { nearM: 45, farM: 300 },
  village: { nearM: 80, farM: 450 },
  ridge: { nearM: 120, farM: 760 },
  river: { nearM: 70, farM: 420 },
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
const TERRAIN_ROW_SPACING_M = 8;
const GROUND_HALF_WIDTH_M = 160;
const TERRAIN_LATERAL_OFFSETS_M = [
  -160, -120, -90, -65, -45, -30, -18, -8, 0, 8, 18, 30, 45, 65, 90, 120, 160,
];
const ROAD_FLAT_HALF_WIDTH_M = 8; // road + shoulders stay untouched
const TERRAIN_BLEND_END_M = 40; // full terrain beyond this lateral distance
const COLOR_BLEND_SAMPLES = 5;
const PARAM_BLEND_ROWS = 25; // ~200 m of terrain-character crossfade

// Shared materials that applyScenery retunes as the rider crosses scenery.
const baseGroundMaterial = new THREE.MeshLambertMaterial({ color: 0x8fae76 });
const skydomeMaterial = new THREE.MeshBasicMaterial({
  color: 0xd9edf7,
  side: THREE.BackSide,
  vertexColors: true,
  depthWrite: false,
  depthTest: false,
  fog: false,
});
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
  const fog = fogProfiles[scenery] || fogProfiles.fields;
  activeScenery = scenery;
  renderer.setClearColor(palette.sky, 1);
  scene.fog.color.setHex(palette.sky);
  scene.fog.near = fog.nearM;
  scene.fog.far = fog.farM;
  baseGroundMaterial.color.setHex(palette.ground);
  skydomeMaterial.color.setHex(palette.sky);
}

// Camera-anchored background dome: rendered first with depth disabled, so
// radius is irrelevant and it never clips. Vertex colors bake a zenith fade
// that the palette sky color multiplies.
export function createSkydome() {
  const geometry = new THREE.SphereGeometry(10, 24, 12);
  const positions = geometry.getAttribute("position");
  const colors = new Float32Array(positions.count * 3);
  for (let index = 0; index < positions.count; index += 1) {
    const up = positions.getY(index) / 10;
    const brightness = 1.04 - Math.max(0, up) * 0.28;
    colors[index * 3] = brightness;
    colors[index * 3 + 1] = brightness;
    colors[index * 3 + 2] = Math.min(1.08, brightness + 0.03);
  }
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const dome = new THREE.Mesh(geometry, skydomeMaterial);
  dome.renderOrder = -1;
  dome.frustumCulled = false;
  return dome;
}

export function pseudoRandom(seed) {
  const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return value - Math.floor(value);
}

// Deterministic 2D value noise (3 octaves) for terrain relief.
function latticeHash(ix, iz) {
  const value = Math.sin(ix * 157.31 + iz * 311.7 + 41.3) * 43758.5453;
  return value - Math.floor(value);
}

function smoothstep(t) {
  return t * t * (3 - 2 * t);
}

function valueNoise(x, z) {
  const ix = Math.floor(x);
  const iz = Math.floor(z);
  const fx = smoothstep(x - ix);
  const fz = smoothstep(z - iz);
  const a = latticeHash(ix, iz);
  const b = latticeHash(ix + 1, iz);
  const c = latticeHash(ix, iz + 1);
  const d = latticeHash(ix + 1, iz + 1);
  return a + (b - a) * fx + (c - a) * fz + (a - b - c + d) * fx * fz;
}

function terrainNoise(x, z) {
  // Normalized to roughly [-1, 1].
  return (
    (valueNoise(x / 210, z / 210) - 0.5) * 1.4 +
    (valueNoise(x / 62 + 17.3, z / 62 + 9.1) - 0.5) * 0.6 +
    (valueNoise(x / 21 + 31.7, z / 21 + 53.9) - 0.5) * 0.22
  );
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

// ---------------------------------------------------------------------------
// Terrain: a corridor grid around the path. Height = road elevation blended
// into noise relief with a cubic falloff by lateral distance, plus a
// per-scenery lateral drop (crossfaded along the path so segment boundaries
// never produce cliffs).

function buildTerrainModel(path) {
  const rowStride = Math.max(
    1,
    Math.round(TERRAIN_ROW_SPACING_M / path.spacingM),
  );
  const rows = [];
  for (let index = 0; index < path.samples.length; index += rowStride) {
    const sample = path.samples[index];
    const profile = terrainProfiles[sample.scenery] || terrainProfiles.fields;
    rows.push({
      sample,
      amplitudeM: profile.amplitudeM,
      lateralDropPerM: profile.lateralDropPerM,
      groundColor: null,
      colorIndex: index,
    });
  }

  // Crossfade terrain character along the route.
  const smoothField = (pick) => {
    const raw = rows.map(pick);
    return raw.map((_, index) => {
      let total = 0;
      for (let tap = -PARAM_BLEND_ROWS; tap <= PARAM_BLEND_ROWS; tap += 1) {
        total += raw[(index + tap + raw.length * 4) % raw.length];
      }
      return total / (PARAM_BLEND_ROWS * 2 + 1);
    });
  };
  const amplitudes = smoothField((row) => row.amplitudeM);
  const drops = smoothField((row) => row.lateralDropPerM);
  rows.forEach((row, index) => {
    row.amplitudeM = amplitudes[index];
    row.lateralDropPerM = drops[index];
  });

  const heightAt = (rowIndex, offsetM) => {
    const row = rows[Math.max(0, Math.min(rows.length - 1, rowIndex))];
    const sample = row.sample;
    const rightX = Math.cos(sample.headingRad);
    const rightZ = Math.sin(sample.headingRad);
    const x = sample.x + rightX * offsetM;
    const z = sample.z + rightZ * offsetM;
    const lateral = Math.abs(offsetM);
    const blend =
      lateral <= ROAD_FLAT_HALF_WIDTH_M
        ? 0
        : smoothstep(
            Math.min(
              1,
              (lateral - ROAD_FLAT_HALF_WIDTH_M) /
                (TERRAIN_BLEND_END_M - ROAD_FLAT_HALF_WIDTH_M),
            ),
          );
    const relief =
      terrainNoise(x, z) * row.amplitudeM -
      Math.max(0, lateral - ROAD_FLAT_HALF_WIDTH_M) * row.lateralDropPerM;
    return { x, z, y: sample.y - 0.08 + relief * blend };
  };

  return { rows, heightAt };
}

function buildTerrainMesh(path, terrain, group) {
  const rows = terrain.rows;
  const cols = TERRAIN_LATERAL_OFFSETS_M;
  const positions = new Float32Array(rows.length * cols.length * 3);
  const colors = new Float32Array(rows.length * cols.length * 3);
  const indices = [];
  const color = new THREE.Color();

  rows.forEach((row, rowIndex) => {
    color.setHex(
      blendedPaletteColor(path.samples, row.colorIndex, (palette) => palette.ground),
    );
    cols.forEach((offsetM, colIndex) => {
      const point = terrain.heightAt(rowIndex, offsetM);
      const vertex = rowIndex * cols.length + colIndex;
      positions[vertex * 3] = point.x;
      positions[vertex * 3 + 1] = point.y;
      positions[vertex * 3 + 2] = point.z;
      // Subtle deterministic tone variation keeps large fields from banding.
      const jitter = 0.9 + 0.2 * valueNoise(point.x / 33 + 7, point.z / 33 + 3);
      colors[vertex * 3] = Math.min(1, color.r * jitter);
      colors[vertex * 3 + 1] = Math.min(1, color.g * jitter);
      colors[vertex * 3 + 2] = Math.min(1, color.b * jitter);
    });
  });

  for (let rowIndex = 0; rowIndex < rows.length - 1; rowIndex += 1) {
    for (let colIndex = 0; colIndex < cols.length - 1; colIndex += 1) {
      const a = rowIndex * cols.length + colIndex;
      const b = a + 1;
      const c = a + cols.length;
      const d = c + 1;
      indices.push(a, b, c, b, d, c);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  const terrainMesh = new THREE.Mesh(geometry, vertexColorMaterial);
  group.add(terrainMesh);
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

// ---------------------------------------------------------------------------
// Props: template parts instanced once per placement. Each part type is one
// InstancedMesh (one draw call), and every placement samples the terrain
// height so props sit on the ground the terrain mesh actually shows.

function createTreeProp() {
  return [
    {
      part: "trunk",
      geometry: () => new THREE.CylinderGeometry(0.08, 0.12, 0.7, 7),
      local: { y: 0.35 },
    },
    {
      part: "foliage",
      geometry: () => new THREE.ConeGeometry(0.52, 1.25, 7),
      local: { y: 1.18 },
    },
  ];
}

function createVillageProp() {
  return [
    {
      part: "wall",
      geometry: () => new THREE.BoxGeometry(0.9, 0.62, 0.8),
      local: { y: 0.31 },
    },
    {
      part: "roof",
      geometry: () => new THREE.ConeGeometry(0.72, 0.42, 4),
      local: { y: 0.83, rotationY: Math.PI / 4 },
    },
  ];
}

function createRockProp() {
  return [
    {
      part: "rock",
      geometry: () => new THREE.DodecahedronGeometry(0.42, 0),
      local: { y: 0.38, scaleX: 1.25, scaleY: 0.72, scaleZ: 0.9 },
    },
  ];
}

function createFieldProp() {
  return [
    {
      part: "field",
      geometry: () => new THREE.CylinderGeometry(0.34, 0.34, 0.56, 14),
      local: { y: 0.34, rotationZ: Math.PI / 2 },
    },
  ];
}

const propBuilders = {
  fields: createFieldProp,
  forest: createTreeProp,
  village: createVillageProp,
  ridge: createRockProp,
  river: createTreeProp,
};

const propSpacingM = {
  fields: 42,
  forest: 15,
  village: 26,
  ridge: 30,
  river: 24,
};

// A second, sparser band farther from the road gives the world depth.
const FAR_PROP_SPACING_MULTIPLIER = 2.4;

function localMatrix(local, wholeScale) {
  bakePosition.set(0, (local.y || 0) * wholeScale, 0);
  bakeEuler.set(0, local.rotationY || 0, local.rotationZ || 0, "ZYX");
  bakeQuaternion.setFromEuler(bakeEuler);
  bakeScale.set(
    (local.scaleX || 1) * wholeScale,
    (local.scaleY || 1) * wholeScale,
    (local.scaleZ || 1) * wholeScale,
  );
  return new THREE.Matrix4().compose(bakePosition, bakeQuaternion, bakeScale);
}

function buildProps(path, terrain, group) {
  const partMatrices = new Map(); // part name -> Matrix4[]
  const partGeometries = new Map();
  const placementDummy = new THREE.Object3D();

  const place = (distanceM, side, offsetM, seed) => {
    const rowIndex = Math.round(distanceM / TERRAIN_ROW_SPACING_M);
    const row =
      terrain.rows[Math.max(0, Math.min(terrain.rows.length - 1, rowIndex))];
    const scenery = row.sample.scenery;
    const parts = (propBuilders[scenery] || createFieldProp)();
    const ground = terrain.heightAt(rowIndex, side * offsetM);
    const scale = 0.8 + pseudoRandom(seed + 57) * 0.5;

    placementDummy.position.set(ground.x, Math.max(ground.y, row.sample.y - 12), ground.z);
    placementDummy.rotation.set(
      0,
      -row.sample.headingRad + side * 0.18 + pseudoRandom(seed) * 0.8,
      0,
    );
    placementDummy.scale.setScalar(1);
    placementDummy.updateMatrix();

    parts.forEach((spec) => {
      if (!partGeometries.has(spec.part)) {
        partGeometries.set(spec.part, spec.geometry());
        partMatrices.set(spec.part, []);
      }
      const matrix = placementDummy.matrix.clone().multiply(
        localMatrix(spec.local, scale),
      );
      partMatrices.get(spec.part).push(matrix);
    });
  };

  let distanceM = 0;
  let index = 0;
  while (distanceM < path.lengthM) {
    const pose = path.poseAt(distanceM);
    const spacing = propSpacingM[pose.scenery] || 35;
    const side = index % 2 === 0 ? -1 : 1;
    const nearOffset = pose.roadWidthM / 2 + 4 + pseudoRandom(index) * 5;
    place(distanceM, side, nearOffset, index);
    if (pseudoRandom(index + 991) > 0.35) {
      const farOffset = 48 + pseudoRandom(index + 13) * 85;
      place(distanceM + spacing * 0.4, -side, farOffset, index + 7919);
    }
    distanceM += spacing;
    index += 1;
  }

  partMatrices.forEach((matrices, part) => {
    const instanced = new THREE.InstancedMesh(
      partGeometries.get(part),
      new THREE.MeshLambertMaterial({ color: propColors[part] }),
      matrices.length,
    );
    matrices.forEach((matrix, matrixIndex) => {
      instanced.setMatrixAt(matrixIndex, matrix);
    });
    instanced.instanceMatrix.needsUpdate = true;
    // One bounding sphere cannot represent instances spread over kilometers.
    instanced.frustumCulled = false;
    instanced.matrixAutoUpdate = false;
    group.add(instanced);
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

function buildBasePlane(path, group) {
  const bounds = new THREE.Box3();
  path.samples.forEach((sample) => {
    bounds.expandByPoint(new THREE.Vector3(sample.x, sample.y, sample.z));
  });
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const base = new THREE.Mesh(
    new THREE.PlaneGeometry(size.x + 2400, size.z + 2400),
    baseGroundMaterial,
  );
  base.rotation.x = -Math.PI / 2;
  base.position.set(center.x, bounds.min.y - 55, center.z);
  group.add(base);
}

export function buildWorld(path) {
  const group = new THREE.Group();
  const terrain = buildTerrainModel(path);
  buildTerrainMesh(path, terrain, group);
  buildRoadSurfaces(path, group);
  buildLaneDashes(path, group);
  buildRailPosts(path, group);
  buildCurveChevrons(path, group);
  buildSegmentGates(path, group);
  buildProps(path, terrain, group);
  buildRiverRibbons(path, group);
  buildBasePlane(path, group);

  return {
    group,
    dispose() {
      group.traverse((node) => {
        if (node.isMesh) node.geometry.dispose();
      });
    },
  };
}
