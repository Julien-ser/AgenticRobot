"""
Hardware connectivity test — no AI, no API key required.

Run this first to verify:
  1. The robot is reachable over WiFi
  2. The TCP firmware is loaded correctly
  3. All peripherals (LED, buzzer, servo, motors) respond

Usage:
    python examples/drive_test.py --ip 192.168.x.x
    python examples/drive_test.py          # reads ROBOT_IP from .env
"""

import argparse
import time
import sys
import os

# Allow running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from robot.controller import RobotController

load_dotenv()


def run_test(ip: str):
    print(f"\nConnecting to robot at {ip} …")

    with RobotController(ip) as robot:

        # ── 1. Battery ────────────────────────────────────────────────────────
        print("\n[1/5] Battery check …")
        batt = robot.get_battery()
        print(f"      Battery: {batt or '(no response)'}")

        # ── 2. LED ────────────────────────────────────────────────────────────
        print("\n[2/5] LED test: Red → Green → Blue …")
        robot.set_led(255, 0, 0);   time.sleep(0.6)
        robot.set_led(0, 255, 0);   time.sleep(0.6)
        robot.set_led(0, 0, 255);   time.sleep(0.6)
        robot.led_off()

        # ── 3. Buzzer ─────────────────────────────────────────────────────────
        print("\n[3/5] Buzzer beep …")
        robot.beep(1000); time.sleep(0.4)
        robot.beep(1400); time.sleep(0.4)

        # ── 4. Servo ──────────────────────────────────────────────────────────
        print("\n[4/5] Servo sweep (centre → left → right → centre) …")
        robot.set_servo(90);  time.sleep(0.5)
        robot.set_servo(45);  time.sleep(0.5)
        robot.set_servo(135); time.sleep(0.5)
        robot.set_servo(90);  time.sleep(0.5)

        # ── 5. Movement ───────────────────────────────────────────────────────
        print("\n[5/5] Movement test")
        print("      ⚠  Clear a 60 cm square of space around the robot.")
        input("      Press Enter to start movement test (Ctrl+C to skip) … ")

        moves = [
            ("Forward 1 s",       lambda: robot.forward(40, 1.0)),
            ("Backward 1 s",      lambda: robot.backward(40, 1.0)),
            ("Strafe left 0.5 s", lambda: robot.strafe_left(40, 0.5)),
            ("Strafe right 0.5 s",lambda: robot.strafe_right(40, 0.5)),
            ("Rotate left 0.6 s", lambda: robot.rotate_left(40, 0.6)),
            ("Rotate right 0.6 s",lambda: robot.rotate_right(40, 0.6)),
        ]
        for label, fn in moves:
            print(f"      {label} …")
            fn()
            time.sleep(0.35)    # brief pause between moves

        # ── Done ──────────────────────────────────────────────────────────────
        robot.set_led(0, 255, 0)
        robot.beep(1200); time.sleep(0.15); robot.beep(1200)
        print("\n✓ All tests passed — robot is ready for agent control!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Freenove robot hardware test")
    parser.add_argument(
        "--ip",
        default=os.getenv("ROBOT_IP"),
        help="Robot IP address (or set ROBOT_IP in .env)",
    )
    args = parser.parse_args()

    if not args.ip:
        parser.error("Provide --ip or set ROBOT_IP in .env")

    try:
        run_test(args.ip)
    except KeyboardInterrupt:
        print("\nTest skipped.")
    except ConnectionRefusedError:
        print(f"\n✗ Could not connect to {args.ip}:4002")
        print("  Check: Is the robot powered on? Is WiFi sketch 06.2 flashed?")
        sys.exit(1)
