"""Face match (OpenCV YuNet + SFace) and blink liveness (MediaPipe face landmarks)."""
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from .config import Config
from .mathutil import BlinkDetector, best_match, eye_aspect_ratio

# MediaPipe face-mesh points: outer, top1, top2, inner, bottom2, bottom1
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [263, 387, 385, 362, 380, 373]
WARMUP_FRAMES = 5


def enable_ir_emitter() -> None:
    """Turn on the IR light if linux-enable-ir-emitter (v7+) is installed and configured."""
    tool = shutil.which("linux-enable-ir-emitter")
    if tool:
        subprocess.run([tool, "run"], capture_output=True, timeout=10, check=False)


def open_camera(path: str, ir: bool) -> cv2.VideoCapture:
    if ir:
        enable_ir_emitter()
    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    if ir:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"GREY"))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open camera {path}")
    for _ in range(WARMUP_FRAMES):
        cap.read()
    return cap


def to_bgr(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if frame.ndim == 2 else frame


def snapshot(path: str, ir: bool, out: Path) -> Path:
    cap = open_camera(path, ir)
    try:
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok:
        raise RuntimeError(f"no frame from {path}")
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), frame)
    return out


@dataclass
class FaceResult:
    matched_frames: int
    best_score: float
    blinked: bool
    frames: int

    def ok(self, cfg: Config) -> bool:
        return self.matched_frames >= cfg.min_face_matches and self.blinked


class FaceCheck:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        m = cfg.models
        self.detector = cv2.FaceDetectorYN.create(str(m / "yunet.onnx"), "", (640, 480), 0.8)
        self.recognizer = cv2.FaceRecognizerSF.create(str(m / "sface.onnx"), "")
        self.landmarker = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(m / "face_landmarker.task")), num_faces=1
            )
        )
        self.file = cfg.enroll_dir / "face.npy"

    def close(self) -> None:
        self.landmarker.close()

    def camera(self) -> cv2.VideoCapture:
        ir = self.cfg.face_camera == "ir"
        return open_camera(self.cfg.ir_camera if ir else self.cfg.rgb_camera, ir)

    def embed(self, bgr: np.ndarray) -> np.ndarray | None:
        """Embedding of the single face in the frame, or None (no face / several faces)."""
        h, w = bgr.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(bgr)
        if faces is None or len(faces) != 1:
            return None
        aligned = self.recognizer.alignCrop(bgr, faces[0])
        return self.recognizer.feature(aligned).ravel().astype(np.float32)

    def ear(self, bgr: np.ndarray) -> float | None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        res = self.landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not res.face_landmarks:
            return None
        lms = res.face_landmarks[0]
        h, w = bgr.shape[:2]

        def pts(idx):
            return np.array([(lms[i].x * w, lms[i].y * h) for i in idx])

        return (eye_aspect_ratio(pts(RIGHT_EYE)) + eye_aspect_ratio(pts(LEFT_EYE))) / 2

    def enrolled(self) -> np.ndarray | None:
        return np.load(self.file) if self.file.exists() else None

    def verify(self, on_frame=None) -> FaceResult:
        enrolled = self.enrolled()
        blink = BlinkDetector(self.cfg.ear_closed, self.cfg.ear_open)
        matched, best, frames, blinked = 0, 0.0, 0, False
        cap = self.camera()
        try:
            end = time.monotonic() + self.cfg.face_timeout_s
            while time.monotonic() < end:
                ok, frame = cap.read()
                if not ok:
                    continue
                frames += 1
                bgr = to_bgr(frame)
                emb = self.embed(bgr)
                if emb is None:
                    continue
                score = best_match(emb, enrolled)
                best = max(best, score)
                if score >= self.cfg.face_threshold:
                    matched += 1
                    ear = self.ear(bgr)
                    if ear is not None:
                        blinked = blink.update(ear) or blinked
                if on_frame:
                    on_frame(score, matched, blinked)
                if matched >= self.cfg.min_face_matches and blinked:
                    break
        finally:
            cap.release()
        return FaceResult(matched, best, blinked, frames)

    def capture_enrollment(self, seconds: float, on_progress=None) -> list[np.ndarray]:
        embs: list[np.ndarray] = []
        cap = self.camera()
        try:
            end = time.monotonic() + seconds
            last = 0.0
            while time.monotonic() < end:
                ok, frame = cap.read()
                if not ok or time.monotonic() - last < 0.3:
                    continue
                emb = self.embed(to_bgr(frame))
                if emb is not None:
                    embs.append(emb)
                    last = time.monotonic()
                    if on_progress:
                        on_progress(len(embs))
        finally:
            cap.release()
        return embs

    def save(self, embeddings: list[np.ndarray], append: bool) -> int:
        existing = self.enrolled() if append else None
        arr = np.stack(embeddings)
        if existing is not None:
            arr = np.concatenate([existing, arr])
        self.file.parent.mkdir(parents=True, exist_ok=True)
        np.save(self.file, arr)
        return len(arr)


def save_intruder(cfg: Config) -> Path | None:
    if not cfg.save_intruders:
        return None
    out = cfg.intruder_dir / f"intruder-{datetime.now():%Y%m%d-%H%M%S}.jpg"
    try:
        return snapshot(cfg.rgb_camera, False, out)
    except RuntimeError:
        return None
