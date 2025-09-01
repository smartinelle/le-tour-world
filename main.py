#!/usr/bin/env python3
"""TerminalRide - Terminal-first indoor cycling app.

Entry point for the application with proper async lifecycle management.
"""

import asyncio
import sys

from terminalride.app import TerminalRideApp
from terminalride.logging_setup import setup_logging
from terminalride.config import get_config


async def main():
    """Main application entry point."""
    # Setup logging
    config = get_config()
    setup_logging(config.log_level.upper())
    
    # Create and run application
    app = TerminalRideApp()
    try:
        await app.run()
    except KeyboardInterrupt:
        print("\nShutting down TerminalRide...")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
    finally:
        await app.cleanup()


if __name__ == "__main__":
    asyncio.run(main())