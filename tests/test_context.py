import unittest

from tirias.context import ConversationContext


class ContextTests(unittest.TestCase):
    def test_context_keeps_only_recent_turns(self):
        context = ConversationContext(max_turns=2)
        context.add_turn("one", "reply one")
        context.add_turn("two", "reply two")
        context.add_turn("three", "reply three")
        self.assertEqual([turn.user for turn in context.recent()], ["two", "three"])

    def test_context_truncates_long_turns(self):
        context = ConversationContext(max_chars=50)
        context.add_turn("x" * 100, "y" * 100)
        self.assertEqual(len(context.recent()[0].user), 50)
        self.assertEqual(len(context.recent()[0].assistant), 50)

    def test_context_ignores_non_text(self):
        context = ConversationContext()
        context.add_turn(None, "reply")
        self.assertEqual(context.recent(), ())

    def test_clear_removes_session_context(self):
        context = ConversationContext()
        context.add_turn("hello", "hi")
        context.clear()
        self.assertEqual(context.recent(), ())


if __name__ == "__main__":
    unittest.main()
