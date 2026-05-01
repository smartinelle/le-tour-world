function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function numeric(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export class RideMotionModel {
  constructor({
    dashSpacing = 7.8,
    maxDt = 0.06,
    speedResponse = 7.5,
  } = {}) {
    this.dashSpacing = dashSpacing;
    this.maxDt = maxDt;
    this.speedResponse = speedResponse;
    this.active = false;
    this.paused = false;
    this.mode = null;
    this.targetSpeedMps = 0;
    this.speedMps = 0;
    this.distanceM = 0;
    this.gradePct = 0;
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
    this.gradePct = this.active ? numeric(snapshot.sim_grade_pct) : 0;
    this.targetSpeedMps =
      this.active && !this.paused ? Math.max(0, numeric(snapshot.speed_mps)) : 0;
    return this.state();
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
      roadOffset: this.roadOffset,
      roadPitch: this.roadPitch,
      cameraBob: this.cameraBob,
      cameraPitch: this.cameraPitch,
      horizonLift: this.horizonLift,
    };
  }
}
