"""HTTP snapshot transport for browser clients."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Protocol

from fastapi import HTTPException, Request
from starlette.responses import StreamingResponse

from terminalride.domain.device_state import DiscoveredDevice
from terminalride.domain.ride_controller import RideController
from terminalride.domain.state import RideSnapshot


class RouteApp(Protocol):
    """Minimal route registration surface used by FastAPI/NiceGUI app."""

    def get(
        self, path: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Register a GET route."""
        ...

    def post(
        self, path: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Register a POST route."""
        ...


def format_sse_event(snapshot: RideSnapshot) -> str:
    """Serialize one ride snapshot as a Server-Sent Events message."""
    payload = json.dumps(snapshot.to_dict(), separators=(",", ":"))
    return f"event: snapshot\ndata: {payload}\n\n"


def _device_status_payload(controller: RideController) -> dict[str, object]:
    return {
        "trainer": controller.trainer.connection_status().to_dict(),
        "hr": controller.hr_service.connection_status().to_dict(),
    }


def _serialize_devices(devices: list[DiscoveredDevice]) -> list[dict[str, object]]:
    return [device.to_dict() for device in devices]


def _validate_device_type(device_type: str) -> str:
    normalized = device_type.lower()
    if normalized not in {"trainer", "hr"}:
        raise HTTPException(status_code=404, detail="Unknown device type")
    return normalized


async def iter_snapshot_events(
    request: Request,
    controller_provider: Callable[[], RideController],
    interval_s: float = 0.25,
) -> AsyncIterator[str]:
    """Yield ride snapshots until the client disconnects."""
    last_event = ""
    while not await request.is_disconnected():
        event = format_sse_event(controller_provider().snapshot())
        if event != last_event:
            yield event
            last_event = event
        await asyncio.sleep(interval_s)


def attach_snapshot_routes(
    web_app: RouteApp,
    controller_provider: Callable[[], RideController],
) -> None:
    """Attach snapshot endpoints to a FastAPI-compatible app."""

    @web_app.get("/api/ride/snapshot")
    async def ride_snapshot() -> dict[str, object]:
        return controller_provider().snapshot().to_dict()

    @web_app.get("/api/devices/status")
    async def device_status() -> dict[str, object]:
        return _device_status_payload(controller_provider())

    @web_app.post("/api/devices/{device_type}/scan")
    async def scan_device(device_type: str) -> dict[str, object]:
        controller = controller_provider()
        device_type = _validate_device_type(device_type)
        if device_type == "trainer":
            devices = await controller.trainer.scan_devices(timeout_s=8.0)
        else:
            devices = await controller.hr_service.scan_devices(timeout_s=8.0)
        return {"device_type": device_type, "devices": _serialize_devices(devices)}

    @web_app.post("/api/devices/{device_type}/connect")
    async def connect_device(device_type: str, request: Request) -> dict[str, object]:
        body = await request.json()
        address = body.get("address")
        if not isinstance(address, str) or not address:
            raise HTTPException(status_code=400, detail="Missing device address")

        controller = controller_provider()
        device_type = _validate_device_type(device_type)
        if device_type == "trainer":
            await controller.trainer.connect_to_device(address)
        else:
            await controller.hr_service.connect_to_device(address)
        return _device_status_payload(controller)

    @web_app.post("/api/devices/{device_type}/disconnect")
    async def disconnect_device(device_type: str) -> dict[str, object]:
        controller = controller_provider()
        device_type = _validate_device_type(device_type)
        if device_type == "trainer":
            await controller.trainer.disconnect()
        else:
            await controller.hr_service.disconnect()
        return _device_status_payload(controller)

    @web_app.get("/api/ride/snapshots")
    async def ride_snapshot_stream(request: Request) -> StreamingResponse:
        return StreamingResponse(
            iter_snapshot_events(request, controller_provider),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


__all__ = ["attach_snapshot_routes", "format_sse_event", "iter_snapshot_events"]
