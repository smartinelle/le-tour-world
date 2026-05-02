"""Tests for shared web theme browser contracts."""

from terminalride.web.theme import WEB_STYLES


def test_theme_preserves_material_icon_ligature_fonts():
    """Quasar icon ligatures must not inherit the app text font."""
    assert ".material-icons" in WEB_STYLES
    assert ".material-symbols" in WEB_STYLES
    assert "font-feature-settings: 'liga'" in WEB_STYLES
    assert "font-family: 'Material Icons' !important" in WEB_STYLES
    assert "font-family: 'Material Symbols Outlined' !important" in WEB_STYLES
