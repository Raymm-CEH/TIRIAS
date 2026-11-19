"""OpenAI conversation provider for TIRIAS."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class OpenAIProvider:
    """Sends conversation requests to OpenAI. It cannot execute local actions."""

    def __init__(self, client=None, model=None):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("TIRIAS_OPENAI_MODEL")

        self.client = client

        if self.client is None and self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                timeout=30.0,
                max_retries=1,
            )

    @property
    def available(self):
        return bool(self.client and self.model)

    def generate(self, message, instructions):
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        if not self.model:
            raise RuntimeError("TIRIAS_OPENAI_MODEL is not configured.")

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=message,
                store=False,
            )
        except OpenAIError as exc:
            raise RuntimeError(
                "The OpenAI request failed. Check the connection and API settings."
            ) from exc

        answer = response.output_text

        if not answer or not answer.strip():
            raise RuntimeError("OpenAI returned an empty response.")

        return answer.strip()
