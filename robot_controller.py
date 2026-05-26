"""
Freenove 4WD Mecanum Car — TCP Controller
Connects to the Pico W over TCP and sends movement/LED/servo commands.

Usage (CLI):
  python robot_controller.py forward [speed] [duration]
  python robot_controller.py backward [speed] [duration]
  python robot_controller.py left [speed] [duration]
  python robot_controller.py right [speed] [duration]
  python robot_controller.py rotate_left [speed] [duration]
  python robot_controller.py rotate_right [speed] [duration]
  python robot_controller.py stop
  python robot_controller.py servo <angle>
  python robot_controller.py buzzer <freq>
  python robot_controller.py led <r> <g> <b>
  python robot_controller.py battery

Config: set CAR_IP and CAR_PORT below, or via env vars CAR_IP / CAR_PORT.
"""

import socket
import time
import sys
import os

# ── Config ────────────────────────────────────────────────────────────────────
CAR_IP   = os.environ.get("CAR_IP",   "192.168.43.133")
CAR_PORT = int(os.environ.get("CAR_PORT", "4002"))
TIMEOUT  = 3.0        # seconds for socket ops
MAX_SPEED = 2000      # Pico W motor max

# ── Protocol helpers ──────────────────────────────────────────────────────────
def build_cmd(*parts) -> bytes:
    """Build a '#'-delimited command ending in newline."""
    return ("#".join(str(p) for p in parts) + "\n").encode()

def send_command(*parts, recv=False) -> str | None:
    """Open a connection, send one command, optionally read a reply."""
    cmd = build_cmd(*parts)
    with socket.create_connection((CAR_IP, CAR_PORT), timeout=TIMEOUT) as s:
        s.sendall(cmd)
        if recv:
            s.settimeout(1.0)
            try:
                return s.recv(256).decode().strip()
            except socket.timeout:
                return None
    return None

# ── Movement API ──────────────────────────────────────────────────────────────
def forward(speed=MAX_SPEED, duration=0.0):
    """Drive straight forward.  angle1=0 → LY positive."""
    send_command("N", 0, speed, 0, 0)
    if duration:
        time.sleep(duration)
        stop()

def backward(speed=MAX_SPEED, duration=0.0):
    """Drive straight backward. angle1=180."""
    send_command("N", 180, speed, 0, 0)
    if duration:
        time.sleep(duration)
        stop()

def strafe_left(speed=MAX_SPEED, duration=0.0):
    """Strafe left (Mecanum only). angle1=90."""
    send_command("N", 90, speed, 0, 0)
    if duration:
        time.sleep(duration)
        stop()

def strafe_right(speed=MAX_SPEED, duration=0.0):
    """Strafe right (Mecanum only). angle1=270."""
    send_command("N", 270, speed, 0, 0)
    if duration:
        time.sleep(duration)
        stop()

def rotate_left(speed=MAX_SPEED, duration=0.0):
    """Rotate counter-clockwise in place. Uses right-joystick axis."""
    send_command("N", 0, 0, 90, speed)
    if duration:
        time.sleep(duration)
        stop()

def rotate_right(speed=MAX_SPEED, duration=0.0):
    """Rotate clockwise in place."""
    send_command("N", 0, 0, 270, speed)
    if duration:
        time.sleep(duration)
        stop()

def stop():
    """Halt all motors."""
    send_command("N", 0, 0, 0, 0)

# ── Extras ────────────────────────────────────────────────────────────────────
def servo(angle: int):
    """Move the head servo to [0–180] degrees."""
    angle = max(0, min(180, int(angle)))
    send_command("S", angle)

def buzzer(freq: int):
    """Play a tone at freq Hz (0 = off)."""
    send_command("B", freq)

def set_led(r: int, g: int, b: int, brightness: int = 255):
    """Set all WS2812 LEDs to an RGB colour."""
    send_command("L", r, g, b, brightness)

def battery() -> str:
    """Query battery voltage; returns string like 'P#7.82'."""
    reply = send_command("P", recv=True)
    return reply or "no reply"

# ── CLI entry-point ───────────────────────────────────────────────────────────
HELP = __doc__

def main():
    args = sys.argv[1:]
    if not args:
        print(HELP)
        return

    cmd = args[0].lower()
    speed    = int(args[1])    if len(args) > 1 else MAX_SPEED
    duration = float(args[2])  if len(args) > 2 else 0.0

    match cmd:
        case "forward":      forward(speed, duration)
        case "backward":     backward(speed, duration)
        case "left":         strafe_left(speed, duration)
        case "right":        strafe_right(speed, duration)
        case "rotate_left":  rotate_left(speed, duration)
        case "rotate_right": rotate_right(speed, duration)
        case "stop":         stop()
        case "servo":        servo(args[1])
        case "buzzer":       buzzer(int(args[1]))
        case "led":          set_led(int(args[1]), int(args[2]), int(args[3]))
        case "battery":      print(battery())
        case _:
            print(f"Unknown command: {cmd}")
            print(HELP)

if __name__ == "__main__":
    main()
