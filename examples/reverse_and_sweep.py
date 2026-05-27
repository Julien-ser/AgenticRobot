"""
Reverse-until-close + full servo sweep — standalone example.

Replicates the agentic session described in the README "Sample Session":

  Phase 1 — Move backward in 0.5 s increments until the ultrasonic sensor
             reads < 10 cm, logging every step to the OLED display.
             The display fills line-by-line (8 lines max); once full it
             scrolls row-by-row (oldest line dropped, new line appended).

  Phase 2 — Sweep the servo from 20° to 140° in 10° steps, reading the
             HC-SR04 distance at every angle and logging each result to
             the rolling OLED display.

  Plot     — Save a dual-panel matplotlib figure (polar + bar) of the
             sweep data to  examples/servo_sweep_output.png.

Requirements:
  pip install -r requirements.txt          (robot SDK + matplotlib + numpy)
  Firmware patches:
    firmware/ultrasonic_patch.md           (adds 'U' TCP command)
    firmware/oled_patch.md                 (adds 'O' TCP command for OLED)

Usage:
    python examples/reverse_and_sweep.py --ip 192.168.x.x
    python examples/reverse_and_sweep.py          # reads ROBOT_IP from .env
"""

import argparse
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from robot.controller import RobotController

load_dotenv()

# ── OLED display buffer ───────────────────────────────────────────────────────
# 128×64 px screen, size-1 font = 21 chars × 8 lines.
# We keep a rolling 8-line buffer; new lines push old ones off the top.

MAX_LINES = 8
_display_buf: list[str] = []


def oled(robot: RobotController, line: str):
    """Append one line to the rolling OLED buffer and push it to the screen."""
    global _display_buf
    _display_buf.append(line[:21])          # hard-clip to 21 chars
    if len(_display_buf) > MAX_LINES:
        _display_buf = _display_buf[-MAX_LINES:]
    robot.display_text("\n".join(_display_buf))
    print(f"  OLED: {line}")


# ── Phase 1: reverse until distance < STOP_CM ────────────────────────────────

STOP_CM    = 10.0
MOVE_SPEED = 40
MOVE_DUR   = 0.5   # seconds per backward burst


def phase1_reverse(robot: RobotController) -> float:
    """Reverse in 0.5 s bursts until distance < STOP_CM. Returns final distance."""
    oled(robot, "=== ROBOT MISSION ===")
    oled(robot, "Phase 1: Reverse")
    oled(robot, f"until dist < {STOP_CM:.0f}cm")
    oled(robot, "--------------------")
    oled(robot, "Checking dist...")

    move_num = 0
    while True:
        dist = robot.get_distance()
        if dist is None:
            raise RuntimeError(
                "No distance reading — is the ultrasonic firmware patch applied?\n"
                "See firmware/ultrasonic_patch.md"
            )

        oled(robot, f"Dist: {dist:.1f}cm {'STOP!' if dist < STOP_CM else f'>= {STOP_CM:.0f}cm'}")
        print(f"  [{move_num}] distance = {dist:.1f} cm")

        if dist < STOP_CM:
            robot.stop()
            print(f"  → Stopped at {dist:.1f} cm after {move_num} move(s)")
            return dist

        move_num += 1
        oled(robot, f"Move back #{move_num} ({MOVE_DUR}s)")
        robot.backward(MOVE_SPEED, MOVE_DUR)

    return dist  # unreachable


# ── Phase 2: servo sweep 20°→140° ────────────────────────────────────────────

SWEEP_ANGLES = list(range(20, 141, 10))   # [20, 30, 40, … 140]
SERVO_SETTLE = 0.25                        # seconds to let servo reach angle


def phase2_sweep(robot: RobotController) -> dict[int, float]:
    """Sweep servo from 20° to 140°, read distance at each angle. Returns {angle: dist}."""
    oled(robot, "Phase 2: Servo Sweep")
    oled(robot, "20deg to 140deg")

    results: dict[int, float] = {}

    for angle in SWEEP_ANGLES:
        robot.set_servo(angle)
        time.sleep(SERVO_SETTLE)

        dist = robot.get_distance()
        if dist is None:
            dist = 300.0   # treat missing reading as max range

        results[angle] = dist
        danger = " !" if dist < 10 else ("  !" if dist < 20 else "")
        oled(robot, f"{angle}deg: {dist:.1f}cm{danger}")
        print(f"  {angle:3d}° → {dist:.1f} cm")

    robot.set_servo(90)   # return head to centre
    oled(robot, "====================")
    oled(robot, "SWEEP COMPLETE")
    oled(robot, "Saving plot...")
    return results


# ── Plot generation ───────────────────────────────────────────────────────────

DISPLAY_CAP = 80   # clip distances in the polar view so spikes don't hide detail


def save_plot(results: dict[int, float], out_path: str):
    angles_deg = sorted(results)
    distances  = [results[a] for a in angles_deg]
    dist_cap   = [min(d, DISPLAY_CAP) for d in distances]
    angles_rad = np.radians(angles_deg)

    fig = plt.figure(figsize=(12, 6), facecolor="#0d1117")
    fig.suptitle(
        "Robot Servo Sweep  |  20° → 140°",
        color="white", fontsize=14, fontweight="bold", y=0.97,
    )

    # ── Polar view ────────────────────────────────────────────────────────────
    ax_p = fig.add_subplot(121, projection="polar", facecolor="#161b22")
    ax_p.set_theta_zero_location("N")
    ax_p.set_theta_direction(-1)

    ax_p.fill(angles_rad, dist_cap, alpha=0.25, color="#58a6ff")
    ax_p.plot(angles_rad, dist_cap, "o-", color="#58a6ff",
              linewidth=2, markersize=6, markerfacecolor="white", zorder=5)

    for a, d in zip(angles_rad, dist_cap):
        ax_p.plot(a, d, "o", color="#ff4444" if d < 10 else "#58a6ff",
                  markersize=8, zorder=6)

    ring = np.linspace(0, 2 * np.pi, 300)
    ax_p.plot(ring, [10] * 300, "--", color="#ff4444", alpha=0.6, linewidth=1.2)
    ax_p.plot(ring, [DISPLAY_CAP] * 300, ":", color="#888", alpha=0.4, linewidth=1)

    ax_p.set_ylim(0, DISPLAY_CAP)
    ax_p.set_thetalim(np.radians(10), np.radians(150))
    ax_p.tick_params(colors="#8b949e", labelsize=8)
    ax_p.set_rlabel_position(165)
    for sp in ax_p.spines.values():
        sp.set_edgecolor("#30363d")
    ax_p.set_title(f"Polar view (capped @ {DISPLAY_CAP} cm)",
                   color="#8b949e", fontsize=10, pad=12)

    red_p  = mpatches.Patch(color="#ff4444", label="< 10 cm danger")
    blue_p = mpatches.Patch(color="#58a6ff", label=f"≥ 10 cm clear")
    cap_p  = mpatches.Patch(color="#888",    label=f"{DISPLAY_CAP} cm cap", alpha=0.5)
    ax_p.legend(handles=[red_p, blue_p, cap_p], loc="lower right", fontsize=8,
                facecolor="#161b22", edgecolor="#30363d", labelcolor="#8b949e",
                bbox_to_anchor=(1.35, -0.05))

    # ── Bar chart ─────────────────────────────────────────────────────────────
    ax_b = fig.add_subplot(122, facecolor="#161b22")

    bar_colors = ["#ff4444" if d < 10 else "#58a6ff" for d in distances]
    bars = ax_b.bar(angles_deg, distances, width=7, color=bar_colors,
                    edgecolor="#30363d", linewidth=0.8, alpha=0.85)

    for bar, val in zip(bars, distances):
        label = f"{val:.0f}" if val < 100 else f"{val:.0f}*"
        ax_b.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3,
                  label, ha="center", va="bottom", color="white",
                  fontsize=7.5, fontweight="bold")

    ax_b.axhline(10, color="#ff4444", linestyle="--", linewidth=1.5, alpha=0.8)
    ax_b.set_xlabel("Servo Angle (degrees)", color="#8b949e", fontsize=10)
    ax_b.set_ylabel("Distance (cm)", color="#8b949e", fontsize=10)
    ax_b.set_title("Distance vs Angle (raw values)", color="#8b949e", fontsize=10)
    ax_b.set_xticks(angles_deg)
    ax_b.tick_params(colors="#8b949e", labelsize=8)
    ax_b.set_ylim(0, max(distances) * 1.12)
    for sp in ax_b.spines.values():
        sp.set_edgecolor("#30363d")
    ax_b.legend(handles=[red_p, blue_p], fontsize=8,
                facecolor="#161b22", edgecolor="#30363d", labelcolor="#8b949e")
    ax_b.annotate("* value exceeds display range — bar = actual",
                  xy=(0.01, 0.01), xycoords="axes fraction",
                  color="#8b949e", fontsize=7, style="italic")
    ax_b.grid(axis="y", color="#30363d", linewidth=0.6, alpha=0.7)
    ax_b.grid(axis="x", color="#30363d", linewidth=0.3, alpha=0.4)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"\n  Plot saved → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Reverse-until-close + servo sweep")
    parser.add_argument(
        "--ip",
        default=os.getenv("ROBOT_IP"),
        help="Robot IP address (or set ROBOT_IP in .env)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(__file__), "servo_sweep_output.png"),
        help="Output path for the sweep plot",
    )
    args = parser.parse_args()

    if not args.ip:
        parser.error("Provide --ip or set ROBOT_IP in .env")

    print(f"\nConnecting to robot at {args.ip} …")
    with RobotController(args.ip) as robot:

        # ── Phase 1 ───────────────────────────────────────────────────────────
        print("\n── Phase 1: Reverse until distance < 10 cm ──")
        final_dist = phase1_reverse(robot)
        print(f"\n  ✓ Phase 1 complete — stopped at {final_dist:.1f} cm")

        time.sleep(0.3)   # brief pause before sweep

        # ── Phase 2 ───────────────────────────────────────────────────────────
        print("\n── Phase 2: Servo sweep 20°→140° ──")
        sweep_data = phase2_sweep(robot)

        # ── Plot ──────────────────────────────────────────────────────────────
        print("\n── Generating plot ──")
        save_plot(sweep_data, args.out)

        # ── Done ──────────────────────────────────────────────────────────────
        robot.set_led(0, 255, 0)
        robot.beep(1200)
        time.sleep(0.15)
        robot.beep(1400)
        print("\n✓ Mission complete!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
    except ConnectionRefusedError as exc:
        print(f"\n✗ Could not connect: {exc}")
        print("  Check: Is the robot powered on? Is WiFi sketch 06.2 flashed?")
        sys.exit(1)
