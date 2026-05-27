"""
High-level robot controller for the Freenove 4WD Mecanum Car.

Speed range: 0–100 (the Pico firmware normalises this to PWM internally).
Angle convention: 0=forward, 90=left strafe, 180=backward, -90=right strafe.
"""

import time
from .client import RobotClient
from .commands import (
    CMD_M_MOTOR, CMD_CAR_ROTATE, CMD_LED, CMD_SERVO,
    CMD_BUZZER, CMD_POWER, CMD_CAR_MODE, CMD_ULTRASONIC, CMD_OLED,
    INTERVAL_CHAR, END_CHAR,
    FORWARD, BACKWARD, STRAFE_LEFT, STRAFE_RIGHT,
    DIAGONAL_FWD_LEFT, DIAGONAL_FWD_RIGHT,
    DIAGONAL_BACK_LEFT, DIAGONAL_BACK_RIGHT,
)


class RobotController:
    """High-level interface. Translates intuitive calls into TCP protocol messages."""

    def __init__(self, host: str, port: int = 4002):
        self.client = RobotClient(host, port)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def connect(self) -> "RobotController":
        self.client.connect()
        return self

    def disconnect(self):
        self.stop()
        self.client.disconnect()

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.disconnect()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _mecanum(self, angle: int, speed: int, rotate: int = 0):
        """Send a raw mecanum drive command."""
        cmd = f"{CMD_M_MOTOR}{INTERVAL_CHAR}{angle}{INTERVAL_CHAR}{speed}{INTERVAL_CHAR}{rotate}{INTERVAL_CHAR}0{END_CHAR}"
        self.client.send(cmd)

    def _timed(self, fn, duration: float | None):
        """Call fn(), wait duration seconds, then stop."""
        fn()
        if duration is not None:
            time.sleep(duration)
            self.stop()

    # ── Motion ───────────────────────────────────────────────────────────────

    def move(self, angle: int, speed: int = 50, duration: float = None):
        """Move in any direction. angle=0 is forward, positive angles go left."""
        self._timed(lambda: self._mecanum(angle, speed), duration)

    def forward(self, speed: int = 50, duration: float = None):
        self.move(FORWARD, speed, duration)

    def backward(self, speed: int = 50, duration: float = None):
        self.move(BACKWARD, speed, duration)

    def strafe_left(self, speed: int = 50, duration: float = None):
        """Slide directly left without yawing (mecanum only)."""
        self.move(STRAFE_LEFT, speed, duration)

    def strafe_right(self, speed: int = 50, duration: float = None):
        """Slide directly right without yawing (mecanum only)."""
        self.move(STRAFE_RIGHT, speed, duration)

    def diagonal(self, direction: str, speed: int = 50, duration: float = None):
        """Move diagonally. direction ∈ {forward_left, forward_right, backward_left, backward_right}."""
        angles = {
            "forward_left":   DIAGONAL_FWD_LEFT,
            "forward_right":  DIAGONAL_FWD_RIGHT,
            "backward_left":  DIAGONAL_BACK_LEFT,
            "backward_right": DIAGONAL_BACK_RIGHT,
        }
        self.move(angles[direction], speed, duration)

    def rotate_left(self, speed: int = 50, duration: float = None):
        """Spin counter-clockwise in place."""
        cmd = f"{CMD_CAR_ROTATE}{INTERVAL_CHAR}0{INTERVAL_CHAR}0{INTERVAL_CHAR}{speed}{INTERVAL_CHAR}0{END_CHAR}"
        self._timed(lambda: self.client.send(cmd), duration)

    def rotate_right(self, speed: int = 50, duration: float = None):
        """Spin clockwise in place."""
        cmd = f"{CMD_CAR_ROTATE}{INTERVAL_CHAR}0{INTERVAL_CHAR}0{INTERVAL_CHAR}{-speed}{INTERVAL_CHAR}0{END_CHAR}"
        self._timed(lambda: self.client.send(cmd), duration)

    def stop(self):
        """Immediately stop all motion."""
        self._mecanum(0, 0, 0)

    # ── Peripherals ──────────────────────────────────────────────────────────

    def set_servo(self, angle: int):
        """Rotate the camera/head servo to angle (0–180°, 90=centre)."""
        angle = max(0, min(180, angle))
        self.client.send(f"{CMD_SERVO}{INTERVAL_CHAR}{angle}{END_CHAR}")

    def set_led(self, r: int, g: int, b: int, mode: int = 1):
        """Set the WS2812 RGB LED. r/g/b ∈ 0–255."""
        self.client.send(f"{CMD_LED}{INTERVAL_CHAR}{mode}{INTERVAL_CHAR}{r}{INTERVAL_CHAR}{g}{INTERVAL_CHAR}{b}{END_CHAR}")

    def led_off(self):
        self.set_led(0, 0, 0, 0)

    def beep(self, frequency: int = 1000):
        """Sound the buzzer at the given Hz."""
        self.client.send(f"{CMD_BUZZER}{INTERVAL_CHAR}{frequency}{END_CHAR}")

    def get_battery(self) -> str:
        """Query battery voltage. Returns the raw response string from the robot."""
        return self.client.send_and_receive(f"{CMD_POWER}{END_CHAR}", expect_prefix="P#")

    def get_distance(self) -> float | None:
        """Query the HC-SR04 ultrasonic sensor distance in centimetres.

        Requires the firmware patch (firmware/ultrasonic_patch.md) that adds the
        'U' command handler to 06.2_Multi_Functional_Car.ino.

        Returns distance in cm (300.0 = nothing in range), or None if the
        firmware doesn't support the command yet.
        """
        response = self.client.send_and_receive(f"{CMD_ULTRASONIC}{END_CHAR}", expect_prefix="U#")
        if response.startswith("U#"):
            try:
                return float(response.split("#")[1])
            except (IndexError, ValueError):
                pass
        return None

    def display_text(self, text: str):
        """Send text to the 0.96″ SSD1306 OLED display (firmware/oled_patch.md required).

        Use \\n for line breaks — they are converted to '|' in the wire protocol
        and re-expanded to newlines by the firmware handler.

        Text capacity at default size-1 font: 21 chars × 8 lines.
        """
        wire_text = text.replace("\n", "|").strip()
        self.client.send(f"{CMD_OLED}{INTERVAL_CHAR}{wire_text}{END_CHAR}")

    def set_mode(self, mode: int):
        """Switch operating mode (0=manual, 1=light-follow, 2=line-track, 3=sonar)."""
        self.client.send(f"{CMD_CAR_MODE}{INTERVAL_CHAR}{mode}{END_CHAR}")
