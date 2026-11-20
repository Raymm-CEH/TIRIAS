"""Local Ollama conversation provider for TIRIAS."""

import os
import re

import ollama


class OllamaProvider:
    """Sends conversation requests to a local Ollama server. It cannot execute local actions."""

    def __init__(self, client=None, model=None, host=None):
        self.model = model or os.getenv("TIRIAS_OLLAMA_MODEL", "qwen2.5:1.5b")
        self.client = client or ollama.Client(
            host=host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            timeout=60.0,
        )

    @property
    def available(self):
        return bool(self.client and self.model)

    def generate(self, message, instructions):
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": message},
                ],
                options={"temperature": 0.2, "num_ctx": 2048},
                keep_alive="2m",  # unload after idle to free RAM for voice
            )
            answer = response["message"]["content"]
        except Exception as exc:
            raise RuntimeError(
                "The local model request failed. Check that Ollama is running "
                "and the model is installed."
            ) from exc

        answer = re.sub(r"^(?:\s*(?:TIRIAS|Assistant)\s*:\s*)+", "", answer or "", flags=re.I)
        if not answer.strip():
            raise RuntimeError("The local model returned an empty response.")

        return answer.strip()
