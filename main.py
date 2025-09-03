#!/usr/bin/env python3
"""Compatibility runner for TerminalRide.

Preferred: run `python -m terminalride` or the `terminalride` CLI.
This shim delegates to the package entry point without console logging
to avoid interfering with the TUI.
"""

import asyncio
import sys

from terminalride.app import main as app_main

if __name__ == "__main__":
    # Do not print or configure logging here; app configures logging itself.
    try:
        asyncio.run(app_main())
    except KeyboardInterrupt:
        sys.exit(0)
