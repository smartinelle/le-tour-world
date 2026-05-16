const SVG_NS = "http://www.w3.org/2000/svg";

const GEOMETRY = {
  width: 1344,
  height: 704,
  cols: 21,
  rows: 11,
  cell: 64,
  protectedRect: { c: 7, r: 3, w: 7, h: 5 },
  visitedRadiusScale: 0.42,
  unvisitedRadiusScale: 0.357,
  unvisitedOpacity: "0.06",
  visitedOpacity: "0.94",
};

const COLORS = {
  slate: "#2d2f33",
  white: "#ffffff",
  zest: "#f43e01",
};

const FTP_COLOR_STOPS = [
  { pct: 0.25, L: 88, C: 0.04, H: 55 },
  { pct: 0.5, L: 80, C: 0.1, H: 48 },
  { pct: 0.75, L: 70, C: 0.16, H: 42 },
  { pct: 1.0, L: 60.5, C: 0.22, H: 35 },
  { pct: 1.3, L: 52, C: 0.21, H: 32 },
  { pct: 1.75, L: 45, C: 0.19, H: 28 },
  { pct: 2.5, L: 0, C: 0, H: 0 },
];

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function numeric(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function oklch({ L, C, H }) {
  return `oklch(${L.toFixed(1)}% ${C.toFixed(3)} ${H.toFixed(1)})`;
}

function wattsToColor(watts, ftp) {
  const ftpValue = Math.max(1, numeric(ftp, 200));
  const pct = clamp(numeric(watts) / ftpValue, 0.25, 2.5);
  let lo = FTP_COLOR_STOPS[0];
  let hi = FTP_COLOR_STOPS[FTP_COLOR_STOPS.length - 1];

  for (let index = 0; index < FTP_COLOR_STOPS.length - 1; index += 1) {
    const current = FTP_COLOR_STOPS[index];
    const next = FTP_COLOR_STOPS[index + 1];
    if (pct >= current.pct && pct <= next.pct) {
      lo = current;
      hi = next;
      break;
    }
  }

  const t = (pct - lo.pct) / (hi.pct - lo.pct || 1);
  return oklch({
    L: lerp(lo.L, hi.L, t),
    C: lerp(lo.C, hi.C, t),
    H: lerp(lo.H, hi.H, t),
  });
}

function speedToCellsPerSec(speedKmh) {
  const speed = Math.abs(numeric(speedKmh));
  return speed < 0.5 ? 0 : clamp(speed * 0.28, 0, 16);
}

function isProtected(col, row) {
  const rect = GEOMETRY.protectedRect;
  return (
    col >= rect.c &&
    col < rect.c + rect.w &&
    row >= rect.r &&
    row < rect.r + rect.h
  );
}

function buildSerpentineRoute() {
  const route = [];
  for (let row = 0; row < GEOMETRY.rows; row += 1) {
    const cells = [];
    for (let col = 0; col < GEOMETRY.cols; col += 1) {
      if (!isProtected(col, row)) cells.push({ col, row });
    }
    if (row % 2 === 1) cells.reverse();
    route.push(...cells);
  }
  return route;
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, String(value));
  }
  return element;
}

class LiveSnake {
  constructor(root) {
    this.root = root;
    this.svg = root.querySelector(".tr-snake-svg");
    this.valueNode = root.querySelector("[data-snake-watts]");
    this.loaderDots = Array.from(root.querySelectorAll(".tr-snake-loader span"));
    this.ftp = Math.max(1, numeric(root.dataset.ftp, 200));
    this.snapshotUrl = root.dataset.snapshotUrl || "/api/ride/snapshots";
    this.route = buildSerpentineRoute();
    this.circles = [];
    this.visited = new Set();
    this.head = 0;
    this.speedKmh = 0;
    this.rawPower = null;
    this.smoothedPower = null;
    this.lastSampleMs = 0;
    this.lastFrameMs = 0;
    this.source = null;
    this.reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    this.buildSvg();
    this.layout();
    this.connect();
    this.frame = this.frame.bind(this);
    this.resizeObserver = new ResizeObserver(() => this.layout());
    this.resizeObserver.observe(this.root.parentElement || this.root);
    requestAnimationFrame(this.frame);
  }

  buildSvg() {
    if (!this.svg) return;
    this.svg.replaceChildren();
    const cells = svgElement("g", { class: "tr-snake-cells" });
    const r = GEOMETRY.cell * GEOMETRY.visitedRadiusScale;
    const unvisitedR = GEOMETRY.cell * GEOMETRY.unvisitedRadiusScale;

    this.route.forEach(({ col, row }, index) => {
      const cx = col * GEOMETRY.cell + GEOMETRY.cell / 2;
      const cy = row * GEOMETRY.cell + GEOMETRY.cell / 2;
      const circle = svgElement("circle", {
        cx,
        cy,
        r: unvisitedR,
        fill: COLORS.slate,
        opacity: GEOMETRY.unvisitedOpacity,
      });
      circle.dataset.routeIndex = String(index);
      cells.append(circle);
      this.circles.push({ circle, r, unvisitedR });
    });

    this.headMarker = svgElement("circle", {
      r: r - 5,
      fill: "none",
      stroke: COLORS.white,
      "stroke-width": 1.6,
      opacity: 0,
    });
    this.svg.append(cells, this.headMarker);
  }

  layout() {
    const parent = this.root.parentElement || this.root;
    const bounds = parent.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;

    const scale = Math.min(
      bounds.width / GEOMETRY.width,
      bounds.height / GEOMETRY.height,
    );
    const width = Math.max(280, Math.floor(GEOMETRY.width * scale));
    const height = Math.max(146, Math.floor(GEOMETRY.height * scale));
    this.root.style.width = `${width}px`;
    this.root.style.height = `${height}px`;
  }

  connect() {
    if (!window.EventSource) return;
    this.source = new EventSource(this.snapshotUrl);
    this.source.addEventListener("snapshot", (event) => {
      try {
        this.updateSnapshot(JSON.parse(event.data));
      } catch {
        // Keep the previous frame if a transient SSE payload is malformed.
      }
    });
  }

  updateSnapshot(snapshot) {
    const now = performance.now();
    const active = Boolean(snapshot.active) && !Boolean(snapshot.paused);
    const power = snapshot.power_w;

    if (typeof power === "number" && Number.isFinite(power)) {
      const elapsedSec =
        this.lastSampleMs > 0 ? Math.max(0.001, (now - this.lastSampleMs) / 1000) : 0;
      const alpha = this.lastSampleMs > 0 ? 1 - Math.exp(-elapsedSec / 3) : 1;
      this.smoothedPower =
        this.smoothedPower === null
          ? power
          : this.smoothedPower * (1 - alpha) + power * alpha;
      this.rawPower = power;
      this.lastSampleMs = now;
    }

    this.speedKmh =
      active && typeof snapshot.speed_mps === "number"
        ? Math.max(0, snapshot.speed_mps * 3.6)
        : 0;
  }

  decayMissingPower(dt, now) {
    if (this.smoothedPower === null || this.lastSampleMs === 0) return;
    if (now - this.lastSampleMs <= 3000) return;
    const alpha = 1 - Math.exp(-dt / 5);
    this.smoothedPower = this.smoothedPower * (1 - alpha);
  }

  frame(now) {
    if (!document.body.contains(this.root)) {
      this.destroy();
      return;
    }

    const dt =
      this.lastFrameMs > 0
        ? clamp((now - this.lastFrameMs) / 1000, 0, 0.08)
        : 0;
    this.lastFrameMs = now;

    this.decayMissingPower(dt, now);
    const power = this.smoothedPower ?? 0;
    const color = wattsToColor(power, this.ftp);
    this.updateReadout(power, color);
    this.updateLoader(now);

    if (!this.reducedMotion) {
      this.advance(dt, color);
    }

    requestAnimationFrame(this.frame);
  }

  updateReadout(power, color) {
    const hasPower = power > 1;
    const cps = speedToCellsPerSec(this.speedKmh);
    if (hasPower || cps > 0) {
      this.root.classList.remove("is-warming");
    }
    this.root.classList.toggle("has-motion", cps > 0);

    if (this.valueNode) {
      this.valueNode.textContent = hasPower ? String(Math.round(power)) : "---";
      this.valueNode.style.color = color;
    }
  }

  updateLoader(now) {
    if (this.loaderDots.length === 0) return;
    const phase = (now / 1500) % this.loaderDots.length;
    const count = this.loaderDots.length;
    this.loaderDots.forEach((dot, index) => {
      const distance = (index - phase + count) % count;
      const opacity = clamp(1 - distance / count, 0.08, 1);
      dot.style.opacity = opacity.toFixed(3);
    });
  }

  advance(dt, color) {
    const cps = speedToCellsPerSec(this.speedKmh);
    if (cps <= 0 || dt <= 0) {
      this.updateHeadMarker();
      return;
    }

    const previousHead = Math.floor(this.head);
    this.head += cps * dt;
    if (this.head >= this.route.length) {
      this.hardReset();
      this.head %= this.route.length;
    }

    const currentHead = Math.floor(this.head);
    for (let index = previousHead; index <= currentHead; index += 1) {
      this.visit(index, color);
    }
    this.updateHeadMarker();
  }

  visit(index, color) {
    const normalized = ((index % this.route.length) + this.route.length) % this.route.length;
    if (this.visited.has(normalized)) return;
    const item = this.circles[normalized];
    if (!item) return;
    item.circle.setAttribute("fill", color);
    item.circle.setAttribute("opacity", GEOMETRY.visitedOpacity);
    item.circle.setAttribute("r", String(item.r));
    this.visited.add(normalized);
  }

  hardReset() {
    this.visited.clear();
    this.circles.forEach(({ circle, unvisitedR }) => {
      circle.setAttribute("fill", COLORS.slate);
      circle.setAttribute("opacity", GEOMETRY.unvisitedOpacity);
      circle.setAttribute("r", String(unvisitedR));
    });
  }

  updateHeadMarker() {
    if (!this.headMarker || this.route.length === 0) return;
    const cps = speedToCellsPerSec(this.speedKmh);
    const index = clamp(Math.floor(this.head), 0, this.route.length - 1);
    const cell = this.route[index];
    const cx = cell.col * GEOMETRY.cell + GEOMETRY.cell / 2;
    const cy = cell.row * GEOMETRY.cell + GEOMETRY.cell / 2;
    this.headMarker.setAttribute("cx", String(cx));
    this.headMarker.setAttribute("cy", String(cy));
    this.headMarker.setAttribute("opacity", cps > 0 ? "0.85" : "0.35");
  }

  destroy() {
    if (this.source) this.source.close();
    if (this.resizeObserver) this.resizeObserver.disconnect();
    this.root.__leTourLiveSnake = null;
  }
}

export function bootLiveSnake() {
  document.querySelectorAll("[data-le-tour-snake]").forEach((root) => {
    if (root.__leTourLiveSnake) return;
    root.__leTourLiveSnake = new LiveSnake(root);
  });
}

window.LeTourLiveSnake = { boot: bootLiveSnake };

function startLiveSnakeObserver() {
  bootLiveSnake();
  if (window.__leTourLiveSnakeObserver) return;
  window.__leTourLiveSnakeObserver = new MutationObserver(() => bootLiveSnake());
  window.__leTourLiveSnakeObserver.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startLiveSnakeObserver, {
    once: true,
  });
} else {
  startLiveSnakeObserver();
}
