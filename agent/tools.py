"""
Claude tool definitions for the Freenove 4WD Mecanum Robot.
Passed directly to the Anthropic API as the `tools` parameter.
"""

ROBOT_TOOLS = [
    {
        "name": "move_forward",
        "description": "Drive the robot straight forward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed":    {"type": "integer", "description": "Speed 0–100 (default 50)", "default": 50},
                "duration": {"type": "number",  "description": "Seconds to move (default 1.0)", "default": 1.0},
            },
        },
    },
    {
        "name": "move_backward",
        "description": "Drive the robot straight backward.",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed":    {"type": "integer", "default": 50},
                "duration": {"type": "number",  "default": 1.0},
            },
        },
    },
    {
        "name": "strafe_left",
        "description": "Slide the robot directly left without turning (mecanum wheel strafing).",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed":    {"type": "integer", "default": 50},
                "duration": {"type": "number",  "default": 1.0},
            },
        },
    },
    {
        "name": "strafe_right",
        "description": "Slide the robot directly right without turning (mecanum wheel strafing).",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed":    {"type": "integer", "default": 50},
                "duration": {"type": "number",  "default": 1.0},
            },
        },
    },
    {
        "name": "rotate_left",
        "description": "Spin the robot counter-clockwise in place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed":    {"type": "integer", "default": 50},
                "duration": {"type": "number",  "description": "Seconds to spin (default 0.5)", "default": 0.5},
            },
        },
    },
    {
        "name": "rotate_right",
        "description": "Spin the robot clockwise in place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed":    {"type": "integer", "default": 50},
                "duration": {"type": "number",  "default": 0.5},
            },
        },
    },
    {
        "name": "move_diagonal",
        "description": "Move the robot diagonally using mecanum wheels.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["forward_left", "forward_right", "backward_left", "backward_right"],
                    "description": "Diagonal direction of travel",
                },
                "speed":    {"type": "integer", "default": 50},
                "duration": {"type": "number",  "default": 1.0},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "stop",
        "description": "Immediately halt all robot motion.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_led",
        "description": "Set the robot's WS2812 RGB LED to a colour. Use this to signal state (e.g. blue=thinking, green=done, red=error).",
        "input_schema": {
            "type": "object",
            "properties": {
                "r": {"type": "integer", "description": "Red 0–255"},
                "g": {"type": "integer", "description": "Green 0–255"},
                "b": {"type": "integer", "description": "Blue 0–255"},
            },
            "required": ["r", "g", "b"],
        },
    },
    {
        "name": "beep",
        "description": "Sound the robot's buzzer briefly.",
        "input_schema": {
            "type": "object",
            "properties": {
                "frequency": {"type": "integer", "description": "Buzzer frequency in Hz (default 1000)", "default": 1000},
            },
        },
    },
    {
        "name": "set_servo",
        "description": "Rotate the robot's camera/head servo to a given angle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "angle": {"type": "integer", "description": "Servo angle 0–180° (90 = centre)"},
            },
            "required": ["angle"],
        },
    },
    {
        "name": "get_battery",
        "description": "Query the robot's current battery voltage. Call this if the user asks about power or if you're unsure whether there's enough charge to complete a task.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "wait",
        "description": "Pause for a number of seconds without moving. Robot stays stopped.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "number", "description": "Duration to pause"},
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "task_complete",
        "description": "Signal that the assigned task has been successfully completed. Always call this when you are done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "One sentence describing what was accomplished"},
            },
            "required": ["summary"],
        },
    },
]
