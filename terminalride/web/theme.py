"""Shared web presentation theme for TerminalRide."""

WEB_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --q-primary: #e85d04;
    --q-secondary: #181b1f;
    --tr-bg: #f5f3ef;
    --tr-bg-alt: #ebe7df;
    --tr-surface: #fffefd;
    --tr-surface-strong: #f8f6f1;
    --tr-text: #181b1f;
    --tr-muted: #667085;
    --tr-soft: #98a2b3;
    --tr-border: #ddd8cf;
    --tr-border-strong: #c9c1b5;
    --tr-accent: #e85d04;
    --tr-accent-dark: #ba4a03;
    --tr-accent-soft: #fff0e5;
    --tr-green: #15803d;
    --tr-green-soft: #e8f6ee;
    --tr-blue: #1769aa;
    --tr-blue-soft: #e8f2fb;
    --tr-danger: #b42318;
    --tr-danger-soft: #fff1f0;
    --tr-shadow: 0 18px 42px rgba(24, 27, 31, 0.08);
    --tr-shadow-tight: 0 10px 28px rgba(24, 27, 31, 0.07);
    --tr-radius: 8px;
}

* {
    box-sizing: border-box;
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

body {
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(245, 243, 239, 0.9)),
        repeating-linear-gradient(
            90deg,
            rgba(24, 27, 31, 0.025) 0,
            rgba(24, 27, 31, 0.025) 1px,
            transparent 1px,
            transparent 72px
        ),
        var(--tr-bg) !important;
    color: var(--tr-text);
    margin: 0;
}

.tr-shell {
    width: min(1220px, calc(100vw - 48px));
    margin: 0 auto;
}

.tr-header {
    background: rgba(255, 254, 253, 0.86) !important;
    border-bottom: 1px solid var(--tr-border);
    backdrop-filter: blur(18px);
    box-shadow: none !important;
}

.tr-brand {
    align-items: center;
    color: var(--tr-text);
    display: inline-flex;
    font-size: 1rem;
    font-weight: 800;
    gap: 0.6rem;
    letter-spacing: 0;
    text-decoration: none;
}

.tr-brand-mark {
    align-items: center;
    background: var(--tr-text);
    border-radius: 6px;
    color: #fffefd;
    display: inline-flex;
    font-size: 0.75rem;
    font-weight: 800;
    height: 28px;
    justify-content: center;
    width: 28px;
}

.nav-link {
    border-radius: 7px;
    color: var(--tr-muted);
    font-size: 0.88rem;
    font-weight: 650;
    padding: 0.56rem 0.72rem;
    text-decoration: none;
    transition: background 0.16s ease, color 0.16s ease;
}

.nav-link:hover {
    background: var(--tr-surface-strong);
    color: var(--tr-text);
}

.nav-link.active {
    background: var(--tr-text);
    color: #fffefd;
}

.tr-page {
    padding: 26px 0 56px;
}

.tr-eyebrow {
    color: var(--tr-muted);
    font-size: 0.76rem;
    font-weight: 750;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.tr-title {
    color: var(--tr-text);
    font-size: clamp(2rem, 3.5vw, 3.25rem);
    font-weight: 800;
    letter-spacing: 0;
    line-height: 0.96;
    margin: 0;
    max-width: 100%;
    overflow-wrap: break-word;
    display: block !important;
    white-space: normal !important;
    word-break: normal;
}

.tr-subtitle {
    color: var(--tr-muted);
    font-size: 1rem;
    line-height: 1.55;
    margin: 0;
}

.tr-panel {
    background: rgba(255, 254, 253, 0.92);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    box-shadow: var(--tr-shadow);
}

.tr-panel-flat {
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
}

.tr-section-label {
    color: var(--tr-muted);
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.tr-btn-primary,
.tr-btn-secondary,
.btn-primary,
.btn-secondary {
    border-radius: var(--tr-radius) !important;
    box-shadow: none !important;
    font-size: 0.9rem !important;
    font-weight: 800 !important;
    letter-spacing: 0 !important;
    min-height: 44px !important;
    padding: 0.72rem 1rem !important;
    text-transform: none !important;
    transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease !important;
}

.q-btn.tr-btn-primary,
.q-btn.btn-primary {
    background: var(--tr-accent) !important;
    border: 1px solid var(--tr-accent) !important;
    color: #fffefd !important;
}

.q-btn.tr-btn-primary:hover,
.q-btn.btn-primary:hover {
    background: var(--tr-accent-dark) !important;
    border-color: var(--tr-accent-dark) !important;
}

.q-btn.tr-btn-secondary,
.q-btn.btn-secondary {
    background: var(--tr-surface) !important;
    border: 1px solid var(--tr-border-strong) !important;
    color: var(--tr-text) !important;
}

.q-btn.tr-mode-button {
    background: var(--tr-surface-strong) !important;
    border: 1px solid var(--tr-border) !important;
    color: var(--tr-muted) !important;
}

.q-btn.tr-mode-button.active {
    background: var(--tr-text) !important;
    border-color: var(--tr-text) !important;
    color: #fffefd !important;
}

.tr-btn-primary,
.btn-primary {
    background: var(--tr-accent) !important;
    border: 1px solid var(--tr-accent) !important;
    color: #fffefd !important;
}

.tr-btn-primary:hover,
.btn-primary:hover {
    background: var(--tr-accent-dark) !important;
    border-color: var(--tr-accent-dark) !important;
}

.tr-btn-secondary,
.btn-secondary {
    background: var(--tr-surface) !important;
    border: 1px solid var(--tr-border-strong) !important;
    color: var(--tr-text) !important;
}

.tr-btn-secondary:hover,
.btn-secondary:hover {
    border-color: var(--tr-text) !important;
}

.tr-status-strip {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.tr-status-tile {
    align-items: center;
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    display: flex;
    gap: 0.72rem;
    min-height: 72px;
    padding: 0.9rem 1rem;
}

.status-dot {
    border-radius: 999px;
    display: inline-block;
    flex: 0 0 auto;
    height: 10px;
    width: 10px;
}

.status-dot.connected {
    background: var(--tr-green);
    box-shadow: 0 0 0 4px var(--tr-green-soft);
}

.status-dot.disconnected {
    background: var(--tr-soft);
    box-shadow: 0 0 0 4px #ece8df;
}

.tr-status-name {
    color: var(--tr-text);
    font-size: 0.9rem;
    font-weight: 800;
    line-height: 1.2;
}

.tr-status-meta {
    color: var(--tr-muted);
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.25;
}

.tr-console-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.16fr) minmax(300px, 0.84fr);
}

.tr-mode-grid {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.tr-mode-button {
    background: var(--tr-surface-strong) !important;
    border: 1px solid var(--tr-border) !important;
    border-radius: var(--tr-radius) !important;
    color: var(--tr-muted) !important;
    font-weight: 800 !important;
    min-height: 50px !important;
    text-transform: none !important;
}

.tr-mode-button.active {
    background: var(--tr-text) !important;
    border-color: var(--tr-text) !important;
    color: #fffefd !important;
}

.tr-control-band {
    background: var(--tr-surface-strong);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    padding: 1rem;
}

.tr-history-row,
.tr-device-row {
    align-items: center;
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    display: grid;
    gap: 1rem;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 1rem;
}

.tr-empty {
    align-items: center;
    background: repeating-linear-gradient(
        -45deg,
        #fffefd,
        #fffefd 10px,
        #f8f6f1 10px,
        #f8f6f1 20px
    );
    border: 1px dashed var(--tr-border-strong);
    border-radius: var(--tr-radius);
    color: var(--tr-muted);
    display: flex;
    justify-content: space-between;
    min-height: 92px;
    padding: 1rem;
}

.session-view {
    background: var(--tr-bg);
    min-height: 100vh;
    padding: 18px;
}

.tr-cockpit {
    display: grid;
    gap: 14px;
    grid-template-rows: auto auto auto auto;
    min-height: auto;
}

.tr-cockpit-top,
.tr-cockpit-controls {
    align-items: center;
    display: grid;
    gap: 12px;
    grid-template-columns: auto minmax(0, 1fr) auto;
}

.tr-power-panel {
    align-items: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: min(46vh, 360px);
    padding: clamp(1rem, 4vw, 3rem);
    text-align: center;
}

.tr-power-value {
    color: var(--tr-accent);
    font-size: clamp(6rem, 18vw, 14rem);
    font-variant-numeric: tabular-nums;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 0.82;
    min-width: 4ch;
}

.tr-power-unit {
    color: var(--tr-muted);
    font-size: clamp(1.2rem, 3vw, 2rem);
    font-weight: 800;
    margin-top: 0.3rem;
}

.tr-metric-rail {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
}

.tr-metric-cell {
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    min-height: 116px;
    padding: 1rem;
}

.tr-metric-value {
    color: var(--tr-text);
    font-size: clamp(1.7rem, 4vw, 3rem);
    font-variant-numeric: tabular-nums;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1;
    min-width: 5ch;
}

.tr-metric-label,
.metric-label {
    color: var(--tr-muted);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    margin-top: 0.7rem;
    text-transform: uppercase;
}

.metric-card {
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    padding: 1rem;
}

.connection-status {
    align-items: center;
    border-radius: var(--tr-radius);
    display: flex;
    gap: 0.7rem;
    padding: 0.9rem 1rem;
}

.connection-status.success {
    background: var(--tr-green-soft);
    color: #14532d;
}

.connection-status.error {
    background: var(--tr-danger-soft);
    color: var(--tr-danger);
}

.connection-status.info {
    background: var(--tr-blue-soft);
    color: var(--tr-blue);
}

.device-list {
    max-height: 300px;
    overflow-y: auto;
}

.scan-dialog {
    max-width: 520px;
    min-width: min(400px, calc(100vw - 32px));
    width: 90vw;
}

.scan-dialog-header,
.scan-dialog-footer {
    background: var(--tr-surface-strong);
    border-color: var(--tr-border);
    padding: 1rem 1.25rem;
}

.scan-dialog-header {
    border-bottom: 1px solid var(--tr-border);
}

.scan-dialog-footer {
    border-top: 1px solid var(--tr-border);
}

.scan-dialog-body {
    padding: 1.25rem;
}

.scan-device-item {
    background: var(--tr-surface) !important;
    border: 1px solid var(--tr-border) !important;
    border-radius: var(--tr-radius) !important;
    box-shadow: none !important;
    padding: 1rem !important;
    transition: background 0.16s ease, border-color 0.16s ease !important;
}

.scan-device-item:hover {
    background: var(--tr-accent-soft) !important;
    border-color: var(--tr-accent) !important;
}

.signal-bars {
    align-items: flex-end;
    display: flex;
    gap: 2px;
    height: 18px;
}

.signal-bar {
    background: var(--tr-border);
    border-radius: 1px;
    width: 4px;
}

.signal-bar.active {
    background: var(--tr-accent);
}

.empty-state {
    color: var(--tr-muted);
    padding: 1.4rem;
    text-align: center;
}

.empty-state-icon {
    color: var(--tr-soft);
    font-size: 2.4rem;
    line-height: 1;
    margin-bottom: 0.8rem;
}

.empty-state-title {
    color: var(--tr-text);
    font-weight: 800;
    margin-bottom: 0.45rem;
}

.empty-state-tips {
    background: var(--tr-accent-soft);
    border: 1px solid rgba(232, 93, 4, 0.16);
    border-radius: var(--tr-radius);
    color: var(--tr-muted);
    font-size: 0.86rem;
    margin-top: 1rem;
    padding: 1rem;
    text-align: left;
}

.empty-state-tips li {
    margin-bottom: 0.45rem;
}

/* Console refinement layer */
.tr-panel-tight {
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(248, 246, 241, 0.76)),
        var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    box-shadow: var(--tr-shadow-tight);
}

.tr-panel-header {
    align-items: start;
    border-bottom: 1px solid var(--tr-border);
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) auto;
    padding-bottom: 14px;
}

.tr-panel-title {
    color: var(--tr-text);
    font-size: 1rem;
    font-weight: 800;
    line-height: 1.2;
}

.tr-btn-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.tr-state-badge {
    align-items: center;
    background: var(--tr-surface-strong);
    border: 1px solid var(--tr-border);
    border-radius: 999px;
    color: var(--tr-muted);
    display: inline-flex;
    font-size: 0.72rem;
    font-weight: 800;
    gap: 0.45rem;
    letter-spacing: 0.08em;
    line-height: 1;
    padding: 0.48rem 0.62rem;
    text-transform: uppercase;
    white-space: nowrap;
}

.tr-state-badge.live,
.tr-state-badge.ready {
    background: var(--tr-green-soft);
    border-color: rgba(21, 128, 61, 0.18);
    color: #14532d;
}

.tr-state-badge.demo {
    background: var(--tr-blue-soft);
    border-color: rgba(23, 105, 170, 0.18);
    color: var(--tr-blue);
}

.tr-status-strip {
    gap: 12px;
}

.tr-status-tile {
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(248, 246, 241, 0.72)),
        var(--tr-surface);
    min-height: 82px;
    padding: 0.95rem 1rem;
}

.tr-console-grid {
    gap: 16px;
    grid-template-columns: minmax(0, 1.3fr) minmax(330px, 0.7fr);
}

.tr-console-main,
.tr-console-side {
    align-content: start;
    display: grid;
    gap: 14px;
}

.tr-console-main {
    grid-template-rows: auto auto auto auto;
}

.tr-console-side {
    grid-template-rows: auto auto;
}

.tr-mode-button {
    min-height: 54px !important;
}

.tr-control-band {
    background:
        linear-gradient(135deg, rgba(255, 240, 229, 0.86), rgba(248, 246, 241, 0.9)),
        var(--tr-surface-strong);
}

.tr-control-value {
    color: var(--tr-text);
    font-family: 'IBM Plex Mono', monospace;
    font-size: clamp(2rem, 5vw, 3.4rem);
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    line-height: 0.95;
}

.tr-meta-grid {
    display: grid;
    gap: 9px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tr-route-picker,
.tr-route-live {
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    display: grid;
    gap: 12px;
    padding: 1rem;
}

.tr-route-stats,
.tr-summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.tr-meta-row {
    background: rgba(255, 254, 253, 0.72);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    min-height: 68px;
    padding: 0.78rem 0.85rem;
}

.tr-meta-value {
    color: var(--tr-text);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.1rem;
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    line-height: 1;
}

.tr-meta-label {
    color: var(--tr-muted);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    margin-top: 0.55rem;
    text-transform: uppercase;
}

.tr-road-preview {
    background: linear-gradient(180deg, #dcecf2 0 44%, #97af77 44% 100%);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    display: block;
    height: 186px;
    overflow: hidden;
    position: relative;
    width: 100%;
}

.tr-road-preview::before {
    background:
        linear-gradient(90deg, transparent 47%, rgba(255, 254, 253, 0.9) 48%, rgba(255, 254, 253, 0.9) 52%, transparent 53%),
        linear-gradient(110deg, transparent 0 30%, #1e2320 31% 69%, transparent 70%);
    bottom: -32px;
    content: "";
    height: 130px;
    left: 22%;
    position: absolute;
    transform: perspective(400px) rotateX(58deg);
    transform-origin: bottom center;
    width: 56%;
}

.tr-road-preview::after {
    background: rgba(255, 254, 253, 0.72);
    border: 1px solid rgba(221, 216, 207, 0.9);
    border-radius: 999px;
    color: var(--tr-muted);
    content: "3D ROAD";
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    padding: 0.42rem 0.58rem;
    position: absolute;
    right: 12px;
    top: 12px;
}

.tr-device-row {
    grid-template-columns: minmax(0, 1fr) auto auto;
    min-height: 96px;
}

.tr-device-meta {
    align-items: end;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.tr-signal-bars {
    align-items: flex-end;
    display: flex;
    gap: 3px;
    height: 20px;
}

.tr-signal-bars span {
    background: var(--tr-border);
    border-radius: 1px;
    display: block;
    width: 4px;
}

.tr-signal-bars span:nth-child(1) { height: 5px; }
.tr-signal-bars span:nth-child(2) { height: 9px; }
.tr-signal-bars span:nth-child(3) { height: 14px; }
.tr-signal-bars span:nth-child(4) { height: 19px; }
.tr-signal-bars span.active { background: var(--tr-accent); }

.tr-table-shell {
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    overflow: hidden;
}

.tr-table-row {
    align-items: center;
    background: rgba(255, 254, 253, 0.78);
    border-bottom: 1px solid var(--tr-border);
    display: grid;
    gap: 14px;
    grid-template-columns: 1.2fr 0.6fr 0.7fr 0.7fr 0.7fr auto;
    min-height: 46px;
    padding: 0 14px;
}

.tr-table-row-actions {
    min-height: 64px;
}

.tr-table-row-actions .q-btn {
    min-height: 34px !important;
    padding: 0.42rem 0.62rem !important;
}

.tr-table-row:last-child {
    border-bottom: 0;
}

.tr-table-head {
    background: var(--tr-surface-strong);
    color: var(--tr-muted);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.tr-form-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.session-view {
    background:
        repeating-linear-gradient(
            90deg,
            rgba(24, 27, 31, 0.025) 0,
            rgba(24, 27, 31, 0.025) 1px,
            transparent 1px,
            transparent 72px
        ),
        var(--tr-bg);
}

.tr-cockpit {
    margin: 0 auto;
    max-width: 1240px;
    width: min(1240px, calc(100vw - 36px));
}

.tr-power-panel {
    min-height: min(46vh, 390px);
}

.tr-power-value,
.tr-metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700;
}

.tr-metric-cell {
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(248, 246, 241, 0.76)),
        var(--tr-surface);
}

.tr-cockpit-statusbar {
    align-items: center;
    background: var(--tr-surface);
    border: 1px solid var(--tr-border);
    border-radius: var(--tr-radius);
    display: flex;
    gap: 10px;
    justify-content: center;
    min-height: 44px;
    padding: 0.7rem 1rem;
}

.scan-pulse {
    animation: pulse 1.8s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.54; }
}

.device-item.connecting {
    border-color: var(--tr-accent) !important;
    background: var(--tr-accent-soft) !important;
    cursor: wait !important;
}

@media (max-width: 860px) {
    .tr-shell {
        width: min(100% - 28px, 1180px);
    }

    .tr-header {
        position: static !important;
    }

    .tr-header .tr-shell {
        flex-wrap: wrap;
        gap: 10px;
    }

    .tr-header .tr-shell > .q-row:last-child {
        justify-content: flex-start;
        overflow-x: auto;
        width: 100%;
    }

    .tr-title {
        font-size: 1.72rem;
        line-height: 1.06;
    }

    .tr-hero-row {
        align-items: flex-start !important;
        flex-direction: column;
    }

    .tr-console-grid,
    .tr-status-strip,
    .tr-cockpit-top,
    .tr-cockpit-controls,
    .tr-form-grid,
    .tr-panel-header {
        grid-template-columns: 1fr;
    }

    .tr-metric-rail {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tr-route-stats,
    .tr-summary-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tr-power-panel {
        min-height: 300px;
    }

    .tr-history-row,
    .tr-device-row {
        grid-template-columns: 1fr;
    }

    .tr-table-row {
        grid-template-columns: 1fr 0.7fr;
    }

    .tr-table-row > :nth-child(n+3):not(:last-child) {
        display: none;
    }
}
</style>
"""
