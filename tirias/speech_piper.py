"""Natural-sounding spoken replies with Piper, falling back to eSpeak NG."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from main import SpeechOutput

VOICE = "en_US-lessac-medium"
VOICE_DIR = Path(__file__).resolve().parents[1] / "models" / "piper"  # git-ignored


class PiperSpeechOutput(SpeechOutput):
    """Same interface as SpeechOutput. Audio is generated and played locally."""

    def __init__(self, voice=VOICE, voice_dir=VOICE_DIR, **kwargs):
        super().__init__(**kwargs)
        self.piper_voice = voice
        self.voice_dir = Path(voice_dir)
        self.player = shutil.which("aplay") or shutil.which("paplay")
        self.piper_ready = (
            (self.voice_dir / f"{voice}.onnx").is_file() and self.player is not None
        )
        if self.piper_ready:
            self.available = True
            self.enabled = True

    def _speak_piper(self, text):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "reply.wav"
                done = subprocess.run(
                    [sys.executable, "-m", "piper", "-m", self.piper_voice,
                     "--data-dir", str(self.voice_dir), "-f", str(out)],
                    input=text, text=True, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=40, check=False,
                )
                if done.returncode != 0 or not out.is_file():
                    return False
                command = [self.player] + (["-q"] if self.player.endswith("aplay") else [])
                subprocess.run(command + [str(out)], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=60, check=False)
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def speak(self, text):
        if not self.enabled or not self.available or not str(text).strip():
            return False
        if self.piper_ready and self._speak_piper(self.prepare_text(text)):
            return True
        if not self.binary:
            return False
        return super().speak(text)
