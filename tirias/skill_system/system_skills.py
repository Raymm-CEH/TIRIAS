"""System control skills: media, volume, brightness. They run only via the gateway.

Every command is a fixed list built from validated integers or booleans. No shell.
"""

import shutil
import subprocess

from jsonschema import Draft202012Validator

from tirias.skill_system.interface import ActionSpec, Skill, SkillManifest

SINK = "@DEFAULT_AUDIO_SINK@"
MIN_BRIGHTNESS = 5  # never allow a black screen

NO_ARGS = {"type": "object", "properties": {}, "additionalProperties": False}


def _int_schema(name, low, high):
    return {
        "type": "object",
        "properties": {name: {"type": "integer", "minimum": low, "maximum": high}},
        "required": [name],
        "additionalProperties": False,
    }


def _run(command):
    """Run one fixed command (never through a shell). Return stdout; raise OSError on failure."""
    executable = shutil.which(command[0])
    if executable is None:
        raise OSError(f"{command[0]} is not installed.")
    try:
        done = subprocess.run(
            [executable, *command[1:]], shell=False, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=5, check=False,
        )
    except subprocess.SubprocessError as error:
        raise OSError(str(error)) from error
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        raise OSError(detail[-1] if detail else f"{command[0]} failed.")
    return done.stdout


class _SystemSkill(Skill):
    SKILL_ID = ""
    NAME = ""
    DESCRIPTION = ""
    PERMISSION = ""
    SCHEMAS = {}

    def __init__(self, runner=None):
        self._runner = runner

    def _run(self, command):
        return (self._runner or _run)(command)  # looked up at call time so tests can patch it

    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            skill_id=self.SKILL_ID, name=self.NAME, version="1.0.0",
            description=self.DESCRIPTION, permissions=(self.PERMISSION,),
        )

    def available_actions(self) -> tuple[str, ...]:
        return tuple(self.SCHEMAS)

    def action_specs(self) -> dict:
        return {
            action: ActionSpec(permission=self.PERMISSION, schema=schema)
            for action, schema in self.SCHEMAS.items()
        }

    def execute(self, action: str, arguments: dict) -> str:
        schema = self.SCHEMAS.get(action)
        if schema is None:
            return "Rejected: unsupported action."
        if (not isinstance(arguments, dict)
                or next(Draft202012Validator(schema).iter_errors(arguments), None) is not None):
            return "Rejected: invalid arguments."
        try:
            message = getattr(self, f"_do_{action}")(**arguments)
        except OSError as error:
            return f"Failed: {error}"
        return f"Done: {message}"


class MediaSkill(_SystemSkill):
    SKILL_ID = "media_control"
    NAME = "Media Control"
    DESCRIPTION = "Play, pause and skip media in the current player."
    PERMISSION = "desktop.interact"
    SCHEMAS = {name: NO_ARGS for name in
               ("play_pause", "play", "pause", "next_track", "previous_track")}

    COMMANDS = {
        "play_pause": ("play-pause", "Toggled play and pause."),
        "play": ("play", "Playing."),
        "pause": ("pause", "Paused."),
        "next_track": ("next", "Next track."),
        "previous_track": ("previous", "Previous track."),
    }

    def execute(self, action, arguments):
        if action not in self.COMMANDS:
            return "Rejected: unsupported action."
        if arguments != {}:
            return "Rejected: invalid arguments."
        command, message = self.COMMANDS[action]
        try:
            self._run(["playerctl", command])
        except OSError as error:
            return f"Failed: {error}"
        return f"Done: {message}"


class VolumeSkill(_SystemSkill):
    SKILL_ID = "volume_control"
    NAME = "Volume Control"
    DESCRIPTION = "Change the speaker volume (never above 100 percent)."
    PERMISSION = "system.manage"
    SCHEMAS = {
        "set_volume": _int_schema("level", 0, 100),
        "change_volume": _int_schema("delta", -50, 50),
        "set_mute": {
            "type": "object",
            "properties": {"muted": {"type": "boolean"}},
            "required": ["muted"],
            "additionalProperties": False,
        },
    }

    def _do_set_volume(self, level):
        self._run(["wpctl", "set-volume", "-l", "1.0", SINK, f"{level}%"])
        self._run(["wpctl", "set-mute", SINK, "0"])
        return f"Volume set to {level} percent."

    def _do_change_volume(self, delta):
        if delta == 0:
            return "Volume unchanged."
        step = f"{abs(delta)}%{'+' if delta > 0 else '-'}"
        self._run(["wpctl", "set-volume", "-l", "1.0", SINK, step])
        if delta > 0:
            self._run(["wpctl", "set-mute", SINK, "0"])
        return "Volume up." if delta > 0 else "Volume down."

    def _do_set_mute(self, muted):
        self._run(["wpctl", "set-mute", SINK, "1" if muted else "0"])
        return "Muted." if muted else "Unmuted."


class BrightnessSkill(_SystemSkill):
    SKILL_ID = "brightness_control"
    NAME = "Brightness Control"
    DESCRIPTION = "Change the screen brightness (never below 5 percent)."
    PERMISSION = "system.manage"
    SCHEMAS = {
        "set_brightness": _int_schema("percent", MIN_BRIGHTNESS, 100),
        "change_brightness": _int_schema("delta", -50, 50),
    }

    def _current_percent(self):
        fields = self._run(["brightnessctl", "-m"]).strip().split(",")
        try:
            return int(fields[3].rstrip("%"))
        except (IndexError, ValueError) as error:
            raise OSError("Could not read the current brightness.") from error

    def _do_set_brightness(self, percent):
        self._run(["brightnessctl", "set", f"{percent}%"])
        return f"Brightness set to {percent} percent."

    def _do_change_brightness(self, delta):
        target = max(MIN_BRIGHTNESS, min(100, self._current_percent() + delta))
        self._run(["brightnessctl", "set", f"{target}%"])
        return f"Brightness set to {target} percent."
