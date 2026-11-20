"""Manage the lifecycle of approved TIRIAS skills."""

from tirias.skill_system.registry import SkillRegistry
from tirias.skill_system.validator import SkillValidator


class SkillManager:
    def __init__(self):
        self.registry = SkillRegistry()
        self.validator = SkillValidator()
        self._enabled: set[str] = set()

    def register_skill(self, skill) -> tuple[bool, list[str]]:
        valid, errors = self.validator.validate(skill)

        if not valid:
            return False, errors

        if not self.registry.register(skill):
            return False, ["Skill registration rejected."]

        return True, []

    def enable_skill(self, skill_id: str) -> bool:
        skill = self.registry.get(skill_id)

        if skill is None:
            return False

        self._enabled.add(skill_id)
        return True

    def disable_skill(self, skill_id: str) -> bool:
        if not isinstance(skill_id, str):
            return False

        skill_id = skill_id.strip().lower()

        if skill_id not in self._enabled:
            return False

        self._enabled.remove(skill_id)
        return True

    def get_enabled_skill(self, skill_id: str):
        if not isinstance(skill_id, str):
            return None

        skill_id = skill_id.strip().lower()

        if skill_id not in self._enabled:
            return None

        return self.registry.get(skill_id)

    def list_enabled_skills(self) -> tuple[str, ...]:
        return tuple(sorted(self._enabled))
