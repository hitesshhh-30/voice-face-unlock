"""Mix the spoken line into the film's sound track as ONE wav, ducking the music
under the voice, so voice, music and picture share a single clock."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """-> (float32 samples shaped (n, channels) in [-1, 1], sample rate)."""
    with wave.open(str(path)) as w:
        ch, rate, n = w.getnchannels(), w.getframerate(), w.getnframes()
        if w.getsampwidth() != 2:
            raise ValueError(f"{path}: only 16-bit wav supported")
        data = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768
    return data.reshape(-1, ch), rate


def write_wav(path: Path, data: np.ndarray, rate: int) -> None:
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(data.shape[1])
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def resample(data: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst:
        return data
    n = int(round(len(data) * dst / src))
    x_old = np.arange(len(data)) / src
    x_new = np.arange(n) / dst
    return np.stack([np.interp(x_new, x_old, data[:, c]) for c in range(data.shape[1])], axis=1).astype(np.float32)


def duck_envelope(n: int, start: int, end: int, rate: int, level: float, fade_s: float = 0.25) -> np.ndarray:
    """Gain 1.0 everywhere, `level` between start..end, with smooth fades."""
    g = np.ones(n, dtype=np.float32)
    fade = max(1, int(fade_s * rate))
    t = np.arange(n)
    down = np.clip((t - (start - fade)) / fade, 0, 1)   # 0 -> 1 into the duck
    up = np.clip(((end + fade) - t) / fade, 0, 1)        # 1 -> 0 out of the duck
    depth = np.minimum(down, up)
    return g - depth * (1 - level)


def mix(music: Path, voice: Path, at_s: float, out: Path, duck: float = 0.3, voice_gain: float = 1.0) -> float:
    """Write music+voice into out. Returns total length in seconds."""
    m, rate = read_wav(music)
    v, vrate = read_wav(voice)
    v = resample(v, vrate, rate)
    if v.shape[1] != m.shape[1]:
        v = np.repeat(v[:, :1], m.shape[1], axis=1)
    start = int(at_s * rate)
    end = start + len(v)
    total = max(len(m), end)
    buf = np.zeros((total, m.shape[1]), dtype=np.float32)
    buf[: len(m)] = m * duck_envelope(len(m), start, end, rate, duck)[:, None]
    buf[start:end] += v * voice_gain
    peak = float(np.abs(buf).max()) or 1.0
    if peak > 0.98:
        buf *= 0.98 / peak
    write_wav(out, buf, rate)
    return total / rate
