"""
TCP command constants for Freenove 4WD Mecanum Car Kit.
Matches the Command.py from the official Freenove TCP client.
"""

# ── Command characters ──────────────────────────────────────────────────────
CMD_MOTOR     = "M"   # 2-wheel drive (not used for mecanum)
CMD_M_MOTOR   = "N"   # Mecanum 4-wheel move: N#angle#speed#rotate#0\n
CMD_CAR_ROTATE = "O"  # Rotate in place:      O#0#0#rotate#0\n
CMD_LED       = "L"   # WS2812 LED:           L#mode#r#g#b\n
CMD_LED_MOD   = "D"   # LED mode
CMD_SERVO     = "S"   # Servo angle:          S#angle\n
CMD_BUZZER    = "B"   # Buzzer:               B#freq\n
CMD_POWER     = "P"   # Battery query:        P\n
CMD_MATRIX_MOD = "T"  # LED matrix mode
CMD_CAR_MODE  = "C"   # Car mode:             C#mode\n
CMD_ULTRASONIC = "U"  # Distance query:       U\n  → U#<cm>\n  (requires firmware patch)
CMD_OLED       = "W"  # OLED display:         W#<text>\n  (pipe '|' = newline on screen)

INTERVAL_CHAR = "#"
END_CHAR = "\n"

# ── Direction angles (degrees) ──────────────────────────────────────────────
FORWARD              = 0
BACKWARD             = 180
STRAFE_LEFT          = 90
STRAFE_RIGHT         = -90
DIAGONAL_FWD_LEFT    = 45
DIAGONAL_FWD_RIGHT   = -45
DIAGONAL_BACK_LEFT   = 135
DIAGONAL_BACK_RIGHT  = -135

# ── Car operating modes ──────────────────────────────────────────────────────
MODE_MANUAL       = 0
MODE_LIGHT_FOLLOW = 1
MODE_LINE_TRACK   = 2
MODE_ULTRASONIC   = 3
MODE_ROTATE       = 4
