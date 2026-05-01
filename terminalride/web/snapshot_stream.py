"""HTTP snapshot transport for browser clients."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Protocol

from fastapi import Request
from starlette.responses import StreamingResponse

from terminalride.domain.ride_controller import RideController
from terminalride.domain.state import RideSnapshot


class RouteApp(Protocol):
    """Minimal route registration surface used by FastAPI/NiceGUI app."""

    def get(
        self, path: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """Register a GET route."""
        ...


def format_sse_event(snapshot: RideSnapshot) -> str:
    """Serialize one ride snapshot as a Server-Sent Events message."""
    payload = json.dumps(snapshot.to_dict(), separators=(",", ":"))
    return f"event: snapshot\ndata: {payload}\n\n"


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
