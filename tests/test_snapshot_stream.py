"""Tests for browser snapshot stream helpers."""

import json
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from starlette.testclient import TestClient

from le_tour.domain.device_state import DeviceConnectionStatus, DiscoveredDevice
from le_tour.domain.state import RideMode, RideSnapshot
from le_tour.web.snapshot_stream import attach_snapshot_routes, format_sse_event


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


def test_device_scan_endpoint_exposes_discovered_devices():
    """Browser clients can scan devices through service APIs."""
    controller = MagicMock()
    controller.trainer.scan_devices = AsyncMock(
        return_value=[
            DiscoveredDevice(
                device_type="trainer",
                name="KICKR Core",
                address="AA:BB",
                rssi=-52,
            )
        ]
    )
    app = FastAPI()
    attach_snapshot_routes(app, lambda: controller)

    response = TestClient(app).post("/api/devices/trainer/scan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["device_type"] == "trainer"
    assert payload["devices"][0]["name"] == "KICKR Core"
    assert payload["devices"][0]["address"] == "AA:BB"
    controller.trainer.scan_devices.assert_awaited_once_with(timeout_s=8.0)


def test_device_connect_endpoint_delegates_to_service():
    """Browser clients can connect selected devices without private clients."""
    controller = MagicMock()
    controller.trainer.connect_to_device = AsyncMock()
    controller.trainer.connection_status.return_value = DeviceConnectionStatus(
        device_type="trainer",
        connected=True,
        name="KICKR Core",
        address="AA:BB",
    )
    controller.hr_service.connection_status.return_value = DeviceConnectionStatus(
        device_type="hr",
        connected=False,
    )
    app = FastAPI()
    attach_snapshot_routes(app, lambda: controller)

    response = TestClient(app).post(
        "/api/devices/trainer/connect",
        json={"address": "AA:BB"},
    )

    assert response.status_code == 200
    assert response.json()["trainer"]["name"] == "KICKR Core"
    controller.trainer.connect_to_device.assert_awaited_once_with("AA:BB")


def test_device_disconnect_endpoint_delegates_to_service():
    """Browser clients can disconnect devices through service APIs."""
    controller = MagicMock()
    controller.hr_service.disconnect = AsyncMock()
    controller.trainer.connection_status.return_value = DeviceConnectionStatus(
        device_type="trainer",
        connected=False,
    )
    controller.hr_service.connection_status.return_value = DeviceConnectionStatus(
        device_type="hr",
        connected=False,
    )
    app = FastAPI()
    attach_snapshot_routes(app, lambda: controller)

    response = TestClient(app).post("/api/devices/hr/disconnect")

    assert response.status_code == 200
    assert response.json()["hr"]["connected"] is False
    controller.hr_service.disconnect.assert_awaited_once()


def test_device_connect_endpoint_rejects_missing_address():
    """Device connect requires a selected BLE address."""
    app = FastAPI()
    attach_snapshot_routes(app, lambda: MagicMock())

    response = TestClient(app).post("/api/devices/trainer/connect", json={})

    assert response.status_code == 400
