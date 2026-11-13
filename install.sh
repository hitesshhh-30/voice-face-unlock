#!/usr/bin/env bash
# Installs voice-face-unlock for the current user (no sudo needed).
set -euo pipefail
APP=voice-face-unlock
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/$APP"
M="$DATA/models"
SRC="$(cd "$(dirname "$0")" && pwd)"

echo "==> Python environment"
python3 -m venv "$DATA/venv"
"$DATA/venv/bin/pip" install -q --upgrade pip
"$DATA/venv/bin/pip" install -q "$SRC"

echo "==> Models (offline after this)"
mkdir -p "$M"
dl() { [ -s "$M/$1" ] || curl -fL --progress-bar -o "$M/$1" "$2"; }
dl yunet.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
dl sface.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx
dl face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
dl speaker.onnx https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34.onnx
if [ ! -d "$M/vosk" ]; then
  curl -fL --progress-bar -o "$M/vosk.zip" https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
  (cd "$M" && unzip -q vosk.zip && rm vosk.zip && mv -T vosk-model-small-en-us-0.15 vosk)
fi

echo "==> Command: ~/.local/bin/$APP"
mkdir -p "$HOME/.local/bin"
ln -sf "$DATA/venv/bin/$APP" "$HOME/.local/bin/$APP"

echo "==> Service (not started yet)"
mkdir -p "$HOME/.config/systemd/user"
cp "$SRC/systemd/$APP.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload

cat <<MSG

Installed. Next:
  1. $APP enroll-voice
  2. $APP enroll-face
  3. $APP test
  4. systemctl --user enable --now $APP
MSG
