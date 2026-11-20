from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tirias.speech_piper import PiperSpeechOutput


def make_voice(tmp_path):
    (tmp_path / "v.onnx").write_bytes(b"x")
    return tmp_path


def test_not_ready_without_voice_file(tmp_path):
    speech = PiperSpeechOutput(voice="v", voice_dir=tmp_path)
    assert speech.piper_ready is False


def test_speaks_through_piper_then_player(tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "-f" in command:
            Path(command[command.index("-f") + 1]).write_bytes(b"RIFF")
        return SimpleNamespace(returncode=0)

    with patch("tirias.speech_piper.shutil.which", return_value="/usr/bin/aplay"), \
         patch("tirias.speech_piper.subprocess.run", side_effect=fake_run):
        speech = PiperSpeechOutput(voice="v", voice_dir=make_voice(tmp_path))
        assert speech.piper_ready is True
        assert speech.speak("hello there") is True
    assert "piper" in calls[0]
    assert calls[1][0] == "/usr/bin/aplay"


def test_piper_failure_without_espeak_returns_false(tmp_path):
    with patch("tirias.speech_piper.shutil.which", return_value="/usr/bin/aplay"), \
         patch("tirias.speech_piper.subprocess.run",
               return_value=SimpleNamespace(returncode=1)):
        speech = PiperSpeechOutput(voice="v", voice_dir=make_voice(tmp_path))
        speech.binary = None
        assert speech.speak("hello") is False
