"""Allowlisted execution of TIRIAS planner steps."""

from tirias.planner import TaskPlan


class Executor:
    """Execute only explicitly approved actions through existing core methods."""

    def __init__(self, core):
        self.core = core

        # Each action maps to a fixed method or fixed operation.
        self._actions = {
            "open_workspace": self._open_workspace,
            "list_files": self.core.list_files,
            "check_disk_space": self._check_disk_space,
            "request_folder": self._request_folder,
        }

    def execute(self, plan: TaskPlan) -> list[str]:
        if not isinstance(plan, TaskPlan):
            return ["Rejected: invalid task plan."]

        if not plan.steps:
            return ["Rejected: the plan contains no steps."]

        results = []

        for step in plan.steps:
            action = self._actions.get(step.action)

            if action is None:
                results.append(
                    f"Rejected unknown action: {step.action}"
                )
                break

            if step.requires_confirmation:
                results.append(
                    f"Confirmation required: {step.description}. "
                    "No action was executed."
                )
                break

            try:
                result = action()
            except Exception:
                # Avoid exposing internal details or claiming success.
                results.append(
                    f"Failed safely while attempting: {step.description}."
                )
                break

            if not isinstance(result, str):
                results.append(
                    f"Failed: {step.description} returned an invalid result."
                )
                break

            results.append(result)

        return results

    def _open_workspace(self) -> str:
        return self.core.go_to("workspace")

    def _check_disk_space(self) -> str:
        import shutil

        try:
            usage = shutil.disk_usage(self.core.home)
        except OSError:
            return "I couldn't check disk space."

        gib = 1024 ** 3
        return (
            f"Your home filesystem has {usage.free / gib:.1f} GiB free "
            f"of {usage.total / gib:.1f} GiB."
        )

    def _request_folder(self) -> str:
        return (
            "Please tell me the project folder name first. "
            "No folder has been created."
        )
