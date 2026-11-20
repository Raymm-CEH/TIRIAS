"""Control center skill: starts the TIRIAS dashboard. Runs only via the gateway."""

import subprocess
import sys
from pathlib import Path

from tirias.skill_system.interface import ActionSpec, Skill, SkillManifest


def _open_control_center(script):
    try:
        check = subprocess.run(
            [sys.executable, "-c", "import tkinter"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except subprocess.SubprocessError as error:
        raise OSError(f"Could not check Tkinter: {error}") from error
    if check.returncode != 0:
        raise OSError(
            "Python Tkinter is missing. On Kali/Debian run: sudo apt install python3-tk"
        )
    subprocess.Popen(
        [sys.executable, str(script)],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class ControlCenterSkill(Skill):
    """Launch the TIRIAS control center from its fixed script path."""

    def __init__(self, script_path, opener=None):
        self._script = Path(script_path).resolve()
        self._open = opener

    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            skill_id="control_center",
            name="Control Center",
            version="1.0.0",
            description="Open the TIRIAS control center dashboard.",
            permissions=("desktop.interact",),
        )

    def available_actions(self) -> tuple[str, ...]:
        return ("open_control_center",)

    def action_specs(self) -> dict:
        return {
            "open_control_center": ActionSpec(
                permission="desktop.interact",
                schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            )
        }

    def execute(self, action: str, arguments: dict) -> str:
        if action != "open_control_center":
            return "Rejected: unsupported control center action."
        if arguments != {}:
            return "Rejected: this action takes no arguments."
        if not self._script.is_file():
            return "Rejected: the control center script is missing."
        try:
            (self._open or _open_control_center)(self._script)
        except OSError as error:
            return f"Launch failed: {error}"
        return "Launch request sent: control center."
