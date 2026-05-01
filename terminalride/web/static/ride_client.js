export class RideApiClient {
  constructor({
    snapshotUrl = "/api/ride/snapshots",
    startUrl = "/api/ride/start",
    stopUrl = "/api/ride/stop",
    pauseUrl = "/api/ride/toggle-pause",
    ergTargetUrl = "/api/ride/erg-target",
    simGradeUrl = "/api/ride/sim-grade",
    routeUrl = "/api/ride/route",
  } = {}) {
    this.snapshotUrl = snapshotUrl;
    this.startUrl = startUrl;
    this.stopUrl = stopUrl;
    this.pauseUrl = pauseUrl;
    this.ergTargetUrl = ergTargetUrl;
    this.simGradeUrl = simGradeUrl;
    this.routeUrl = routeUrl;
  }

  connectSnapshots({ onSnapshot, onError }) {
    const source = new EventSource(this.snapshotUrl);
    source.addEventListener("snapshot", (event) => {
      onSnapshot(JSON.parse(event.data));
    });
    source.onerror = () => {
      if (onError) onError();
    };
    return source;
  }

  startRide(mode) {
    return this.postJson(this.startUrl, { mode });
  }

  stopRide() {
    return this.postJson(this.stopUrl);
  }

  togglePause() {
    return this.postJson(this.pauseUrl);
  }

  adjustErgTarget(delta) {
    return this.postJson(this.ergTargetUrl, { delta });
  }

  adjustSimGrade(delta) {
    return this.postJson(this.simGradeUrl, { delta });
  }

  async getRoute() {
    const response = await fetch(this.routeUrl);
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json();
  }

  async postJson(path, payload = {}) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json();
  }
}
