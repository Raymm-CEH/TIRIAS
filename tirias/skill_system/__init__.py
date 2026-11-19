"""TIRIAS skill system."""

from tirias.skill_system.application_skill import ApplicationSkill
from tirias.skill_system.manager import SkillManager


def create_default_skill_manager():
    """Create a manager containing TIRIAS built-in skills."""
    manager = SkillManager()

    success, errors = manager.register_skill(ApplicationSkill())

    if not success:
        raise RuntimeError(f"Could not register application skill: {errors}")

    return manager
