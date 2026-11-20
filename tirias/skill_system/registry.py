"""Central registry for approved TIRIAS skills."""

from tirias.skill_system.interface import Skill


class SkillRegistry:
    """Store and retrieve registered TIRIAS skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> bool:
        """Register a skill if its identity is valid and unused."""

        if not isinstance(skill, Skill):
            return False

        try:
            manifest = skill.manifest
            skill_id = manifest.skill_id
        except (AttributeError, TypeError):
            return False

        if not isinstance(skill_id, str):
            return False

        skill_id = skill_id.strip()

        if not skill_id or skill_id != skill_id.lower():
            return False

        if skill_id in self._skills:
            return False

        self._skills[skill_id] = skill
        return True

    def get(self, skill_id: str) -> Skill | None:
        """Retrieve a registered skill."""

        if not isinstance(skill_id, str):
            return None

        return self._skills.get(skill_id.strip().lower())

    def list_skills(self) -> list[Skill]:
        """Return all registered skills."""

        return list(self._skills.values())

    def list_skill_ids(self) -> tuple[str, ...]:
        """Return registered skill identifiers."""

        return tuple(self._skills.keys())

    def contains(self, skill_id: str) -> bool:
        """Check whether a skill is registered."""

        return self.get(skill_id) is not None
