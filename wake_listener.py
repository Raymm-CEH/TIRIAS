#!/usr/bin/env python3
"""TIRIAS v0.7 opt-in wake phrase listener using local Vosk recognition.

This is a software wake-phrase prototype, not a dedicated low-power wake-word model.
It continuously processes microphone audio locally while running. Audio is not saved.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from main import TIRIASCore, VoiceInput, VoiceInputError, dispatch_voice_transcript

WAKE_PHRASES = ("hey tirias", "hey tirias", "okay tirias", "ok tirias")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip(" .,!?\t\n")


def split_wake_phrase(text: str):
    """Return (wake_detected, words_after_wake_phrase)."""
    normalized = clean(text)
    for phrase in WAKE_PHRASES:
        pos = normalized.find(phrase)
        if pos >= 0:
            return True, normalized[pos + len(phrase):].strip(" .,!?\t\n")
    return False, ""


def main() -> int:
    voice = VoiceInput()
    if not voice.ready:
        print(voice.status())
        print("Run 'bash setup_voice.sh' from this project folder first.")
        return 2

    try:
        import sounddevice as sd
        from vosk import KaldiRecognizer, Model, SetLogLevel
    except Exception as exc:
        print(f"Wake listener dependencies unavailable: {exc}")
        print("Run 'bash setup_voice.sh' from this project folder.")
        return 2

    SetLogLevel(-1)
    try:
        model = Model(str(voice.model_path))
    except Exception as exc:
        print(f"Couldn't load the local Vosk model: {exc}")
        return 2

    core = TIRIASCore(voice_input=voice)
    import numpy as np
    from scipy.signal import resample_poly
    capture_rate = 48000
    recognizer = KaldiRecognizer(model, 16000)
    import queue
    audio_queue = queue.Queue(maxsize=64)

    def callback(indata, frames, time_info, status):
        try:
            audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            pass

    print("TIRIAS v0.7 — Wake phrase prototype")
    print("Listening locally for 'Hey TIRIAS'. Say the wake phrase, then a command.")
    print("Example: 'Hey TIRIAS' (pause), then 'What time is it?'")
    print("Microphone is active until you press Ctrl+C. No audio is saved.")
    core.speak_response("Wake phrase listener is active. Say Hey TIRIAS when you need me.")
    armed_until = 0.0
    armed_seconds = 8.0

    try:
        with sd.RawInputStream(device=0, samplerate=capture_rate, blocksize=12000,
                               dtype="int16", channels=1, callback=callback):
            while True:
                try:
                    chunk = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    if armed_until and time.monotonic() > armed_until:
                        armed_until = 0.0
                        print("Wake session expired. Say 'Hey TIRIAS' to try again.")
                    continue

                audio = np.frombuffer(chunk, dtype=np.int16)
                audio = resample_poly(audio, 1, 3).astype(np.int16)
                chunk = audio.tobytes()
                if not recognizer.AcceptWaveform(chunk):
                    continue
                result = json.loads(recognizer.Result())
                transcript = clean(str(result.get("text", "")))
                if not transcript:
                    continue

                if armed_until and time.monotonic() <= armed_until:
                    print(f"You > {transcript}")
                    keep_running, response = dispatch_voice_transcript(core, transcript)
                    print(f"TIRIAS > {response}\n")
                    core.speak_response(response)
                    armed_until = 0.0
                    recognizer.Reset()
                    if not keep_running:
                        return 0
                    continue

                detected, trailing = split_wake_phrase(transcript)
                if detected:
                    print("Wake phrase detected.")
                    if trailing:
                        print(f"You > {trailing}")
                        keep_running, response = dispatch_voice_transcript(core, trailing)
                        print(f"TIRIAS > {response}\n")
                        core.speak_response(response)
                        if not keep_running:
                            return 0
                    else:
                        armed_until = time.monotonic() + armed_seconds
                        print(f"I'm listening for your command for {int(armed_seconds)} seconds…")
                        core.speak_response("Yes? I'm listening.")
                recognizer.Reset()
    except KeyboardInterrupt:
        print("\nTIRIAS wake listener stopped. Microphone released.")
        core.speak_response("Wake listener stopped.")
        return 0
    except Exception as exc:
        print(f"Wake listener error: {exc}")
        print("Check 'voice devices' and your desktop microphone permissions.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
