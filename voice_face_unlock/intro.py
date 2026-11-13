"""Full-screen intro video after unlock, with the voice starting on the impact frame.
Preview: voice-face-unlock intro.  Any key / click skips it."""
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "wayland,x11")

import cv2  # noqa: E402
import pygame  # noqa: E402

from . import config as config_mod  # noqa: E402
from . import sysinfo, tts  # noqa: E402

VIDEO = Path(__file__).resolve().parent.parent / "assets" / "intro.mp4"
VOICE_AT_S = 2.8      # impact frame in the film
MAX_EXTRA_HOLD_S = 6  # hold last frame at most this long waiting for the voice


def find_video(cfg) -> Path | None:
    for p in (cfg.intro_video and Path(cfg.intro_video).expanduser(), config_mod.DATA_DIR / "intro.mp4", VIDEO):
        if p and p.exists():
            return p
    return None


def play_video(path: Path, on_time) -> None:
    """Play the video full-screen; on_time(t) is called every frame."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    sw, sh = screen.get_size()
    clock = pygame.time.Clock()
    last = None
    frame_i = 0
    try:
        while True:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    return
            ok, frame = cap.read()
            t = frame_i / fps
            if not ok:
                if not on_time(t, finished=True):
                    return
                frame = None
            else:
                frame_i += 1
                on_time(t, finished=False)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if (rgb.shape[1], rgb.shape[0]) != (sw, sh):
                    rgb = cv2.resize(rgb, (sw, sh), interpolation=cv2.INTER_AREA)
                last = pygame.image.frombuffer(rgb.tobytes(), (sw, sh), "RGB")
            if last is not None:
                screen.blit(last, (0, 0))
                pygame.display.flip()
            clock.tick(fps)
    finally:
        cap.release()
        pygame.quit()


def main() -> None:
    cfg = config_mod.load()
    bat = sysinfo.battery()
    line = sysinfo.intro_line(cfg.boss_name, cfg.say_success, datetime.now(), bat)

    # make the voice in the background while the video starts (hides network latency)
    wav: dict = {}
    maker = threading.Thread(target=lambda: wav.update(p=tts.synthesize(cfg, line)), daemon=True)
    if cfg.speak:
        maker.start()
    state = {"player": None, "held": 0.0}

    def on_time(t: float, finished: bool) -> bool:
        """Start the voice at the impact. Returns True to keep holding the last frame."""
        if cfg.speak and state["player"] is None and t >= VOICE_AT_S:
            maker.join(timeout=1.5)
            state["player"] = tts.play(wav.get("p"), line) or False
        if finished:
            p = state["player"]
            state["held"] += 1 / 30
            return bool(p) and p.poll() is None and state["held"] < MAX_EXTRA_HOLD_S
        return True

    video = find_video(cfg) if cfg.intro_animation else None
    try:
        if video:
            play_video(video, on_time)
        else:
            on_time(VOICE_AT_S, finished=False)
    except pygame.error as e:
        print(f"intro video unavailable: {e}", file=sys.stderr)
        on_time(VOICE_AT_S, finished=False)
    if state["player"]:
        state["player"].wait()


if __name__ == "__main__":
    main()
