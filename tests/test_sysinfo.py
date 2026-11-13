from datetime import datetime

from voice_face_unlock.sysinfo import greeting, intro_line, spoken_time


def test_greeting_by_hour():
    assert greeting(datetime(2026, 1, 1, 8)) == "Good morning"
    assert greeting(datetime(2026, 1, 1, 13)) == "Good afternoon"
    assert greeting(datetime(2026, 1, 1, 19)) == "Good evening"
    assert greeting(datetime(2026, 1, 1, 2)) == "Burning the midnight oil"


def test_spoken_time():
    assert spoken_time(datetime(2026, 1, 1, 19, 42)) == "7:42 P M"
    assert spoken_time(datetime(2026, 1, 1, 9, 0)) == "9 o'clock A M"


def test_intro_line_is_short_when_battery_ok():
    line = intro_line("boss", "Impact confirmed.", datetime(2026, 1, 1, 19, 42), (82, False))
    assert line == "Impact confirmed. Good evening, boss. All systems online."


def test_intro_line_low_battery_and_desktop():
    assert "plug in soon" in intro_line("boss", "", datetime(2026, 1, 1, 9), (15, False))
    assert "plug in soon" not in intro_line("boss", "", datetime(2026, 1, 1, 9), (15, True))
    assert "Battery" not in intro_line("boss", "", datetime(2026, 1, 1, 9), (None, False))
