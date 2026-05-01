function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function numeric(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const DEFAULT_ROUTE_SEGMENTS = [
  { name: "Valley Rollers", lengthM: 420, gradePct: 0.4, scenery: "fields" },
  { name: "Pine Rise", lengthM: 360, gradePct: 3.2, scenery: "forest" },
  { name: "Mill Descent", lengthM: 320, gradePct: -2.1, scenery: "village" },
  { name: "Ridge Steps", lengthM: 460, gradePct: 5.6, scenery: "ridge" },
  { name: "River Run", lengthM: 520, gradePct: -0.6, scenery: "river" },
];

function normalizeSegments(segments) {
  return segments
    .map((segment) => ({
      name: String(segment.name || "Route segment"),
      lengthM: Math.max(1, numeric(segment.lengthM, 1)),
      gradePct: numeric(segment.gradePct),
      scenery: String(segment.scenery || "fields"),
    }))
    .filter((segment) => segment.lengthM > 0);
}

export class RideMotionModel {
  constructor({
    dashSpacing = 7.8,
    maxDt = 0.06,
    speedResponse = 7.5,
    routeSegments = DEFAULT_ROUTE_SEGMENTS,
  } = {}) {
    this.dashSpacing = dashSpacing;
    this.maxDt = maxDt;
    this.speedResponse = speedResponse;
    this.routeSegments = normalizeSegments(routeSegments);
    this.routeLengthM = this.routeSegments.reduce(
      (total, segment) => total + segment.lengthM,
      0,
    );
    this.active = false;
    this.paused = false;
    this.mode = null;
    this.targetSpeedMps = 0;
    this.speedMps = 0;
    this.distanceM = 0;
    this.gradePct = 0;
    this.routeGradePct = 0;
    this.routeSegmentName = "Valley Rollers";
    this.routeSegmentProgress = 0;
    this.routeSegmentRemainingM = 0;
    this.nextSegmentName = "Pine Rise";
    this.nextSegmentGradePct = 3.2;
    this.scenery = "fields";
    this.roadOffset = 0;
    this.roadPitch = 0;
    this.cameraBob = 0;
    this.cameraPitch = 0;
    this.horizonLift = 0;
  }

  updateFromSnapshot(snapshot) {
    this.active = Boolean(snapshot.active);
    this.paused = Boolean(snapshot.paused);
    this.mode = snapshot.mode || null;
    this.distanceM = this.active ? numeric(snapshot.distance_m) : 0;
    const routeSegment = this.segmentForDistance(this.distanceM);
    this.routeGradePct = routeSegment.gradePct;
    this.routeSegmentName = routeSegment.name;
    this.routeSegmentProgress = routeSegment.progress;
    this.routeSegmentRemainingM = routeSegment.remainingM;
    this.nextSegmentName = routeSegment.nextName;
    this.nextSegmentGradePct = routeSegment.nextGradePct;
    this.scenery = routeSegment.scenery;
    this.gradePct =
      this.active && this.mode === "sim"
        ? numeric(snapshot.sim_grade_pct)
        : this.routeGradePct;
    this.targetSpeedMps =
      this.active && !this.paused ? Math.max(0, numeric(snapshot.speed_mps)) : 0;
    return this.state();
  }

  segmentForDistance(distanceM) {
    if (this.routeSegments.length === 0 || this.routeLengthM <= 0) {
      return {
        name: "Route segment",
        gradePct: 0,
        progress: 0,
        remainingM: 0,
        nextName: "Route segment",
        nextGradePct: 0,
        scenery: "fields",
      };
    }

    let routeDistanceM = numeric(distanceM) % this.routeLengthM;
    if (routeDistanceM < 0) routeDistanceM += this.routeLengthM;

    for (let index = 0; index < this.routeSegments.length; index += 1) {
      const segment = this.routeSegments[index];
      if (routeDistanceM < segment.lengthM) {
        const nextSegment =
          this.routeSegments[(index + 1) % this.routeSegments.length];
        return {
          name: segment.name,
          gradePct: segment.gradePct,
          progress: routeDistanceM / segment.lengthM,
          remainingM: segment.lengthM - routeDistanceM,
          nextName: nextSegment.name,
          nextGradePct: nextSegment.gradePct,
          scenery: segment.scenery,
        };
      }
      routeDistanceM -= segment.lengthM;
    }

    const lastSegment = this.routeSegments[this.routeSegments.length - 1];
    return {
      name: lastSegment.name,
      gradePct: lastSegment.gradePct,
      progress: 1,
      remainingM: 0,
      nextName: this.routeSegments[0].name,
      nextGradePct: this.routeSegments[0].gradePct,
      scenery: lastSegment.scenery,
    };
  }

  advance(dt, nowMs) {
    const boundedDt = clamp(numeric(dt), 0, this.maxDt);
    const response = 1 - Math.exp(-this.speedResponse * boundedDt);
    this.speedMps += (this.targetSpeedMps - this.speedMps) * response;

    if (Math.abs(this.speedMps) < 0.01 && this.targetSpeedMps === 0) {
      this.speedMps = 0;
    }

    this.roadOffset =
      (this.roadOffset + this.speedMps * boundedDt) % this.dashSpacing;
    this.roadPitch = clamp(this.gradePct * 0.006, -0.08, 0.08);
    this.cameraBob = Math.sin(nowMs * 0.004) * 0.03 * Math.min(this.speedMps, 10);
    this.cameraPitch = clamp(this.gradePct * 0.006, -0.08, 0.08);
    this.horizonLift = clamp(this.gradePct * 0.08, -0.8, 0.8);
    return this.state();
  }

  state() {
    return {
      active: this.active,
      paused: this.paused,
      mode: this.mode,
      speedMps: this.speedMps,
      targetSpeedMps: this.targetSpeedMps,
      distanceM: this.distanceM,
      gradePct: this.gradePct,
      routeGradePct: this.routeGradePct,
      routeSegmentName: this.routeSegmentName,
      routeSegmentProgress: this.routeSegmentProgress,
      routeSegmentRemainingM: this.routeSegmentRemainingM,
      nextSegmentName: this.nextSegmentName,
      nextSegmentGradePct: this.nextSegmentGradePct,
      scenery: this.scenery,
      roadOffset: this.roadOffset,
      roadPitch: this.roadPitch,
      cameraBob: this.cameraBob,
      cameraPitch: this.cameraPitch,
      horizonLift: this.horizonLift,
    };
  }
}
