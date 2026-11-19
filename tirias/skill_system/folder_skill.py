"""Folder skill: opens a folder in the approved file manager. Runs only via the gateway."""

import shutil
import subprocess
from pathlib import Path

from tirias.app_registry import get_application
from tirias.skill_system.interface import ActionSpec, Skill, SkillManifest

MAX_PATH_CHARS = 4096


def _open_in_file_manager(folder):
    app = get_application("thunar")
    executable = shutil.which(app.executable) if app else None
    if executable is None:
        raise OSError("The file manager was not found.")
    subprocess.Popen(
        [executable, str(folder)],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class FolderSkill(Skill):
    """Open folders that live inside one allowed root (normally the user's home)."""

    def __init__(self, allowed_root, opener=None):
        self._root = Path(allowed_root).expanduser().resolve()
        self._open = opener

    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            skill_id="folder_access",
            name="Folder Access",
            version="1.0.0",
            description="Open folders inside the allowed area in the file manager.",
            permissions=("files.read",),
        )

    def available_actions(self) -> tuple[str, ...]:
        return ("open_folder",)

    def action_specs(self) -> dict:
        return {
            "open_folder": ActionSpec(
                permission="files.read",
                schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": MAX_PATH_CHARS,
                            "pattern": r"^/[^\x00-\x1f\x7f]*$",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            )
        }

    def execute(self, action: str, arguments: dict) -> str:
        if action != "open_folder":
            return "Rejected: unsupported folder action."
        if not isinstance(arguments, dict) or set(arguments) != {"path"}:
            return "Rejected: provide only a path argument."
        raw = arguments["path"]
        if not isinstance(raw, str) or not raw.startswith("/") or len(raw) > MAX_PATH_CHARS:
            return "Rejected: invalid folder path."
        try:
            folder = Path(raw).resolve()
        except (OSError, RuntimeError, ValueError):
            return "Rejected: invalid folder path."
        if folder != self._root and self._root not in folder.parents:
            return "Rejected: folder is outside the allowed area."
        if not folder.is_dir():
            return "Rejected: folder does not exist."
        try:
            (self._open or _open_in_file_manager)(folder)
        except OSError as error:
            return f"Launch failed: {error}"
        return "Launch request sent: folder."
