"""Tiny system stats from /proc and /sys (no extra dependencies)."""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path


def battery() -> tuple[int | None, bool]:
    """(percent, charging). (None, False) on desktops."""
    for bat in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        try:
            pct = int((bat / "capacity").read_text())
            status = (bat / "status").read_text().strip()
            return pct, status in ("Charging", "Full")
        except (OSError, ValueError):
            continue
    return None, False


def _cpu_times() -> tuple[int, int]:
    parts = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
    idle = parts[3] + parts[4]
    return idle, sum(parts)


def cpu_percent(interval: float = 0.2) -> int:
    i1, t1 = _cpu_times()
    time.sleep(interval)
    i2, t2 = _cpu_times()
    return round(100 * (1 - (i2 - i1) / max(t2 - t1, 1)))


def ram_percent() -> int:
    info = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, v = line.split(":", 1)
        info[k] = int(v.split()[0])
    return round(100 * (1 - info["MemAvailable"] / info["MemTotal"]))


def greeting(now: datetime) -> str:
    h = now.hour
    if 5 <= h < 12:
        return "Good morning"
    if 12 <= h < 17:
        return "Good afternoon"
    if 17 <= h < 22:
        return "Good evening"
    return "Burning the midnight oil"


def spoken_time(now: datetime) -> str:
    return now.strftime("%-I:%M %p").replace(":00 ", " o'clock ").replace("AM", "A M").replace("PM", "P M")


def intro_line(cfg_name: str, success: str, now: datetime, bat: tuple[int | None, bool]) -> str:
    """Short spoken line. Battery is only mentioned when it is low."""
    pct, charging = bat
    parts = [success, f"{greeting(now)}, {cfg_name}."]
    if pct is not None and pct <= 20 and not charging:
        parts.append(f"Battery at {pct} percent, I'd plug in soon.")
    parts.append("All systems online.")
    return " ".join(p for p in parts if p)
