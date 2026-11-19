"""Try conversation providers in order until one answers."""


class FallbackProvider:
    """Wraps several providers. Cloud failures fall through to the next one."""

    def __init__(self, providers):
        self.providers = list(providers)

    @property
    def available(self):
        return any(getattr(p, "available", False) for p in self.providers)

    def generate(self, message, instructions):
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        for provider in self.providers:
            if not getattr(provider, "available", False):
                continue
            try:
                return provider.generate(message, instructions)
            except RuntimeError:
                continue

        raise RuntimeError("No conversation provider could answer right now.")
