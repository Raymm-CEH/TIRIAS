"""Local command capture with faster-whisper. Same interface as main.VoiceInput.

Audio stays in memory. Nothing is saved or uploaded.
"""
import time

import numpy as np

from main import VoiceInputError

CAPTURE_RATE = 48000  # this ThinkPad's mic runs at 48 kHz
WHISPER_RATE = 16000
CHUNK = 4800  # 100 ms at 48 kHz
PROMPT = (
    "TIRIAS commands: open terminal, open settings, open my files, open my browser, "
    "open control center, search for, what time is it."
)


class WhisperVoiceInput:
    def __init__(self, model_name="base.en", device=None, max_seconds=10,
                 silence_seconds=0.8, wait_seconds=5.0):
        self.model_name = model_name
        self.device = device
        self.max_seconds = max(3, int(max_seconds))
        self.silence_chunks = max(2, int(silence_seconds * 10))
        self.wait_seconds = wait_seconds
        self._model = None

    @property
    def ready(self):
        try:
            import faster_whisper  # noqa: F401
            import sounddevice  # noqa: F401
            import scipy.signal  # noqa: F401
        except Exception:
            return False
        return True

    def status(self):
        if not self.ready:
            return "Voice input: faster-whisper, sounddevice or scipy is missing."
        return f"Voice input: ready. Whisper '{self.model_name}' runs locally on this computer."

    def list_devices(self):
        import sounddevice as sd
        lines = [f"  [{i}] {d['name']} (inputs: {d['max_input_channels']})"
                 for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
        return "Available microphone inputs:\n" + "\n".join(lines)

    def _record(self):
        import sounddevice as sd

        chunks, levels = [], []
        spoken = False
        quiet = 0
        threshold = 300.0
        started = time.monotonic()
        with sd.InputStream(samplerate=CAPTURE_RATE, channels=1, dtype="int16",
                            blocksize=CHUNK, device=self.device) as stream:
            while time.monotonic() - started < self.max_seconds:
                data, _ = stream.read(CHUNK)
                block = data[:, 0]
                chunks.append(block.copy())
                level = float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))
                if len(levels) < 3:  # measure the room noise at the start
                    levels.append(level)
                    if len(levels) == 3:
                        threshold = max(300.0, min(levels) * 3.0)
                    continue
                if level > threshold:
                    spoken, quiet = True, 0
                elif spoken:
                    quiet += 1
                    if quiet >= self.silence_chunks:
                        break
                elif time.monotonic() - started > self.wait_seconds:
                    return None
        return np.concatenate(chunks) if spoken else None

    def listen_once(self):
        try:
            from faster_whisper import WhisperModel
            from scipy.signal import resample_poly

            audio = self._record()
            if audio is None:
                return ""
            mono16 = resample_poly(audio.astype(np.float32) / 32768.0, 1,
                                   CAPTURE_RATE // WHISPER_RATE).astype(np.float32)
            if self._model is None:
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            segments, _ = self._model.transcribe(
                mono16, language="en", vad_filter=True, beam_size=1,
                condition_on_previous_text=False, initial_prompt=PROMPT,
            )
            return " ".join(s.text.strip() for s in segments).strip()
        except Exception as exc:
            raise VoiceInputError(f"Whisper voice input failed: {exc}") from exc
