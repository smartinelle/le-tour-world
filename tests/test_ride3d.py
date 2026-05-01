"""Tests for the Three.js ride prototype page."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from terminalride.domain.state import RideMode
from terminalride.web.ride3d import RIDE3D_HTML, parse_ride_mode

RIDE3D_JS = Path("terminalride/web/static/ride3d.js").read_text()


def test_ride3d_page_consumes_snapshot_stream():
    """3D prototype is a browser-only snapshot stream consumer."""
    assert '<script type="module" src="/static/ride3d.js"></script>' in RIDE3D_HTML
    assert 'new EventSource("/api/ride/snapshots")' in RIDE3D_JS
    assert "https://esm.sh/three" in RIDE3D_JS
    assert "speed_mps" in RIDE3D_JS
    assert "canvas" in RIDE3D_HTML


def test_ride3d_page_has_session_controls():
    """3D prototype can start and stop local ride sessions."""
    assert 'data-start-mode="free"' in RIDE3D_HTML
    assert 'data-start-mode="erg"' in RIDE3D_HTML
    assert 'data-start-mode="sim"' in RIDE3D_HTML
    assert 'id="stop-ride"' in RIDE3D_HTML
    assert 'postRideAction("/api/ride/start"' in RIDE3D_JS
    assert 'postRideAction("/api/ride/stop")' in RIDE3D_JS


def test_parse_ride_mode():
    """Browser-supplied ride mode strings map to domain modes."""
    assert parse_ride_mode("free") is RideMode.FREE
    assert parse_ride_mode("ERG") is RideMode.ERG
    assert parse_ride_mode(None) is RideMode.FREE


def test_parse_ride_mode_rejects_unknown_mode():
    """Unsupported ride mode strings return a 400 response."""
    with pytest.raises(HTTPException) as exc_info:
        parse_ride_mode("climb")

    assert exc_info.value.status_code == 400
