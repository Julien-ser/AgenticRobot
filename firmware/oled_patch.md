# Firmware — 0.96″ SSD1306 OLED Patch

Adds a 128×64 OLED display wired to the Pico W over I2C.  
New TCP command: `W#<text>\n` — display a message on the screen.

---

## Wiring

| OLED pin | Connect to         | Board label | GP# | I2C role |
|----------|--------------------|-------------|-----|----------|
| GND      | Robot GND          | GND         | —   | —        |
| VCC      | Buck converter out | —           | —   | 3.3 V    |
| SCL      | Robot SCL          | **[1]**     | GP1 | I2C0 SCL |
| SDA      | Robot SDA          | **[0]**     | GP0 | I2C0 SDA |

> **Why [0]/[1] and not [17]/[22]?**
> GP17 is I2C0 SCL and GP22 is I2C1 SDA — they belong to **different I2C
> peripherals** on the RP2040. arduino-pico won't let you pair them on the
> same `Wire` instance. Software bit-bang I2C would technically work on them,
> but GP0+GP1 are the RP2040's native I2C0 default pair (no pin remapping
> needed at all) and both are confirmed free on the Freenove board.

---

## Required Arduino Libraries

Install both from **Arduino IDE → Library Manager** before compiling:

1. **Adafruit SSD1306** — search `SSD1306` → install "Adafruit SSD1306"
2. **Adafruit GFX Library** — installed automatically as a dependency

---

## TL;DR — patch summary (3 sections)

1. Add `#include` lines and a global `display` object at the top of the `.ino`
2. Initialize I2C + display in `setup()`
3. Add a `W#` handler in the TCP receive loop (before `Get_Command()`)

---

## Step-by-step patch

### 1. Add includes and globals

At the **very top** of `06.2_Multi_Functional_Car.ino`, after the existing
`#include` block, add:

```cpp
// ── 0.96″ OLED (SSD1306 over I2C0, default pins) ─────────────────────────────
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// GP0 and GP1 are the RP2040's default I2C0 pins — no remapping needed.
// Both are free (unused) on the Freenove 4WD Car board.
// Board labels: [0] = SDA, [1] = SCL
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_RESET     -1    // no reset pin wired
#define OLED_I2C_ADDR 0x3C   // default for most 0.96″ modules; try 0x3D if blank

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
// ─────────────────────────────────────────────────────────────────────────────
```

### 2. Initialize in `setup()`

Inside `setup()`, **before** `server.begin()` (or anywhere in setup before the
main loop):

```cpp
  // ── OLED init (Wire = I2C0, default GP0+GP1 — no pin remapping needed) ──────
  Wire.begin();
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
    // OLED not found — continue without it (don't hang the robot)
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("AgenticRobot");
    display.println("Ready.");
    display.display();
  }
  // ──────────────────────────────────────────────────────────────────────────
```

### 3. Add the `W#` TCP handler

In the `while (client.connected())` loop, find the same line you used for the
ultrasonic patch:

```cpp
String inputStringTemp = client.readStringUntil('\n');
```

Just **after** the ultrasonic handler (or after the `inputStringTemp =` line if
you haven't applied the ultrasonic patch), add:

```cpp
// ── OLED display command: W#<text>\n  (pipe '|' = newline on screen) ─────────
if (inputStringTemp.startsWith("W#")) {
    String msg = inputStringTemp.substring(2);  // strip "W#"
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    // Replace pipe chars with real newlines for multi-line messages
    msg.replace("|", "\n");
    display.println(msg);
    display.display();
    continue;
}
// ─────────────────────────────────────────────────────────────────────────────
```

### 4. Upload

- Board: **Raspberry Pi Pico W**
- Confirm WiFi SSID/password are correct
- Upload (Ctrl+U)
- The display should show **"AgenticRobot / Ready."** on boot

---

## Protocol

| Direction       | Message                              |
|-----------------|--------------------------------------|
| Agent → Robot   | `W#<text>\n`                         |
| (no reply)      | —                                    |
| Multi-line      | `W#Line 1\|Line 2\|Line 3\n`         |

**Text capacity at size-1 (6×8 px font):** 21 chars × 8 lines = 168 chars max.

---

## Verify

```python
from robot.controller import RobotController

with RobotController("YOUR_ROBOT_IP") as r:
    r.display_text("Hello from\nClaude Code!")
```

Or via Claude Code once the MCP server is running:

```
"Show 'Obstacle ahead!' on the robot's screen"
```

---

## Address troubleshooting

If the display stays blank after upload:

```cpp
// Scan for the I2C address — add temporarily to setup():
for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
        Serial.printf("I2C device at 0x%02X\n", addr);
    }
}
```

Most 0.96″ modules are `0x3C`; a minority ship as `0x3D`.
