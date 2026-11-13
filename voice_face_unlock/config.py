"""Settings. Defaults here; override any key in ~/.config/voice-face-unlock/config.toml."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

APP = "voice-face-unlock"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / APP
CONFIG_FILE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP / "config.toml"


@dataclass
class Config:
    # What you say. Spoken variants Vosk may hear ("bite" sounds like "byte").
    phrase: str = "hey the byte has landed"
    phrase_variants: list[str] = field(default_factory=lambda: [
        "hey the byte has landed", "hey the bite has landed",
        "the byte has landed", "the bite has landed",
    ])

    # Voice check: cosine similarity to your enrolled voice (0..1). Higher = stricter.
    voice_threshold: float = 0.55

    # Face check
    ir_camera: str = "/dev/video2"      # infrared sensor (preferred: photos on screens fail)
    rgb_camera: str = "/dev/video0"     # colour sensor, used for intruder photos
    face_camera: str = "ir"             # "ir" or "rgb"
    face_threshold: float = 0.45        # SFace cosine similarity. OpenCV's suggested 0.363; we're stricter.
    face_timeout_s: float = 5.0         # how long to look for face + blink
    min_face_matches: int = 3           # frames that must match your face

    # Blink (eye aspect ratio)
    ear_closed: float = 0.18
    ear_open: float = 0.24

    # Safety
    max_failures: int = 3               # after this many failures...
    cooldown_s: float = 60.0            # ...voice unlock pauses this long

    # Talk back + intro
    speak: bool = True
    voice_model: str = "en_GB-alan-medium"   # Piper voice in models/ (falls back to spd-say)
    boss_name: str = "boss"
    intro_animation: bool = True
    say_success: str = "Impact confirmed. Ninja inside."
    say_denied: str = "Unknown entity. Face cached. Have a nice day."
    say_cooldown: str = "Too many attempts. Use your password."
    save_intruders: bool = True

    @property
    def models(self) -> Path:
        return DATA_DIR / "models"

    @property
    def enroll_dir(self) -> Path:
        return DATA_DIR / "enroll"

    @property
    def intruder_dir(self) -> Path:
        return DATA_DIR / "intruders"


def load(path: Path = CONFIG_FILE) -> Config:
    cfg = Config()
    if path.exists():
        data = tomllib.loads(path.read_text())
        known = {f.name for f in fields(Config)}
        for key, value in data.items():
            if key not in known:
                raise ValueError(f"{path}: unknown setting '{key}'")
            setattr(cfg, key, value)
    return cfg
