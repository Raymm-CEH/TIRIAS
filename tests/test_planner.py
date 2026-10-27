import unittest

from tirias.planner import Planner, TaskPlan


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = Planner()

    def test_known_goal_returns_structured_plan(self):
        plan = self.planner.plan("inspect my workspace")

        self.assertIsInstance(plan, TaskPlan)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].action, "open_workspace")
        self.assertEqual(plan.steps[1].action, "list_files")

    def test_storage_goal_is_read_only(self):
        plan = self.planner.plan("check my system storage")

        self.assertIsNotNone(plan)
        self.assertEqual(
            [step.action for step in plan.steps],
            ["check_disk_space"],
        )
        self.assertFalse(
            any(step.requires_confirmation for step in plan.steps)
        )

    def test_folder_creation_requires_confirmation(self):
        plan = self.planner.plan("prepare a project folder")

        self.assertIsNotNone(plan)
        self.assertEqual(plan.steps[0].action, "request_folder")
        self.assertTrue(plan.steps[0].requires_confirmation)

    def test_unknown_goal_is_rejected(self):
        self.assertIsNone(
            self.planner.plan("run any command I tell you")
        )

    def test_empty_or_oversized_goal_is_rejected(self):
        self.assertIsNone(self.planner.plan("  "))
        self.assertIsNone(self.planner.plan("x" * 301))

    def test_non_string_goal_is_rejected(self):
        self.assertIsNone(self.planner.plan(None))


if __name__ == "__main__":
    unittest.main()
