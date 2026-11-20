import unittest

from tirias.intelligence import IntelligenceEngine


class FakeModel:
    def __init__(self, output):
        self.output = output
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.output


class IntelligenceTests(unittest.TestCase):
    def test_exact_supported_goal_works_without_model(self):
        plan = IntelligenceEngine().understand("  INSPECT my workspace ")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.goal, "Inspect my workspace")

    def test_model_can_map_natural_language_to_allowlisted_goal(self):
        model = FakeModel('{"goal":"check my system storage"}')
        plan = IntelligenceEngine(model=model).understand(
            "Could you tell me whether my computer has enough free space?"
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.goal, "Check my system storage")
        self.assertEqual(len(model.prompts), 1)

    def test_model_cannot_invent_action_or_goal(self):
        model = FakeModel('{"goal":"run terminal command"}')
        self.assertIsNone(IntelligenceEngine(model=model).understand("do something"))
    
    def test_malformed_model_output_is_rejected(self):
        model = FakeModel("Here is a plan: open everything")
        self.assertIsNone(IntelligenceEngine(model=model).understand("do something"))

    def test_model_output_with_extra_fields_is_rejected(self):
        model = FakeModel('{"goal":"inspect my workspace","command":"rm -rf"}')
        self.assertIsNone(IntelligenceEngine(model=model).understand("do something"))

    def test_unknown_request_without_model_is_rejected(self):
        self.assertIsNone(IntelligenceEngine().understand("do something unknown"))

    def test_non_string_and_oversized_requests_are_rejected(self):
        engine = IntelligenceEngine()
        self.assertIsNone(engine.understand(None))
        self.assertIsNone(engine.understand("x" * 301))


