// World-fixed route centerline compiler.
//
// Turns a validated route spec (constant-grade, constant-turn segments) into a
// dense polyline indexed by arc length. Samples are spaced uniformly so
// distance -> pose lookups are exact and O(1); the trainer's ridden distance
// is the source of truth, which rules out parametric splines that would need
// arc-length reparameterization.
//
// Rides loop (the runtime wraps distance modulo route length), so the compiled
// path must close geometrically. Segment specs rarely close on their own; the
// compiler smooths grade/turn-rate across segment joins (including the seam),
// removes any residual net turn, then distributes the remaining position and
// elevation misclosure linearly along the path. The visual grade therefore
// differs from the physical grade by a constant bias of net-elevation/length;
// resistance and HUD always use the physical grade from the route spec.

const SAMPLE_SPACING_M = 4;
const TRANSITION_WINDOW_M = 30;
const SMOOTHING_TAPS = 9;
const TWO_PI = Math.PI * 2;

function numeric(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function wrapToPi(angleRad) {
  let wrapped = angleRad % TWO_PI;
  if (wrapped > Math.PI) wrapped -= TWO_PI;
  if (wrapped < -Math.PI) wrapped += TWO_PI;
  return wrapped;
}

function normalizeSegments(route) {
  return route.segments.map((segment) => ({
    name: String(segment.name || "Route segment"),
    lengthM: Math.max(1, numeric(segment.length_m, 1)),
    gradePct: numeric(segment.grade_pct),
    turnDeg: numeric(segment.turn_deg),
    roadWidthM: clamp(numeric(segment.road_width_m, 8.6), 4, 14),
    kind: String(segment.kind || "rolling"),
    surface: String(segment.surface || "asphalt"),
    scenery: String(segment.scenery || "fields"),
  }));
}

function segmentIndexAt(boundaries, routeDistanceM) {
  for (let index = 0; index < boundaries.length; index += 1) {
    if (routeDistanceM < boundaries[index].endM) return index;
  }
  return boundaries.length - 1;
}

export function buildRoutePath(route) {
  const segments = normalizeSegments(route);
  const lengthM = segments.reduce((total, segment) => total + segment.lengthM, 0);

  let cursorM = 0;
  const boundaries = segments.map((segment) => {
    const startM = cursorM;
    cursorM += segment.lengthM;
    return { startM, endM: cursorM, segment };
  });

  const wrap = (distanceM) => ((distanceM % lengthM) + lengthM) % lengthM;
  const rawSegmentAt = (distanceM) =>
    boundaries[segmentIndexAt(boundaries, wrap(distanceM))].segment;

  // Piecewise-constant grade and turn rate, averaged over a wrap-aware window
  // so segment joins and the loop seam both curve smoothly.
  const smoothed = (distanceM, pick) => {
    let total = 0;
    for (let tap = 0; tap < SMOOTHING_TAPS; tap += 1) {
      const offsetM =
        (tap / (SMOOTHING_TAPS - 1) - 0.5) * TRANSITION_WINDOW_M;
      total += pick(rawSegmentAt(distanceM + offsetM));
    }
    return total / SMOOTHING_TAPS;
  };
  const gradeAt = (distanceM) => smoothed(distanceM, (segment) => segment.gradePct);
  const turnRateAt = (distanceM) =>
    smoothed(
      distanceM,
      (segment) => ((segment.turnDeg * Math.PI) / 180) / segment.lengthM,
    );

  const sampleCount = Math.max(8, Math.ceil(lengthM / SAMPLE_SPACING_M));
  const spacingM = lengthM / sampleCount;

  // Net turn must be a multiple of a full turn for the seam headings to
  // match. Routes that are not authored as geometric loops usually end far
  // from their start, and redistributing kilometers of position drift would
  // collapse the centerline — so also consider bending in a whole extra turn
  // in either direction (curling the route into a loop) and keep whichever
  // candidate leaves the smallest position misclosure to redistribute.
  let netTurnRad = 0;
  for (let index = 0; index < sampleCount; index += 1) {
    netTurnRad += turnRateAt((index + 0.5) * spacingM) * spacingM;
  }
  const headingResidualRad = wrapToPi(netTurnRad);

  const integrate = (turnCorrectionRadPerM) => {
    const points = [];
    let x = 0;
    let y = 0;
    let z = 0;
    let headingRad = 0;
    for (let index = 0; index <= sampleCount; index += 1) {
      points.push({ x, y, z });
      const midM = index * spacingM + spacingM / 2;
      headingRad += (turnRateAt(midM) - turnCorrectionRadPerM) * spacingM;
      x += Math.sin(headingRad) * spacingM;
      z -= Math.cos(headingRad) * spacingM;
      y += (gradeAt(midM) / 100) * spacingM;
    }
    const end = points[points.length - 1];
    return { points, driftM: Math.hypot(end.x, end.z) };
  };

  let best = null;
  let bestExtraTurns = 0;
  [0, 1, -1].forEach((extraTurns) => {
    const candidate = integrate(
      (headingResidualRad + extraTurns * TWO_PI) / lengthM,
    );
    if (best === null || candidate.driftM < best.driftM) {
      best = candidate;
      bestExtraTurns = extraTurns;
    }
  });

  const samples = best.points.map((point, index) => {
    const distanceM = index * spacingM;
    const segment = rawSegmentAt(Math.min(distanceM, lengthM - 0.001));
    return {
      distanceM,
      x: point.x,
      y: point.y,
      z: point.z,
      headingRad: 0,
      roadWidthM: segment.roadWidthM,
      surface: segment.surface,
      scenery: segment.scenery,
      kind: segment.kind,
      segmentName: segment.name,
    };
  });

  // Distribute the remaining position/elevation misclosure along the path.
  const last = samples[samples.length - 1];
  const closure = {
    driftM: Math.hypot(last.x, last.z),
    elevationDriftM: last.y,
    headingResidualRad,
    extraTurns: bestExtraTurns,
  };
  samples.forEach((sample) => {
    const share = sample.distanceM / lengthM;
    sample.x -= last.x * share;
    sample.y -= last.y * share;
    sample.z -= last.z * share;
  });

  // Drift correction bends tangents away from the integrated headings, so
  // recompute headings from the corrected positions (unwrapped so poses can
  // be linearly interpolated across samples).
  let previousHeadingRad = 0;
  samples.forEach((sample, index) => {
    const before = samples[Math.max(0, index - 1)];
    const after = samples[Math.min(samples.length - 1, index + 1)];
    const rawHeadingRad = Math.atan2(after.x - before.x, -(after.z - before.z));
    const unwrapped =
      index === 0
        ? rawHeadingRad
        : previousHeadingRad + wrapToPi(rawHeadingRad - previousHeadingRad);
    sample.headingRad = unwrapped;
    previousHeadingRad = unwrapped;
  });

  const poseAt = (distanceM) => {
    const routeDistanceM = wrap(numeric(distanceM));
    const index = Math.min(
      sampleCount - 1,
      Math.floor(routeDistanceM / spacingM),
    );
    const current = samples[index];
    const next = samples[index + 1];
    const progress = (routeDistanceM - current.distanceM) / spacingM;
    return {
      distanceM: routeDistanceM,
      x: current.x + (next.x - current.x) * progress,
      y: current.y + (next.y - current.y) * progress,
      z: current.z + (next.z - current.z) * progress,
      headingRad:
        current.headingRad + (next.headingRad - current.headingRad) * progress,
      roadWidthM:
        current.roadWidthM + (next.roadWidthM - current.roadWidthM) * progress,
      surface: current.surface,
      scenery: current.scenery,
    };
  };

  return {
    lengthM,
    spacingM,
    samples,
    segmentBoundaries: boundaries,
    closure,
    poseAt,
  };
}
