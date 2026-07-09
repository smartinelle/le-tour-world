#!/usr/bin/env python3
"""Run the le-tour web UI."""

import os
import socket

from le_tour.web import run_web_ui


def port_is_free(host: str, port: int) -> bool:
    """True when the address can be bound (uvicorn hides its own bind error)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


if __name__ == "__main__":
    host = os.environ.get("LE_TOUR_HOST", "127.0.0.1")
    port = int(os.environ.get("LE_TOUR_PORT", "8080"))

    if not port_is_free(host, port):
        print(
            f"Port {port} is already used by another app "
            f"(check with: lsof -i :{port}).\n"
            f"Pick a free port, e.g.: LE_TOUR_PORT={port + 100} "
            "uv run python run_web.py"
        )
        raise SystemExit(1)

    print(f"Starting le-tour Web UI (pid {os.getpid()})...")
    print(f"Open http://{host}:{port} in your browser")
    print(f"Stop with Ctrl+C, or: kill {os.getpid()}")
    run_web_ui(host=host, port=port)
