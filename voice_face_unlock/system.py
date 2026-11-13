"""GNOME session lock state, unlock, and talk-back."""
from __future__ import annotations

import getpass
import shutil
import subprocess


def _run(*cmd: str) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def session_id() -> str:
    """The user's graphical session (works from a systemd --user service too)."""
    sid = _run("loginctl", "show-user", getpass.getuser(), "-p", "Display", "--value")
    if not sid:
        raise RuntimeError("no graphical session found for this user")
    return sid


def is_locked(sid: str) -> bool:
    return _run("loginctl", "show-session", sid, "-p", "LockedHint", "--value") == "yes"


def unlock(sid: str) -> None:
    subprocess.run(["loginctl", "unlock-session", sid], check=True)


def say(text: str, enabled: bool = True) -> None:
    if not enabled or not text:
        return
    if shutil.which("spd-say"):
        subprocess.run(["spd-say", "-w", "-r", "-10", text], check=False)
    else:
        print(f"[say] {text}")
