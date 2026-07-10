function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function numeric(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeSegments(segments) {
  return segments
    .map((segment) => ({
      name: String(segment.name || "Route segment"),
      lengthM: Math.max(1, numeric(segment.lengthM ?? segment.length_m, 1)),
      gradePct: numeric(segment.gradePct ?? segment.grade_pct),
      turnDeg: numeric(segment.turnDeg ?? segment.turn_deg),
      roadWidthM: clamp(numeric(segment.roadWidthM ?? segment.road_width_m, 8.6), 4, 14),
      kind: String(segment.kind || "rolling"),
      surface: String(segment.surface || "asphalt"),
      scenery: String(segment.scenery || "fields"),
    }))
    .filter((segment) => segment.lengthM > 0);
}

export class RideMotionModel {
  constructor({
    dashSpacing = 7.8,
    maxDt = 0.06,
    // Eased so the once-per-second snapshot speed step glides instead of
    // surging: ~95% converged by the time the next snapshot lands.
    speedResponse = 3.0,
    staleSnapshotMs = 3000,
    routeSegments = [],
  } = {}) {
    this.dashSpacing = dashSpacing;
    this.maxDt = maxDt;
    this.speedResponse = speedResponse;
    this.staleSnapshotMs = staleSnapshotMs;
    this.lastSnapshotAtMs = null;
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
    this.renderDistanceM = 0;
    this.gradePct = 0;
    this.routeGradePct = 0;
    this.routeSegmentName = "Route segment";
    this.routeSegmentKind = "rolling";
    this.routeSurface = "asphalt";
    this.routeHeadingDeg = 0;
    this.routeCurveStrength = 0;
    this.roadWidthM = 8.6;
    this.routeSegmentProgress = 0;
    this.routeSegmentRemainingM = 0;
    this.nextSegmentName = "Route segment";
    this.nextSegmentGradePct = 0;
    this.segmentGateAlpha = 0;
    this.scenery = "fields";
    this.roadOffset = 0;
    this.roadPitch = 0;
    this.cameraBob = 0;
    this.cameraPitch = 0;
    this.cameraRoll = 0;
    this.cameraLookX = 0;
    this.horizonLift = 0;
    this.worldYaw = 0;
    this.roadScaleX = 1;
    this.shoulderSpreadM = 5.4;
    this.sceneryDrift = 0;
  }

  updateFromSnapshot(snapshot) {
    this.lastSnapshotAtMs =
      typeof performance !== "undefined" ? performance.now() : 0;
    this.active = Boolean(snapshot.active);
    this.paused = Boolean(snapshot.paused);
    this.mode = snapshot.mode || null;
    this.distanceM = this.active ? numeric(snapshot.distance_m) : 0;
    const routeSegment = this.segmentForDistance(this.distanceM);
    this.routeGradePct = routeSegment.gradePct;
    this.routeSegmentName = routeSegment.name;
    this.routeSegmentKind = routeSegment.kind;
    this.routeSurface = routeSegment.surface;
    this.routeHeadingDeg = routeSegment.headingDeg;
    this.routeCurveStrength = routeSegment.curveStrength;
    this.roadWidthM = routeSegment.roadWidthM;
    this.routeSegmentProgress = routeSegment.progress;
    this.routeSegmentRemainingM = routeSegment.remainingM;
    this.nextSegmentName = routeSegment.nextName;
    this.nextSegmentGradePct = routeSegment.nextGradePct;
    this.segmentGateAlpha = this.active
      ? clamp((this.routeSegmentProgress - 0.72) / 0.28, 0, 1)
      : 0;
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
        headingDeg: 0,
        curveStrength: 0,
        roadWidthM: 8.6,
        kind: "rolling",
        surface: "asphalt",
        scenery: "fields",
      };
    }

    let routeDistanceM = numeric(distanceM) % this.routeLengthM;
    if (routeDistanceM < 0) routeDistanceM += this.routeLengthM;
    let completedHeadingDeg = 0;

    for (let index = 0; index < this.routeSegments.length; index += 1) {
      const segment = this.routeSegments[index];
      if (routeDistanceM < segment.lengthM) {
        const nextSegment =
          this.routeSegments[(index + 1) % this.routeSegments.length];
        const progress = routeDistanceM / segment.lengthM;
        const headingDeg = completedHeadingDeg + segment.turnDeg * progress;
        return {
          name: segment.name,
          gradePct: segment.gradePct,
          kind: segment.kind,
          surface: segment.surface,
          headingDeg,
          curveStrength: clamp(segment.turnDeg / 60, -1, 1),
          roadWidthM: segment.roadWidthM,
          progress,
          remainingM: segment.lengthM - routeDistanceM,
          nextName: nextSegment.name,
          nextGradePct: nextSegment.gradePct,
          scenery: segment.scenery,
        };
      }
      routeDistanceM -= segment.lengthM;
      completedHeadingDeg += segment.turnDeg;
    }

    const lastSegment = this.routeSegments[this.routeSegments.length - 1];
    return {
      name: lastSegment.name,
      gradePct: lastSegment.gradePct,
      progress: 1,
      remainingM: 0,
      nextName: this.routeSegments[0].name,
      nextGradePct: this.routeSegments[0].gradePct,
      headingDeg: completedHeadingDeg,
      curveStrength: 0,
      roadWidthM: lastSegment.roadWidthM,
      kind: lastSegment.kind,
      surface: lastSegment.surface,
      scenery: lastSegment.scenery,
    };
  }

  advance(dt, nowMs) {
    const boundedDt = clamp(numeric(dt), 0, this.maxDt);

    // A dead server must not leave the world riding forever: without fresh
    // snapshots the last known speed would be integrated indefinitely, so
    // coast to a stop when the stream goes stale.
    if (
      this.lastSnapshotAtMs !== null &&
      numeric(nowMs) - this.lastSnapshotAtMs > this.staleSnapshotMs
    ) {
      this.targetSpeedMps = 0;
    }

    const response = 1 - Math.exp(-this.speedResponse * boundedDt);
    this.speedMps += (this.targetSpeedMps - this.speedMps) * response;

    if (Math.abs(this.speedMps) < 0.01 && this.targetSpeedMps === 0) {
      this.speedMps = 0;
    }

    // Continuous route distance for the world-fixed camera: integrate the
    // smoothed speed between snapshots and gently converge on the authoritative
    // snapshot distance, snapping only across resets and large gaps.
    this.renderDistanceM += this.speedMps * boundedDt;
    const distanceErrorM = this.distanceM - this.renderDistanceM;
    if (Math.abs(distanceErrorM) > 25) {
      this.renderDistanceM = this.distanceM;
    } else {
      this.renderDistanceM += distanceErrorM * (1 - Math.exp(-1.5 * boundedDt));
    }

    this.roadOffset =
      (this.roadOffset + this.speedMps * boundedDt) % this.dashSpacing;
    this.roadPitch = clamp(this.gradePct * 0.006, -0.08, 0.08);
    // No camera bob: a rider's eyeline does not oscillate on smooth road,
    // and any rhythmic vertical motion reads as the world bumping. Terrain
    // height alone moves the camera vertically.
    this.cameraBob = 0;
    this.cameraPitch = clamp(this.gradePct * 0.006, -0.08, 0.08);
    this.cameraRoll = clamp(-this.routeCurveStrength * 0.08, -0.08, 0.08);
    this.cameraLookX = clamp(this.routeCurveStrength * 4.5, -4.5, 4.5);
    this.horizonLift = clamp(this.gradePct * 0.08, -0.8, 0.8);
    this.worldYaw = clamp(-this.routeHeadingDeg * 0.012, -0.75, 0.75);
    this.roadScaleX = clamp(this.roadWidthM / 8.6, 0.48, 1.65);
    this.shoulderSpreadM = this.roadWidthM / 2 + 1.1;
    this.sceneryDrift =
      Math.sin((this.routeHeadingDeg * Math.PI) / 180) * 5 +
      this.routeCurveStrength * 4;
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
      renderDistanceM: this.renderDistanceM,
      gradePct: this.gradePct,
      routeGradePct: this.routeGradePct,
      routeSegmentName: this.routeSegmentName,
      routeSegmentKind: this.routeSegmentKind,
      routeSurface: this.routeSurface,
      routeHeadingDeg: this.routeHeadingDeg,
      routeCurveStrength: this.routeCurveStrength,
      roadWidthM: this.roadWidthM,
      routeSegmentProgress: this.routeSegmentProgress,
      routeSegmentRemainingM: this.routeSegmentRemainingM,
      nextSegmentName: this.nextSegmentName,
      nextSegmentGradePct: this.nextSegmentGradePct,
      segmentGateAlpha: this.segmentGateAlpha,
      scenery: this.scenery,
      roadOffset: this.roadOffset,
      roadPitch: this.roadPitch,
      cameraBob: this.cameraBob,
      cameraPitch: this.cameraPitch,
      cameraRoll: this.cameraRoll,
      cameraLookX: this.cameraLookX,
      horizonLift: this.horizonLift,
      worldYaw: this.worldYaw,
      roadScaleX: this.roadScaleX,
      shoulderSpreadM: this.shoulderSpreadM,
      sceneryDrift: this.sceneryDrift,
    };
  }
}
