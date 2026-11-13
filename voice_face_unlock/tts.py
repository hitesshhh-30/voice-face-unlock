"""Talk back: natural Piper voice if its model is installed, else spd-say."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from .config import Config


def _piper_wav(cfg: Config, text: str) -> Path | None:
    model = cfg.models / f"{cfg.voice_model}.onnx"
    if not model.exists():
        return None
    from piper import PiperVoice  # heavy import, only when needed

    out = Path(tempfile.mkstemp(suffix=".wav", prefix="vfu-")[1])
    with wave.open(str(out), "wb") as w:
        PiperVoice.load(str(model)).synthesize_wav(text, w)
    return out


def speak(cfg: Config, text: str, wait: bool = True) -> subprocess.Popen | None:
    """Speak text. Returns the player process when wait=False."""
    if not cfg.speak or not text:
        return None
    wav = _piper_wav(cfg, text)
    if wav and shutil.which("pw-play"):
        cmd = ["pw-play", str(wav)]
    elif wav and shutil.which("aplay"):
        cmd = ["aplay", "-q", str(wav)]
    elif shutil.which("spd-say"):
        cmd = ["spd-say", "-w", "-r", "-10", text]
    else:
        print(f"[say] {text}")
        return None
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if wait:
        proc.wait()
        return None
    return proc
