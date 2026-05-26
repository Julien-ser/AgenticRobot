"""
MCP server that exposes Freenove 4WD Mecanum Robot control tools to Claude Code.

Claude Code connects to this server and can directly call robot tools during
any conversation — no separate agent script needed.

Start via:  python -m robot_mcp
Configure:  add to ~/.claude/settings.json mcpServers (already done if you ran setup)
"""

import os
import sys
import time
from typing import Literal

# ── Path setup ───────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from mcp.server.fastmcp import FastMCP
from robot.controller import RobotController

# ── MCP app ───────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "freenove-robot",
    description=(
        "Control a Freenove 4WD Mecanum Wheel Robot Car over WiFi. "
        "Tools: omnidirectional motion (forward/backward/strafe/diagonal/rotate), "
        "ultrasonic distance sensor, RGB LED, buzzer, servo head, battery query."
    ),
)

# ── Singleton robot connection (connects lazily on first tool call) ───────────
_robot: RobotController | None = None


def get_robot() -> RobotController:
    """Return the live robot controller, reconnecting if the socket dropped."""
    global _robot
    if _robot is None or not _robot.client.is_connected():
        ip = os.environ.get("ROBOT_IP", "")
        if not ip or "x" in ip:
            raise RuntimeError(
                "ROBOT_IP not configured.\n"
                "Edit Projects/AgenticRobot/.env and set ROBOT_IP=<your robot's IP>.\n"
                "Find the IP in your router's DHCP table or the Freenove Windows app."
            )
        _robot = RobotController(ip)
        _robot.connect()
    return _robot


# ═══════════════════════════════════════════════════════════════════════════════
# Motion tools
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def move_forward(speed: int = 50, duration: float = 1.0) -> str:
    """Drive the robot straight forward, then stop.

    Args:
        speed: Motor speed 0–100. Use 30–50 indoors, 60–80 in open space.
        duration: Seconds to drive before auto-stopping.
    """
    get_robot().forward(speed, duration)
    return f"Moved forward — speed={speed}, duration={duration}s"


@mcp.tool()
def move_backward(speed: int = 50, duration: float = 1.0) -> str:
    """Drive the robot straight backward, then stop.

    Args:
        speed: Motor speed 0–100.
        duration: Seconds to drive.
    """
    get_robot().backward(speed, duration)
    return f"Moved backward — speed={speed}, duration={duration}s"


@mcp.tool()
def strafe_left(speed: int = 50, duration: float = 1.0) -> str:
    """Slide the robot directly left without yawing (mecanum wheel strafing).

    Args:
        speed: Motor speed 0–100.
        duration: Seconds to strafe.
    """
    get_robot().strafe_left(speed, duration)
    return f"Strafed left — speed={speed}, duration={duration}s"


@mcp.tool()
def strafe_right(speed: int = 50, duration: float = 1.0) -> str:
    """Slide the robot directly right without yawing (mecanum wheel strafing).

    Args:
        speed: Motor speed 0–100.
        duration: Seconds to strafe.
    """
    get_robot().strafe_right(speed, duration)
    return f"Strafed right — speed={speed}, duration={duration}s"


@mcp.tool()
def rotate_left(speed: int = 50, duration: float = 0.5) -> str:
    """Spin the robot counter-clockwise in place.

    Args:
        speed: Rotation speed 0–100.
        duration: Seconds to spin.
    """
    get_robot().rotate_left(speed, duration)
    return f"Rotated CCW — speed={speed}, duration={duration}s"


@mcp.tool()
def rotate_right(speed: int = 50, duration: float = 0.5) -> str:
    """Spin the robot clockwise in place.

    Args:
        speed: Rotation speed 0–100.
        duration: Seconds to spin.
    """
    get_robot().rotate_right(speed, duration)
    return f"Rotated CW — speed={speed}, duration={duration}s"


@mcp.tool()
def move_diagonal(
    direction: Literal["forward_left", "forward_right", "backward_left", "backward_right"],
    speed: int = 50,
    duration: float = 1.0,
) -> str:
    """Move diagonally using the mecanum wheels (combines forward+strafe without any speed loss).

    Args:
        direction: forward_left | forward_right | backward_left | backward_right
        speed: Motor speed 0–100.
        duration: Seconds to drive.
    """
    get_robot().diagonal(direction, speed, duration)
    return f"Diagonal {direction} — speed={speed}, duration={duration}s"


@mcp.tool()
def stop() -> str:
    """Immediately halt all robot motion."""
    get_robot().stop()
    return "Robot stopped"


# ═══════════════════════════════════════════════════════════════════════════════
# Sensor tools
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_distance() -> str:
    """Read the HC-SR04 ultrasonic sensor — returns distance to nearest obstacle in cm.

    The sensor is mounted on the servo head. Use set_servo() to aim it before
    reading (90° = straight ahead, 45° = front-left, 135° = front-right).

    Returns MAX_DISTANCE (300 cm) if no object is detected within range.

    IMPORTANT: Requires the firmware patch in firmware/ultrasonic_patch.md.
    Without the patch the robot will return no response and this tool will say so.
    """
    robot = get_robot()
    dist = robot.get_distance()
    if dist is None:
        return (
            "No response from ultrasonic sensor.\n"
            "Apply the 4-line firmware patch in firmware/ultrasonic_patch.md and re-upload the sketch."
        )
    label = "clear" if dist >= 290 else ("close!" if dist < 20 else "ok")
    return f"Distance: {dist:.1f} cm ({label})"


@mcp.tool()
def scan_distances() -> str:
    """Sweep the servo and read ultrasonic distance at left (45°), centre (90°), right (135°).

    Returns a summary of obstacles in all three directions.
    Useful before navigating to check which directions are clear.

    IMPORTANT: Requires the firmware patch in firmware/ultrasonic_patch.md.
    """
    robot = get_robot()
    results = {}

    for label, angle in [("left(45°)", 45), ("centre(90°)", 90), ("right(135°)", 135)]:
        robot.set_servo(angle)
        time.sleep(0.4)       # let servo settle
        dist = robot.get_distance()
        results[label] = f"{dist:.1f} cm" if dist is not None else "no data"

    robot.set_servo(90)       # return to centre
    lines = [f"  {k}: {v}" for k, v in results.items()]
    return "Scan results:\n" + "\n".join(lines)


@mcp.tool()
def get_battery() -> str:
    """Query the robot's battery voltage.

    Warn the user if voltage is below 6.5 V — low battery affects motor performance.
    """
    reading = get_robot().get_battery()
    if not reading:
        return "No battery response (robot may not support this query in current firmware)"
    try:
        volts = float(reading.replace("V", "").strip())
        status = "⚠ LOW — consider charging" if volts < 6.5 else "OK"
        return f"Battery: {volts:.2f} V ({status})"
    except ValueError:
        return f"Battery: {reading}"


# ═══════════════════════════════════════════════════════════════════════════════
# Peripheral tools
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def set_led(r: int, g: int, b: int) -> str:
    """Set the WS2812 RGB LED colour.

    Conventions:
      (0, 0, 255)   → working / moving
      (0, 255, 0)   → done / success
      (255, 0, 0)   → stopped / error
      (255, 128, 0) → warning
      (0, 0, 0)     → off / idle

    Args:
        r: Red 0–255.
        g: Green 0–255.
        b: Blue 0–255.
    """
    get_robot().set_led(r, g, b)
    return f"LED → RGB({r}, {g}, {b})"


@mcp.tool()
def beep(frequency: int = 1000) -> str:
    """Sound the buzzer for a short burst at the given frequency.

    Args:
        frequency: Hz. 400–800 = low beep, 1000–1500 = mid, 2000+ = high/alert.
    """
    get_robot().beep(frequency)
    return f"Beeped at {frequency} Hz"


@mcp.tool()
def set_servo(angle: int) -> str:
    """Rotate the camera/ultrasonic head servo to a target angle.

    The HC-SR04 ultrasonic sensor is mounted here, so aiming the servo
    lets you scan different directions before calling get_distance().

    Args:
        angle: 0–180 degrees. 90 = straight ahead (centre). 0 = full right, 180 = full left.
    """
    get_robot().set_servo(angle)
    return f"Servo → {angle}°"


@mcp.tool()
def wait(seconds: float) -> str:
    """Pause for a number of seconds (robot stays stopped).

    Args:
        seconds: How long to wait.
    """
    time.sleep(seconds)
    return f"Waited {seconds}s"
