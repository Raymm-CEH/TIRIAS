
"""Safe, deterministic task planning for TIRIAS.

This module proposes actions only. It never executes commands or changes files.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanStep:
    action: str
    description: str
    requires_confirmation: bool = False


@dataclass(frozen=True)
class TaskPlan:
    goal: str
    steps: tuple[PlanStep, ...]


class Planner:
    """Translate explicitly supported goals into allowlisted action plans."""

    def plan(self, goal: str) -> TaskPlan | None:
        if not isinstance(goal, str):
            return None

        normalized = " ".join(goal.casefold().split())
        if not normalized or len(normalized) > 300:
            return None

        plans = {
            "inspect my workspace": TaskPlan(
                goal="Inspect my workspace",
                steps=(
                    PlanStep(
                        "open_workspace",
                        "Open the known TIRIAS workspace folder",
                    ),
                    PlanStep(
                        "list_files",
                        "List the contents of the current folder",
                    ),
                ),
            ),
            "check my system storage": TaskPlan(
                goal="Check my system storage",
                steps=(
                    PlanStep(
                        "check_disk_space",
                        "Check available space on the home filesystem",
                    ),
                ),
            ),
            "prepare a project folder": TaskPlan(
                goal="Prepare a project folder",
                steps=(
                    PlanStep(
                        "request_folder",
                        "Ask for a project folder name and validate it",
                        requires_confirmation=True,
                    ),
                ),
            ),
        }

        return plans.get(normalized)

