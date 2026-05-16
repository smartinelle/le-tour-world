"""Tests for shared web theme browser contracts."""

import re

from le_tour.web.theme import WEB_STYLES


def test_theme_preserves_material_icon_ligature_fonts():
    """Quasar icon ligatures must not inherit the app text font."""
    assert ".material-icons" in WEB_STYLES
    assert ".material-symbols" in WEB_STYLES
    assert "font-feature-settings: 'liga'" in WEB_STYLES
    assert "font-family: 'Material Icons' !important" in WEB_STYLES
    assert "font-family: 'Material Symbols Outlined' !important" in WEB_STYLES


def test_theme_has_no_decorative_gradients():
    """Decorative gradients are forbidden — they create the AI-slop look."""
    assert "linear-gradient" not in WEB_STYLES
    assert "repeating-linear-gradient" not in WEB_STYLES


def test_theme_has_no_heavy_backdrop_blur():
    """Large backdrop-filter surfaces hurt scroll perf and look cheap."""
    assert "backdrop-filter" not in WEB_STYLES


def test_theme_has_no_drop_shadows():
    """Groq depth comes from background-color shifts, never box-shadow.

    Status dots are the documented exception (they use box-shadow as a soft
    halo around the dot, not for elevation).
    """
    shadow_lines = [
        line.strip()
        for line in WEB_STYLES.splitlines()
        if "box-shadow" in line and "!important" not in line.lower()
    ]
    # Allow only the status-dot halos and !important resets.
    offenders = [
        line for line in shadow_lines if "0 0 0 4px" not in line and "none" not in line
    ]
    assert not offenders, f"Unexpected box-shadows: {offenders}"


def test_theme_uses_only_template_font_weights():
    """Groq spec: Sans 300/400, Mono 400/500. Allow 300, 400, 500 only."""
    weights = {int(m) for m in re.findall(r"font-weight:\s*(\d+)", WEB_STYLES)}
    allowed = {300, 400, 500}
    assert weights.issubset(allowed), f"Non-template font weights: {weights - allowed}"


def test_theme_titles_use_text_balance():
    """Headings must opt into text-wrap: balance to avoid orphan words."""
    title_block = re.search(r"\.tr-title\s*\{[^}]+\}", WEB_STYLES)
    assert title_block is not None
    assert "text-wrap: balance" in title_block.group(0)


def test_theme_data_values_use_tabular_nums():
    """All numeric readouts must use tabular-nums so digits don't jump.

    Matches the canonical (single-class) definition only — descendant
    selectors that override sub-properties are not required to repeat
    tabular-nums since it inherits.
    """
    for cls in (
        ".tr-power-value",
        ".tr-metric-value",
        ".tr-control-value",
        ".tr-meta-value",
        ".tr-erg-target-value",
        ".tr-target-readout",
    ):
        # `(?m)^` plus optional comma-list anchors to the start of a rule.
        block = re.search(
            r"(?m)^" + re.escape(cls) + r"(?:,[^{]*)?\s*\{[^}]+\}",
            WEB_STYLES,
        )
        assert block is not None, f"Missing canonical rule for {cls}"
        assert "tabular-nums" in block.group(0), f"{cls} missing tabular-nums"


def test_theme_exposes_groq_color_palette():
    """The full Groq palette must be exposed as CSS variables."""
    for token in (
        "--color-obsidian-slate",
        "--color-canvas-white",
        "--color-warm-mist",
        "--color-ash-concrete",
        "--color-deep-pewter",
        "--color-steel-gray",
        "--color-soft-stone",
        "--color-faded-quartz",
        "--color-neon-zest",
        "--color-deep-ember",
        "--color-lavender-haze",
        "--color-violet-tint",
    ):
        assert token in WEB_STYLES, f"Missing color token {token}"


def test_theme_exposes_groq_spacing_scale():
    """Spacing scale must use the 8px-base Groq tokens."""
    for token in (
        "--spacing-8",
        "--spacing-16",
        "--spacing-24",
        "--spacing-32",
        "--spacing-40",
        "--spacing-48",
        "--spacing-56",
        "--spacing-80",
    ):
        assert token in WEB_STYLES, f"Missing spacing token {token}"


def test_theme_exposes_groq_radius_scale():
    """Radius philosophy: cards 0, misc 5, forms 10, buttons 1000."""
    for token in (
        "--radius-md",
        "--radius-lg",
        "--radius-full",
        "--radius-cards",
        "--radius-buttons",
    ):
        assert token in WEB_STYLES, f"Missing radius token {token}"


def test_theme_exposes_groq_type_scale():
    """Type scale tokens from caption to display must exist."""
    for token in (
        "--text-caption",
        "--text-body-lg",
        "--text-heading-sm",
        "--text-heading",
        "--text-heading-lg",
        "--text-display",
        "--font-space-grotesk",
        "--font-ibm-plex-mono",
    ):
        assert token in WEB_STYLES, f"Missing type token {token}"


def test_theme_session_view_uses_dvh_not_vh():
    """Mobile chrome eats vh — use dvh for full-height session shells."""
    block = re.search(r"\.session-view\s*\{[^}]+\}", WEB_STYLES)
    assert block is not None
    assert "100dvh" in block.group(0)
    assert "100vh" not in block.group(0)


def test_theme_respects_reduced_motion():
    """A prefers-reduced-motion media query must exist."""
    assert "@media (prefers-reduced-motion: reduce)" in WEB_STYLES


def test_theme_loads_space_grotesk_from_google_fonts():
    """Space Grotesk is loaded — Groq's primary typeface."""
    assert "Space+Grotesk" in WEB_STYLES
    assert "IBM+Plex+Mono" in WEB_STYLES


def test_theme_button_uses_pill_radius():
    """Per Groq spec, primary buttons must use --radius-buttons (1000px pill)."""
    block = re.search(
        r"\.tr-btn-primary,\s*\.tr-btn-secondary[^{]*\{[^}]+\}",
        WEB_STYLES,
    )
    assert block is not None
    assert "var(--radius-buttons)" in block.group(0)


def test_theme_segmented_control_suppresses_quasar_overlays():
    """Segmented controls should not flash Quasar hover/ripple colors."""
    focus_block = re.search(
        r"\.q-btn\.tr-seg \.q-focus-helper,[^{]*\{[^}]+\}",
        WEB_STYLES,
    )
    assert focus_block is not None
    assert "background: transparent !important" in focus_block.group(0)
    assert "opacity: 0 !important" in focus_block.group(0)

    ripple_block = re.search(r"\.q-btn\.tr-seg \.q-ripple,[^{]*\{[^}]+\}", WEB_STYLES)
    assert ripple_block is not None
    assert "display: none !important" in ripple_block.group(0)

    active_hover_block = re.search(
        r"\.q-btn\.tr-seg\.active:hover\s*\{[^}]+\}", WEB_STYLES
    )
    assert active_hover_block is not None
    assert (
        "background: var(--color-canvas-white) !important"
        in active_hover_block.group(0)
    )
    assert "color: var(--color-neon-zest) !important" in active_hover_block.group(0)


def test_theme_home_activity_calendar_matches_card_spec():
    """Home activity uses one card, fixed week columns, and binary cell colors."""
    panel_block = re.search(r"\.tr-home-activity-panel\s*\{[^}]+\}", WEB_STYLES)
    assert panel_block is not None
    assert "grid-column: 1 / -1" in panel_block.group(0)

    scroll_block = re.search(r"\.tr-home-activity-scroll\s*\{[^}]+\}", WEB_STYLES)
    assert scroll_block is not None
    assert "overflow-x: auto" in scroll_block.group(0)

    grid_block = re.search(r"\.tr-home-activity-grid\s*\{[^}]+\}", WEB_STYLES)
    assert grid_block is not None
    assert "minmax(var(--activity-cell-min), 1fr)" in grid_block.group(0)
    assert "min-width: var(--activity-min-width)" in grid_block.group(0)
    assert "width: 100%" in grid_block.group(0)

    empty_cell_block = re.search(r"\.tr-home-activity-cell\s*\{[^}]+\}", WEB_STYLES)
    assert empty_cell_block is not None
    assert "aspect-ratio: 1" in empty_cell_block.group(0)
    assert "background: var(--color-warm-mist)" in empty_cell_block.group(0)
    assert "border: 0" in empty_cell_block.group(0)

    active_cell_block = re.search(
        r"\.tr-home-activity-cell\.active\s*\{[^}]+\}",
        WEB_STYLES,
    )
    assert active_cell_block is not None
    assert "background: var(--color-neon-zest)" in active_cell_block.group(0)


def test_theme_panels_use_card_radius():
    """Per Groq spec, panels must use --radius-cards (0px)."""
    block = re.search(r"\.tr-panel,[^{]*\{[^}]+\}", WEB_STYLES)
    assert block is not None
    assert "var(--radius-cards)" in block.group(0)
