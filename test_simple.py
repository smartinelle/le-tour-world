#!/usr/bin/env python3
"""Simple test of TerminalRide with basic input."""

import asyncio
import time

import pytest

from terminalride.app import TerminalRideApp
from terminalride.ui.views import ViewState

class SimpleInput:
    """Simple input handler for testing."""
    
    def __init__(self):
        self.commands = ['1', '2', '3', 'q']  # Predefined commands
        self.index = 0
        self.last_input = time.time()
        
    async def get_next_command(self):
        """Get next command after a delay."""
        current_time = time.time()
        
        # Wait 5 seconds between commands
        if current_time - self.last_input > 5.0:
            if self.index < len(self.commands):
                cmd = self.commands[self.index]
                self.index += 1
                self.last_input = current_time
                print(f"\n>>> Simulating key press: {cmd}")
                return cmd
        
        return None

@pytest.mark.asyncio
async def test_app():
    """Test app with simulated input."""
    app = TerminalRideApp()
    simple_input = SimpleInput()
    
    # Override the input method
    async def mock_get_key():
        return await simple_input.get_next_command()
    
    app._get_key_async = mock_get_key
    
    try:
        await app.run()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await app.cleanup()

if __name__ == "__main__":
    print("Testing TerminalRide with simulated keyboard input...")
    print("Will simulate pressing: 1, 2, 3, q with 5 second delays")
    asyncio.run(test_app())