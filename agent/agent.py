"""
Agentic robot controller powered by Claude tool_use.

The agent receives a natural-language task, reasons step-by-step, and calls
robot tools (move, rotate, LED, beep, …) until the task is complete.

Usage:
    python -m agent.agent --ip 192.168.x.x --task "Drive in a square"
    python -m agent.agent --ip 192.168.x.x          # interactive mode

Environment variables (.env):
    ROBOT_IP          - IP address of the Pico W on your network
    ANTHROPIC_API_KEY - Your Anthropic API key
"""

import os
import time
import argparse

import anthropic
from dotenv import load_dotenv

from robot.controller import RobotController
from .tools import ROBOT_TOOLS

load_dotenv()

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an agentic controller for a Freenove 4WD Mecanum Wheel Robot Car.
You receive high-level tasks in plain English and execute them by calling the available robot tools.

=== Robot Capabilities ===
• Mecanum wheels — move in any direction without turning first (forward, backward, strafe, diagonal)
• Rotate in place clockwise or counter-clockwise
• WS2812 RGB LED — use for status: blue=working, green=done, red=error/stop
• Buzzer — brief audio feedback
• Servo — camera/head angle (0–180°, 90=centre)
• Battery query — check voltage (warn if < 6.5 V)

=== Guidelines ===
• Speed 30–50 is safe indoors; 60–80 for faster open-space moves
• Always call stop() before a sharp direction change if you didn't use the duration parameter
• Signal transitions with set_led() and beep() so a human watching knows what's happening
• Prefer using the duration parameter directly over issuing a separate stop() call
• Think out loud (text block) before each tool call, especially for multi-step plans
• When the full task is done, call task_complete() with a one-line summary
• If battery is low (< 6.5 V), stop immediately and report
"""

# ── Tool executor ─────────────────────────────────────────────────────────────

def execute_tool(robot: RobotController, name: str, inputs: dict) -> str:
    """Dispatch a Claude tool_use call to the actual robot and return a result string."""
    s   = inputs.get("speed", 50)
    dur = inputs.get("duration", None)

    print(f"  ↳ {name}({', '.join(f'{k}={v}' for k, v in inputs.items())})")

    try:
        match name:
            case "move_forward":
                robot.forward(s, dur or 1.0)
                return f"Moved forward — speed={s}, duration={dur or 1.0}s"

            case "move_backward":
                robot.backward(s, dur or 1.0)
                return "Moved backward"

            case "strafe_left":
                robot.strafe_left(s, dur or 1.0)
                return "Strafed left"

            case "strafe_right":
                robot.strafe_right(s, dur or 1.0)
                return "Strafed right"

            case "rotate_left":
                robot.rotate_left(s, dur or 0.5)
                return "Rotated left (CCW)"

            case "rotate_right":
                robot.rotate_right(s, dur or 0.5)
                return "Rotated right (CW)"

            case "move_diagonal":
                robot.diagonal(inputs["direction"], s, dur or 1.0)
                return f"Moved diagonally {inputs['direction']}"

            case "stop":
                robot.stop()
                return "Stopped"

            case "set_led":
                robot.set_led(inputs["r"], inputs["g"], inputs["b"])
                return f"LED → RGB({inputs['r']}, {inputs['g']}, {inputs['b']})"

            case "beep":
                robot.beep(inputs.get("frequency", 1000))
                return "Beeped"

            case "set_servo":
                robot.set_servo(inputs["angle"])
                return f"Servo → {inputs['angle']}°"

            case "get_battery":
                reading = robot.get_battery()
                return f"Battery: {reading}"

            case "wait":
                time.sleep(inputs["seconds"])
                return f"Waited {inputs['seconds']}s"

            case "task_complete":
                return f"COMPLETE: {inputs['summary']}"

            case _:
                return f"Unknown tool: {name}"

    except Exception as exc:
        return f"Error in {name}: {exc}"


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(robot_ip: str, task: str, max_turns: int = 40):
    """Connect to the robot, hand the task to Claude, execute tools until done."""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    print(f"\n{'═'*60}")
    print(f"  Task : {task}")
    print(f"  Robot: {robot_ip}:4002")
    print(f"{'═'*60}\n")

    with RobotController(robot_ip) as robot:
        # Announce start
        robot.set_led(0, 0, 255)   # blue = agent active
        robot.beep(800)

        messages = [{"role": "user", "content": task}]

        for turn in range(max_turns):
            print(f"[Turn {turn + 1}]")

            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=ROBOT_TOOLS,
                messages=messages,
            )

            # Append assistant turn
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            task_done    = False

            for block in response.content:
                if block.type == "text" and block.text.strip():
                    print(f"  Claude: {block.text.strip()}")

                elif block.type == "tool_use":
                    result = execute_tool(robot, block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result,
                    })
                    if block.name == "task_complete":
                        print(f"\n  ✓ {result}")
                        task_done = True

            # Signal completion
            if task_done:
                robot.set_led(0, 255, 0)   # green = done
                robot.beep(1200)
                time.sleep(0.1)
                robot.beep(1200)
                break

            # Natural end with no tool calls
            if response.stop_reason == "end_turn" and not tool_results:
                print("  Agent ended turn without calling task_complete.")
                break

            # Feed tool results back
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        else:
            print("⚠  Max turns reached — stopping robot.")
            robot.stop()
            robot.set_led(255, 50, 0)   # orange = timeout


# ── Interactive REPL ──────────────────────────────────────────────────────────

def interactive_mode(robot_ip: str):
    """Simple REPL: type a task, watch the robot execute it."""
    print("Agentic Robot — Interactive Mode")
    print("Enter a task and press Enter. Type 'quit' to exit.\n")

    while True:
        try:
            task = input("Task> ").strip()
            if task.lower() in ("quit", "exit", "q"):
                break
            if task:
                run_agent(robot_ip, task)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude-powered Freenove Robot Agent")
    parser.add_argument("--ip",       default=os.getenv("ROBOT_IP"),
                        help="Robot IP address (or set ROBOT_IP env var)")
    parser.add_argument("--task",     default=None,
                        help="Task to execute; omit for interactive mode")
    parser.add_argument("--max-iter", type=int, default=40,
                        help="Maximum agent turns (default 40)")
    args = parser.parse_args()

    if not args.ip:
        parser.error("Provide --ip or set ROBOT_IP in .env")

    if args.task:
        run_agent(args.ip, args.task, args.max_iter)
    else:
        interactive_mode(args.ip)
