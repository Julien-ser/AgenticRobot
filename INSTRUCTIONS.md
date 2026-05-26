# Agentic Robot — Setup & Configuration Guide

Complete step-by-step guide: from unboxed hardware to Claude Code driving your robot.

---

## Table of Contents

1. [What You Need](#1-what-you-need)
2. [Robot Hardware Overview](#2-robot-hardware-overview)
3. [Install Arduino IDE & Board Support](#3-install-arduino-ide--board-support)
4. [Flash the WiFi Firmware](#4-flash-the-wifi-firmware)
5. [Apply the Ultrasonic Sensor Patch](#5-apply-the-ultrasonic-sensor-patch)
6. [Find the Robot's IP Address](#6-find-the-robots-ip-address)
7. [Set Up the Python Environment](#7-set-up-the-python-environment)
8. [Configure the .env File](#8-configure-the-env-file)
9. [Test the Hardware Connection](#9-test-the-hardware-connection)
10. [Enable the MCP Server in Claude Code](#10-enable-the-mcp-server-in-claude-code)
11. [Drive the Robot with Claude Code](#11-drive-the-robot-with-claude-code)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What You Need

### Hardware
- Freenove 4WD Car Kit for Raspberry Pi Pico W (assembled)
- Raspberry Pi Pico W (already soldered onto the car board)
- HC-SR04 ultrasonic sensor (mounted on the servo head)
- USB-A to Micro-USB cable (for flashing firmware)
- 4× AA batteries (or the included Li-ion pack)
- Your home WiFi network (2.4 GHz — Pico W does not support 5 GHz)

### Software
- [Arduino IDE 2.x](https://www.arduino.cc/en/software) — for flashing firmware
- Python 3.10+ — already installed on your machine
- This project's Python packages — installed in Step 7

### Reference
- GitHub firmware repo: https://github.com/Freenove/Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico
- Firmware folder used: `Mecanum_wheels/Sketches/06.2_Multi_Functional_Car/`

---

## 2. Robot Hardware Overview

```
         ┌──────────────────────────────┐
         │       Servo head             │
         │   [HC-SR04 ultrasonic]       │  ← distance sensor (TRIG=pin4, ECHO=pin5)
         └──────────┬───────────────────┘
                    │
┌───────────────────▼──────────────────────┐
│           Raspberry Pi Pico W            │
│  WiFi chip  GPIO  PWM  ADC  USB          │
│    TCP server port 4002                  │
└─┬──────┬──────┬──────┬────────────────┬─┘
  │      │      │      │                │
[FL]   [FR]  [BL]   [BR]         [WS2812 LED]
Mecanum wheels (4-motor independent drive)
```

**Key points:**
- The Pico W runs a **TCP server on port 4002**. All commands are plain text strings sent over WiFi.
- The **mecanum wheels** let the robot move in any direction without rotating first (strafe left/right, diagonal movement).
- The **ultrasonic sensor** sits on a servo so it can be aimed left, centre, or right.
- The **WS2812 RGB LED** is used for visual status feedback.

---

## 3. Install Arduino IDE & Board Support

### 3a. Install Arduino IDE
Download and install Arduino IDE 2.x from: https://www.arduino.cc/en/software

### 3b. Add Raspberry Pi Pico W board support

1. Open Arduino IDE → **File → Preferences**
2. In "Additional boards manager URLs", add:
   ```
   https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
   ```
3. Click OK.
4. Go to **Tools → Board → Boards Manager**
5. Search for `Raspberry Pi Pico` (by Earle F. Philhower)
6. Click **Install** (the package is ~200 MB — takes a few minutes)

### 3c. Install required libraries

In Arduino IDE → **Tools → Manage Libraries**, install:
- `Freenove_WS2812_Lib_for_PICO` (search "Freenove WS2812")

> The other required libraries (`Servo`, ultrasonic helpers) are included directly in the sketch folder — no extra install needed.

---

## 4. Flash the WiFi Firmware

### 4a. Open the sketch

The patched sketch is included in this repo. In Arduino IDE → **File → Open**, navigate to:
```
firmware/06.2_Multi_Functional_Car/06.2_Multi_Functional_Car.ino
```

> This is based on `06.2_Multi_Functional_Car` from the
> [Freenove repo](https://github.com/Freenove/Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico),
> with the ultrasonic TCP patch already applied (see `firmware/ultrasonic_patch.md`).

### 4b. Set your WiFi credentials

Near the top of the `.ino` file, find and edit these two lines:
```cpp
const char* ssid     = "YOUR_WIFI_NETWORK_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
```
Replace with your actual 2.4 GHz WiFi network name and password.

> ⚠️ The Pico W only connects to **2.4 GHz** networks. If your router has both 2.4 and 5 GHz on the same name (SSID), you may need to split them in your router settings, or temporarily disable 5 GHz.

### 4c. Select the board

**Tools → Board → Raspberry Pi RP2040 Boards → Raspberry Pi Pico W**

> Make sure you select **Pico W** (with WiFi), not plain Pico.

### 4d. Connect and upload

1. Hold the **BOOTSEL button** on the Pico W while plugging in the USB cable.
2. Release BOOTSEL after plugging in — the Pico appears as a USB drive.
3. In Arduino IDE, select the correct **Port** under **Tools → Port** (it may show as `UF2 Board` or `RPI-RP2`).
4. Click **Upload** (→ arrow button). Wait ~30 seconds.
5. The Pico will reboot automatically and attempt to connect to WiFi.

### 4e. Verify connection

Open **Tools → Serial Monitor** (baud rate: 115200). After a few seconds you should see something like:
```
Connecting to WiFi...
Connected! IP address: 192.168.1.42
TCP Server started on port 4002
```

Write down the IP address — you'll need it in Step 8.

---

## 5. Ultrasonic Sensor — Already Patched

The sketch at `firmware/06.2_Multi_Functional_Car/` already includes the TCP distance query patch — **no manual patching needed** if you flashed the included sketch.

The patch adds a `U\n` command so Python can query the HC-SR04 on demand:

| Direction     | Message              |
|---------------|----------------------|
| Agent → Robot | `U\n`                |
| Robot → Agent | `U#<distance_cm>\n`  |

### 5a. Verify the ultrasonic sensor

After flashing, open the Arduino Serial Monitor, type `U` and press Enter. You should see:
```
U#47
```
47 cm = sensor is responding. (300 = nothing detected within range.)

Or verify with Python after Step 9:

```bash
python -c "
from robot.controller import RobotController
import os; from dotenv import load_dotenv; load_dotenv()
with RobotController(os.getenv('ROBOT_IP')) as r:
    print('Distance:', r.get_distance(), 'cm')
"
```

> If you're starting from a fresh Freenove clone instead, see
> [`firmware/ultrasonic_patch.md`](firmware/ultrasonic_patch.md) for the exact lines to add.

---

## 6. Find the Robot's IP Address

You need the robot's IP address to connect to it. Three ways to find it:

### Option A — Serial Monitor (easiest)
After uploading, open **Tools → Serial Monitor**. The IP is printed on connection:
```
Connected! IP address: 192.168.1.42
```

### Option B — Router DHCP table
Log into your router admin panel (usually `192.168.1.1` or `192.168.0.1`) and look in the DHCP client list for a device named `PicoW` or similar.

### Option C — Freenove TCP App (Windows)
Download the Freenove Windows control app from the repo (`TCP/Application/windows/`). Launch it — it will scan and show the robot's IP when connected.

> 💡 **Tip:** Assign a static IP (DHCP reservation) in your router so the IP never changes. Look up your router model + "DHCP reservation" for instructions.

---

## 7. Set Up the Python Environment

Open a terminal (PowerShell, Command Prompt, or bash) and navigate to the project directory:

```bash
cd /path/to/AgenticRobot
```

Install the required packages:

```powershell
pip install -r requirements.txt
```

This installs:
- `mcp` — Model Context Protocol SDK (used by the Claude Code MCP server)
- `anthropic` — Anthropic Python SDK (used by the standalone agent fallback)
- `python-dotenv` — reads `.env` configuration files

---

## 8. Configure the .env File

Copy the example file:

```bash
# Linux / macOS
cp .env.example .env

# Windows PowerShell
copy .env.example .env
```

Open `.env` in any text editor and fill in:

```env
# Your robot's IP address (from Step 6)
ROBOT_IP=192.168.1.42

# Only needed if using the standalone agent.py (not needed for MCP / Claude Code)
ANTHROPIC_API_KEY=sk-ant-...
```

> ⚠️ Never commit `.env` to git — it's already in `.gitignore`.

---

## 9. Test the Hardware Connection

With the robot powered on and connected to WiFi, run the hardware test:

```bash
python examples/drive_test.py
```

This tests (in order):
1. **Battery level** — queries voltage; warns if below 6.5 V
2. **LED** — cycles Red → Green → Blue
3. **Buzzer** — two beeps
4. **Servo** — sweeps centre → left → right → centre
5. **Motors** — forward, backward, strafe left/right, rotate left/right (asks for confirmation first)

**Expected output:**
```
Connecting to robot at 192.168.1.42 …
✓ Connected to robot at 192.168.1.42:4002

[1/5] Battery check …
      Battery: 7.8V

[2/5] LED test: Red → Green → Blue …
[3/5] Buzzer beep …
[4/5] Servo sweep (centre → left → right → centre) …
[5/5] Movement test
      ⚠  Clear a 60 cm square of space around the robot.
      Press Enter to start movement test (Ctrl+C to skip) …

✓ All tests passed — robot is ready for agent control!
```

If you applied the ultrasonic patch, also verify it:

```bash
python -c "
from robot.controller import RobotController
import os; from dotenv import load_dotenv; load_dotenv()
with RobotController(os.getenv('ROBOT_IP')) as r:
    print('Distance:', r.get_distance(), 'cm')
"
```

---

## 10. Enable the MCP Server in Claude Code

The `.mcp.json` file at the vault root tells Claude Code about the `robot` MCP server. Claude Code reads this automatically — you just need to approve it.

### 10a. Restart or use /mcp

Either:
- **Restart Claude Code** — it will detect `.mcp.json` on startup and ask you to approve the `robot` server, **or**
- **Type `/mcp`** in Claude Code — you'll see a list of available MCP servers. Find `robot` and enable it.

### 10b. What happens when enabled

Claude Code starts a background process:
```
python -m robot_mcp
```
(from the `Projects/AgenticRobot/` directory)

This process:
- Reads `ROBOT_IP` from your `.env` file
- Waits for tool calls — it does **not** connect to the robot yet
- Connects to the robot's TCP socket on the **first tool call**

### 10c. Verify the server is running

Type `/mcp` in Claude Code. You should see `robot` listed as **connected** with a list of its tools:

```
robot (connected)
  ├─ move_forward
  ├─ move_backward
  ├─ strafe_left / strafe_right
  ├─ rotate_left / rotate_right
  ├─ move_diagonal
  ├─ stop
  ├─ get_distance
  ├─ scan_distances
  ├─ get_battery
  ├─ set_led
  ├─ beep
  ├─ set_servo
  └─ wait
```

---

## 11. Drive the Robot with Claude Code

Once the MCP server is connected, just talk to me naturally. I'll call the robot tools automatically. The robot **must be powered on and connected to WiFi** when you ask.

### Quick commands to try

```
"Check the robot battery"

"Drive forward for 2 seconds"

"Do a celebration spin"

"Scan for obstacles in all directions and tell me what you see"

"Drive in a square pattern"

"Strafe right 1 second, then come back"

"Keep going forward and stop if anything is closer than 25 cm"

"Set the LED to purple and beep twice"

"Drive diagonally forward-right at speed 40 for 1.5 seconds"
```

### What I do with sensor data

When you ask me to navigate, I'll:
1. Aim the servo to different angles
2. Read the ultrasonic distance at each angle
3. Choose the clearest direction
4. Drive that way — and stop or re-plan if I detect something close

### Standalone agent (alternative, no MCP needed)

If you don't want to use the MCP approach, the standalone agent works too:

```bash
# One-shot task
python -m agent.agent --task "Drive in a square pattern"

# Interactive REPL
python -m agent.agent
```

> This requires `ANTHROPIC_API_KEY` to be set in your `.env`.

---

## 12. Troubleshooting

### "Could not connect to 192.168.x.x:4002"
- Is the robot powered on? Check the power switch.
- Is it connected to WiFi? Open Serial Monitor and look for the IP print.
- Is the IP in `.env` correct? Double-check against router DHCP table.
- Is your PC on the same WiFi network as the robot?
- Did you flash the correct sketch (`06.2_Multi_Functional_Car`)? Plain Pico sketches don't have WiFi.

### "ROBOT_IP not configured"
- You haven't created `.env` yet. Run: `copy .env.example .env` and fill in the IP.

### "MCP robot server shows as failed / not connected"
- The `mcp` package isn't installed: `pip install mcp`
- Check the path in `.mcp.json` — the `cwd` must point to the `AgenticRobot` folder exactly.
- Open a terminal and run `python -m robot_mcp` manually — any import errors will show here.

### "get_distance() returns None"
- The ultrasonic firmware patch hasn't been applied yet — follow Step 5.
- Re-upload the sketch and try again.

### Motors not responding / robot drives erratically
- Check battery level — low batteries cause erratic PWM behavior.
- Make sure you're in manual mode (Mode 0). If the robot was in autonomous mode, it ignores motor commands. Send: `C#0\n`.

### Robot connects but LED/buzzer don't respond
- Some commands need mode 1 for the LED. The Python SDK handles this automatically (mode=1 is default). If issues persist, power-cycle the robot.

### WiFi not connecting (stuck on "Connecting to WiFi...")
- Confirm the SSID and password are correct (case-sensitive).
- Make sure your network is 2.4 GHz. The Pico W does not support 5 GHz.
- Some networks block new devices — check your router's MAC filter settings.

### Arduino IDE doesn't see the Pico W port
- Hold BOOTSEL while plugging in USB — the Pico appears as a USB mass-storage drive (`RPI-RP2`).
- Install the RP2040 board package if you haven't (Step 3b).
- On Windows: Device Manager → look for "RP2 Boot" under ports.

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Flash firmware | Arduino IDE → upload `06.2_Multi_Functional_Car.ino` |
| Test hardware | `python examples/drive_test.py` |
| Start MCP server | Claude Code → `/mcp` → enable `robot` |
| Standalone agent | `python -m agent.agent --task "..."` |
| Find robot IP | Serial Monitor or router DHCP table |
| Robot TCP port | `4002` |
| Default speed range | `30–50` (indoor), `60–80` (open space) |
| Battery warning | < 6.5 V → charge soon |
| Ultrasonic max range | 300 cm (returns 300 if nothing detected) |

---

*For TCP protocol details and extension ideas, see the [Freenove firmware repo](https://github.com/Freenove/Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico).*
