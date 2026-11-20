"""Validation rules for TIRIAS skills."""

import re

from tirias.skill_system.interface import Skill, SkillManifest


ALLOWED_PERMISSIONS = {
    "applications.launch",
    "applications.status",
    "windows.control",
    "files.read",
    "files.write",
    "system.read",
    "system.manage",
    "desktop.interact",
    "network.read",
}


class SkillValidator:
    """Validate skill structure and declared capabilities."""

    SKILL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,49}$")
    ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
    VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

    def validate(self, skill: Skill) -> tuple[bool, list[str]]:
        errors = []

        if not isinstance(skill, Skill):
            return False, ["Object does not implement the Skill interface."]

        try:
            manifest = skill.manifest
            actions = skill.available_actions()
        except Exception:
            return False, ["Could not inspect the skill safely."]

        if not isinstance(manifest, SkillManifest):
            return False, ["Invalid skill manifest."]

        if not isinstance(manifest.skill_id, str):
            errors.append("Skill ID must be text.")
        elif not self.SKILL_ID_PATTERN.fullmatch(manifest.skill_id):
            errors.append("Invalid skill ID.")

        if not isinstance(manifest.name, str) or not manifest.name.strip():
            errors.append("Skill name is required.")

        if (
            not isinstance(manifest.version, str)
            or not self.VERSION_PATTERN.fullmatch(manifest.version)
        ):
            errors.append("Version must use MAJOR.MINOR.PATCH format.")

        if (
            not isinstance(manifest.description, str)
            or not manifest.description.strip()
        ):
            errors.append("Skill description is required.")

        if not isinstance(manifest.permissions, tuple):
            errors.append("Permissions must be a tuple.")
        else:
            for permission in manifest.permissions:
                if permission not in ALLOWED_PERMISSIONS:
                    errors.append(f"Unknown permission: {permission}")

        if not isinstance(actions, tuple) or not actions:
            errors.append("Skill must declare at least one action.")
        else:
            if len(actions) != len(set(actions)):
                errors.append("Duplicate actions are not allowed.")

            for action in actions:
                if (
                    not isinstance(action, str)
                    or not self.ACTION_PATTERN.fullmatch(action)
                ):
                    errors.append(f"Invalid action name: {action!r}")

        if not callable(getattr(skill, "execute", None)):
            errors.append("Skill execution method is missing.")

        return not errors, errors
