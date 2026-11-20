#!/usr/bin/env python3
"""TIRIAS wake-word voice loop: wake word -> listen -> command router -> spoken reply.

Run from the project folder with the .venv active:
    python wake_listener.py --dry-run     # hear and print only, execute nothing
    python wake_listener.py               # full loop
    python wake_listener.py --model path/to/tirias.onnx   # custom wake word later

Audio stays in memory. The wake-word microphone stream is closed while Tirias listens
for a command and while it speaks, so it can never trigger on its own voice.
"""
import argparse
import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np
import openwakeword
import sounddevice as sd
from openwakeword.model import Model

from main import TIRIASCore, VoiceInputError, dispatch_voice_transcript
from tirias.conversation import ConversationEngine
from tirias.providers.fallback import FallbackProvider
from tirias.providers.ollama_provider import OllamaProvider
from tirias.providers.openai_provider import OpenAIProvider

FRAME = 1280  # 80 ms at 16 kHz
DEFAULT_MODEL = os.path.join(
    os.path.dirname(openwakeword.__file__), "resources", "models", "hey_jarvis_v0.1.onnx"
)


def load_model(path):
    try:
        return Model(wakeword_model_paths=[path])
    except TypeError:
        return Model(wakeword_model_paths=[path], inference_framework="onnx")


def build_core():
    conversation = ConversationEngine(
        provider=FallbackProvider([OllamaProvider(), OpenAIProvider()])
    )
    return TIRIASCore(conversation=conversation)


def open_stream(device):
    for rate in (16000, 48000):
        factor = rate // 16000
        try:
            stream = sd.InputStream(
                samplerate=rate, channels=1, dtype="int16",
                blocksize=FRAME * factor, device=device,
            )
            stream.start()
            return stream, factor
        except Exception as err:
            last_error = err
    raise SystemExit(f"Could not open the microphone: {last_error}")


def wait_for_wake(stream, factor, model, threshold, consecutive):
    """Block until the score stays at or above the threshold for N frames in a row."""
    streak = 0
    while True:
        data, _ = stream.read(FRAME * factor)
        audio = data[:, 0]
        if factor > 1:
            audio = audio.reshape(-1, factor).astype(np.float32).mean(axis=1).astype(np.int16)
        score = max(model.predict(audio).values())
        streak = streak + 1 if score >= threshold else 0
        if streak >= consecutive:
            return score


def make_cue_file(tones):
    """Write a short chime (list of (Hz, seconds)) to a temp WAV file; return its path."""
    rate = 16000
    parts = []
    for freq, seconds in tones:
        t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
        parts.append(np.sin(2 * np.pi * freq * t) * np.hanning(t.size) * 0.4)
    pcm = (np.concatenate(parts) * 32767).astype(np.int16)
    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    handle.close()
    with wave.open(handle.name, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    atexit.register(lambda path=handle.name: os.path.exists(path) and os.remove(path))
    return handle.name


def play_cue(path):
    player = shutil.which("aplay") or shutil.which("paplay")
    if not path or not player:
        return
    command = [player] + (["-q"] if player.endswith("aplay") else []) + [path]
    try:
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def notify(message):
    if not shutil.which("notify-send"):
        return
    try:
        subprocess.Popen(["notify-send", "-t", "3000", "TIRIAS", message],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def run(args):
    core = build_core()
    listen_cue = make_cue_file([(660, 0.09), (880, 0.09)]) if args.cue == "beep" else None
    giveup_cue = make_cue_file([(440, 0.12), (330, 0.14)]) if args.cue == "beep" else None
    if args.stt == "whisper":
        from tirias.voice_whisper import WhisperVoiceInput
        core.voice_input = WhisperVoiceInput(model_name=args.whisper_model, device=args.device)
    if args.tts == "piper":
        from tirias.speech_piper import PiperSpeechOutput
        speech = PiperSpeechOutput()
        print("Speech: Piper voice." if speech.piper_ready
              else "Speech: Piper voice not found; using eSpeak NG.")
        core.speech = speech
    print(core.voice_input.status())
    model = load_model(args.model)
    mode = "DRY RUN (nothing is executed)" if args.dry_run else "live"
    print(f"Wake listener ready [{mode}]. Say the wake word. Ctrl+C to stop.")

    while True:
        stream, factor = open_stream(args.device)
        try:
            score = wait_for_wake(stream, factor, model, args.threshold, args.frames)
        finally:
            stream.stop()
            stream.close()

        print(f"\nWake word heard (score {score:.2f}). Listening for your command...")
        notify("Listening...")
        play_cue(listen_cue)  # blocking and short, so it is over before capture starts
        try:
            transcript = core.voice_input.listen_once()
        except VoiceInputError as exc:
            print(exc)
            transcript = ""
            time.sleep(2)

        if not transcript:
            print("(no command heard)")
            notify("Didn't catch a command.")
            play_cue(giveup_cue)
        else:
            print(f'You said: "{transcript}"')
            if not args.dry_run:
                keep, text = dispatch_voice_transcript(core, transcript)
                print(f"TIRIAS > {text}")
                core.speak_response(text)  # blocking; the mic is closed meanwhile
                if not keep:
                    return

        model = load_model(args.model)  # fresh detector state after every wake
        time.sleep(args.cooldown)


def main():
    parser = argparse.ArgumentParser(description="TIRIAS wake-word voice loop")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="wake word .onnx file")
    parser.add_argument("--device", default=None, help="input device number")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--frames", type=int, default=2, help="consecutive frames needed")
    parser.add_argument("--cooldown", type=float, default=2.0, help="seconds to ignore after a wake")
    parser.add_argument("--tts", choices=["piper", "espeak"], default="piper",
                        help="voice for spoken replies")
    parser.add_argument("--stt", choices=["vosk", "whisper"], default="vosk",
                        help="speech recognizer for the command after the wake word")
    parser.add_argument("--whisper-model", default="base.en", help="tiny.en, base.en or small.en")
    parser.add_argument("--cue", choices=["beep", "none"], default="beep",
                        help="chime when the wake word is heard")
    parser.add_argument("--dry-run", action="store_true", help="print what was heard; run nothing")
    args = parser.parse_args()
    if args.device is not None:
        args.device = int(args.device)
    try:
        run(args)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
