"""Secure execution gateway: the only approved route from a request to Skill.execute()."""

import json
import time
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from tirias.skill_system.manager import SkillManager


@dataclass(frozen=True)
class GatewayResult:
    allowed: bool
    message: str


class SkillGateway:
    """Deny-by-default checks between a request and a skill action."""

    def __init__(self, manager: SkillManager, granted_permissions,
                 confirm=None, audit_path=None):
        self._manager = manager
        self._granted = frozenset(granted_permissions)
        self._confirm = confirm or (lambda prompt: False)  # no confirmer = deny
        self._audit_path = Path(audit_path) if audit_path else None

    def request(self, skill_id, action, arguments) -> GatewayResult:
        skill = self._manager.get_enabled_skill(skill_id)
        if skill is None:
            return self._deny(skill_id, action, arguments,
                              "skill is not registered and enabled")

        try:
            actions = skill.available_actions()
            getter = getattr(skill, "action_specs", None)
            specs = getter() if callable(getter) else {}
            declared = skill.manifest.permissions
        except Exception:
            return self._deny(skill_id, action, arguments,
                              "skill could not be inspected")

        if not isinstance(action, str) or action not in actions:
            return self._deny(skill_id, action, arguments, "action is not declared")

        spec = specs.get(action)
        if spec is None:
            return self._deny(skill_id, action, arguments, "action has no security spec")

        if spec.permission not in declared:
            return self._deny(skill_id, action, arguments,
                              "permission is not declared by the skill")

        if spec.permission not in self._granted:
            return self._deny(skill_id, action, arguments,
                              "permission is not granted by policy")

        if not isinstance(arguments, dict):
            return self._deny(skill_id, action, arguments, "arguments must be a dictionary")

        problem = next(Draft202012Validator(spec.schema).iter_errors(arguments), None)
        if problem is not None:
            return self._deny(skill_id, action, arguments,
                              f"invalid arguments: {problem.message}")

        if spec.sensitive and not self._confirm(
            f"Allow {skill_id}.{action} with {arguments}?"
        ):
            return self._deny(skill_id, action, arguments, "not confirmed by the user")

        try:
            output = skill.execute(action, arguments)
        except Exception:
            self._record("error", skill_id, action, arguments, "skill raised an error")
            return GatewayResult(False, "Failed: the skill hit an error.")

        self._record("allowed", skill_id, action, arguments)
        return GatewayResult(True, str(output))

    def _deny(self, skill_id, action, arguments, reason) -> GatewayResult:
        self._record("denied", skill_id, action, arguments, reason)
        return GatewayResult(False, f"Denied: {reason}.")

    def _record(self, outcome, skill_id, action, arguments, reason="") -> None:
        if self._audit_path is None:
            return
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "outcome": outcome,
            "skill": str(skill_id)[:80],
            "action": str(action)[:80],
            "arguments": repr(arguments)[:200],
            "reason": reason,
        }
        try:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
        except OSError:
            pass
