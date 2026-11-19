import unittest

from tirias.skill_system.interface import Skill, SkillManifest
from tirias.skill_system.manager import SkillManager


class DemoSkill(Skill):
    @property
    def manifest(self):
        return SkillManifest(
            skill_id="demo_skill",
            name="Demo Skill",
            version="1.0.0",
            description="A harmless test skill.",
            permissions=(),
        )

    def available_actions(self):
        return ("say_hello",)

    def execute(self, action, arguments):
        if action == "say_hello":
            return "Hello from the demo skill!"
        return "Unknown action."


class InvalidSkill(Skill):
    @property
    def manifest(self):
        return SkillManifest(
            skill_id="INVALID ID",
            name="Invalid Skill",
            version="1.0",
            description="An invalid test skill.",
            permissions=(),
        )

    def available_actions(self):
        return ("say_hello",)

    def execute(self, action, arguments):
        return "Test."


class SkillSystemTests(unittest.TestCase):
    def setUp(self):
        self.manager = SkillManager()
        self.skill = DemoSkill()

    def test_valid_skill_registers(self):
        success, errors = self.manager.register_skill(self.skill)
        self.assertTrue(success)
        self.assertEqual(errors, [])

    def test_invalid_skill_is_rejected(self):
        success, errors = self.manager.register_skill(InvalidSkill())
        self.assertFalse(success)
        self.assertTrue(errors)

    def test_duplicate_skill_is_rejected(self):
        self.manager.register_skill(self.skill)
        success, errors = self.manager.register_skill(self.skill)
        self.assertFalse(success)

    def test_skill_must_be_registered_before_enabling(self):
        self.assertFalse(self.manager.enable_skill("demo_skill"))

    def test_registered_skill_can_be_enabled(self):
        self.manager.register_skill(self.skill)
        self.assertTrue(self.manager.enable_skill("demo_skill"))

    def test_disabled_skill_cannot_be_retrieved_as_enabled(self):
        self.manager.register_skill(self.skill)
        self.manager.enable_skill("demo_skill")
        self.assertTrue(self.manager.disable_skill("demo_skill"))
        self.assertIsNone(
            self.manager.get_enabled_skill("demo_skill")
        )

    def test_enabled_skill_can_execute_demo_action(self):
        self.manager.register_skill(self.skill)
        self.manager.enable_skill("demo_skill")

        enabled_skill = self.manager.get_enabled_skill("demo_skill")
        result = enabled_skill.execute("say_hello", {})

        self.assertEqual(result, "Hello from the demo skill!")


if __name__ == "__main__":
    unittest.main()
