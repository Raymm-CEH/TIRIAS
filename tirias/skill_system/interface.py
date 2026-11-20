"""Common interface for TIRIAS skills."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    name: str
    version: str
    description: str
    permissions: tuple[str, ...] = ()


class Skill(ABC):
    """Base interface that every TIRIAS skill must implement."""

    @property
    @abstractmethod
    def manifest(self) -> SkillManifest:
        """Return the skill's identity and declared permissions."""
        raise NotImplementedError

    @abstractmethod
    def available_actions(self) -> tuple[str, ...]:
        """Return the actions this skill exposes."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: str, arguments: dict) -> str:
        """Execute one supported action."""
        raise NotImplementedError


@dataclass(frozen=True)
class ActionSpec:
    """What one skill action needs before it is allowed to run."""

    permission: str
    schema: dict
    sensitive: bool = False
