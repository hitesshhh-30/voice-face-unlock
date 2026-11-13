"""Full-screen intro video after unlock.

Voice + film sound are pre-mixed into ONE wav (music ducked under the voice) and
the picture follows the wall clock started with that audio, so nothing drifts.
Preview: voice-face-unlock intro.  Any key / click skips it."""
from __future__ import annotations

import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "wayland,x11")

import cv2  # noqa: E402
import pygame  # noqa: E402

from . import config as config_mod  # noqa: E402
from . import mixer, sysinfo, tts  # noqa: E402

VIDEO = Path(__file__).resolve().parent.parent / "assets" / "intro.mp4"
VOICE_AT_S = 6.3      # just after the impact (6.0 s) in the film
MUSIC_DUCK = 0.3      # music level while the voice speaks
AUDIO_LATENCY = "250ms"  # big audio buffer: no crackle while the video decodes


def find_video(cfg) -> Path | None:
    for p in (cfg.intro_video and Path(cfg.intro_video).expanduser(), config_mod.DATA_DIR / "intro.mp4", VIDEO):
        if p and p.exists():
            return p
    return None


def build_soundtrack(cfg, video: Path | None, line: str) -> Path | None:
    """Voice (cached per line) mixed into the film sound. Falls back to whichever exists."""
    voice = tts.synthesize(cfg, line, cache=True) if cfg.speak else None
    music = video.with_suffix(".wav") if video else None
    if not (music and music.exists()):
        return voice
    if not voice:
        return music
    out = Path(tempfile.mkstemp(suffix=".wav", prefix="vfu-intro-")[1])
    mixer.mix(music, voice, VOICE_AT_S, out, duck=MUSIC_DUCK)
    return out


def play_video(path: Path, t0: float, keep_holding) -> None:
    """Show the frame that belongs to (now - t0); hold the last frame while keep_holding()."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    sw, sh = screen.get_size()
    clock = pygame.time.Clock()
    shown = -1          # index of the frame currently on screen
    done = False
    try:
        while True:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    return
            want = int((time.monotonic() - t0) * fps)
            frame = None
            while not done and shown < want:      # catch up: drop frames if we're late
                ok = cap.grab()
                if not ok:
                    done = True
                    break
                shown += 1
                if shown == want:
                    ok, frame = cap.retrieve()
            if frame is not None:
                if (frame.shape[1], frame.shape[0]) != (sw, sh):
                    frame = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_AREA)
                # BGR straight from OpenCV, no colour conversion or copy (less CPU)
                screen.blit(pygame.image.frombuffer(frame.data, (sw, sh), "BGR"), (0, 0))
                pygame.display.flip()
            if done and not keep_holding():
                return
            clock.tick(fps * 2)
    finally:
        cap.release()
        pygame.quit()


def main() -> None:
    cfg = config_mod.load()
    line = sysinfo.intro_line(cfg.boss_name, cfg.say_success, datetime.now(), sysinfo.battery())
    video = find_video(cfg) if cfg.intro_animation else None
    track = build_soundtrack(cfg, video, line)

    player = tts.play(track, line, latency=AUDIO_LATENCY)
    t0 = time.monotonic()
    try:
        os.nice(10)  # video yields the CPU to the sound player (it keeps normal priority)
    except OSError:
        pass
    try:
        if video:
            play_video(video, t0, lambda: bool(player) and player.poll() is None)
    except pygame.error as e:
        print(f"intro video unavailable: {e}", file=sys.stderr)
    if player:
        if video:
            player.terminate()   # skipped or finished: stop sound with the picture
        else:
            player.wait()
    if track and track.name.startswith("vfu-intro-"):
        track.unlink(missing_ok=True)


def warm_cache(cfg=None) -> None:
    """Pre-make the greeting lines so the intro starts instantly."""
    cfg = cfg or config_mod.load()
    for hour in (8, 13, 19, 2):
        line = sysinfo.intro_line(cfg.boss_name, cfg.say_success, datetime(2026, 1, 1, hour), (None, False))
        tts.synthesize(cfg, line, cache=True)


if __name__ == "__main__":
    main()
