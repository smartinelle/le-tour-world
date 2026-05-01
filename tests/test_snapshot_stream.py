"""Tests for browser snapshot stream helpers."""

import json

from terminalride.domain.state import RideMode, RideSnapshot
from terminalride.web.snapshot_stream import format_sse_event


def test_format_sse_event_serializes_snapshot():
    """SSE event contains a compact JSON ride snapshot payload."""
    snapshot = RideSnapshot(
        session_state="active",
        active=True,
        mode=RideMode.SIM,
        elapsed_s=12.5,
        power_w=205,
        cadence_rpm=87,
        speed_mps=8.4,
        distance_m=103.0,
        hr_bpm=144,
        sim_grade_pct=3.0,
        trainer_connected=True,
        hr_connected=True,
    )

    event = format_sse_event(snapshot)

    assert event.startswith("event: snapshot\n")
    assert event.endswith("\n\n")
    payload = event.split("data: ", 1)[1].strip()
    data = json.loads(payload)
    assert data["mode"] == "sim"
    assert data["power_w"] == 205
    assert data["trainer_connected"] is True
