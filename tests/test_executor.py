import unittest

from tirias.executor import Executor
from tirias.planner import Planner, PlanStep, TaskPlan


class FakeCore:
    def __init__(self):
        self.calls = []

    def go_to(self, key):
        self.calls.append(("go_to", key))
        return "Workspace opened."

    def list_files(self):
        self.calls.append(("list_files",))
        return "Files listed."


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.core = FakeCore()
        self.executor = Executor(self.core)

    def test_executes_known_action(self):
        plan = Planner().plan("inspect my workspace")
        results = self.executor.execute(plan)

        self.assertEqual(results[0], "Workspace opened.")
        self.assertEqual(self.core.calls[0], ("go_to", "workspace"))

    def test_rejects_unknown_action(self):
        plan = TaskPlan(
            goal="Test",
            steps=(PlanStep("run_shell", "Run arbitrary shell command"),),
        )

        results = self.executor.execute(plan)

        self.assertIn("Rejected unknown action", results[0])
        self.assertEqual(self.core.calls, [])

    def test_does_not_execute_confirmation_required_step(self):
        plan = TaskPlan(
            goal="Test",
            steps=(
                PlanStep(
                    "request_folder",
                    "Prepare a project folder",
                    requires_confirmation=True,
                ),
            ),
        )

        results = self.executor.execute(plan)

        self.assertIn("Confirmation required", results[0])
        self.assertEqual(self.core.calls, [])

    def test_rejects_invalid_plan(self):
        results = self.executor.execute("not a plan")

        self.assertEqual(results, ["Rejected: invalid task plan."])

    def test_rejects_empty_plan(self):
        plan = TaskPlan(goal="Empty", steps=())

        results = self.executor.execute(plan)

        self.assertEqual(results, ["Rejected: the plan contains no steps."])


if __name__ == "__main__":
    unittest.main()
