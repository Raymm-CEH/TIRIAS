#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_DIR="$ROOT/models/$MODEL_NAME"
LEGACY_MODEL_DIR="$ROOT/../tirias-core-v0.5/models/$MODEL_NAME"
MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

printf '\nTIRIAS v0.6 voice setup\n'
printf 'This installs local Python audio/speech packages and downloads an English model.\n\n'

sudo apt update
sudo apt install -y --no-upgrade python3-venv libportaudio2 curl unzip

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    python3 -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install "vosk==0.3.45" "sounddevice==0.5.6"

mkdir -p "$ROOT/models"
if [[ ! -d "$MODEL_DIR/am" || ! -d "$MODEL_DIR/conf" ]]; then
    if [[ -d "$LEGACY_MODEL_DIR/am" && -d "$LEGACY_MODEL_DIR/conf" ]]; then
        printf '\nReusing the Vosk model from the adjacent TIRIAS v0.5 folder.\n'
        ln -s "$LEGACY_MODEL_DIR" "$MODEL_DIR"
    fi
fi
if [[ ! -d "$MODEL_DIR/am" || ! -d "$MODEL_DIR/conf" ]]; then
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT
    printf '\nDownloading the official Vosk small English model (about 40 MB)...\n'
    curl --fail --location --retry 3 --output "$TMP_DIR/model.zip" "$MODEL_URL"
    unzip -q "$TMP_DIR/model.zip" -d "$ROOT/models"
fi

if [[ ! -d "$MODEL_DIR/am" || ! -d "$MODEL_DIR/conf" ]]; then
    printf '\nERROR: the speech model did not extract to the expected location: %s\n' "$MODEL_DIR" >&2
    exit 1
fi

printf '\nVoice setup complete. Start TIRIAS using:\n  bash run_tirias.sh\n'
printf 'Then type: voice input status\n'
printf 'To give a spoken command, type: listen\n\n'
