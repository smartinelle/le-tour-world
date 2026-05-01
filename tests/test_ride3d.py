"""Tests for the Three.js ride prototype page."""

from terminalride.web.ride3d import RIDE3D_HTML


def test_ride3d_page_consumes_snapshot_stream():
    """3D prototype is a browser-only snapshot stream consumer."""
    assert 'new EventSource("/api/ride/snapshots")' in RIDE3D_HTML
    assert "https://esm.sh/three" in RIDE3D_HTML
    assert "speed_mps" in RIDE3D_HTML
    assert "canvas" in RIDE3D_HTML
