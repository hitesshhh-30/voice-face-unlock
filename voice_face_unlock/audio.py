"""Microphone input (16 kHz mono int16) via arecord — no extra system libraries needed."""
from __future__ import annotations

import subprocess

import numpy as np

RATE = 16000
CHUNK = 4000  # samples = 0.25 s


class Mic:
    def __init__(self, device: str | None = None):
        cmd = ["arecord", "-q", "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"]
        if device:
            cmd += ["-D", device]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self, samples: int = CHUNK) -> bytes:
        data = self.proc.stdout.read(samples * 2)
        if not data:
            raise RuntimeError("microphone stopped (is another app holding it?)")
        return data

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def to_float(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
