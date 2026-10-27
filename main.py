#!/usr/bin/env python3
"""TIRIAS Core v0.6: natural-language commands with optional speech input/output."""
from datetime import datetime
from pathlib import Path
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import time

VERSION = "v0.6"

# Only these known applications may be launched. No user-provided shell text is used.
APPS = {
    "terminal": [["x-terminal-emulator"], ["xfce4-terminal"], ["gnome-terminal"], ["konsole"], ["xterm"]],
    "files": [["xdg-open", "{target}"], ["thunar", "{target}"], ["nautilus", "{target}"], ["dolphin", "{target}"], ["pcmanfm", "{target}"]],
    "browser": [["firefox"], ["chromium"], ["chromium-browser"], ["brave-browser"]],
    "settings": [["xfce4-settings-manager"], ["gnome-control-center"], ["systemsettings"]],
}

NAVIGATION_ALIASES = {
    "home": {
        "go home", "go to home", "go to my home folder", "take me home",
        "take me to home", "switch to home", "switch to my home folder",
        "navigate to home", "navigate to my home folder", "return home",
    },
    "downloads": {
        "go downloads", "go to downloads", "go to my downloads", "go to my downloads folder",
        "take me to downloads", "take me to my downloads", "switch to downloads",
        "switch to my downloads folder", "navigate to downloads", "navigate to my downloads",
    },
    "documents": {
        "go documents", "go to documents", "go to my documents", "go to my documents folder",
        "take me to documents", "take me to my documents", "switch to documents",
        "switch to my documents folder", "navigate to documents", "navigate to my documents",
    },
    "workspace": {
        "go workspace", "go to workspace", "go to my workspace", "go to tirias workspace",
        "take me to workspace", "take me to my workspace", "switch to workspace",
        "switch to tirias workspace", "navigate to workspace", "navigate to my workspace",
    },
}

FOLDER_SHOW_ALIASES = {
    "home": {"show me my home folder", "open home folder", "open my home folder", "show my home folder"},
    "downloads": {"show me my downloads", "show my downloads", "open downloads", "open my downloads", "open downloads folder", "open my downloads folder", "show me my downloads folder"},
    "documents": {"show me my documents", "show my documents", "open documents", "open my documents", "open documents folder", "open my documents folder", "show me my documents folder"},
    "workspace": {"show me my workspace", "open workspace", "open my workspace", "open tirias workspace", "show me tirias workspace"},
}

APP_ALIASES = {
    "terminal": {"terminal", "a terminal", "the terminal", "command terminal"},
    "files": {"files", "file manager", "folder window", "my files"},
    "browser": {"browser", "web browser", "internet browser", "the browser", "my browser"},
    "settings": {"settings", "system settings", "computer settings"},
    "control-center": {"control center", "tirias control center", "dashboard", "tirias dashboard"},
}

TIME_ALIASES = {
    "time", "what time is it", "what's the time", "what is the time", "what time is it right now",
    "tell me the time", "tell me what time it is", "can you tell me the time", "current time",
}
STATUS_ALIASES = {
    "status", "system status", "show status", "show me the status", "show system info",
    "show system information", "show me system info", "show me system information", "how are you running", "what is your status",
}
WHERE_ALIASES = {
    "where am i", "where are we", "current folder", "what folder am i in", "which folder am i in",
    "where are you working", "where is tirias working", "what is the current folder", "current directory", "pwd",
}
LIST_ALIASES = {
    "list files", "show files", "show me the files", "show me my files", "list my files",
    "what's in this folder", "what is in this folder", "show me what's in this folder",
    "show me what is in this folder", "show me this folder", "list this folder", "show folder contents",
    "what files are here", "show files here", "list files here", "what's here", "what is here",
}
DISK_ALIASES = {
    "disk space", "check disk space", "show disk space", "check my disk space", "check disk usage",
    "how much space do i have left", "how much space is left", "how much space is left on my computer",
    "how much disk space is left", "how much free space do i have", "how much space is free",
    "how much storage do i have left", "how much storage is left", "check my storage",
    "show available storage", "show me available space", "storage remaining", "free disk space",
}

QUIT_ALIASES = {"quit", "exit", "goodbye", "close tirias", "shut down tirias", "stop tirias"}
CANCEL_ALIASES = {"cancel", "cancel that", "never mind", "nevermind", "forget it", "don't do it", "do not do it", "cancel the action"}
CONFIRM_ALIASES = {"confirm", "yes", "yes please", "do it", "proceed", "go ahead", "confirm action"}


VOICE_ON_ALIASES = {
    "voice on", "turn voice on", "turn on voice", "enable voice", "enable speech",
    "turn on speech", "speech on", "speak responses", "start speaking",
}
VOICE_OFF_ALIASES = {
    "voice off", "turn voice off", "turn off voice", "disable voice", "disable speech",
    "turn off speech", "speech off", "mute tirias", "stop speaking",
}
VOICE_STATUS_ALIASES = {
    "voice status", "speech status", "is voice on", "is speech on", "are you speaking",
}


class SpeechOutput:
    """Optional local text-to-speech using the installed eSpeak NG executable."""

    def __init__(self, binary=None, enabled=None, voice="en-us", speed=165):
        self.binary = binary if binary is not None else shutil.which("espeak-ng")
        self.available = bool(self.binary)
        self.enabled = self.available if enabled is None else bool(enabled and self.available)
        self.voice = voice
        self.speed = int(speed)

    def enable(self):
        if not self.available:
            self.enabled = False
            return False
        self.enabled = True
        return True

    def disable(self):
        self.enabled = False

    @staticmethod
    def prepare_text(text):
        """Keep spoken output concise; full results remain visible in the terminal."""
        spoken = re.sub(r"\s+", " ", str(text)).strip()
        if len(spoken) > 280:
            shortened = spoken[:250].rsplit(" ", 1)[0].rstrip(" ,.;:")
            spoken = shortened + ". More details are displayed on screen."
        return spoken

    def speak(self, text):
        """Speak text through stdin, never a shell; return False if TTS fails."""
        if not self.enabled or not self.available or not str(text).strip():
            return False
        spoken = self.prepare_text(text)
        try:
            completed = subprocess.run(
                [self.binary, "-v", self.voice, "-s", str(self.speed), "--stdin"],
                input=spoken,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=25,
                check=False,
            )
            return completed.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False



LISTEN_ALIASES = {
    "listen", "start listening", "listen for a command", "listen for commands",
    "listen for my command", "use microphone", "push to talk", "voice command",
}
VOICE_INPUT_STATUS_ALIASES = {
    "voice input status", "microphone status", "check microphone", "check voice input",
    "is microphone ready", "is voice input ready",
}
VOICE_DEVICE_ALIASES = {
    "voice devices", "list audio devices", "list microphones", "show microphones",
}


class VoiceInputError(RuntimeError):
    """Raised when microphone capture or offline speech recognition is unavailable."""


class VoiceInput:
    """Optional push-to-talk speech recognition using Vosk and sounddevice.

    Audio is processed locally and held in memory only. Nothing is saved or uploaded.
    """

    MODEL_NAME = "vosk-model-small-en-us-0.15"

    def __init__(self, model_path=None, sample_rate=16000, max_seconds=10):
        default_model = Path(__file__).resolve().parent / "models" / self.MODEL_NAME
        self.model_path = Path(
            model_path or os.environ.get("TIRIAS_VOSK_MODEL", str(default_model))
        ).expanduser().resolve()
        self.sample_rate = int(sample_rate)
        self.max_seconds = max(3, int(max_seconds))
        self._model = None

    def _setup_errors(self):
        errors = []
        try:
            import sounddevice  # noqa: F401
        except Exception:
            errors.append("Python microphone package 'sounddevice' is missing or unavailable")
        try:
            import vosk  # noqa: F401
        except Exception:
            errors.append("offline speech-recognition package 'vosk' is missing")
        if not (self.model_path.is_dir() and (self.model_path / "am").is_dir() and
                (self.model_path / "conf").is_dir()):
            errors.append(f"offline English model is missing at {self.model_path}")
        return errors

    @property
    def ready(self):
        return not self._setup_errors()

    def status(self):
        errors = self._setup_errors()
        if errors:
            return "Voice input: setup needed. " + "; ".join(errors) + ". Run 'bash setup_voice.sh' from this TIRIAS project folder."
        return f"Voice input: ready. Recognition runs locally using the model at {self.model_path}."

    def list_devices(self):
        try:
            import sounddevice as sd
        except Exception:
            return "Audio-device listing is unavailable because 'sounddevice' isn't installed. Run 'bash setup_voice.sh'."
        try:
            devices = sd.query_devices()
        except Exception as exc:
            return f"I couldn't list audio devices: {exc}"
        lines = []
        for index, device in enumerate(devices):
            if int(device.get("max_input_channels", 0)) > 0:
                lines.append(f"  [{index}] {device.get('name', 'Unnamed input')} (inputs: {device.get('max_input_channels')})")
        if not lines:
            return "No microphone input devices were reported. Check your microphone and Linux audio settings."
        return "Available microphone inputs:\n" + "\n".join(lines)

    def listen_once(self):
        """Listen for one utterance, stopping after Vosk detects a pause or timeout."""
        errors = self._setup_errors()
        if errors:
            raise VoiceInputError(self.status())

        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel
            SetLogLevel(-1)
            if self._model is None:
                self._model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(self._model, self.sample_rate)
            audio_queue = queue.Queue(maxsize=64)

            def audio_callback(indata, frames, time_info, status):
                # Keep callbacks small; dropped blocks are safer than blocking the audio thread.
                try:
                    audio_queue.put_nowait(bytes(indata))
                except queue.Full:
                    pass

            deadline = time.monotonic() + self.max_seconds
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                while time.monotonic() < deadline:
                    remaining = max(0.05, deadline - time.monotonic())
                    try:
                        chunk = audio_queue.get(timeout=min(0.5, remaining))
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(chunk):
                        result = json.loads(recognizer.Result())
                        transcript = str(result.get("text", "")).strip()
                        if transcript:
                            return transcript

            result = json.loads(recognizer.FinalResult())
            return str(result.get("text", "")).strip()
        except VoiceInputError:
            raise
        except Exception as exc:
            raise VoiceInputError(
                "Microphone capture failed. Check that a microphone is connected and permitted, "
                "then run 'voice devices' to inspect input devices. Details: " + str(exc)
            ) from exc


def is_listen_request(raw: str) -> bool:
    """True only for explicit push-to-talk phrases, not general conversation."""
    c = normalize(raw)
    c = re.sub(r"^please,\s*", "please ", c)
    if c.startswith("please "):
        c = c[7:].strip()
    return c in LISTEN_ALIASES


def dispatch_voice_transcript(core, transcript):
    """Pass recognized words through the same restricted command router as typed text."""
    transcript = str(transcript or "").strip()
    if not transcript:
        return True, "I didn't catch a command. Type 'listen' to try again, or enter a command."
    return core.handle_command(transcript)

def normalize(text: str) -> str:
    """Normalize a spoken/typed phrase without interpreting it as executable code."""
    text = text.strip().replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[.!?]+$", "", text).strip()
    return text.casefold()


class TIRIASCore:
    def __init__(self, home=None, audit_path=None, speech=None, voice_input=None):
        self.home = Path(home or Path.home()).expanduser().resolve()
        self.current_dir = self.home
        self.workspace = self.home / "TIRIAS-Workspace"
        self.pending = None
        self.speech = speech if speech is not None else SpeechOutput()
        self.voice_input = voice_input if voice_input is not None else VoiceInput()
        self.audit_path = Path(audit_path) if audit_path else self.home / ".local/state/tirias/audit.log"

    def speak_response(self, response):
        """Speak a response if spoken output is enabled; terminal output is unaffected."""
        return self.speech.speak(response)

    def audit(self, event):
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as f:
                f.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')} | {event}\n")
        except OSError:
            pass

    def launch(self, app, target=None):
        if app == "control-center":
            control_center = Path(__file__).resolve().with_name("control_center.py")
            if not control_center.is_file():
                return "TIRIAS Control Center is missing from this project folder."
            try:
                check = subprocess.run(
                    [sys.executable, "-c", "import tkinter"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    text=True, timeout=5, check=False,
                )
                if check.returncode != 0:
                    return ("TIRIAS Control Center needs Python Tkinter. On Kali/Debian, install it with "
                            "'sudo apt install python3-tk', then try again. Details: " +
                            (check.stderr.strip().splitlines()[-1] if check.stderr.strip() else "Tkinter unavailable."))
                subprocess.Popen(
                    [sys.executable, str(control_center)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True,
                )
                self.audit("launched_app app=control-center")
                return "Opening the TIRIAS Control Center."
            except (OSError, subprocess.SubprocessError) as exc:
                return f"I couldn't open the TIRIAS Control Center: {exc}"
        for template in APPS[app]:
            if shutil.which(template[0]):
                args = [x.replace("{target}", str(target)) for x in template]
                try:
                    subprocess.Popen(args, start_new_session=True)
                    self.audit(f"launched_app app={app}")
                    return f"Opening {app}."
                except OSError as e:
                    return f"I couldn't open {app}: {e}"
        return f"I couldn't find a supported {app} application on this computer."

    def list_files(self):
        try:
            entries = sorted(self.current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
        except OSError as e:
            return f"I couldn't list that folder: {e}"
        if not entries:
            return f"{self.current_dir} is empty."
        lines = [f"  {p.name}{'/' if p.is_dir() else ''}" for p in entries[:30]]
        if len(entries) > 30:
            lines.append(f"  ... and {len(entries)-30} more")
        return f"Contents of {self.current_dir}:\n" + "\n".join(lines)

    def request_folder(self, name):
        name = name.strip()
        if not name or name in {".", ".."} or name.startswith(".") or any(c in name for c in "/\\\0"):
            return "Choose a simple folder name without slashes or a leading dot."
        if len(name) > 64 or name.strip() != name or any(ord(c) < 32 for c in name):
            return "Use a folder name of 1–64 characters, without control characters or extra spaces."
        self.pending = ("create_folder", name)
        return f"This will create '{name}' inside {self.workspace}. Type 'confirm' (or 'yes') to proceed, or 'cancel' to discard it."

    def confirm(self):
        if not self.pending:
            return "There is no pending action to confirm."
        action, name = self.pending
        self.pending = None
        if action != "create_folder":
            return "That pending action is not supported."
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            target = (self.workspace / name).resolve()
            if target.parent != self.workspace.resolve():
                return "Blocked: target is outside the TIRIAS workspace."
            target.mkdir(exist_ok=False)
            self.audit("confirmed_action=create_folder")
            return f"Created folder: {target}"
        except FileExistsError:
            return "A file or folder with that name already exists. Nothing was changed."
        except OSError as e:
            return f"I couldn't create that folder: {e}"

    def _destination(self, key):
        return {
            "home": self.home,
            "downloads": self.home / "Downloads",
            "documents": self.home / "Documents",
            "workspace": self.workspace,
        }[key]

    def go_to(self, key):
        dest = self._destination(key)
        try:
            if key == "workspace":
                dest.mkdir(parents=True, exist_ok=True)
            elif not dest.exists():
                return f"That folder doesn't exist: {dest}"
            if not dest.is_dir():
                return f"That destination isn't a folder: {dest}"
            self.current_dir = dest.resolve()
            self.audit(f"changed_session_directory destination={key}")
            return f"TIRIAS's current folder is now {self.current_dir}."
        except OSError as e:
            return f"I couldn't switch folders: {e}"

    def show_folder(self, key):
        dest = self._destination(key)
        try:
            if key == "workspace":
                dest.mkdir(parents=True, exist_ok=True)
            elif not dest.exists():
                return f"That folder doesn't exist: {dest}"
            if not dest.is_dir():
                return f"That destination isn't a folder: {dest}"
            self.current_dir = dest.resolve()
            self.audit(f"opened_known_folder destination={key}")
            return self.launch("files", self.current_dir)
        except OSError as e:
            return f"I couldn't open that folder: {e}"

    def _parse_folder_request(self, command):
        # Name is passed only to pathlib; it is never interpreted by a shell.
        match = re.fullmatch(
            r"(?:please\s+)?(?:(?:create|make|add)(?:\s+me)?(?:\s+a)?(?:\s+new)?\s+folder|new\s+folder)\s+(?:(?:called|named|titled)\s+)?(.+)",
            command.strip(),
            flags=re.IGNORECASE,
        )
        return match.group(1).strip() if match else None

    def handle_command(self, raw):
        command = re.sub(r"\s+", " ", raw.strip().replace("’", "'").replace("‘", "'"))
        command = re.sub(r"^please,\s*", "", command, flags=re.IGNORECASE)
        c = normalize(command)
        if not c:
            return True, "I didn't catch a command. Type 'help' or ask me in plain language."

        # Only exit TIRIAS itself; no OS shutdown commands are performed.
        if c in QUIT_ALIASES:
            self.pending = None
            return False, "TIRIAS shutting down. Goodbye."
        if c.startswith("please ") and c[7:] in QUIT_ALIASES:
            self.pending = None
            return False, "TIRIAS shutting down. Goodbye."

        # Spoken output is optional; typed commands always remain available.
        base_command = c[7:] if c.startswith("please ") else c
        if base_command in VOICE_ON_ALIASES:
            if self.speech.enable():
                self.audit("spoken_responses=enabled")
                return True, "Voice responses are enabled."
            return True, ("I couldn't enable spoken responses because espeak-ng isn't installed or available. "
                          "Install it with: sudo apt install espeak-ng. Typed commands still work.")
        if base_command in VOICE_OFF_ALIASES:
            self.speech.disable()
            self.audit("spoken_responses=disabled")
            return True, "Voice responses are disabled. You can still type commands."
        if base_command in VOICE_STATUS_ALIASES:
            availability = "available" if self.speech.available else "not installed"
            state = "on" if self.speech.enabled else "off"
            return True, f"Speech engine: {availability}. Spoken responses: {state}."
        if base_command in VOICE_INPUT_STATUS_ALIASES:
            return True, self.voice_input.status()
        if base_command in VOICE_DEVICE_ALIASES:
            return True, self.voice_input.list_devices()
        if base_command in LISTEN_ALIASES:
            return True, "Push-to-talk is handled by the TIRIAS interactive loop. Type 'listen' at the main prompt to start microphone capture."

        if c in {"help", "commands", "what can you do", "what can you do for me", "show me your commands", "what commands do you know"}:
            return True, (
                f"TIRIAS Core {VERSION} — natural-language commands with optional voice input and spoken responses\n\n"
                "Try asking in different ways:\n"
                "  'What time is it?' / 'Tell me the time'\n"
                "  'Show me system info' / 'How are you running?'\n"
                "  'Where am I?' / 'What folder am I in?'\n"
                "  'Take me to Downloads' / 'Go to my Documents'\n"
                "  'Show me my downloads' / 'Open my workspace'\n"
                "  'Show me what's in this folder' / 'List files here'\n"
                "  'How much space do I have left?'\n"
                "  'Launch my browser' / 'Open a terminal' / 'Open settings'\n"
                "  'Create a folder called Projects' — asks before creating\n"
                "  'Confirm' or 'yes' / 'Cancel' or 'never mind'\n"
                "  'Voice on' / 'Voice off' / 'Voice status'\n"
                "  'Listen' — push-to-talk, up to 10 seconds; stops after a pause\n"
                "  'Voice input status' / 'Voice devices'\n"
                "  'Open Control Center' — launch the TIRIAS desktop dashboard\n\n"
                "Spoken responses use local eSpeak NG when installed. Speech recognition uses a local Vosk model; "
                "audio is processed in memory and not saved or uploaded. Commands are matched locally; "
                "arbitrary shell commands are never executed."
            )

        if c in CANCEL_ALIASES or c.startswith("please ") and c[7:] in CANCEL_ALIASES:
            if self.pending:
                self.pending = None
                self.audit("cancelled_pending_action")
                return True, "Cancelled. No changes were made."
            return True, "There is no pending action to cancel."
        if c in CONFIRM_ALIASES or c.startswith("please ") and c[7:] in CONFIRM_ALIASES:
            return True, self.confirm()

        if c in TIME_ALIASES or c.startswith("please ") and c[7:] in TIME_ALIASES:
            return True, f"The system time is {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z').strip()}."
        if c in STATUS_ALIASES or c.startswith("please ") and c[7:] in STATUS_ALIASES:
            return True, (f"TIRIAS Core {VERSION} is running.\nOperating system: {platform.system()} {platform.release()}\n"
                f"Python: {platform.python_version()}\nCurrent folder: {self.current_dir}\nWorkspace: {self.workspace}\n"
                f"Pending action: {'yes' if self.pending else 'no'}\n"
                f"Speech engine: {'available' if self.speech.available else 'not installed'}\n"
                f"Spoken responses: {'on' if self.speech.enabled else 'off'}\n"
                f"{self.voice_input.status()}")
        if c in WHERE_ALIASES or c.startswith("please ") and c[7:] in WHERE_ALIASES:
            return True, f"TIRIAS is currently working in {self.current_dir}."

        # Navigation commands affect TIRIAS's session folder, not the parent terminal.
        for key, aliases in NAVIGATION_ALIASES.items():
            if c in aliases or (c.startswith("please ") and c[7:] in aliases):
                return True, self.go_to(key)

        # Requests to show/open a known folder open it in the file manager.
        for key, aliases in FOLDER_SHOW_ALIASES.items():
            if c in aliases or (c.startswith("please ") and c[7:] in aliases):
                return True, self.show_folder(key)

        if c in LIST_ALIASES or c.startswith("please ") and c[7:] in LIST_ALIASES:
            return True, self.list_files()
        if c in DISK_ALIASES or c.startswith("please ") and c[7:] in DISK_ALIASES:
            try:
                usage = shutil.disk_usage(self.home)
                gib = 1024 ** 3
                return True, f"Your home filesystem has {usage.free/gib:.1f} GiB free of {usage.total/gib:.1f} GiB."
            except OSError as e:
                return True, f"I couldn't check disk space: {e}"

        # Controlled app launch: accept exact patterns for allowlisted app names only.
        for app, names in APP_ALIASES.items():
            open_phrases = set()
            for name in names:
                open_phrases.update({f"open {name}", f"launch {name}", f"start {name}", f"open the {name}", f"launch the {name}", f"start the {name}"})
            if c in open_phrases or (c.startswith("please ") and c[7:] in open_phrases):
                if app == "files":
                    return True, self.launch("files", self.current_dir)
                return True, self.launch(app)

        folder_name = self._parse_folder_request(command)
        if folder_name is not None:
            return True, self.request_folder(folder_name)

        return True, "I don't recognize that request yet. Try 'help'. For safety, I never execute arbitrary terminal text."


def main():
    tirias = TIRIASCore()
    print(
        f"TIRIAS Core {VERSION}\nNatural-language commands with optional voice input/output. "
        "Type 'help' for examples.\n"
    )
    tirias.speak_response("TIRIAS is online. Voice interface ready. Type listen to give a spoken command.")
    while True:
        try:
            raw = input("You > ")
        except (EOFError, KeyboardInterrupt):
            print("\nTIRIAS > Shutting down.")
            break

        if is_listen_request(raw):
            print(f"\nTIRIAS > {tirias.voice_input.status()}")
            if not tirias.voice_input.ready:
                keep_running, response = True, tirias.voice_input.status()
            else:
                print(f"TIRIAS > Listening for up to {tirias.voice_input.max_seconds} seconds. Say one command; it stops after a pause.\n")
                try:
                    transcript = tirias.voice_input.listen_once()
                    if transcript:
                        print(f"You (voice) > {transcript}")
                    keep_running, response = dispatch_voice_transcript(tirias, transcript)
                except VoiceInputError as exc:
                    keep_running, response = True, str(exc)
        else:
            keep_running, response = tirias.handle_command(raw)

        print(f"\nTIRIAS > {response}\n")
        tirias.speak_response(response)
        if not keep_running:
            break


if __name__ == "__main__":
    main()
