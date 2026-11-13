"""Full-screen HUD intro after unlock. Run standalone: python -m voice_face_unlock.intro
Any key / click skips it."""
from __future__ import annotations

import math
import os
import random
import sys
from datetime import datetime

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "wayland,x11")

import pygame  # noqa: E402

from . import config as config_mod  # noqa: E402
from . import sysinfo, tts  # noqa: E402

DURATION = 7.0
BG = (4, 10, 20)
CYAN = (0, 220, 255)
DIM = (0, 90, 120)
WHITE = (230, 250, 255)
GREEN = (60, 255, 160)
AMBER = (255, 190, 60)


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    path = pygame.font.match_font("dejavusansmono,ubuntumono,liberationmono,monospace", bold=bold)
    return pygame.font.Font(path, size)


def _arc(surf, color, center, radius, start, length, width):
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    pygame.draw.arc(surf, color, rect, start, start + length, width)


def _typed(text: str, t: float, start: float, speed: float = 40) -> str:
    return text[: max(0, int((t - start) * speed))]


def _ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _bar(surf, x, y, w, label, pct, t, start, font):
    p = _ease((t - start) / 0.8) * (pct or 0) / 100
    surf.blit(font.render(f"{label:<8}{'--' if pct is None else f'{pct:>3}%'}", True, CYAN), (x, y))
    pygame.draw.rect(surf, DIM, (x, y + 30, w, 8), 1)
    color = AMBER if label.startswith("BAT") and pct is not None and pct <= 20 else CYAN
    pygame.draw.rect(surf, color, (x + 2, y + 32, int((w - 4) * p), 4))


def play(name: str, line: str, stats: dict, checks: list[str]) -> None:
    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    W, H = screen.get_size()
    cx, cy = W // 2, H // 2
    s = H / 1080
    big, mid, small = _font(int(64 * s), True), _font(int(28 * s)), _font(int(22 * s))
    clock = pygame.time.Clock()
    random.seed(7)
    particles = [(random.uniform(0, W), random.uniform(0, H), random.uniform(20, 80)) for _ in range(120)]
    hexes = "".join(random.choice("0123456789ABCDEF ") for _ in range(4000))
    t0 = pygame.time.get_ticks() / 1000
    fade = pygame.Surface((W, H))
    fade.fill((0, 0, 0))

    running = True
    while running:
        t = pygame.time.get_ticks() / 1000 - t0
        if t > DURATION:
            break
        for e in pygame.event.get():
            if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False

        screen.fill(BG)

        # drifting particles + faint hex rain
        for i, (px, py, sp) in enumerate(particles):
            y = (py - t * sp) % H
            pygame.draw.circle(screen, DIM, (int(px), int(y)), 1 + (i % 2))
        for row in range(0, H, int(26 * s)):
            off = int((t * 60 + row) % 300)
            txt = hexes[off: off + 18]
            screen.blit(small.render(txt, True, (0, 40, 55)), (int(20 * s), row))
            screen.blit(small.render(txt[::-1], True, (0, 40, 55)), (W - int(260 * s), row))

        # reactor rings
        grow = _ease(t / 1.2)
        for i, (r, spd, ln, w) in enumerate([(260, 0.8, 4.2, 3), (220, -1.4, 2.4, 6), (180, 2.2, 1.2, 2),
                                             (300, -0.4, 5.6, 1), (140, 3.0, 3.6, 4)]):
            rad = int(r * s * grow)
            if rad > w:
                for k in range(3 if i % 2 else 2):
                    _arc(screen, CYAN if i % 2 == 0 else DIM, (cx, cy - int(60 * s)), rad,
                         t * spd + k * (2 * math.pi / (3 if i % 2 else 2)), ln / 3, w)
        pulse = 0.6 + 0.4 * math.sin(t * 6)
        pygame.draw.circle(screen, (0, int(120 * pulse), int(160 * pulse)), (cx, cy - int(60 * s)),
                           int(90 * s * grow))
        pygame.draw.circle(screen, CYAN, (cx, cy - int(60 * s)), int(90 * s * grow), 2)

        # scan line
        sy = int((t * 0.6 % 1) * H)
        pygame.draw.line(screen, (0, 70, 90), (0, sy), (W, sy), 2)

        # centre title
        if t > 1.3:
            title = _typed(f"WELCOME BACK, {name.upper()}", t, 1.3, 22)
            surf = big.render(title, True, WHITE)
            screen.blit(surf, surf.get_rect(center=(cx, cy + int(260 * s))))
        if t > 2.6:
            sub = datetime.now().strftime("%A %d %B  ·  %H:%M:%S")
            surf = mid.render(sub, True, CYAN)
            screen.blit(surf, surf.get_rect(center=(cx, cy + int(320 * s))))

        # left: identity checks
        lx, ly = int(320 * s), int(cy - 120 * s)
        screen.blit(mid.render(_typed("// IDENTITY", t, 0.3), True, DIM), (lx, ly))
        for i, c in enumerate(checks):
            st = 0.6 + i * 0.45
            if t > st:
                ok = t > st + 0.3
                txt = f"{c:<10} {'[ OK ]' if ok else '[....]'}"
                screen.blit(mid.render(txt, True, GREEN if ok else CYAN), (lx, ly + int((50 + i * 40) * s)))
        if t > 2.2:
            screen.blit(mid.render(_typed("ACCESS GRANTED", t, 2.2), True, GREEN),
                        (lx, ly + int((70 + len(checks) * 40) * s)))

        # right: system stats
        rx, ry, bw = W - int(640 * s), int(cy - 120 * s), int(320 * s)
        screen.blit(mid.render(_typed("// SYSTEMS", t, 0.5), True, DIM), (rx, ry))
        bat_label = "BATTERY+" if stats.get("charging") else "BATTERY"
        for i, (label, key) in enumerate([(bat_label, "battery"), ("CPU", "cpu"), ("MEMORY", "ram")]):
            st = 0.9 + i * 0.35
            if t > st:
                _bar(screen, rx, ry + int((50 + i * 60) * s), bw, label, stats.get(key), t, st, mid)
        if t > 2.4:
            screen.blit(mid.render(_typed("ALL SYSTEMS ONLINE", t, 2.4), True, GREEN),
                        (rx, ry + int(250 * s)))

        # fade in / out
        a = 255 * (1 - _ease(t / 0.4)) if t < 0.4 else 255 * _ease((t - (DURATION - 0.8)) / 0.8)
        if a > 0:
            fade.set_alpha(int(a))
            screen.blit(fade, (0, 0))

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


def main() -> None:
    cfg = config_mod.load()
    now = datetime.now()
    bat = sysinfo.battery()
    stats = {"battery": bat[0], "charging": bat[1], "cpu": sysinfo.cpu_percent(), "ram": sysinfo.ram_percent()}
    line = sysinfo.intro_line(cfg.boss_name, cfg.say_success, now, bat)
    voice = tts.speak(cfg, line, wait=False)
    try:
        if cfg.intro_animation:
            play(cfg.boss_name, line, stats, ["VOICE", "FACE", "LIVENESS"])
    except pygame.error as e:
        print(f"intro animation unavailable: {e}", file=sys.stderr)
    if voice:
        voice.wait()


if __name__ == "__main__":
    main()
