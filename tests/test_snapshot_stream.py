"""Tests for browser snapshot stream helpers."""

import json
from unittest.mock import MagicMock

from fastapi import FastAPI
from starlette.testclient import TestClient

from terminalride.domain.device_state import DeviceConnectionStatus
from terminalride.domain.state import RideMode, RideSnapshot
from terminalride.web.snapshot_stream import attach_snapshot_routes, format_sse_event


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


def test_device_status_endpoint_exposes_service_status():
    """Browser clients can read hardware state without private service access."""
    controller = MagicMock()
    controller.trainer.connection_status.return_value = DeviceConnectionStatus(
        device_type="trainer",
        connected=True,
        name="KICKR Core",
        rssi=-48,
        has_control=True,
    )
    controller.hr_service.connection_status.return_value = DeviceConnectionStatus(
        device_type="hr",
        connected=False,
    )
    app = FastAPI()
    attach_snapshot_routes(app, lambda: controller)

    response = TestClient(app).get("/api/devices/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trainer"]["connected"] is True
    assert payload["trainer"]["name"] == "KICKR Core"
    assert payload["trainer"]["has_control"] is True
    assert payload["hr"]["connected"] is False
