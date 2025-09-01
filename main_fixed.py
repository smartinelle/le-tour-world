#!/usr/bin/env python3
"""TerminalRide - Fixed version with working keyboard input."""

import asyncio
import sys
from terminalride.config import get_config
from terminalride.logging_setup import setup_logging
from terminalride.devices.ftms_client import FtmsClient

async def main():
    """Simple working version."""
    config = get_config()
    setup_logging(config.log_level.upper())
    
    # Connect to trainer
    trainer = FtmsClient()
    print("🔍 Connecting to KICKR CORE...")
    
    try:
        await trainer.scan_and_connect(timeout_s=10.0)
        device_info = trainer.device_info
        print(f"✅ Connected to {device_info.get('name', 'Unknown')}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print("\n🚴 TerminalRide - Ready!")
    print("Press 1, 2, or 3 and then Enter:")
    print("  1 = Free Ride")
    print("  2 = ERG Mode") 
    print("  3 = SIM Mode")
    print("  q = Quit")
    
    while True:
        try:
            choice = input("\n>>> ").strip()
            
            if choice == '1':
                print("🚴 Free Ride Mode - Start pedaling!")
                await trainer.start_session()
                input("Press Enter to stop...")
                await trainer.stop_session()
                print("✅ Session completed")
                
            elif choice == '2':
                print("🎯 ERG Mode - Target 150W")
                await trainer.request_control()
                await trainer.start_session()
                await trainer.set_target_power(150)
                print("💪 Start pedaling! Trainer will control resistance.")
                input("Press Enter to stop...")
                await trainer.stop_session()
                print("✅ ERG Session completed")
                
            elif choice == '3':
                print("⛰️ SIM Mode - 5% grade")
                await trainer.request_control()
                await trainer.start_session()
                await trainer.set_simulation_params(5.0)
                print("🏔️ Start pedaling! Feel the hill!")
                input("Press Enter to stop...")
                await trainer.stop_session()
                print("✅ SIM Session completed")
                
            elif choice == 'q':
                break
                
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    await trainer.disconnect()
    print("👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())