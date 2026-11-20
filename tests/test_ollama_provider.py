import pytest

from tirias.providers.fallback import FallbackProvider
from tirias.providers.ollama_provider import OllamaProvider


class FakeClient:
    def __init__(self, content="  hello there  ", error=None):
        self.content = content
        self.error = error
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"message": {"content": self.content}}


class StubProvider:
    def __init__(self, available=True, answer="ok", error=None):
        self.available = available
        self.answer = answer
        self.error = error
        self.called = False

    def generate(self, message, instructions):
        self.called = True
        if self.error:
            raise self.error
        return self.answer


def test_returns_stripped_answer_and_sends_instructions():
    client = FakeClient()
    provider = OllamaProvider(client=client, model="test-model")
    assert provider.generate("hi", "be brief") == "hello there"
    sent = client.calls[0]
    assert sent["model"] == "test-model"
    assert sent["messages"][0] == {"role": "system", "content": "be brief"}


def test_rejects_empty_message():
    provider = OllamaProvider(client=FakeClient(), model="m")
    with pytest.raises(ValueError):
        provider.generate("   ", "x")


def test_empty_answer_is_an_error():
    provider = OllamaProvider(client=FakeClient(content="  "), model="m")
    with pytest.raises(RuntimeError):
        provider.generate("hi", "x")


def test_client_failure_becomes_runtime_error():
    provider = OllamaProvider(client=FakeClient(error=ConnectionError("down")), model="m")
    with pytest.raises(RuntimeError):
        provider.generate("hi", "x")


def test_fallback_uses_second_provider_when_first_fails():
    first = StubProvider(error=RuntimeError("cloud down"))
    second = StubProvider(answer="local answer")
    assert FallbackProvider([first, second]).generate("hi", "x") == "local answer"


def test_fallback_skips_unavailable_provider():
    first = StubProvider(available=False)
    second = StubProvider(answer="local answer")
    result = FallbackProvider([first, second]).generate("hi", "x")
    assert result == "local answer"
    assert not first.called


def test_fallback_raises_when_everything_fails():
    providers = [StubProvider(error=RuntimeError("a")), StubProvider(error=RuntimeError("b"))]
    with pytest.raises(RuntimeError):
        FallbackProvider(providers).generate("hi", "x")
