"""Small pure functions (easy to unit test)."""
from __future__ import annotations

import re

import numpy as np


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def best_match(probe: np.ndarray, enrolled: np.ndarray) -> float:
    """Highest cosine similarity of probe against each enrolled row."""
    if enrolled is None or len(enrolled) == 0:
        return 0.0
    return max(cosine(probe, row) for row in np.atleast_2d(enrolled))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", text.lower())).strip()


def phrase_matches(heard: str, variants: list[str]) -> bool:
    """True if what Vosk heard contains one of the accepted phrase variants."""
    h = f" {normalize_text(heard)} "
    return any(f" {normalize_text(v)} " in h for v in variants)


def eye_aspect_ratio(pts: np.ndarray) -> float:
    """EAR from 6 eye points ordered: outer, top1, top2, inner, bottom2, bottom1."""
    p = np.asarray(pts, dtype=np.float32)
    vertical = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    horizontal = 2.0 * np.linalg.norm(p[0] - p[3])
    return float(vertical / horizontal) if horizontal > 0 else 0.0


class BlinkDetector:
    """Detects open -> closed -> open. A photo can't do that."""

    def __init__(self, closed: float, open_: float):
        self.closed, self.open = closed, open_
        self.state = "need_open"

    def update(self, ear: float) -> bool:
        if self.state == "need_open" and ear >= self.open:
            self.state = "need_closed"
        elif self.state == "need_closed" and ear <= self.closed:
            self.state = "need_reopen"
        elif self.state == "need_reopen" and ear >= self.open:
            self.state = "done"
        return self.state == "done"
