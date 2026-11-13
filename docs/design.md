# Voice + Face Unlock — Design (short)

Date: 2026-11-13 · Status: approved by owner in chat

## Intent
Unlock the GNOME lock screen hands-free by saying **"Hey, the byte has landed"**,
JARVIS-style, safely enough for a personal laptop. Weekend project, to be
published on GitHub so others can install it with their own voice/face.

## Goals
- Say the phrase while the screen is locked → laptop unlocks within a few seconds.
- Three checks must all pass: phrase + speaker voice + live face (IR camera) with a blink.
- Laptop talks back on success; on failure says a denial line and saves an intruder photo locally.
- Everything offline, nothing leaves the laptop.

## Non-goals
- Login screen right after boot (password stays; also unlocks keyring).
- sudo / PAM integration.
- Non-GNOME desktops (may work, not targeted).

## Anti-goals (failure even if it "works")
- Any change that can lock the owner out (no PAM edits, password always works).
- Personal biometric data (voice samples, face encodings, intruder photos) ending up in git.
- Listening to the mic while the screen is unlocked.

## Constraints (this laptop)
Ubuntu 24.04, GNOME on Wayland, GDM. Python 3.12. Mic: ALC3254.
Camera: one module with RGB `/dev/video0` and IR greyscale 640x360 `/dev/video2`.

## Approaches considered
1. **Howdy via PAM** + voice trigger — Howdy does face check at the lock-screen prompt.
   Trade-off: needs root/PAM edits, 24.04 install is fiddly, voice can't drive the prompt cleanly.
2. **Own user-level service (chosen — Claude's call)** — same face method as Howdy
   (dlib face encodings) on the IR camera, plus blink check, run as a normal user
   service; unlock via `loginctl unlock-session`. No root, no PAM, easy for others to install.
3. Voice only — rejected, replayable recording.

## Design
- **Lock watcher:** only active while the session is locked (logind `LockedHint` / GNOME ScreenSaver).
- **Phrase:** Vosk offline speech recognition, grammar limited to the phrase.
- **Speaker check:** speaker-embedding model compared to ~10 enrolled samples (cosine threshold).
- **Face check:** IR camera frames → face detection → encoding compared to enrolled encodings.
- **Blink check:** eye-aspect-ratio from facial landmarks must dip and recover within ~3 s.
- **Unlock:** `loginctl unlock-session <id>`.
- **Talk back:** `spd-say` (piper optional later). Success: "Impact confirmed. Ninja inside."
  Failure: "Unknown entity. Face cached. Have a nice day." + intruder photo to `~/.local/share/<app>/intruders/`.
- **Enrollment CLI:** `enroll-voice` (record 10 samples), `enroll-face` (live capture, several poses/lighting).
- **Data:** stored in `~/.local/share/<app>/`, never in the repo; `.gitignore` covers any local data dirs.
- **Runs as:** systemd `--user` service.

## Left to the builder
Exact libraries/model choices for speaker embedding and landmarks, thresholds (tuned
with owner), project/app name (owner decides later).
