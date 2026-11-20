import unittest

from tirias.skill_system.application_skill import ApplicationSkill


class MockAppController:
    def __init__(self):
        self.launched = []

    def launch(self, app_id):
        self.launched.append(app_id)
        return f"Mock launch: {app_id}"


class ApplicationSkillTests(unittest.TestCase):
    def setUp(self):
        self.controller = MockAppController()
        self.skill = ApplicationSkill(self.controller)

    def test_manifest(self):
        self.assertEqual(
            self.skill.manifest.skill_id,
            "application_control",
        )
        self.assertIn(
            "applications.launch",
            self.skill.manifest.permissions,
        )

    def test_available_actions(self):
        self.assertEqual(
            self.skill.available_actions(),
            ("launch_application",),
        )

    def test_approved_application_is_forwarded(self):
        result = self.skill.execute(
            "launch_application",
            {"app_id": "firefox"},
        )
        self.assertEqual(result, "Mock launch: firefox")
        self.assertEqual(self.controller.launched, ["firefox"])

    def test_unknown_application_is_rejected(self):
        result = self.skill.execute(
            "launch_application",
            {"app_id": "unknown_app"},
        )
        self.assertIn("not approved", result)
        self.assertEqual(self.controller.launched, [])

    def test_unknown_action_is_rejected(self):
        result = self.skill.execute("delete_everything", {})
        self.assertIn("unsupported", result)
        self.assertEqual(self.controller.launched, [])

    def test_invalid_arguments_are_rejected(self):
        result = self.skill.execute(
            "launch_application",
            {"app_id": "firefox", "extra": "unexpected"},
        )
        self.assertIn("only an app_id", result)
        self.assertEqual(self.controller.launched, [])

    def test_non_dictionary_arguments_are_rejected(self):
        result = self.skill.execute("launch_application", "firefox")
        self.assertIn("dictionary", result)
        self.assertEqual(self.controller.launched, [])


if __name__ == "__main__":
    unittest.main()
