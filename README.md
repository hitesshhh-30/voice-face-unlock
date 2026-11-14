# voice-face-unlock 🥷

Unlock your Linux lock screen by voice. Say **"Hey, the byte has landed"**, look at the camera, blink, and it unlocks with a cinematic intro and a spoken greeting.

It unlocks only when **all** of these pass: the phrase, **your voice**, **your face** (IR camera), and **a blink**.
On a wrong person it says *"Unknown entity"* and saves a photo locally. Your **password always works**.

**Needs:** Ubuntu/GNOME, mic, webcam (IR recommended), Python 3.10+. No root, no PAM changes.

## Install
```bash
git clone https://github.com/hitesshhh-30/voice-face-unlock && cd voice-face-unlock
./install.sh
voice-face-unlock enroll-voice     # say the phrase 8 times
voice-face-unlock enroll-face      # look at the camera ~8 s
voice-face-unlock test             # checks everything, does not unlock
systemctl --user enable --now voice-face-unlock
```

## Options
- **Name & phrases:** `~/.config/voice-face-unlock/config.toml`, e.g. `boss_name = "ninja"` (all keys in `voice_face_unlock/config.py`).
- **Natural voice (optional):** put a [Cartesia](https://cartesia.ai) API key in `~/.config/voice-face-unlock/cartesia.key`; otherwise an offline Piper voice is used.
- **Preview the intro:** `voice-face-unlock intro`
- **Logs:** `journalctl --user -u voice-face-unlock -f`
- **Uninstall:** `systemctl --user disable --now voice-face-unlock && rm -rf ~/.local/share/voice-face-unlock`

Your voice and face are stored only in `~/.local/share/voice-face-unlock/`, never in the repo.
Convenience-level security, not bank-grade; don't rely on it on shared machines.

Intro sound effects from [Pixabay](https://pixabay.com/service/license-summary/). MIT license.
