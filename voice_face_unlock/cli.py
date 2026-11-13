"""voice-face-unlock: enroll-voice | enroll-face | snapshot | test | run"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

from . import config as config_mod
from .audio import Mic
from .config import Config
from .mathutil import phrase_matches

log = logging.getLogger("voice-face-unlock")


def _need_enrollment(cfg: Config) -> None:
    missing = [n for n in ("voice.npy", "face.npy") if not (cfg.enroll_dir / n).exists()]
    if missing:
        sys.exit(f"Not enrolled yet ({', '.join(missing)} missing). Run enroll-voice and enroll-face first.")


def cmd_enroll_voice(cfg: Config, args) -> None:
    from .voice import PhraseListener, SpeakerCheck

    listener, speaker = PhraseListener(cfg), SpeakerCheck(cfg)
    embs = []
    print(f'Say "{cfg.phrase}" {args.count} times, in your normal voice. Pause between each.\n')
    with Mic() as mic:
        for i in range(1, args.count + 1):
            print(f"  [{i}/{args.count}] listening... ", end="", flush=True)
            for text, pcm in listener.utterances(mic):
                if phrase_matches(text, cfg.phrase_variants):
                    embs.append(speaker.embed(pcm))
                    print("got it ✓")
                    break
                print(f'(heard "{text}", try again) ', end="", flush=True)
    speaker.save(embs)
    print(f"\nVoice saved ({len(embs)} samples) → {speaker.file}")


def cmd_enroll_face(cfg: Config, args) -> None:
    from .face import FaceCheck

    fc = FaceCheck(cfg)
    try:
        print(f"Look at the camera ({cfg.face_camera}). Move your head a little: left, right, up, down.")
        print(f"Capturing for {args.seconds:.0f} seconds...")
        embs = fc.capture_enrollment(args.seconds, lambda n: print(f"\r  face samples: {n}", end="", flush=True))
        print()
        if len(embs) < 5:
            sys.exit("Too few face samples. Sit closer, face the camera, check the light, and try again.")
        total = fc.save(embs, append=not args.reset)
        print(f"Face saved ({len(embs)} new, {total} total) → {fc.file}")
        print("Tip: run again with/without glasses or in different light to add more.")
    finally:
        fc.close()


def cmd_snapshot(cfg: Config, args) -> None:
    from .face import snapshot

    out = Path(args.out)
    print("Eye 1 (colour):", snapshot(cfg.rgb_camera, False, out / "eye1-colour.jpg"))
    print("Eye 2 (infrared):", snapshot(cfg.ir_camera, True, out / "eye2-infrared.jpg"))


def check_face(cfg: Config, fc, verbose: bool) -> bool:
    if verbose:
        print("Face: look at the camera and blink once...")
    r = fc.verify()
    if verbose:
        print(f"  frames={r.frames} matched={r.matched_frames} best={r.best_score:.2f} "
              f"(need {cfg.face_threshold}) blinked={r.blinked}")
    return r.ok(cfg)


def cmd_test(cfg: Config, args) -> None:
    """Full check without unlocking — prints the scores so you can tune thresholds."""
    from .face import FaceCheck
    from .voice import PhraseListener, SpeakerCheck

    _need_enrollment(cfg)
    listener, speaker, fc = PhraseListener(cfg), SpeakerCheck(cfg), FaceCheck(cfg)
    try:
        print(f'Say "{cfg.phrase}"...')
        with Mic() as mic:
            pcm = listener.wait_for_phrase(mic)
        v = speaker.score(pcm)
        print(f"  phrase ✓  voice score={v:.2f} (need {cfg.voice_threshold}) {'✓' if v >= cfg.voice_threshold else '✗'}")
        f_ok = check_face(cfg, fc, verbose=True)
        ok = v >= cfg.voice_threshold and f_ok
        print("RESULT:", "WOULD UNLOCK 🔓" if ok else "DENIED ❌")
    finally:
        fc.close()


def cmd_run(cfg: Config, args) -> None:
    from . import system, tts
    from .face import FaceCheck, save_intruder
    from .guard import Guard
    from .voice import PhraseListener, SpeakerCheck

    _need_enrollment(cfg)
    listener, speaker, fc = PhraseListener(cfg), SpeakerCheck(cfg), FaceCheck(cfg)
    guard = Guard(cfg.max_failures, cfg.cooldown_s)
    if cfg.speak:  # pre-make greeting voices so the intro starts without a network wait
        import threading

        from .intro import warm_cache
        threading.Thread(target=warm_cache, args=(cfg,), daemon=True).start()
    sid = system.session_id()
    log.info("ready (session %s). Waiting for the lock screen.", sid)

    def locked() -> bool:
        return system.is_locked(sid)

    try:
        while True:
            if not locked() or guard.blocked():
                time.sleep(1)
                continue
            log.info("screen locked: listening")
            with Mic() as mic:  # mic is only open while locked
                pcm = listener.wait_for_phrase(mic, keep_going=locked)
            if pcm is None:
                log.info("unlocked another way: mic off")
                continue
            v = speaker.score(pcm)
            log.info("phrase heard, voice score %.2f", v)
            if v >= cfg.voice_threshold and check_face(cfg, fc, verbose=False):
                guard.success()
                system.unlock(sid)
                log.info("UNLOCKED")
                time.sleep(0.6)  # let GNOME finish the unlock animation
                subprocess.run([sys.executable, "-m", "voice_face_unlock.intro"], check=False)
            else:
                photo = save_intruder(cfg)
                log.warning("DENIED (voice %.2f). intruder photo: %s", v, photo)
                tts.speak(cfg, cfg.say_cooldown if guard.fail() else cfg.say_denied, cache=True)
    finally:
        fc.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="voice-face-unlock", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("enroll-voice", help="record your voice saying the phrase")
    s.add_argument("--count", type=int, default=8)
    s = sub.add_parser("enroll-face", help="let the camera learn your face")
    s.add_argument("--seconds", type=float, default=8)
    s.add_argument("--reset", action="store_true", help="replace saved face instead of adding")
    s = sub.add_parser("snapshot", help="save one photo from each camera sensor")
    s.add_argument("--out", default=".")
    sub.add_parser("test", help="run all checks once without unlocking")
    sub.add_parser("intro", help="preview the welcome animation + voice")
    sub.add_parser("run", help="run the unlock service")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = config_mod.load()
    {"enroll-voice": cmd_enroll_voice, "enroll-face": cmd_enroll_face, "snapshot": cmd_snapshot,
     "test": cmd_test, "run": cmd_run,
     "intro": lambda cfg, args: __import__("voice_face_unlock.intro", fromlist=["main"]).main()}[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
