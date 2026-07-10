"""Shared web presentation theme for le-tour.

The token layer follows the Groq design system (DESIGN.md at the repo root):
warm-gray neutrals, single neon-zest accent, Space Grotesk + IBM Plex Mono,
8px spacing base, sharp cards (radius 0), pill buttons (radius 1000), no
shadows — depth comes from background-color shifts only.
"""

WEB_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    /* ── Groq palette ─────────────────────────────────────────── */
    --color-obsidian-slate: #2d2f33;
    --color-canvas-white:   #ffffff;
    --color-warm-mist:      #f3f3ee;
    --color-ash-concrete:   #e8e8de;
    --color-deep-pewter:    #2a2a25;
    --color-steel-gray:     #c2c2be;
    --color-soft-stone:     #69695d;
    --color-faded-quartz:   #9c9c90;
    --color-neon-zest:      #f43e01;
    --color-deep-ember:     #c23101;
    --color-lavender-haze:  #e09afe;
    --color-violet-tint:    #d377fd;

    /* Semantic state colors — used only inside connection/error/info pills */
    --color-success:        #15803d;
    --color-success-soft:   #e8f6ee;
    --color-info:           #1769aa;
    --color-info-soft:      #e8f2fb;
    --color-danger:         #b42318;
    --color-danger-soft:    #fff1f0;

    /* Quasar primary/secondary shims */
    --q-primary:   var(--color-neon-zest);
    --q-secondary: var(--color-obsidian-slate);

    /* ── Typography ───────────────────────────────────────────── */
    --font-space-grotesk: 'Space Grotesk', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-ibm-plex-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;

    --text-caption:    10px;  --leading-caption:    1.57;  --tracking-caption:    0.1px;
    --text-body-lg:    15px;  --leading-body-lg:    1.57;  --tracking-body-lg:    -0.3px;
    --text-heading-sm: 24px;  --leading-heading-sm: 1.4;   --tracking-heading-sm: -0.48px;
    --text-heading:    32px;  --leading-heading:    1.3;   --tracking-heading:    -0.64px;
    --text-heading-lg: 36px;  --leading-heading-lg: 1;     --tracking-heading-lg: -0.72px;
    --text-display:    46px;  --leading-display:    0.9;   --tracking-display:    -0.92px;

    --font-weight-light:   300;
    --font-weight-regular: 400;
    --font-weight-medium:  500;

    /* ── Spacing (8px base) ───────────────────────────────────── */
    --spacing-8:   8px;
    --spacing-16:  16px;
    --spacing-24:  24px;
    --spacing-32:  32px;
    --spacing-40:  40px;
    --spacing-48:  48px;
    --spacing-56:  56px;
    --spacing-80:  80px;
    --spacing-120: 120px;
    --spacing-128: 128px;

    /* ── Layout ───────────────────────────────────────────────── */
    --page-max-width: 1440px;

    /* ── Border radius ────────────────────────────────────────── */
    --radius-md:      6px;
    --radius-lg:      12px;
    --radius-full:    1000px;
    --radius-misc:    6px;
    /* Cards override the DESIGN.md spec value of 0 — the live Groq site
       uses softly rounded surfaces (~12px). 0px reads as bug, not intent. */
    --radius-cards:   12px;
    --radius-forms:   10px;
    --radius-buttons: 1000px;

    /* ── Z-index scale ────────────────────────────────────────── */
    --z-base:   1;
    --z-sticky: 100;
    --z-header: 200;
    --z-dialog: 1000;
    --z-toast:  2000;
}

* {
    box-sizing: border-box;
    font-family: var(--font-space-grotesk);
    font-weight: var(--font-weight-regular);
}

/* Material icons must keep their own ligature font — guarded by tests. */
.material-icons,
.material-icons-outlined,
.material-icons-round,
.material-icons-sharp,
.material-icons-two-tone,
.material-symbols,
.material-symbols-outlined,
.material-symbols-rounded,
.material-symbols-sharp {
    direction: ltr;
    display: inline-block;
    font-feature-settings: 'liga';
    -webkit-font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
    font-family: inherit;
    font-style: normal;
    font-weight: normal;
    letter-spacing: normal;
    line-height: 1;
    text-transform: none;
    white-space: nowrap;
    word-wrap: normal;
}

.material-icons,
.material-icons-two-tone     { font-family: 'Material Icons' !important; }
.material-icons-outlined     { font-family: 'Material Icons Outlined' !important; }
.material-icons-round        { font-family: 'Material Icons Round' !important; }
.material-icons-sharp        { font-family: 'Material Icons Sharp' !important; }
.material-symbols,
.material-symbols-outlined   { font-family: 'Material Symbols Outlined' !important; }
.material-symbols-rounded    { font-family: 'Material Symbols Rounded' !important; }
.material-symbols-sharp      { font-family: 'Material Symbols Sharp' !important; }

body {
    background: var(--color-warm-mist) !important;
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-body-lg);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-body-lg);
    line-height: var(--leading-body-lg);
    margin: 0;
}

.tr-shell {
    width: min(var(--page-max-width), calc(100vw - 48px));
    margin: 0 auto;
}

/* ── Header ───────────────────────────────────────────────────── */

.tr-header {
    background: var(--color-warm-mist) !important;
    border-bottom: none;
    box-shadow: none !important;
    position: sticky;
    top: 0;
    z-index: var(--z-header);
}

.tr-brand {
    align-items: center;
    color: var(--color-obsidian-slate);
    display: inline-flex;
    font-family: var(--font-space-grotesk);
    font-size: var(--text-body-lg);
    font-weight: var(--font-weight-regular);
    gap: var(--spacing-8);
    letter-spacing: var(--tracking-body-lg);
    text-decoration: none;
}

.tr-brand-mark {
    align-items: center;
    background: var(--color-deep-pewter);
    border-radius: var(--radius-misc);
    color: var(--color-canvas-white);
    display: inline-flex;
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    height: 28px;
    justify-content: center;
    letter-spacing: var(--tracking-caption);
    width: 28px;
}

.nav-link {
    background: transparent;
    border: none;
    color: var(--color-soft-stone);
    font-family: var(--font-space-grotesk);
    font-size: 14px;
    font-weight: var(--font-weight-light);
    letter-spacing: var(--tracking-body-lg);
    padding: 10px 14px;
    text-decoration: none;
    transition: color 0.16s ease-out;
}

.nav-link:hover {
    color: var(--color-obsidian-slate);
}

.nav-link.active {
    color: var(--color-neon-zest);
}

.tr-header-status {
    align-items: center;
    background: var(--color-warm-mist);
    border: 1px solid var(--color-steel-gray);
    border-radius: var(--radius-full);
    color: var(--color-soft-stone);
    display: inline-flex;
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    font-weight: var(--font-weight-regular);
    font-variant-numeric: tabular-nums;
    gap: var(--spacing-8);
    min-height: 32px;
    padding: 0 12px;
    white-space: nowrap;
}

.tr-header-status .status-dot {
    height: 8px;
    width: 8px;
}

.tr-page {
    padding: var(--spacing-32) 0 var(--spacing-80);
}

/* ── Type primitives ──────────────────────────────────────────── */

.tr-eyebrow {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    line-height: var(--leading-caption);
    text-transform: uppercase;
}

.tr-title {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-heading-lg);
    font-weight: var(--font-weight-light);
    letter-spacing: var(--tracking-heading-lg);
    line-height: var(--leading-heading-lg);
    margin: 0;
    max-width: 100%;
    overflow-wrap: break-word;
    text-wrap: balance;
    display: block !important;
    white-space: normal !important;
    word-break: normal;
}

.tr-subtitle {
    color: var(--color-soft-stone);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-body-lg);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-body-lg);
    line-height: var(--leading-body-lg);
    margin: 0;
    text-wrap: pretty;
}

.tr-section-label {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    text-transform: uppercase;
}

/* ── Panels — depth via background only, never shadow ─────────── */

.tr-panel,
.tr-panel-flat,
.tr-panel-tight {
    background: var(--color-canvas-white);
    border: none;
    border-radius: var(--radius-cards);
}

/* ── Buttons ──────────────────────────────────────────────────── */

.tr-btn-primary,
.tr-btn-secondary,
.btn-primary,
.btn-secondary {
    border-radius: var(--radius-buttons) !important;
    box-shadow: none !important;
    font-family: var(--font-space-grotesk) !important;
    font-size: 14px !important;
    font-weight: var(--font-weight-regular) !important;
    letter-spacing: 0 !important;
    min-height: 40px !important;
    padding: 10px 16px !important;
    text-transform: none !important;
    transition: background 0.16s ease-out, border-color 0.16s ease-out, color 0.16s ease-out !important;
}

.q-btn.tr-btn-primary,
.q-btn.btn-primary,
.tr-btn-primary,
.btn-primary {
    background: var(--color-neon-zest) !important;
    border: 1px solid var(--color-canvas-white) !important;
    color: var(--color-canvas-white) !important;
}

.q-btn.tr-btn-primary:hover,
.q-btn.btn-primary:hover,
.tr-btn-primary:hover,
.btn-primary:hover {
    background: var(--color-deep-ember) !important;
    border-color: var(--color-canvas-white) !important;
}

.q-btn.tr-btn-secondary,
.q-btn.btn-secondary,
.tr-btn-secondary,
.btn-secondary {
    background: transparent !important;
    border: 1px solid var(--color-obsidian-slate) !important;
    color: var(--color-obsidian-slate) !important;
}

.tr-btn-secondary:hover,
.btn-secondary:hover {
    background: var(--color-warm-mist) !important;
}

.q-btn.tr-btn-danger {
    border-color: var(--color-deep-ember) !important;
    color: var(--color-deep-ember) !important;
}

.q-btn.tr-btn-danger:hover {
    background: var(--color-warm-mist) !important;
}

.q-btn.tr-btn-danger-fill {
    background: var(--color-deep-ember) !important;
    border-color: var(--color-deep-ember) !important;
    color: var(--color-canvas-white) !important;
}

/* ── Status strip & tiles ─────────────────────────────────────── */

.tr-status-strip {
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.tr-status-strip-two {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tr-status-tile {
    align-items: center;
    background: var(--color-warm-mist);
    border: none;
    border-radius: var(--radius-cards);
    display: flex;
    gap: var(--spacing-16);
    min-height: 80px;
    padding: var(--spacing-16) var(--spacing-24);
}

.status-dot {
    border-radius: var(--radius-full);
    display: inline-block;
    flex: 0 0 auto;
    height: 10px;
    width: 10px;
}

.status-dot.connected {
    background: var(--color-success);
    box-shadow: 0 0 0 4px var(--color-success-soft);
}

.status-dot.disconnected {
    background: var(--color-faded-quartz);
    box-shadow: 0 0 0 4px var(--color-ash-concrete);
}

.tr-status-name {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-body-lg);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-body-lg);
    line-height: 1.2;
}

.tr-status-meta {
    color: var(--color-soft-stone);
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    font-weight: var(--font-weight-regular);
    line-height: 1.25;
}

/* ── Console grid ─────────────────────────────────────────────── */

.tr-console-grid {
    display: grid;
    gap: var(--spacing-24);
    grid-template-columns: minmax(0, 1.3fr) minmax(330px, 0.7fr);
}

/* Segmented control — single pill containing N slots, active slot is the
   "raised" white card on a warm-mist track. Used for ride-mode selection. */
.tr-segmented {
    background: var(--color-warm-mist);
    border-radius: var(--radius-buttons);
    display: inline-grid;
    gap: 2px;
    grid-template-columns: repeat(var(--seg-cols, 3), minmax(0, 1fr));
    min-height: 48px;
    padding: 3px;
    width: 100%;
}

.q-btn.tr-seg {
    background: transparent !important;
    border: none !important;
    border-radius: var(--radius-buttons) !important;
    box-shadow: none !important;
    color: var(--color-soft-stone) !important;
    font-family: var(--font-ibm-plex-mono) !important;
    font-size: var(--text-caption) !important;
    font-weight: var(--font-weight-regular) !important;
    letter-spacing: var(--tracking-caption) !important;
    min-height: 0 !important;
    padding: 0 16px !important;
    text-transform: uppercase !important;
    transition: background 0.16s ease-out, color 0.16s ease-out !important;
}

.q-btn.tr-seg:hover {
    color: var(--color-obsidian-slate) !important;
}

.q-btn.tr-seg.active {
    background: var(--color-canvas-white) !important;
    color: var(--color-neon-zest) !important;
}

.q-btn.tr-seg.active:hover {
    background: var(--color-canvas-white) !important;
    color: var(--color-neon-zest) !important;
}

.q-btn.tr-seg .q-focus-helper,
.q-btn.tr-seg .q-focus-helper::before,
.q-btn.tr-seg .q-focus-helper::after {
    background: transparent !important;
    opacity: 0 !important;
}

.q-btn.tr-seg .q-ripple,
.q-btn.tr-seg .q-ripple__inner {
    display: none !important;
}

/* Action row: secondary action stays left, primary action owns the right side. */
.tr-action-row {
    align-items: stretch;
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: auto auto;
    justify-content: space-between;
    width: 100%;
}

/* Home page two-up: Ride Setup and Recent Rides side-by-side at wide
   widths, equal columns. Stacks (still equal width) below 1280px. */
.tr-home-grid {
    display: grid;
    gap: var(--spacing-24);
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.tr-home-grid > .tr-panel {
    display: flex;
    flex-direction: column;
}

.tr-home-activity-panel {
    gap: var(--spacing-24);
    grid-column: 1 / -1;
    overflow: hidden;
}

.tr-home-activity-scroll {
    max-width: 100%;
    overflow-x: auto;
    padding-bottom: var(--spacing-8);
    scrollbar-width: thin;
}

.tr-home-activity-scroll:focus-visible {
    outline: 1px solid var(--color-obsidian-slate);
    outline-offset: 4px;
}

.tr-home-activity-grid {
    --activity-cell-min: 10px;
    --activity-gap: 6px;

    display: grid;
    gap: var(--activity-gap);
    grid-template-columns: repeat(
        var(--activity-weeks),
        minmax(var(--activity-cell-min), 1fr)
    );
    min-width: var(--activity-min-width);
    width: 100%;
}

.tr-home-activity-week {
    display: grid;
    gap: var(--activity-gap);
    grid-template-rows: repeat(7, auto);
    min-width: var(--activity-cell-min);
}

.tr-home-activity-cell {
    aspect-ratio: 1;
    background: var(--color-warm-mist);
    border: 0;
    border-radius: 2px;
    display: block;
    width: 100%;
}

.tr-home-activity-cell.active {
    background: var(--color-neon-zest);
}

@media (max-width: 1279px) {
    .tr-home-grid {
        grid-template-columns: minmax(0, 1fr);
    }
}

/* Settings 2x2: all four sections at once, equal columns and rows. */
.tr-settings-grid {
    align-items: stretch;
    display: grid;
    gap: var(--spacing-24);
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    width: 100%;
}

.tr-settings-grid > .tr-panel {
    display: flex;
    flex-direction: column;
    min-height: 404px;
}

@media (max-width: 859px) {
    .tr-settings-grid {
        grid-template-columns: minmax(0, 1fr);
    }

    .tr-settings-grid > .tr-panel {
        min-height: 0;
    }
}

/* Hero variant of the primary button — taller, larger label, fills its grid cell. */
.q-btn.tr-btn-hero {
    font-size: 16px !important;
    letter-spacing: 0 !important;
    min-height: 56px !important;
    padding: 16px 32px !important;
    width: 100% !important;
}

.tr-control-band {
    background: var(--color-ash-concrete);
    border: none;
    border-radius: var(--radius-cards);
    padding: var(--spacing-16);
}

/* Mode setup is part of the cockpit panel — no own background, no border,
   just spacing. Mode-specific layout variants control the column splits.
   min-height keeps the card height stable when switching Free/ERG/SIM. */
.tr-mode-setup {
    background: transparent;
    border: none;
    border-radius: 0;
    display: grid;
    gap: var(--spacing-16);
    margin-top: var(--spacing-24);
    min-height: 328px;
    padding: 0;
    width: 100%;
}

.tr-setup-hint {
    color: var(--color-soft-stone);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-body-lg);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-body-lg);
    line-height: var(--leading-body-lg);
    text-wrap: pretty;
}

.tr-setup-erg {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-24);
    justify-content: center;
    padding: var(--spacing-16) 0;
    text-align: center;
    width: 100%;
}

.tr-setup-erg-row {
    align-items: center;
    display: grid;
    gap: var(--spacing-32);
    grid-template-columns: minmax(110px, 1fr) auto minmax(110px, 1fr);
    max-width: 560px;
    width: 100%;
}

.tr-setup-erg-row .q-btn:first-child {
    justify-self: end;
}

.tr-setup-erg-row .q-btn:last-child {
    justify-self: start;
}

.tr-setup-erg-readout {
    align-items: baseline;
    display: flex;
    gap: var(--spacing-8);
    min-width: 6ch;
    justify-content: center;
}

/* Larger readout for the centered ERG target so it feels like a hero. */
.tr-setup-erg-readout .tr-erg-target-value {
    font-size: 72px;
    line-height: 0.9;
}

.tr-setup-erg-readout .tr-power-unit {
    font-size: 20px;
    margin-top: 0;
}

.tr-setup-sim {
    align-items: stretch;
    display: grid;
    gap: var(--spacing-16);
    width: 100%;
}

.tr-setup-sim .q-field {
    width: 100%;
}

.tr-erg-target-value {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-display);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.1em;
    line-height: var(--leading-display);
}

/* ── Route cards (home) ──────────────────────────────────────── */

.tr-home-routes-panel {
    grid-column: 1 / -1;
}

.tr-route-cards {
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    width: 100%;
}

.tr-route-card {
    background: var(--color-canvas-white);
    border: 1px solid var(--color-steel-gray);
    border-radius: var(--radius-cards);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-16);
    padding: var(--spacing-16);
    text-align: left;
    transition: border-color 120ms ease, transform 120ms ease;
}

.tr-route-card:hover,
.tr-route-card:focus-visible {
    border-color: var(--color-neon-zest);
    transform: translateY(-1px);
}

.tr-route-card .tr-route-profile {
    height: 72px;
}

.tr-route-card-head {
    align-items: center;
    display: flex;
    gap: var(--spacing-8);
    justify-content: space-between;
    width: 100%;
}

.tr-route-card-title {
    color: var(--color-obsidian-slate);
    font-weight: 500;
}

/* ── Route profile ────────────────────────────────────────────── */

.tr-route-profile {
    background: var(--color-canvas-white);
    border: 1px solid var(--color-steel-gray);
    border-radius: var(--radius-cards);
    height: 128px;
    overflow: hidden;
    position: relative;
    width: 100%;
}

.tr-route-profile svg {
    height: 100%;
    inset: 0;
    position: absolute;
    width: 100%;
}

.tr-route-profile polyline {
    fill: none;
    stroke: var(--color-obsidian-slate);
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 4;
    vector-effect: non-scaling-stroke;
}

.tr-route-profile-ticks {
    inset: 0;
    position: absolute;
}

.tr-route-profile-ticks span {
    background: var(--color-steel-gray);
    height: 100%;
    position: absolute;
    top: 0;
    width: 1px;
}

/* ── List rows ───────────────────────────────────────────────── */

.tr-history-row {
    align-items: center;
    background: var(--color-warm-mist);
    border: none;
    border-radius: var(--radius-cards);
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: minmax(0, 1fr) auto;
    padding: var(--spacing-16);
}

.tr-empty {
    align-items: center;
    background: var(--color-warm-mist);
    border: 1px dashed var(--color-steel-gray);
    border-radius: var(--radius-cards);
    color: var(--color-soft-stone);
    display: flex;
    justify-content: space-between;
    min-height: 92px;
    padding: var(--spacing-16);
}

/* ── Session view ─────────────────────────────────────────────── */

/* Session view fills the viewport. The cockpit grid uses fr units so the
   power panel grows to absorb available height while the top bar, metric
   rail, and controls stay at their natural size. */
.session-view {
    background: var(--color-warm-mist);
    min-height: 100dvh;
    padding: var(--spacing-24);
}

.tr-cockpit {
    display: grid;
    gap: var(--spacing-16);
    grid-template-rows: auto minmax(0, 1fr) auto auto;
    margin: 0 auto;
    max-width: var(--page-max-width);
    min-height: calc(100dvh - 2 * var(--spacing-24));
    width: min(var(--page-max-width), calc(100vw - 48px));
}

.tr-cockpit-top,
.tr-cockpit-controls {
    align-items: center;
    display: grid;
    gap: var(--spacing-16);
}

.tr-cockpit-top      { grid-template-columns: auto minmax(0, 1fr) auto; }
.tr-cockpit-controls { grid-template-columns: auto minmax(0, 1fr) auto; }

/* Clock readout in the top-right of the cockpit. */
.tr-cockpit-clock {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: clamp(28px, 3vw, 40px);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.05em;
    line-height: 1;
    text-align: right;
}

/* Inline +/- target row for ERG and SIM modes inside the power panel. */
.tr-cockpit-target-row {
    align-items: center;
    display: flex;
    gap: var(--spacing-24);
    justify-content: center;
}

.tr-cockpit-target-readout {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: clamp(20px, 1.8vw, 28px);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.04em;
    min-width: 7ch;
}

/* Route info — two-line consistent typography for SIM mode. */
.tr-cockpit-route {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-8);
}

.tr-cockpit-route-current {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-body-lg);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-body-lg);
}

.tr-cockpit-route-meta {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    text-transform: uppercase;
}

/* Hero card. Fills the cockpit's main row, contents centered both axes. */
.tr-power-panel {
    align-items: center;
    background: var(--color-canvas-white);
    border-radius: 20px;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-16);
    justify-content: center;
    padding: clamp(var(--spacing-24), 4vw, var(--spacing-56));
    text-align: center;
}

.tr-power-panel.tr-snake-panel {
    overflow: hidden;
    padding: clamp(12px, 2vw, var(--spacing-32));
    position: relative;
}

.tr-snake-canvas {
    aspect-ratio: 21 / 11;
    max-height: 704px;
    max-width: 1344px;
    position: relative;
}

.tr-snake-svg {
    display: block;
    height: 100%;
    overflow: visible;
    width: 100%;
}

.tr-snake-watts-island {
    align-items: center;
    background: var(--color-canvas-white);
    display: flex;
    flex-direction: column;
    height: 45.4545%;
    justify-content: center;
    left: 33.3333%;
    pointer-events: none;
    position: absolute;
    top: 27.2727%;
    width: 33.3333%;
    z-index: 2;
}

.tr-snake-readout {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 4px;
    opacity: 1;
    transition: opacity 0.22s ease-out;
}

.tr-snake-power-value {
    color: var(--color-neon-zest);
    font-family: var(--font-space-grotesk);
    font-size: clamp(68px, 13vw, 200px);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0;
    line-height: 0.9;
}

.tr-snake-loader {
    align-items: center;
    display: flex;
    gap: 0;
    height: 45.4545%;
    justify-content: center;
    left: 33.3333%;
    opacity: 0;
    pointer-events: none;
    position: absolute;
    top: 27.2727%;
    transition: opacity 0.32s ease-out;
    width: 33.3333%;
    z-index: 3;
}

.tr-snake-loader span {
    background: var(--color-neon-zest);
    border-radius: var(--radius-full);
    display: block;
    height: clamp(22px, 4.6vw, 64px);
    margin-left: clamp(-18px, -2.25vw, -10px);
    opacity: 0.12;
    width: clamp(22px, 4.6vw, 64px);
}

.tr-snake-loader span:first-child {
    margin-left: 0;
}

.tr-snake-canvas.is-warming .tr-snake-loader {
    opacity: 1;
}

.tr-snake-canvas.is-warming .tr-snake-readout {
    opacity: 0;
}

/* Tight value+unit pair inside the power panel. */
.tr-power-readout {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

/* Hero readout — actual cockpit-scale, overrides the strict template's
   46px display size. A power figure must read across a room. */
.tr-power-value {
    color: var(--color-neon-zest);
    font-family: var(--font-ibm-plex-mono);
    font-size: clamp(96px, 14vw, 200px);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.04em;
    line-height: 0.9;
    min-width: 4ch;
}

.tr-power-unit {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: clamp(14px, 1.2vw, 20px);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    text-transform: uppercase;
}

.tr-metric-rail {
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: repeat(5, minmax(0, 1fr));
}

/* Metric cell content is centered on both axes — fill the card, don't
   pile up in a corner. Value dominates, label is a small caption below. */
.tr-metric-cell {
    align-items: center;
    background: var(--color-canvas-white);
    border: none;
    border-radius: var(--radius-cards);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-8);
    justify-content: center;
    min-height: 140px;
    padding: var(--spacing-24);
    text-align: center;
}

.tr-metric-value {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: clamp(36px, 4vw, 56px);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.04em;
    line-height: 1;
}

.tr-metric-label,
.metric-label {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    margin-top: 0;
    text-transform: uppercase;
}

.metric-card {
    background: var(--color-warm-mist);
    border: none;
    border-radius: var(--radius-cards);
    padding: var(--spacing-16);
}

/* ── Connection status banner ─────────────────────────────────── */

.connection-status {
    align-items: center;
    border-radius: var(--radius-misc);
    display: flex;
    gap: var(--spacing-16);
    padding: var(--spacing-16);
}

.connection-status.success { background: var(--color-success-soft); color: var(--color-success); }
.connection-status.error   { background: var(--color-danger-soft);  color: var(--color-danger); }
.connection-status.info    { background: var(--color-info-soft);    color: var(--color-info); }

/* ── Scan dialog ──────────────────────────────────────────────── */

.device-list { max-height: 300px; overflow-y: auto; }

.scan-dialog {
    max-width: 520px;
    min-width: min(400px, calc(100vw - 32px));
    padding-bottom: env(safe-area-inset-bottom);
    width: 90vw;
}

.scan-dialog-header,
.scan-dialog-footer {
    background: var(--color-warm-mist);
    border-color: var(--color-steel-gray);
    padding: var(--spacing-16) var(--spacing-24);
}

.scan-dialog-header { border-bottom: 1px solid var(--color-steel-gray); }
.scan-dialog-footer { border-top:    1px solid var(--color-steel-gray); }

.scan-dialog-body { padding: var(--spacing-24); }

.scan-device-item {
    background: var(--color-canvas-white) !important;
    border: 1px solid var(--color-steel-gray) !important;
    border-radius: var(--radius-cards) !important;
    box-shadow: none !important;
    padding: var(--spacing-16) !important;
    transition: background 0.16s ease-out, border-color 0.16s ease-out !important;
}

.scan-device-item:hover {
    background: var(--color-warm-mist) !important;
    border-color: var(--color-obsidian-slate) !important;
}

.signal-bars {
    align-items: flex-end;
    display: flex;
    gap: 2px;
    height: 18px;
}

.signal-bar { background: var(--color-steel-gray); border-radius: 1px; width: 4px; }
.signal-bar.active { background: var(--color-obsidian-slate); }

.empty-state {
    color: var(--color-soft-stone);
    padding: var(--spacing-24);
    text-align: center;
}

.empty-state-icon {
    color: var(--color-faded-quartz);
    font-size: 32px;
    line-height: 1;
    margin-bottom: var(--spacing-8);
}

.empty-state-title {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-weight: var(--font-weight-regular);
    margin-bottom: var(--spacing-8);
}

.empty-state-tips {
    background: var(--color-warm-mist);
    border: 1px solid var(--color-steel-gray);
    border-radius: var(--radius-misc);
    color: var(--color-soft-stone);
    font-size: 13px;
    margin-top: var(--spacing-16);
    padding: var(--spacing-16);
    text-align: left;
}

.empty-state-tips li { margin-bottom: 6px; }

/* ── Panel header & badges ────────────────────────────────────── */

.tr-panel-header {
    align-items: start;
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: minmax(0, 1fr) auto;
    margin-bottom: var(--spacing-24);
    width: 100%;
}

.tr-panel-header .tr-panel-action {
    align-self: start;
    justify-self: end;
}

.tr-panel-title {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-heading-sm);
    font-weight: var(--font-weight-light);
    letter-spacing: var(--tracking-heading-sm);
    line-height: var(--leading-heading-sm);
    text-wrap: balance;
}

.tr-btn-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-16);
}

.tr-state-badge {
    align-items: center;
    background: var(--color-warm-mist);
    border: 1px solid var(--color-steel-gray);
    border-radius: var(--radius-full);
    color: var(--color-soft-stone);
    display: inline-flex;
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    gap: 6px;
    letter-spacing: var(--tracking-caption);
    line-height: 1;
    padding: 6px 10px;
    text-transform: uppercase;
    white-space: nowrap;
}

.tr-state-badge.live,
.tr-state-badge.ready {
    background: var(--color-success-soft);
    border-color: var(--color-success);
    color: var(--color-success);
}

.tr-state-badge.demo {
    background: var(--color-info-soft);
    border-color: var(--color-info);
    color: var(--color-info);
}

/* ── Cockpit values ───────────────────────────────────────────── */

.tr-control-value {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-heading);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.05em;
    line-height: var(--leading-heading);
}

.tr-meta-grid {
    display: grid;
    gap: var(--spacing-8);
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
}

.tr-route-picker,
.tr-route-live {
    background: var(--color-warm-mist);
    border: none;
    border-radius: var(--radius-cards);
    display: grid;
    gap: var(--spacing-16);
    padding: var(--spacing-16);
}

.tr-route-stats,
.tr-summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.tr-object-panel {
    align-self: stretch;
    width: calc((100% - var(--spacing-24)) / 2);
}

.tr-object-panel .tr-summary-grid-session {
    grid-template-columns: repeat(5, minmax(0, 1fr));
}

.tr-object-panel .tr-summary-grid-snapshot {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.tr-meta-row {
    background: var(--color-canvas-white);
    border: 1px solid var(--color-steel-gray);
    border-radius: var(--radius-cards);
    min-height: 68px;
    padding: var(--spacing-16);
}

.tr-meta-value {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: 14px;
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: var(--tracking-caption);
    line-height: 1;
}

.tr-meta-label {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    margin-top: 6px;
    text-transform: uppercase;
}

.tr-device-row {
    align-items: center;
    background: var(--color-warm-mist);
    border: none;
    border-radius: var(--radius-cards);
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: minmax(0, 1fr) 112px 132px;
    min-height: 96px;
    padding: var(--spacing-16);
    width: 100%;
}

.tr-device-main {
    align-items: center;
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: auto minmax(0, 1fr);
    min-width: 0;
}

.tr-device-copy {
    min-width: 0;
}

.tr-device-row .tr-status-name,
.tr-device-row .tr-status-meta {
    overflow-wrap: anywhere;
}

.tr-device-state {
    align-items: flex-end;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-8);
    justify-self: stretch;
    min-width: 0;
}

.tr-device-state .tr-state-badge {
    justify-content: center;
    width: 100%;
}

.q-btn.tr-device-action {
    justify-self: stretch;
    min-width: 132px !important;
    width: 132px !important;
}

.tr-signal-bars {
    align-items: flex-end;
    display: flex;
    gap: 3px;
    height: 20px;
}

.tr-signal-bars span {
    background: var(--color-steel-gray);
    border-radius: 1px;
    display: block;
    width: 4px;
}

.tr-signal-bars span:nth-child(1) { height: 5px; }
.tr-signal-bars span:nth-child(2) { height: 9px; }
.tr-signal-bars span:nth-child(3) { height: 14px; }
.tr-signal-bars span:nth-child(4) { height: 19px; }
.tr-signal-bars span.active       { background: var(--color-obsidian-slate); }

/* ── Sessions table ───────────────────────────────────────────────
   Fixed pixel grid so header and rows always align. Rows use display:
   contents so each cell participates directly in the parent grid.
   Numeric columns set .num for right alignment. */

.tr-sessions {
    border-top: 1px solid var(--color-steel-gray);
    display: grid;
    width: 100%;
}

.tr-sessions-compact {
    grid-template-columns:
        180px        /* date */
        80px         /* mode */
        100px        /* duration */
        110px        /* distance */
        90px         /* avg power */
        70px         /* tss */
        minmax(0, 1fr)  /* spacer */
        40px;        /* chevron */
}

.tr-sessions-full {
    grid-template-columns:
        180px           /* date */
        64px            /* mode */
        82px            /* duration */
        92px            /* distance */
        82px            /* avg power */
        82px            /* max power */
        82px            /* avg hr */
        82px            /* max hr */
        82px            /* normalized power */
        58px            /* intensity factor */
        58px            /* training stress */
        58px            /* ftp */
        minmax(0, 1fr)  /* spacer */
        32px;           /* chevron */
}

.tr-sessions-row { display: contents; }

.tr-sessions-row > * {
    align-items: center;
    background: var(--color-canvas-white);
    border-bottom: 1px solid var(--color-steel-gray);
    color: var(--color-obsidian-slate);
    display: flex;
    font-family: var(--font-ibm-plex-mono);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    height: 56px;
    padding: 0 var(--spacing-16);
    white-space: nowrap;
}

.tr-sessions-full .tr-sessions-row > * {
    font-size: 12px;
    padding: 0 10px;
}

.tr-sessions-row > .num { justify-content: flex-end; }

.tr-sessions-row.head > * {
    background: var(--color-warm-mist);
    color: var(--color-soft-stone);
    font-size: var(--text-caption);
    font-variant-numeric: normal;
    height: 36px;
    letter-spacing: var(--tracking-caption);
    text-transform: uppercase;
}

.tr-sessions-row.body { cursor: pointer; }
.tr-sessions-row.body:hover > * { background: var(--color-warm-mist); }

.tr-sessions-row .chevron {
    color: var(--color-faded-quartz);
    font-family: var(--font-space-grotesk);
    font-size: 18px;
    justify-content: center;
}

.tr-sessions-row.body:hover .chevron {
    color: var(--color-obsidian-slate);
}

/* Recent rides teaser — same row geometry, no header, "View all" link in
   the panel header instead. Used on the home page. */

.tr-panel-action {
    color: var(--color-soft-stone);
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    font-weight: var(--font-weight-regular);
    text-decoration: none;
    transition: color 0.16s ease-out;
    white-space: nowrap;
}

.tr-panel-action:hover { color: var(--color-obsidian-slate); }

.tr-panel-action-button {
    appearance: none;
    background: transparent;
    border: 0;
    cursor: pointer;
    line-height: 1;
    padding: 0;
    text-align: right;
}

/* Detail action rows keep navigation on the left and destructive/export actions
   on the right without turning the footer into a toolbar. */
.tr-detail-actions {
    align-items: center;
    display: flex;
    gap: var(--spacing-16);
    justify-content: space-between;
    width: 100%;
}

.tr-detail-actions-right {
    align-items: center;
    display: flex;
    gap: var(--spacing-16);
}

.tr-dialog-card {
    background: var(--color-canvas-white) !important;
    border-radius: var(--radius-cards) !important;
    box-shadow: none !important;
    display: grid;
    gap: var(--spacing-16);
    min-width: min(420px, calc(100vw - 32px));
    padding: var(--spacing-24) !important;
}

/* History summary bar — 4 inline aggregate tiles above the sessions table. */

.tr-summary-bar {
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-bottom: var(--spacing-24);
}

.tr-summary-tile {
    background: var(--color-canvas-white);
    border: none;
    border-radius: var(--radius-cards);
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: var(--spacing-24);
}

.tr-summary-value {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-heading-sm);
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: 0.05em;
    line-height: 1;
}

.tr-summary-label {
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    text-transform: uppercase;
}

/* ── Activity graphs ─────────────────────────────────────────── */

.tr-activity-graph {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-16);
    padding: var(--spacing-24);
    width: 100%;
}

.tr-activity-graph-collapsible {
    gap: 0;
    padding: 0;
}

.tr-activity-graph-header {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-16);
    justify-content: space-between;
}

.tr-activity-graph-summary {
    align-items: center;
    cursor: pointer;
    display: flex;
    gap: var(--spacing-16);
    justify-content: space-between;
    list-style: none;
    padding: var(--spacing-24);
}

.tr-activity-graph-summary::-webkit-details-marker {
    display: none;
}

.tr-activity-graph-summary-icon {
    color: var(--color-soft-stone);
    flex: 0 0 auto;
    transition: color 0.16s ease-out, transform 0.16s ease-out;
}

.tr-activity-graph-summary:hover .tr-activity-graph-summary-icon {
    color: var(--color-obsidian-slate);
}

.tr-activity-graph-collapsible[open] .tr-activity-graph-summary-icon {
    transform: rotate(180deg);
}

.tr-activity-graph-collapsible > .tr-activity-graph-viewport,
.tr-activity-graph-collapsible > .tr-activity-graph-empty {
    margin-left: var(--spacing-24);
    margin-right: var(--spacing-24);
}

.tr-activity-graph-controls {
    align-items: center;
    background: var(--color-warm-mist);
    border-radius: var(--radius-full);
    display: inline-flex;
    gap: 2px;
    padding: 3px;
}

.tr-activity-graph-control {
    border-radius: var(--radius-full);
    color: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    letter-spacing: var(--tracking-caption);
    line-height: 1;
    min-width: 42px;
    padding: 8px 10px;
    text-align: center;
    text-decoration: none;
    text-transform: uppercase;
}

.tr-activity-graph-control:hover {
    color: var(--color-obsidian-slate);
}

.tr-activity-graph-control.active {
    background: var(--color-canvas-white);
    color: var(--color-neon-zest);
}

.tr-activity-graph-viewport {
    min-height: 260px;
    overflow: hidden;
    width: 100%;
}

.tr-activity-graph-svg {
    display: block;
    height: auto;
    overflow: visible;
    width: 100%;
}

.tr-activity-graph-grid line {
    stroke: var(--color-ash-concrete);
    stroke-width: 1;
}

.tr-activity-graph-grid text,
.tr-activity-graph-axis text,
.tr-activity-graph-reference text,
.tr-activity-graph-legend text {
    fill: var(--color-soft-stone);
    font-family: var(--font-ibm-plex-mono);
    font-size: 11px;
    letter-spacing: var(--tracking-caption);
}

.tr-activity-graph-axis line {
    stroke: var(--color-steel-gray);
    stroke-width: 1.2;
}

.tr-activity-graph-axis-title {
    fill: var(--color-faded-quartz) !important;
    text-transform: uppercase;
}

.tr-activity-graph-bar.primary {
    fill: var(--color-neon-zest);
}

.tr-activity-graph-bar.secondary {
    fill: var(--color-obsidian-slate);
}

.tr-activity-graph-line {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 2.6;
}

.tr-activity-graph-line.primary,
.tr-activity-graph-point.primary {
    stroke: var(--color-neon-zest);
}

.tr-activity-graph-line.secondary,
.tr-activity-graph-point.secondary {
    stroke: var(--color-obsidian-slate);
}

.tr-activity-graph-line.secondary {
    opacity: 0.78;
    stroke-dasharray: 7 7;
    stroke-width: 1.8;
}

.tr-activity-graph-point {
    fill: var(--color-canvas-white);
    stroke-width: 2.2;
}

.tr-activity-graph-point.secondary {
    opacity: 0.78;
    stroke-width: 1.8;
}

.tr-activity-graph-reference line {
    stroke: var(--color-faded-quartz);
    stroke-dasharray: 6 6;
    stroke-width: 1.4;
}

.tr-activity-graph-hit {
    cursor: crosshair;
    fill: transparent;
    pointer-events: all;
}

.tr-activity-graph-tooltip {
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.12s ease-out;
}

.tr-activity-graph-hover:hover .tr-activity-graph-tooltip {
    opacity: 1;
}

.tr-activity-graph-tooltip rect {
    fill: var(--color-obsidian-slate);
}

.tr-activity-graph-tooltip text {
    fill: var(--color-canvas-white);
    font-family: var(--font-ibm-plex-mono);
    font-size: 9px;
    letter-spacing: var(--tracking-caption);
}

.tr-activity-graph-tooltip text.value {
    fill: var(--color-neon-zest);
    font-size: 11px;
}

.tr-activity-graph-legend .primary {
    fill: var(--color-neon-zest);
}

.tr-activity-graph-legend .secondary {
    fill: var(--color-obsidian-slate);
}

.tr-activity-graph-empty {
    align-items: flex-start;
    background: var(--color-warm-mist);
    border-radius: var(--radius-cards);
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-height: 180px;
    justify-content: center;
    padding: var(--spacing-24);
}

/* ── Helper classes consumed by app.py / components ───────────── */

.tr-cell-strong {
    color: var(--color-obsidian-slate);
    font-weight: var(--font-weight-regular);
}

.tr-cell-soft {
    color: var(--color-soft-stone);
    font-size: 13px;
}

.tr-shortcut-label {
    background: var(--color-warm-mist);
    border-radius: var(--radius-misc);
    color: var(--color-soft-stone);
    display: inline-block;
    font-family: var(--font-ibm-plex-mono);
    font-size: var(--text-caption);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--tracking-caption);
    margin-bottom: var(--spacing-16);
    padding: 4px 8px;
    text-transform: uppercase;
}

.tr-card-title {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: var(--text-heading-sm);
    font-weight: var(--font-weight-light);
    letter-spacing: var(--tracking-heading-sm);
    line-height: var(--leading-heading-sm);
    margin-bottom: var(--spacing-8);
    text-wrap: balance;
}

.tr-card-description {
    color: var(--color-soft-stone);
    text-wrap: pretty;
}

.tr-target-readout {
    color: var(--color-obsidian-slate);
    font-family: var(--font-ibm-plex-mono);
    font-size: 14px;
    font-variant-numeric: tabular-nums;
    font-weight: var(--font-weight-medium);
    letter-spacing: var(--tracking-caption);
}

/* ── User cluster (header) ────────────────────────────────────── */

.tr-user-cluster {
    align-items: center;
    border-left: 1px solid var(--color-steel-gray);
    display: flex;
    gap: var(--spacing-8);
    margin-left: var(--spacing-8);
    padding-left: var(--spacing-16);
}

.tr-avatar {
    align-items: center;
    background: var(--color-warm-mist);
    border-radius: var(--radius-full);
    color: var(--color-obsidian-slate);
    display: inline-flex;
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    font-weight: var(--font-weight-regular);
    height: 32px;
    justify-content: center;
    width: 32px;
}

.tr-avatar-img {
    border-radius: var(--radius-full);
    height: 32px;
    object-fit: cover;
    width: 32px;
}

.tr-user-name {
    color: var(--color-obsidian-slate);
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    font-weight: var(--font-weight-regular);
}

.tr-logout-link {
    color: var(--color-soft-stone);
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    font-weight: var(--font-weight-regular);
    margin-left: var(--spacing-8);
    text-decoration: none;
    transition: color 0.16s ease-out;
}

.tr-logout-link:hover { color: var(--color-deep-ember); }

/* ── Forms ────────────────────────────────────────────────────── */

.tr-form-grid {
    display: grid;
    gap: var(--spacing-16);
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

/* Compact status pill used in the cockpit top + bottom rows. */
.tr-cockpit-statusbar {
    align-items: center;
    background: var(--color-canvas-white);
    border: none;
    border-radius: var(--radius-full);
    display: inline-flex;
    gap: var(--spacing-16);
    justify-content: flex-start;
    min-height: 40px;
    padding: 0 var(--spacing-24);
}

/* ── Motion ───────────────────────────────────────────────────── */

@media (prefers-reduced-motion: reduce) {
    .scan-pulse { animation: none; }
    * { transition-duration: 0.001ms !important; }
}

.scan-pulse { animation: pulse 1.8s ease-in-out infinite; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.54; }
}

.device-item.connecting {
    border-color: var(--color-neon-zest) !important;
    background: var(--color-warm-mist) !important;
    cursor: wait !important;
}

/* ── Responsive ───────────────────────────────────────────────── */

@media (max-width: 1279px) {
    .tr-sessions-full {
        grid-template-columns:
            180px           /* date */
            64px            /* mode */
            82px            /* duration */
            92px            /* distance */
            82px            /* avg power */
            82px            /* max power */
            82px            /* avg hr */
            82px            /* normalized power */
            58px            /* intensity factor */
            58px            /* training stress */
            minmax(0, 1fr)  /* spacer */
            32px;           /* chevron */
    }

    .tr-sessions-full .tr-sessions-row > :nth-child(8),
    .tr-sessions-full .tr-sessions-row > :nth-child(12) {
        display: none;
    }
}

@media (max-width: 1159px) {
    .tr-sessions-full {
        grid-template-columns:
            180px           /* date */
            64px            /* mode */
            82px            /* duration */
            92px            /* distance */
            82px            /* avg power */
            82px            /* normalized power */
            58px            /* intensity factor */
            58px            /* training stress */
            minmax(0, 1fr)  /* spacer */
            32px;           /* chevron */
    }

    .tr-sessions-full .tr-sessions-row > :nth-child(6),
    .tr-sessions-full .tr-sessions-row > :nth-child(7) {
        display: none;
    }
}

@media (max-width: 1023px) {
    .tr-sessions-full {
        grid-template-columns:
            180px           /* date */
            70px            /* mode */
            90px            /* duration */
            100px           /* distance */
            90px            /* avg power */
            minmax(0, 1fr)  /* spacer */
            40px;           /* chevron */
    }

    .tr-sessions-full .tr-sessions-row > :nth-child(9),
    .tr-sessions-full .tr-sessions-row > :nth-child(10),
    .tr-sessions-full .tr-sessions-row > :nth-child(11) {
        display: none;
    }
}

@media (max-width: 860px) {
    .tr-shell { width: min(100% - 28px, var(--page-max-width)); }

    .tr-header { position: static !important; }

    .tr-header .tr-shell {
        flex-wrap: wrap;
        gap: var(--spacing-16);
    }

    .tr-header .tr-shell > .q-row:last-child {
        justify-content: flex-start;
        overflow-x: auto;
        width: 100%;
    }

    .tr-title {
        font-size: var(--text-heading-sm);
        line-height: var(--leading-heading-sm);
    }

    .tr-hero-row {
        align-items: flex-start !important;
        flex-direction: column;
    }

    .tr-console-grid,
    .tr-status-strip,
    .tr-cockpit-top,
    .tr-cockpit-controls,
    .tr-form-grid {
        grid-template-columns: 1fr;
    }

    .tr-setup-erg {
        grid-template-columns: 1fr;
    }

    .tr-setup-erg-row {
        gap: var(--spacing-16);
        grid-template-columns: 1fr;
        max-width: none;
    }

    .tr-setup-erg-row .q-btn:first-child,
    .tr-setup-erg-row .q-btn:last-child {
        justify-self: stretch;
    }

.tr-metric-rail {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tr-route-stats,
    .tr-summary-grid,
    .tr-object-panel .tr-summary-grid-session,
    .tr-object-panel .tr-summary-grid-snapshot {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tr-summary-bar {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tr-activity-graph-header {
        flex-direction: column;
    }

    .tr-activity-graph-controls {
        width: 100%;
    }

    .tr-activity-graph-control {
        flex: 1;
    }

    .tr-power-panel { min-height: 300px; }

    .tr-history-row,
    .tr-device-row { grid-template-columns: 1fr; }

    .tr-device-state {
        align-items: flex-start;
    }

    .q-btn.tr-device-action {
        min-width: 0 !important;
        width: 100% !important;
    }

    .tr-object-panel {
        width: 100%;
    }

    .tr-detail-actions,
    .tr-detail-actions-right {
        align-items: stretch;
        flex-direction: column;
    }

    /* Sessions tables collapse to date + chevron only on phone. */
    .tr-sessions {
        grid-template-columns: minmax(0, 1fr) 40px;
    }

    .tr-sessions-row > :nth-child(n+2):nth-last-child(n+2) {
        display: none;
    }
}

/* Tablet layer — keep compact recent-ride rows readable but drop the spacer. */
@media (min-width: 861px) and (max-width: 1023px) {
    .tr-sessions-compact {
        grid-template-columns:
            minmax(0, 1.4fr)  /* date */
            70px              /* mode */
            90px              /* duration */
            100px             /* distance */
            40px;             /* chevron */
    }

    .tr-sessions-compact .tr-sessions-row > :nth-child(5),
    .tr-sessions-compact .tr-sessions-row > :nth-child(6),
    .tr-sessions-compact .tr-sessions-row > :nth-child(7) {
        display: none;
    }
}
</style>
"""
