"""Talk back. Order: Cartesia (natural, online) -> Piper (offline) -> spd-say.

Cartesia key: env CARTESIA_API_KEY or ~/.config/voice-face-unlock/cartesia.key (chmod 600).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import wave
from pathlib import Path

from .config import CONFIG_FILE, DATA_DIR, Config

CARTESIA_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = "2025-04-16"
KEY_FILE = CONFIG_FILE.parent / "cartesia.key"
CACHE = DATA_DIR / "voice-cache"


def cartesia_key() -> str | None:
    key = os.environ.get("CARTESIA_API_KEY")
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    return key or None


def _cartesia_wav(cfg: Config, text: str, out: Path) -> bool:
    key = cartesia_key()
    if not key or not cfg.cartesia_voice_id:
        return False
    body = {
        "model_id": cfg.cartesia_model,
        "transcript": text,
        "voice": {"mode": "id", "id": cfg.cartesia_voice_id},
        "language": "en",
        "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 44100},
    }
    req = urllib.request.Request(
        CARTESIA_URL, data=json.dumps(body).encode(), method="POST",
        headers={"X-API-Key": key, "Cartesia-Version": CARTESIA_VERSION, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.cartesia_timeout_s) as r:
            pcm = r.read()
    except Exception:
        return False
    if len(pcm) < 1000:
        return False
    # write our own header: Cartesia's streamed wav header has no real length
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(pcm)
    return True


def _piper_wav(cfg: Config, text: str, out: Path) -> bool:
    model = cfg.models / f"{cfg.voice_model}.onnx"
    if not model.exists():
        return False
    from piper import PiperVoice  # heavy import, only when needed

    with wave.open(str(out), "wb") as w:
        PiperVoice.load(str(model)).synthesize_wav(text, w)
    return True


def synthesize(cfg: Config, text: str, cache: bool = False) -> Path | None:
    """Make a wav for text. cache=True reuses a file for fixed lines (denied, cooldown)."""
    if cache:
        CACHE.mkdir(parents=True, exist_ok=True)
        tag = hashlib.sha1(f"{cfg.cartesia_voice_id}|{text}".encode()).hexdigest()[:16]
        cached = CACHE / f"{tag}.wav"
        if cached.exists():
            return cached
        out = cached
    else:
        out = Path(tempfile.mkstemp(suffix=".wav", prefix="vfu-")[1])
    if _cartesia_wav(cfg, text, out) or _piper_wav(cfg, text, out):
        return out
    out.unlink(missing_ok=True)
    return None


def play(wav: Path | None, text: str = "") -> subprocess.Popen | None:
    if wav and shutil.which("pw-play"):
        cmd = ["pw-play", str(wav)]
    elif wav and shutil.which("aplay"):
        cmd = ["aplay", "-q", str(wav)]
    elif text and shutil.which("spd-say"):
        cmd = ["spd-say", "-w", text]
    else:
        return None
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def speak(cfg: Config, text: str, cache: bool = True) -> None:
    if not cfg.speak or not text:
        return
    p = play(synthesize(cfg, text, cache=cache), text)
    if p:
        p.wait()
