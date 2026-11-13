# voice-face-unlock 🥷

Unlock your Linux lock screen by saying a phrase, JARVIS-style:

> **You:** "Hey, the byte has landed."
> **Laptop:** "Impact confirmed. Ninja inside." 🔓

It only unlocks when **all three** pass:

| Check | Stops |
|---|---|
| 🎤 Phrase + **your voice** (speaker verification) | other people, wrong words |
| 📷 **Your face** on the infrared camera | voice recordings, phones/screens showing your photo |
| 👁️ **A blink** | printed photos |

Fail → it says *"Unknown entity. Face cached."* and saves an intruder photo locally.
After 3 failures it pauses for 60 s. Your **password always still works**.

100% offline. No root. No changes to PAM/login. Mic is only on while the screen is locked.

## Requirements
- Linux with GNOME (tested: Ubuntu 24.04, Wayland)
- Microphone, webcam (IR camera strongly recommended)
- Python 3.10+, `arecord`, `curl`, `unzip`; `spd-say` for talk-back

## Install
```bash
git clone <this repo> && cd voice-face-unlock
./install.sh
```

### IR camera light (most laptops need this on Linux)
If `voice-face-unlock snapshot` gives a black infrared image, install
[linux-enable-ir-emitter](https://github.com/EmixamPP/linux-enable-ir-emitter) and run
`linux-enable-ir-emitter configure` once (as your normal user). This app calls
`linux-enable-ir-emitter run` automatically before using the camera.

## Set up
```bash
voice-face-unlock snapshot --out /tmp     # see what each camera sensor sees
voice-face-unlock enroll-voice            # say the phrase 8 times
voice-face-unlock enroll-face             # look at the camera ~8 s (repeat w/ glasses, night light)
voice-face-unlock test                    # all checks, prints scores, does NOT unlock
systemctl --user enable --now voice-face-unlock
journalctl --user -u voice-face-unlock -f # watch logs
```

## Configure
Optional `~/.config/voice-face-unlock/config.toml`, e.g.:
```toml
phrase = "hey the byte has landed"
phrase_variants = ["hey the byte has landed", "hey the bite has landed"]
voice_threshold = 0.55
face_threshold = 0.45
face_camera = "ir"         # or "rgb" (less secure: a phone video could pass)
say_success = "Impact confirmed. Ninja inside."
```
All keys: see `voice_face_unlock/config.py`.

## Your data
Stored only in `~/.local/share/voice-face-unlock/` (voice/face embeddings — numbers, not
recordings or photos — plus intruder photos). Never in this repo; `.gitignore` blocks it.

## Honest security note
This is convenience + reasonable protection, not bank-grade. A determined attacker with your
voice *and* physical access to your live face could pass. Don't use it on shared/work machines.
After a reboot you still log in with your password (that also unlocks your keyring).

## Uninstall
```bash
systemctl --user disable --now voice-face-unlock
rm -rf ~/.local/share/voice-face-unlock ~/.config/systemd/user/voice-face-unlock.service ~/.local/bin/voice-face-unlock
```
