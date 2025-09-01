#!/usr/bin/env python3
"""TerminalRide - Simple version with line-based input."""

import asyncio
import sys
from terminalride.config import get_config
from terminalride.logging_setup import setup_logging

# Simple menu-driven version
class SimpleTerminalRide:
    def __init__(self):
        from terminalride.devices.ftms_client import FtmsClient
        from terminalride.modes.erg import ErgController
        from terminalride.modes.sim import SimPhysics, SimConfig
        from terminalride.store.repository import TrainingRepository
        
        self.trainer_client = FtmsClient()
        self.erg_controller = ErgController()
        self.sim_solver = SimPhysics(SimConfig())
        self.repository = TrainingRepository()
        self.connected = False

    async def connect_trainer(self):
        """Connect to trainer."""
        print("🔍 Scanning for BLE FTMS trainers...")
        try:
            await self.trainer_client.scan_and_connect(timeout_s=10.0)
            device_info = self.trainer_client.device_info
            print(f"✅ Connected to {device_info.get('name', 'Unknown Trainer')}")
            self.connected = True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("🎮 Running in demo mode")
            self.connected = False

    def show_menu(self):
        """Show main menu."""
        print("\n" + "="*50)
        print("🚴 TerminalRide - Indoor Cycling")
        print("="*50)
        
        if self.connected:
            trainer_name = self.trainer_client.device_info.get('name', 'Unknown')
            print(f"📡 Connected: {trainer_name}")
        else:
            print("📡 Status: Demo Mode")
            
        print("\nTraining Modes:")
        print("  [1] Free Ride")
        print("  [2] ERG Mode (Target Power)")  
        print("  [3] SIM Mode (Virtual Route)")
        print("\nOptions:")
        print("  [s] Statistics")
        print("  [c] Settings") 
        print("  [q] Quit")
        print("\nEnter your choice and press Enter:")

    async def handle_training_mode(self, mode):
        """Handle training mode."""
        mode_names = {1: "Free Ride", 2: "ERG Mode", 3: "SIM Mode"}
        print(f"\n🏃 Starting {mode_names[mode]}...")
        
        if not self.connected:
            print("📊 Demo mode - simulated data only")
        
        print("\nTraining Controls:")
        print("  [p] Pause/Resume")
        print("  [+] Increase power/grade")
        print("  [-] Decrease power/grade") 
        print("  [s] Stop and save")
        print("  [Enter] Continue")
        
        current_power = 150 if mode == 2 else 0
        current_grade = 0.0 if mode == 3 else 0.0
        
        while True:
            if mode == 2:  # ERG Mode
                print(f"🎯 Target Power: {current_power}W | Current: {current_power}W")
            elif mode == 3:  # SIM Mode  
                print(f"⛰️  Grade: {current_grade:.1f}% | Speed: 25.5 km/h")
            else:  # Free Ride
                print(f"⚡ Power: 180W | Speed: 28.2 km/h | Distance: 5.2km")
            
            try:
                choice = input(">>> ").lower().strip()
                
                if choice == 's':
                    print("💾 Session saved!")
                    break
                elif choice == '+' and mode == 2:
                    current_power = min(400, current_power + 10)
                elif choice == '-' and mode == 2:
                    current_power = max(100, current_power - 10)
                elif choice == '+' and mode == 3:
                    current_grade = min(15.0, current_grade + 1.0)
                elif choice == '-' and mode == 3:
                    current_grade = max(-10.0, current_grade - 1.0)
                elif choice == 'p':
                    print("⏸️  Paused - press Enter to continue")
                elif choice == '':
                    continue
                else:
                    print("❓ Unknown command")
                    
            except KeyboardInterrupt:
                break
        
        print(f"✅ {mode_names[mode]} session completed")

    async def run(self):
        """Main application loop."""
        await self.connect_trainer()
        
        while True:
            try:
                self.show_menu()
                choice = input(">>> ").strip().lower()
                
                if choice == 'q':
                    print("👋 Goodbye!")
                    break
                elif choice in ['1', '2', '3']:
                    await self.handle_training_mode(int(choice))
                elif choice == 's':
                    print("📊 Statistics - No sessions recorded yet")
                    input("Press Enter to continue...")
                elif choice == 'c':
                    print("⚙️  Settings - Configuration coming soon")
                    input("Press Enter to continue...")
                else:
                    print("❓ Invalid choice. Try again.")
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                break

async def main():
    """Main entry point."""
    config = get_config()
    setup_logging(config.log_level.upper())
    
    print("🚴 TerminalRide - Simple Edition")
    print("Press Ctrl+C at any time to quit")
    
    app = SimpleTerminalRide()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())