#!/usr/bin/env python3
"""TIRIAS voice test: record a few seconds, transcribe locally, speak the result back.

Audio stays in memory. Nothing is uploaded. Only the downloaded models are saved.
Run from the project folder with the .venv active:  python voice_test.py
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

CAPTURE_RATE = 48000   # your ThinkPad mic works at 48 kHz, not 16 kHz
WHISPER_RATE = 16000
VOICE = "en_US-lessac-medium"
VOICE_DIR = Path(__file__).resolve().parent / "models" / "piper"  # models/ is git-ignored


def record(seconds, device):
    print(f"\nRecording for {seconds} seconds... speak now.")
    audio = sd.rec(int(seconds * CAPTURE_RATE), samplerate=CAPTURE_RATE,
                   channels=1, dtype="int16", device=device)
    sd.wait()
    audio = audio[:, 0]
    peak = int(np.abs(audio).max())
    print(f"Microphone peak level: {peak} / 32767")
    if peak < 300:
        print("That is very quiet. Check the mic is not muted, or try --device N.")
    # 48 kHz -> 16 kHz in one pass over the whole clip (avoids per-chunk edge artifacts)
    mono16 = resample_poly(audio.astype(np.float32) / 32768.0, 1, CAPTURE_RATE // WHISPER_RATE)
    return mono16.astype(np.float32)


def transcribe(audio, model_name):
    from faster_whisper import WhisperModel
    print(f"Loading Whisper '{model_name}' (the first run downloads it)...")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language="en", vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


def play(wav_path):
    for player in (["aplay", "-q"], ["paplay"]):
        if shutil.which(player[0]):
            subprocess.run(player + [str(wav_path)], check=False)
            return True
    print("No audio player found. Install one with: sudo apt install alsa-utils")
    return False


def speak_piper(text):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    if not (VOICE_DIR / f"{VOICE}.onnx").exists():
        print("Downloading the Piper voice (first run)...")
        subprocess.run([sys.executable, "-m", "piper.download_voices",
                        "--data-dir", str(VOICE_DIR), VOICE], check=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "reply.wav"
        subprocess.run([sys.executable, "-m", "piper", "-m", VOICE,
                        "--data-dir", str(VOICE_DIR), "-f", str(out)],
                       input=text, text=True, check=True)
        play(out)


def speak(text):
    try:
        speak_piper(text)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Piper failed ({exc}). Falling back to espeak-ng.")
        if shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", "--stdin"], input=text, text=True, check=False)


def main():
    parser = argparse.ArgumentParser(description="TIRIAS voice test")
    parser.add_argument("--seconds", type=int, default=5)
    parser.add_argument("--device", default=None, help="input device number or name (see --list)")
    parser.add_argument("--model", default="base.en", help="whisper model: tiny.en, base.en, small.en")
    parser.add_argument("--list", action="store_true", help="list audio devices and exit")
    args = parser.parse_args()

    if args.list:
        print(sd.query_devices())
        return 0

    device = args.device
    if device is not None:
        try:
            device = int(device)
        except ValueError:
            pass

    audio = record(args.seconds, device)
    text = transcribe(audio, args.model)
    if not text:
        print("\nI did not hear any words. Try again closer to the mic, or run with --list.")
        return 1
    print(f'\nI heard: "{text}"')
    speak(f"I heard you say: {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
