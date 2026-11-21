"""Window skill: close the active window, only after the user confirms. Runs only via the gateway."""

import os
import re

from jsonschema import Draft202012Validator

from tirias.skill_system.interface import ActionSpec, Skill, SkillManifest
from tirias.skill_system.system_phrases import _clean
from tirias.skill_system.system_skills import _run

_CLOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "window_id": {"type": "string", "pattern": r"^0x[0-9a-fA-F]{1,10}$"},
        "title": {"type": "string", "minLength": 1, "maxLength": 200,
                  "pattern": r"^[^\x00-\x1f\x7f]+$"},
    },
    "required": ["window_id", "title"],
    "additionalProperties": False,
}
_CLOSE_PHRASE = re.compile(
    r"close (?:this |the |my |the current |the active |current |active )?window"
)


def parse_window_request(text):
    """True only for an explicit 'close this window' style command."""
    return bool(_CLOSE_PHRASE.fullmatch(_clean(text))) if isinstance(text, str) else False


def _list_windows(run):
    """Map window id (int) to title using wmctrl -l."""
    windows = {}
    for line in run(["wmctrl", "-l"]).splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            windows[int(parts[0], 16)] = parts[3].strip()
        except ValueError:
            continue
    return windows


def _ancestor_pids():
    """This process and its parents (the terminal Tirias may be running in)."""
    pids = set()
    pid = os.getpid()
    for _ in range(64):
        pids.add(pid)
        try:
            with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
                data = handle.read()
            pid = int(data.rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
        if pid <= 1:
            break
    return pids


def find_active_window(runner=None):
    """Return (window_id, title) of the active window, or raise OSError."""
    run = runner or _run
    try:
        active = int(run(["xdotool", "getactivewindow"]).strip())
    except ValueError as error:
        raise OSError("No active window was reported.") from error
    title = _list_windows(run).get(active)
    if title is None:
        raise OSError("The active window is not a normal application window.")
    if not title:
        raise OSError("The active window has no title, so I can't tell which one it is.")
    try:
        pid = int(run(["xdotool", "getwindowpid", str(active)]).strip())
    except (OSError, ValueError):
        pid = None  # unknown owner: the confirmation question shows the title instead
    if pid is not None and pid in _ancestor_pids():
        raise OSError("That is the window I'm running in, so I won't close it.")
    return f"0x{active:08x}", title


class WindowSkill(Skill):
    """Close one specific window, identified by id and title, after confirmation."""

    def __init__(self, runner=None):
        self._runner = runner

    def _run(self, command):
        return (self._runner or _run)(command)

    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            skill_id="window_control", name="Window Control", version="1.0.0",
            description="Close an application window after confirmation.",
            permissions=("windows.control",),
        )

    def available_actions(self) -> tuple[str, ...]:
        return ("close_window",)

    def action_specs(self) -> dict:
        return {
            "close_window": ActionSpec(
                permission="windows.control", schema=_CLOSE_SCHEMA, sensitive=True
            )
        }

    def describe_action(self, action, arguments):
        return f"Close the window '{arguments.get('title', '')}'?"

    def execute(self, action: str, arguments: dict) -> str:
        if action != "close_window":
            return "Rejected: unsupported window action."
        if (not isinstance(arguments, dict)
                or next(Draft202012Validator(_CLOSE_SCHEMA).iter_errors(arguments), None)):
            return "Rejected: invalid arguments."
        window_id, title = arguments["window_id"], arguments["title"]
        try:
            current = _list_windows(self._runner or _run).get(int(window_id, 16))
        except OSError as error:
            return f"Failed: {error}"
        if current is None:
            return "Rejected: that window no longer exists."
        if current != title:
            return "Rejected: that window has changed. Ask me again."
        try:
            self._run(["wmctrl", "-i", "-c", window_id])
        except OSError as error:
            return f"Failed: {error}"
        return f"Done: Asked '{title}' to close."
