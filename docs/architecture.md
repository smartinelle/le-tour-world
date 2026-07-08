# Architectural Framework for an AI-Generated Procedural Virtual Cycling Engine in Three.js

Virtual cycling platforms have introduced immersive training environments for indoor athletes. Implementing an engine capable of instantly synthesizing personalized, responsive 3D environments from a single natural language prompt requires an architecture that bridges generative artificial intelligence, procedural graphics rendering, and real-time Internet of Things (IoT) hardware telemetry.

Traditional text-to-3D asset pipelines generate dense, unstructured polygon meshes that require intensive server-side computations, resulting in high token costs and latency. For real-time virtual training, this document outlines an alternative, token-efficient paradigm: compiling a high-level, language-model-generated Domain-Specific Language (DSL) into procedural, instanced 3D scenes within a client-side Three.js engine.

## System Architecture and Project Genesis

Building a procedural 3D application starts with a modular web application framework. Using Node.js and a modern bundler like Vite, developers can structure the environment to isolate the rendering loop, the physics simulation, and the hardware communications layer.

The workspace isolates raw assets and configuration maps from the core executable modules. Static assets such as textures, audio files, and any pre-compiled 3D models are served directly from a dedicated static folder to prevent bundling overhead. The runtime execution is driven by WebGL or the modern WebGPU standard, operating within a continuous render loop driven by the browser's animation frame engine.

| **Directory Path** | **File Component**     | **Structural Responsibility**                                            | **Core Dependencies**                                      |
| ------------------ | ---------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------- |
| `/`                | `package.json`         | Project metadata, build scripts, and dependency management               | `three`, `vite`, `three-mesh-bvh`<br><br>[cite: 9, 14, 15] |
| `/`                | `index.html`           | Entry point defining the canvas viewport and mounting the main script    | Browser DOM, module scripts                                |
| `/src/`            | `main.js`              | Initializes the rendering engine, scene, and camera systems              | `three`, `OrbitControls`<br><br>[cite: 9, 12, 16]          |
| `/src/terrain/`    | `ProceduralTerrain.js` | Builds chunked terrains, applying seeded noise algorithms                | `three`, custom noise utilities                            |
| `/src/terrain/`    | `noise.js`             | Generates deterministic height profiles using numeric seeds              | Pure functional mathematics                                |
| `/src/physics/`    | `NewtonianPhysics.js`  | Computes speed updates based on slope, wind, and rolling resistance      | Cardano's cubic mathematical solver                        |
| `/src/bluetooth/`  | `FTMSController.js`    | Establishes Web Bluetooth connection and manages smart trainer telemetry | Web Bluetooth GATT API                                     |
| `/public/`         | `/textures/`           | Stores normal, roughness, and color maps for roads and terrain           | Static Web Server                                          |

The core initialization sequence creates a `THREE.Scene`, a `THREE.PerspectiveCamera`, and a `THREE.WebGLRenderer` configured with performance features such as anti-aliasing and color-space management. To keep visual frame updates smooth, the rendering cycle utilizes an animation loop that updates internal coordinates and physics states before dispatching the draw commands directly to the GPU.

## Token-Lean Generative Scene Compilers: AI to Parametric DSL

Generating virtual worlds with AI usually presents a trade-off between creative variety and generation speed. Direct generation of 3D meshes using neural radiance fields or diffusion pipelines introduces rendering challenges, such as unoptimized mesh topologies, heavy asset loading overhead, and high API token costs.

To bypass these bottlenecks, this architecture compiles a single natural language prompt into a compact, structured configuration payload. Rather than specifying explicit coordinate points for every physical entity, a Large Language Model (LLM) outputs a high-level design specification in JSON format.

```
[ Rider Prompt: "Alpine pine forest road" ] 
               │
               ▼
┌──────────────────────────────────────────────┐
│       LLM Text Comprehension Engine          │
│   (Parses user intent to linear tokens)      │
└──────────────────────────────────────────────┘
               │
               ▼  [ High-Level Assembly Array ]
┌──────────────────────────────────────────────┐
│  State Sequence Mapping: `[A, B, C, D]`       │
│  (Compact JSON metadata structure)            │
└──────────────────────────────────────────────┘
               │
               ▼  [ AST Parsing & Assembly ]
┌──────────────────────────────────────────────┐
│       Procedural Graphics Compiler           │
│   (Maps templates to physical coordinates)    │
└──────────────────────────────────────────────┘
               │
               ├───────────────────────────────┐
               ▼                               ▼
┌────────────────────────────────┐ ┌────────────────────────────────┐
│   Abstract Placer Engine       │ │   Concrete Provider Engine     │
│ (Evaluates layout constraints) │ │  (Instantiates scene elements) │
└────────────────────────────────┘ └────────────────────────────────┘
```

The compiled sequence parses a compact index array representing a state pattern of scene elements. For example, the design of a map is represented by an array such as `config = [A, C, A, B, D]` where each character points to a localized asset template. The client-side application decodes this sequence into a structured model state containing exact dimensions, materials, and placement constraints:

|**Generation Pipeline Component**|**Large-Scale LLM Coordinates (Traditional JSON)**|**Compiled Template Index Series (Low-Token DSL)**|
|---|---|---|
|**Payload Representation**|Lists of coordinates, rotations, and scales for all objects|A compact layout grid and discrete asset template indices|
|**Average Token Size**|$25,000 - 150,000\text{ tokens}$ per scene|$300 - 1,500\text{ tokens}$ per scene|
|**Verification Method**|Manual validation of coordinates; error-prone collisions|Deterministic compiler validation with BEV grid checks|
|**Parsing Pipeline**|Slow parsing of deeply nested JSON trees|Fast translation of linear index arrays|
|**Stylistic Customization**|Relies on the model's spatial layout abilities|Uses pre-built, style-consistent template assets|

At runtime, the parser walks through the compiled sequence using a Placer-Provider pattern to assemble the 3D scene. The abstract `Placer` class manages placement logic (such as arranging trees along the road corridor or aligning boulders to cliffs), while the concrete `Provider` manages the loading, pooling, and instantiating of Three.js materials and geometries.

Because the placers operate in a deterministic sequence, they can evaluate spatial coordinates relative to previously placed objects. This avoids asset collisions and ensures a natural distribution of scenery without requiring the AI model to calculate coordinates directly.

## Memory-Optimized Rendering: Geometry Primitives and Textures

To render these scenes efficiently on lightweight devices, the engine constructs environments programmatically rather than relying on external asset files. Built-in Three.js constructors generate clean 3D shapes from numerical parameters.

|**Three.js Geometry Class**|**Key Parameter Config**|**Computational Weight**|**Primary Use Case in Virtual Maps**|
|---|---|---|---|
|`BoxGeometry`<br><br>[cite: 26]|Width, Height, Depth, Segments|Very Low (12 triangles)|Roadside crates, structural barriers, low-poly buildings|
|`SphereGeometry`<br><br>[cite: 26]|Radius, Width Segments, Height Segments|Moderate ($16 \times 8$ for background objects)|Dynamic skydomes, distant background hills, sun/moon actors|
|`CylinderGeometry`<br><br>[cite: 26]|Radius Top, Radius Bottom, Height, Segments|Low to Moderate|Tree trunks, power line poles, structural pillars|
|`PlaneGeometry`<br><br>[cite: 26]|Width, Height, Width Segments, Height Segments|Low to High (depending on subdivision)|Flat ground, water planes, terrain elevation blocks|
|`TorusGeometry`<br><br>[cite: 26]|Radius, Tube, Radial/Tubular Segments|Moderate|Abstract visual landmarks, tunnel rings, arches|
|`ExtrudeGeometry`<br><br>[cite: 26]|Shape, Depth, Bevel Settings, Steps|High|Bridge railings, retaining walls, highway barriers|
|`LatheGeometry`<br><br>[cite: 26]|Vector 2D points, Segments|Moderate|Classical pottery, decorative columns, support posts|
|`TubeGeometry`<br><br>[cite: 26]|Spline Curve Path, Segments, Radius|High|Mountain tunnels, elevated pipes, dynamic path wires|

To optimize rendering performance, identical geometries are shared across meshes. Rather than generating separate geometries for 500 identical pine trees, the engine instantiates a single `CylinderGeometry` and shares it across an `InstancedMesh`. This groups thousands of objects into a single GPU draw call.

For custom scene designs, the engine uses `three-bvh-csg` (Constructive Solid Geometry) to perform boolean operations on primitives. This allows the engine to dynamically carve tunnels or clip structures out of basic geometries at runtime.

JavaScript

```
import { Brush, Evaluator, SUBTRACTION } from 'three-bvh-csg';

// Instantiating the CSG Brush entities with standard geometries
const mountainBrush = new Brush(new THREE.BoxGeometry(20, 20, 20));
const tunnelHoleBrush = new Brush(new THREE.CylinderGeometry(4, 4, 30, 16));

// Positioning the cutting tool
tunnelHoleBrush.position.set(0, 0, 0);
tunnelHoleBrush.rotation.x = Math.PI / 2;

// Executing the Boolean Subtraction Operation
const csgEvaluator = new Evaluator();
const carvedMountainGeometry = csgEvaluator.evaluate(mountainBrush, tunnelHoleBrush, SUBTRACTION).geometry;
```

To prevent repetitive, tiled surfaces when sharing materials across objects, the engine uses a custom `MaterialFactory`. This utility manages a pool of physically-based materials (PBR) incorporating color, normal, roughness, and ambient occlusion maps.

To apply these textures dynamically without allocating excessive GPU memory, the engine partitions geometries into sub-groups using `geometry.addGroup()`. It then modifies the UV coordinates of each instance to offset the texture mapping:

JavaScript

```
function applyRandomizedUvOffset(geometry, faceIndex, offsetU, offsetV) {
  const uvAttribute = geometry.getAttribute('uv');
  const indexAttribute = geometry.getIndex();
  
  // Locating the three vertices that comprise the target face
  const vertexIndices = [
    indexAttribute.getX(faceIndex * 3),
    indexAttribute.getY(faceIndex * 3),
    indexAttribute.getZ(faceIndex * 3)
  ];
  
  // Shifting the UV coordinates for each vertex of the face
  vertexIndices.forEach((vertexIndex) => {
    let u = uvAttribute.getX(vertexIndex);
    let v = uvAttribute.getY(vertexIndex);
    
    uvAttribute.setXY(vertexIndex, u + offsetU, v + offsetV);
  });
  
  uvAttribute.needsUpdate = true;
}
```

This dynamic offset technique allows the engine to reuse a single texture atlas across hundreds of unique objects while avoiding a repetitive, tiled appearance. To reduce network requests, smaller texture maps are packed into a single texture atlas managed by a canvas-based bin packing algorithm.

## Advanced Procedural Road Construction and Terrain Deformation

Creating a smooth, realistic road is critical for keeping virtual training simulations stable. Mismatches between the road spline and the terrain elevation can create gaps, overlapping geometries, or bumpy roads that disrupt training.

```
                [ Road Alignment & Deformation Loop ]
                                  │
                                  ▼
                     [ Get Current Rider Position ]
                                  │
                                  ▼
                   [ Identify Surrounding Terrain ]
           (getChunkKey: `${Math.round(x)},${Math.round(z)}`)
                                  │
                                  ▼
                [ Query Vertices in Deformation Radius ]
                                  │
                                  ▼
                   [ Apply Cubic Falloff Equation ]
             \xi = ((R_{deform} - d) / R_{deform})^3
                                  │
                                  ▼
                [ Interpolate Terrain Height to Spline ]
                                  │
                                  ▼
             [ Recalculate Normals & Re-render Chunk ]
```

The centerline of the road is defined by interpolating three-dimensional coordinates using a `CatmullRomCurve3` spline. The lateral edges of the road are then calculated by projecting parallel paths offset from this centerline:

1. **Calculate Spline Normals**: At each spline coordinate $P_i$, tangent vector $T_i$ and binormal vector $B_i$ are computed to determine road orientation and banking.
    
2. **Project Lateral Vertices**: A lateral offset vector $S_i$ is calculated by taking the cross product of the tangent vector $T_i$ and the up-axis vector $U = (0, 1, 0)$:
    
    $$S_i = \frac{T_i \times U}{\|T_i \times U\|}$$
    
3. **Generate Road Borders**: The left and right boundary vertices are generated based on the target road width $W_r$:
    
    $$P_{\text{left}, i} = P_i - S_i \cdot \frac{W_r}{2}$$
    
    $$P_{\text{right}, i} = P_i + S_i \cdot \frac{W_r}{2}$$
    

These alternating vertices are stored in a flat `Float32Array` within a `THREE.BufferGeometry` and indexed to form a contiguous road mesh.

When rendering detailed, winding roads at a large scale, floating-point precision limitations can cause visual artifacts like flickering, crumpled, or distorted faces. To prevent these errors, the engine anchors the coordinates.

The engine uses a local coordinate system centered on a nearby origin anchor, calculating offsets relative to this point before converting to Mercator coordinates:

JavaScript

```
function convertMetersToMercator(meters, latitude) {
  const earthCircumference = 40075016.686;
  return meters / (earthCircumference * Math.cos(latitude * Math.PI / 180));
}

function generateLocalAnchorRoadSegment(centerPoint, leftOffsetMeters, rightOffsetMeters, latitude) {
  const widthMercator = convertMetersToMercator(leftOffsetMeters + rightOffsetMeters, latitude);
  
  const localVertexLeft = new THREE.Vector3(
    -widthMercator / 2, 
    0, 
    0
  );
  const localVertexRight = new THREE.Vector3(
    widthMercator / 2, 
    0, 
    0
  );
  
  return { localVertexLeft, localVertexRight };
}
```

This local positioning approach prevents precision loss, keeping the road geometry smooth even under close camera zooms.

To align the surrounding terrain to the road, the engine uses a chunk-based deformation system. The terrain is divided into local chunks managed via unique spatial coordinate keys:

JavaScript

```
const getChunkKey = (position, chunkSize) => {
  const chunkX = Math.round(position.x / chunkSize);
  const chunkZ = Math.round(position.z / chunkSize);
  return `${chunkX},${chunkZ}`;
};
```

As the rider moves through the world, distant terrain chunks are recycled and repositioned ahead of the path. The engine updates the active deformation states through dedicated caching methods:

- **`saveChunkDeformation`**: Caches the vertex modifications of a deformed chunk to preserve its state when repositioned.
    
- **`loadChunkDeformation`**: Restores previously cached terrain modifications when a chunk is reloaded.
    
- **`getNeighboringChunks`**: Retrieves chunks within the deformation zone to limit height calculations and improve rendering performance.
    

When aligning terrain to the road, the height of each terrain vertex within a deformation radius $R_{\text{deform}}$ is blended using a cubic falloff function to ensure a smooth transition:

$$\xi = \left( \frac{R_{\text{deform}} - d}{R_{\text{deform}}} \right)^3$$

$$V_{\text{terrain}, y} = (1 - \xi) \cdot V_{\text{terrain}, y} + \xi \cdot P_{\text{spline}, y}$$

This cubic interpolation smoothly blends the terrain edges with the road shoulder, preventing steep cuts or gaps between the road and the surrounding landscape.

## Interactive Cycling Physics and Cardano's Equations

To convert a rider's physical power output (Watts) into virtual speed (meters per second), the physics engine running in the background thread performs a continuous Newtonian simulation. This simulation calculates the opposing forces acting on the rider at each step:

$$\sum F_{\text{resistance}} = F_{\text{gravity}} + F_{\text{rolling}} + F_{\text{aerodynamic}}$$

### Gravity Resistance

Gravity pulls the combined mass of the rider and bike, $W$ (in kilograms), down slopes. On a gradient percentage $G$, the gravity force is calculated as:

$$F_{\text{gravity}} = g \cdot W \cdot \sin\left(\arctan\left(\frac{G}{100}\right)\right)$$

Where $g$ is the gravitational acceleration constant ($9.80665\text{ m/s}^2$).

### Rolling Resistance

Rolling resistance models tire friction against the road surface. It is calculated as:

$$F_{\text{rolling}} = g \cdot W \cdot C_{\text{rr}} \cdot \cos\left(\arctan\left(\frac{G}{100}\right)\right)$$

The rolling coefficient $C_{\text{rr}}$ varies based on the tire and road surface conditions specified in the active biome.

### Aerodynamic Drag

Aerodynamic drag models air resistance as speed increases. It is calculated using the rider's drag area $C_d A$ and the local air density $\rho$:

$$F_{\text{aerodynamic}} = 0.5 \cdot C_d A \cdot \rho \cdot V_{\text{apparent}}^2$$

The apparent wind speed $V_{\text{apparent}}$ accounts for both the groundspeed $V_{\text{gs}}$ and any headwind or crosswind components. Taking the wind direction angle $\alpha_w$ (where $0^\circ$ represents a direct headwind and $180^\circ$ a tailwind), the apparent wind velocity is calculated as:

$$V_{\text{apparent}} = \sqrt{V_{\text{gs}}^2 + V_{\text{wind}}^2 + 2 \cdot V_{\text{gs}} \cdot V_{\text{wind}} \cdot \cos(\alpha_w)}$$

Using this apparent velocity, the yaw angle $\psi$ is calculated to determine the offset of the wind relative to the rider's path:

$$\psi = \arctan\left( \frac{V_{\text{wind}} \cdot \sin(\alpha_w)}{V_{\text{gs}} + V_{\text{wind}} \cdot \cos(\alpha_w)} \right)$$

This drag calculation is multiplied by the drivetrain efficiency factor $\eta$ to account for mechanical power loss (typically set to $\eta = 0.95$, representing a $5\%$ loss through the chain and gears).

### Resolving Ground Speed via Cardano's Method

To find the steady-state ground speed $V_{\text{gs}}$ for a given leg power input $P_{\text{legs}}$, the physics equations are rewritten as a cubic polynomial:

$$a V_{\text{gs}}^3 + b V_{\text{gs}}^2 + c V_{\text{gs}} + d = 0$$

Where the coefficients are defined as:

$$a = 0.5 \cdot C_d A \cdot \rho$$

$$b = V_{\text{wind}} \cdot \cos(\alpha_w) \cdot C_d A \cdot \rho$$

$$c = g \cdot W \cdot \left[ \sin\left(\arctan\left(\frac{G}{100}\right)\right) + C_{\text{rr}} \cdot \cos\left(\arctan\left(\frac{G}{100}\right)\right) \right] + 0.5 \cdot C_d A \cdot \rho \cdot V_{\text{wind}}^2$$

$$d = -\eta \cdot P_{\text{legs}}$$

To solve this cubic equation in real-time, the engine uses Cardano's method. First, the cubic polynomial is divided by the leading coefficient $a$ and transformed into a depressed cubic:

$$t^3 + p \cdot t + q = 0$$

The variables are shifted using $V_{\text{gs}} = t - \frac{b}{3a}$, with the new coefficients $p$ and $q$ calculated as:

$$p = \frac{3ac - b^2}{3a^2}$$

$$q = \frac{2b^3 - 9abc + 27a^2d}{27a^3}$$

The discriminant $\Delta$ is evaluated to determine the number and type of roots:

$$\Delta = \frac{q^2}{4} + \frac{p^3}{27}$$

- **If $\Delta > 0$**: The equation has one real root and two complex roots. The real root represents the physical velocity and is calculated as:
    
    $$u = \sqrt[3]{-\frac{q}{2} + \sqrt{\Delta}}$$
    
    $$v = \sqrt[3]{-\frac{q}{2} - \sqrt{\Delta}}$$
    
    $$V_{\text{gs}} = u + v - \frac{b}{3a}$$
    
- **If $\Delta \le 0$**: The equation has three real roots (known as the _casus irreducibilis_). The engine evaluates the roots using trigonometric conversions to find the physical velocity:
    
    $$\theta = \arccos\left( \frac{3q}{2p} \sqrt{-\frac{3}{p}} \right)$$
    
    $$V_{\text{gs}} = 2 \sqrt{-\frac{p}{3}} \cdot \cos\left( \frac{\theta}{3} \right) - \frac{b}{3a}$$
    

This ensures that the simulated speed matches physical laws at every frame update.

## Structured Training and Smart Trainer Integration

To make training effective, the application integrates structured workouts with dynamic resistance adjustments on the smart trainer. Workouts are structured as percentage-based targets scaled against the rider's Functional Threshold Power (FTP).

|**Workout Zone**|**Intensity Range (% of FTP)**|**Cardiovascular Focus**|**Targeted Adaptations**|
|---|---|---|---|
|**Zone 1: Recovery**<br><br>[cite: 44]|$< 55\%$<br><br>[cite: 44]|Active Recovery|Promotes blood flow, reduces muscle tightness, assists recovery|
|**Zone 2: Endurance**<br><br>[cite: 44]|$56\% - 75\%$<br><br>[cite: 44]|Aerobic Base|Enhances fat oxidation, increases mitochondrial density|
|**Zone 3: Tempo**<br><br>[cite: 44]|$76\% - 90\%$<br><br>[cite: 44]|Aerobic Endurance|Improves glycogen storage, develops muscular endurance|
|**Zone 4: Threshold**<br><br>[cite: 44]|$91\% - 105\%$<br><br>[cite: 44]|Lactate Threshold|Delays onset of fatigue, raises threshold power output|
|**Zone 5: VO2 Max**<br><br>[cite: 44]|$106\% - 150\%$<br><br>[cite: 44]|Anaerobic Capacity|Improves maximal oxygen uptake, develops high-intensity power|

An athlete's FTP is determined using standardized tests, such as taking $95\%$ of the average power sustained during a 20-minute maximum effort. Heart rate training zones are calculated relative to the rider's estimated maximum heart rate ($HR_{\text{max}}$):

$$\text{Female } HR_{\text{max}} = 210 - \frac{\text{Age}}{2} - \left(0.05 \cdot \text{Weight}_{\text{lbs}}\right)$$

$$\text{Male } HR_{\text{max}} = 210 - \frac{\text{Age}}{2} - \left(0.05 \cdot \text{Weight}_{\text{lbs}}\right) + 4$$

The app connects to smart trainers via Web Bluetooth using the standard Fitness Machine Service (FTMS) over GATT profiles. The system connects to the machine, discovers the primary service, and subscribes to telemetry characteristics to read ride data:

JavaScript

```
let gattServer;
let ftmsService;
let controlPointChar;

async function initializeTrainerConnection() {
  const device = await navigator.bluetooth.requestDevice({
    filters: [{ services: ['00001826-0000-1000-8000-00805f9b34fb'] }] // Standard FTMS UUID
  });
  
  gattServer = await device.gatt.connect();
  ftmsService = await gattServer.getPrimaryService('00001826-0000-1000-8000-00805f9b34fb'); //
  
  // Locating the Control Point characteristic for writing commands
  controlPointChar = await ftmsService.getCharacteristic('00002ad9-0000-1000-8000-00805f9b34fb'); // [cite: 47]
  
  // Starting the control session
  await controlPointChar.writeValue(new Uint8Array([0x80])); // Request Control Opcode
}
```

The application runs in one of two modes depending on the workout type:

- **ERG Mode**: The trainer adjusts resistance automatically to hold a target wattage regardless of the rider's cadence. The app calculates the target wattage based on the active workout segment's FTP percentage and writes it to the Control Point (`0x2AD9`).
    
- **Simulation Mode**: The trainer adjusts resistance dynamically to match the virtual grade of the terrain. The physics loop calculates the gradient of the road spline at the rider's position and transmits it to the trainer, allowing the rider to feel the hills as they ride.
    

This dual-mode approach allows the app to handle both structured training sessions and open-world free rides on AI-generated maps, providing a complete indoor training experience.

## Architectural Synthesis and Implementation Strategy

By prioritizing procedural construction over raw asset streaming, this architecture solves several performance bottlenecks common in virtual training engines:

- **High Network Payload Sizes**: Transmitting a highly compressed template configuration payload instead of raw 3D models reduces network transfer sizes from megabytes to kilobytes. This minimizes load times and cuts API cost and latency.
    
- **Low Shading Budgets**: Standard text-to-3D tools generate dense, unoptimized meshes that can degrade performance on mobile or lower-end devices. This proposed engine uses clean client-side primitives, shared geometry structures (`InstancedMesh`), and texture atlases to maintain 60 FPS rendering within a $500\text{k}$ triangle budget.
    
- **Physics Sync and Trainer Feedback**: The engine runs a continuous Newtonian simulation loop that updates speed and resistance based on the terrain gradient. Resolving the cubic resistance equations via Cardano's method ensures that grade changes are translated to the smart trainer immediately, creating a realistic and responsive virtual ride.
    

This framework allows developers to build a lightweight, responsive training platform that runs entirely in the browser, enabling the generation of infinite virtual worlds for indoor athletes.

→ filed in thesis/concepts/procedural_cycling_engine_threejs.md (durable engineering pattern + strategic positioning; full architecture preserved here as evidence trail).
