#!/usr/bin/env python3
"""Demo TerminalRide functionality with your KICKR CORE."""

import asyncio
import time
from terminalride.devices.ftms_client import FtmsClient
from terminalride.modes.erg import ErgController
from terminalride.modes.sim import SimPhysics, SimConfig
from terminalride.logging_setup import setup_logging


class TrainerDemo:
    def __init__(self):
        self.trainer = FtmsClient()
        self.erg_controller = ErgController()
        self.sim_solver = SimPhysics(SimConfig())
        self.connected = False

    async def connect_and_demo(self):
        print("🚴 TerminalRide - KICKR CORE Demo")
        print("=" * 40)

        print("🔍 Connecting to your KICKR CORE...")
        try:
            await self.trainer.scan_and_connect(timeout_s=10.0)
            device_info = self.trainer.device_info
            trainer_name = device_info.get("name", "Unknown")
            print(f"✅ Connected to {trainer_name}")
            self.connected = True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

        print("📡 Subscribing to bike data...")
        latest_data = {}

        def data_callback(sample):
            latest_data.update(sample)
            power = sample.get("power_w", 0)
            cadence = sample.get("cadence_rpm", 0)
            speed = sample.get("speed_mps", 0)
            print(
                f"📊 Power: {power}W | Cadence: {cadence}rpm | Speed: {speed*3.6:.1f}km/h"
            )

        await self.trainer.subscribe_bike_data(data_callback)

        print("\n🎯 Demo: ERG Mode (Target Power Control)")
        print("Setting target power to 150W...")

        try:
            await self.trainer.request_control()
            await self.trainer.start_session()
            await self.trainer.set_target_power(150)

            print("💪 Start pedaling! The trainer will adjust resistance.")
            print("📈 Watching data for 30 seconds...")

            start_time = time.time()
            while time.time() - start_time < 30:
                await asyncio.sleep(1)
                if latest_data:
                    current_power = latest_data.get("power_w", 0)
                    optimal_power = self.erg_controller.update(150, current_power, 1.0)
                    if abs(optimal_power - 150) > 5:
                        await self.trainer.set_target_power(optimal_power)

            print("🛑 Stopping ERG mode...")
            await self.trainer.stop_session()

        except Exception as e:
            print(f"❌ ERG demo failed: {e}")

        print("\n⛰️  Demo: SIM Mode (Grade Simulation)")
        print("Setting grade to 5% uphill...")

        try:
            await self.trainer.start_session()
            await self.trainer.set_simulation_params(5.0)

            print("🏔️  Pedal and feel the increased resistance!")
            print("📊 Physics calculation demo:")

            for power in [150, 200, 250, 300]:
                speed = self.sim_solver.solve_speed(power, 5.0)
                print(f"   {power}W at 5% grade → {speed*3.6:.1f} km/h")

            print("📈 Watching data for 15 seconds...")
            await asyncio.sleep(15)

            print("🛑 Stopping SIM mode...")
            await self.trainer.stop_session()

        except Exception as e:
            print(f"❌ SIM demo failed: {e}")

        print("\n🎉 Demo completed!")
        await self.trainer.disconnect()


async def main():
    setup_logging("INFO")
    demo = TrainerDemo()
    await demo.connect_and_demo()


if __name__ == "__main__":
    print("Starting demo in 2 seconds...")
    time.sleep(2)
    asyncio.run(main())
