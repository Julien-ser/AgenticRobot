# AgenticRobot 🤖

Control a **Freenove 4WD Mecanum Wheel Robot Car** with natural-language commands — powered by Claude via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).

Talk to Claude Code and it drives the robot. No app, no joystick — just describe what you want:

```
"Drive in a square pattern"
"Scan for obstacles and find the clearest direction"
"Do a celebration spin, flash the LED green, and beep twice"
"Keep moving forward and stop if anything is closer than 25 cm"
```

---

## How It Works

```
You (Claude Code)  →  MCP tool call  →  robot_mcp server  →  TCP command  →  Pico W  →  Robot
```

1. Claude Code connects to the `robot_mcp` server (started automatically via `.mcp.json`).
2. You describe a task in plain English; Claude calls tools like `move_forward`, `scan_distances`, `set_led`.
3. Each tool call sends a plain-text TCP command to the Pico W on **port 4002**.
4. Tool results flow back to Claude, which adapts and continues until the task is complete.

There's also a **standalone agent** (`agent/`) that uses the Anthropic API directly — no Claude Code needed.

---

## What Can It Do?

The robot can sweep its ultrasonic sensor head and build a live obstacle map:

![Robot obstacle radar — 20–140° sweep showing distances at each angle](docs/robot_radar.png)

*Above: `scan_distances` result visualised — the servo sweeps from 20° to 140° while Claude reads HC-SR04 distances. Claude uses this to plan its next move.*

---

## Hardware

- **[Freenove 4WD Car Kit for Raspberry Pi Pico W](https://github.com/Freenove/Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico)**
  - Raspberry Pi Pico W (on-board WiFi)
  - 4× mecanum wheels (strafe in any direction without rotating)
  - HC-SR04 ultrasonic sensor on a servo head (aimed left/centre/right)
  - WS2812 RGB LED + buzzer

---

## Quick Start

### 1. Flash the firmware

The patched sketch is included in this repo at:
```
firmware/06.2_Multi_Functional_Car/06.2_Multi_Functional_Car.ino
```

Open it in **Arduino IDE**, fill in your WiFi credentials near the top:
```cpp
const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

Select **Raspberry Pi Pico W** as the board and upload.

> ⚠️ The Pico W only connects to **2.4 GHz** networks.

This sketch is based on [`06.2_Multi_Functional_Car`](https://github.com/Freenove/Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico) from the Freenove repo, with one addition: a `U\n` TCP command that returns the HC-SR04 distance reading on demand. See [`firmware/ultrasonic_patch.md`](firmware/ultrasonic_patch.md) for the patch details if you want to apply it to a fresh Freenove clone instead.

### 3. Find the robot's IP

Power on the robot. Check your router's DHCP table, or read it from the Arduino IDE Serial Monitor at 115200 baud:
```
Connected! IP address: 192.168.1.42
TCP Server started on port 4002
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure `.env`

```bash
cp .env.example .env
# Edit .env — set ROBOT_IP and (if using standalone agent) ANTHROPIC_API_KEY
```

### 6. Test the hardware

```bash
python examples/drive_test.py
```

Tests: battery → LED (R/G/B) → buzzer → servo sweep → motors. No API key needed.

### 7a. Use via Claude Code (MCP — recommended)

Add the MCP server to your Claude Code config (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "robot": {
      "command": "python",
      "args": ["-m", "robot_mcp"],
      "cwd": "/path/to/AgenticRobot"
    }
  }
}
```

Then just talk to Claude Code naturally — it will call the robot tools automatically.

### 7b. Use the standalone agent

```bash
python -m agent.agent --task "Drive in a square pattern"
python -m agent.agent          # interactive REPL
```

Requires `ANTHROPIC_API_KEY` in `.env`.

---

## Available Tools

| Tool | Description |
|------|-------------|
| `move_forward` / `move_backward` | Drive straight (speed 0–100, duration in seconds) |
| `strafe_left` / `strafe_right` | Slide sideways without yawing (mecanum only) |
| `rotate_left` / `rotate_right` | Spin in place |
| `move_diagonal` | Diagonal movement (forward_left, forward_right, …) |
| `stop` | Emergency stop |
| `get_distance` | HC-SR04 distance reading in cm (requires firmware patch) |
| `scan_distances` | Sweep servo and read distance at 45°, 90°, 135° |
| `get_battery` | Query voltage (warns if < 6.5 V) |
| `set_led` | WS2812 RGB colour |
| `beep` | Buzzer at given Hz |
| `set_servo` | Aim the head servo (0–180°, 90 = straight ahead) |
| `wait` | Pause for N seconds |

---

## Project Layout

```
robot/              ← TCP SDK (no AI dependency)
  commands.py       ← protocol constants
  client.py         ← raw socket I/O
  controller.py     ← high-level API

robot_mcp/          ← MCP server (Claude Code integration)
  server.py         ← FastMCP tool definitions
  __main__.py       ← entry point: python -m robot_mcp

agent/              ← Standalone Claude agent (no MCP needed)
  tools.py          ← tool definitions for the Anthropic API
  agent.py          ← agent loop + tool executor

firmware/
  ultrasonic_patch.md  ← 4-line patch to add TCP distance query

examples/
  drive_test.py     ← hardware connectivity test (no API key)

docs/
  robot_radar.png   ← example obstacle radar visualisation
```

---

## Firmware & Attribution

The robot firmware is from **[Freenove's open-source kit](https://github.com/Freenove/Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico)** — specifically sketch `06.2_Multi_Functional_Car`, which runs a TCP server on the Pico W and handles motor, servo, LED, and buzzer commands.

This project adds:
- A Python TCP SDK (`robot/`) that wraps the Freenove protocol
- An MCP server (`robot_mcp/`) exposing all robot functions as Claude tools
- A standalone agentic loop (`agent/`) using the Anthropic API directly
- A [4-line firmware patch](firmware/ultrasonic_patch.md) to expose the ultrasonic sensor over TCP

The Freenove firmware repo is **not bundled here** — clone it separately from the link above and flash `06.2_Multi_Functional_Car.ino`.

---

## Detailed Setup Guide

See [`INSTRUCTIONS.md`](INSTRUCTIONS.md) for a step-by-step walkthrough: Arduino IDE setup, board support installation, firmware flashing, IP discovery, MCP configuration, and troubleshooting.
