# Firmware — Ultrasonic TCP Query Patch

The stock `06.2_Multi_Functional_Car` sketch uses the HC-SR04 sensor only for its
built-in autonomous obstacle-avoidance mode. This patch adds a `U\n` TCP command
so the Python MCP server can query distance on demand.

---

## TL;DR — patched sketch included

The ready-to-flash sketch (with this patch already applied) lives at:
```
firmware/06.2_Multi_Functional_Car/06.2_Multi_Functional_Car.ino
```
Just set your WiFi credentials, select **Raspberry Pi Pico W**, and upload.
You do **not** need to apply the patch manually if you use this copy.

---

## If you want to apply it to a fresh Freenove clone

### 1. Open the sketch

In Arduino IDE → **File → Open**, navigate to:
```
Mecanum_wheels/Sketches/06.2_Multi_Functional_Car/06.2_Multi_Functional_Car.ino
```

### 2. Find the WiFi receive loop

Search (Ctrl+F) for:
```cpp
String inputStringTemp = client.readStringUntil('\n');
```

You'll be inside a `while (client.connected())` block. Just after this line (and
before the call to `Get_Command(str)`), add:

```cpp
// ── Ultrasonic query: handle before Get_Command to avoid atoi(NULL) on a no-param command ──
if (inputStringTemp == "U") {
  float dist = Get_Sonar();
  client.print("U#" + String((int)dist) + "\n");
  continue;
}
```

> **Why before `Get_Command()`?**  
> `Get_Command` splits the string on `#` and calls `atoi` on each segment.
> A bare `"U"` with no `#` produces a null segment, which crashes `atoi`.
> Intercepting it first (and using `continue` to skip the rest of the loop body)
> avoids that entirely.

> **`Get_Sonar()`** is already declared in `Freenove_4WD_Car_For_Pico_W.h` and
> implemented in `Freenove_4WD_Car_For_Pico_W.cpp`. Returns distance in cm as a
> `float`; returns `MAX_DISTANCE` (300) if nothing is in range.

### 3. Upload

- Board: **Raspberry Pi Pico W**
- Confirm WiFi SSID/password are still correct
- Upload (Ctrl+U)

### 4. Verify

```python
from robot.controller import RobotController
with RobotController("YOUR_ROBOT_IP") as r:
    print(r.get_distance())   # e.g. 47.0
```

---

## Protocol

| Direction      | Message                   |
|----------------|---------------------------|
| Agent → Robot  | `U\n`                     |
| Robot → Agent  | `U#<distance_cm>\n`       |

Example: `U#47\n` = 47 cm to nearest obstacle.

The Python `get_distance()` method in `robot/controller.py` sends `U\n` and
parses the `U#<value>` response. If it times out, it returns `None` and the MCP
tool reports that the patch hasn't been applied.
