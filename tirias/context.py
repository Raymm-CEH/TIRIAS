"""Small, bounded conversational context for TIRIAS.

This is session-only context. It is not written to disk and is never treated
as authority to execute an action.
"""
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Turn:
    user: str
    assistant: str


class ConversationContext:
    def __init__(self, max_turns: int = 8, max_chars: int = 500):
        self.max_turns = max(1, int(max_turns))
        self.max_chars = max(50, int(max_chars))
        self._turns = deque(maxlen=self.max_turns)

    def add_turn(self, user: str, assistant: str) -> None:
        if not isinstance(user, str) or not isinstance(assistant, str):
            return
        self._turns.append(Turn(
            user=user.strip()[:self.max_chars],
            assistant=assistant.strip()[:self.max_chars],
        ))

    def recent(self) -> tuple[Turn, ...]:
        return tuple(self._turns)

    def clear(self) -> None:
        self._turns.clear()

    def render(self) -> str:
        """Return a compact transcript for model context, not executable data."""
        return "\n".join(
            f"User: {turn.user}\nTIRIAS: {turn.assistant}"
            for turn in self._turns
        )
