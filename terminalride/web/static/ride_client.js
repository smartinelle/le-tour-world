export class RideApiClient {
  constructor({
    snapshotUrl = "/api/ride/snapshots",
    startUrl = "/api/ride/start",
    stopUrl = "/api/ride/stop",
    pauseUrl = "/api/ride/toggle-pause",
    ergTargetUrl = "/api/ride/erg-target",
    simGradeUrl = "/api/ride/sim-grade",
    routesUrl = "/api/ride/routes",
    routeUrl = "/api/ride/route",
    devicesStatusUrl = "/api/devices/status",
  } = {}) {
    this.snapshotUrl = snapshotUrl;
    this.startUrl = startUrl;
    this.stopUrl = stopUrl;
    this.pauseUrl = pauseUrl;
    this.ergTargetUrl = ergTargetUrl;
    this.simGradeUrl = simGradeUrl;
    this.routesUrl = routesUrl;
    this.routeUrl = routeUrl;
    this.devicesStatusUrl = devicesStatusUrl;
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

  startRide(mode, routeId = null) {
    return this.postJson(this.startUrl, { mode, route_id: routeId });
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

  async getRoutes() {
    const response = await fetch(this.routesUrl);
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json();
  }

  async getRoute(routeId = null) {
    const url = new URL(this.routeUrl, window.location.origin);
    if (routeId) url.searchParams.set("route_id", routeId);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json();
  }

  async getDeviceStatus() {
    const response = await fetch(this.devicesStatusUrl);
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
