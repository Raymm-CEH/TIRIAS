"""Optional local GGUF language-model adapter for TIRIAS.

The model may suggest a supported goal, but it cannot execute actions.
Its output is treated as untrusted text and validated by IntelligenceEngine.
"""
from __future__ import annotations

import os
from pathlib import Path


class LocalModelUnavailable(RuntimeError):
    """Raised when local model inference is not configured or available."""


class LocalGGUFModel:
    """Lazy adapter for llama-cpp-python; no network access is used."""

    def __init__(self, model_path: str | Path | None = None, n_ctx: int = 2048):
        configured = model_path or os.environ.get("TIRIAS_MODEL_PATH")
        self.model_path = Path(configured).expanduser() if configured else None
        self.n_ctx = int(n_ctx)
        self._model = None

    @property
    def available(self) -> bool:
        return bool(self.model_path and self.model_path.is_file())

    def generate(self, prompt: str) -> str:
        if not self.available:
            raise LocalModelUnavailable(
                "Set TIRIAS_MODEL_PATH to a local GGUF model file."
            )
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise LocalModelUnavailable(
                "llama-cpp-python is not installed in this Python environment."
            ) from exc

        if self._model is None:
            self._model = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                verbose=False,
            )
        result = self._model.create_chat_completion(
            messages=[
                {"role": "system", "content": "Follow the user's task only by selecting one allowed goal. Return only JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        return str(result["choices"][0]["message"]["content"])
