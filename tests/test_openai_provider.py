import unittest
from unittest.mock import patch

from tirias.providers.openai_provider import OpenAIProvider


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, responses):
        self.responses = responses


class OpenAIProviderTests(unittest.TestCase):
        
    def test_successful_response(self):
        responses = FakeResponses(
            response=FakeResponse("Hello from TIRIAS.")
        )
        provider = OpenAIProvider(
            client=FakeClient(responses),
            model="test-model",
        )

        answer = provider.generate(
            "Hello",
            "Be helpful and explain clearly.",
        )

        self.assertEqual(answer, "Hello from TIRIAS.")
        self.assertEqual(len(responses.calls), 1)

        request = responses.calls[0]

        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["input"], "Hello")
        self.assertEqual(
            request["instructions"],
            "Be helpful and explain clearly.",
        )
        self.assertFalse(request["store"])

    def test_missing_client_configuration(self):
        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAIProvider(model="test-model")

        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            provider.generate("Hello", "Be helpful.")

    def test_missing_model_configuration(self):
        with patch.dict("os.environ", {"TIRIAS_OPENAI_MODEL": ""}):
            provider = OpenAIProvider(
                client=FakeClient(FakeResponses()),
                model="",
            )

        with self.assertRaisesRegex(RuntimeError, "TIRIAS_OPENAI_MODEL"):
            provider.generate("Hello", "Be helpful.")

    def test_empty_message_is_rejected(self):
        provider = OpenAIProvider(
            client=FakeClient(FakeResponses()),
            model="test-model",
        )

        with self.assertRaises(ValueError):
            provider.generate("   ", "Be helpful.")

    def test_empty_response_is_rejected(self):
        provider = OpenAIProvider(
            client=FakeClient(
                FakeResponses(response=FakeResponse("  "))
            ),
            model="test-model",
        )

        with self.assertRaisesRegex(RuntimeError, "empty response"):
            provider.generate("Hello", "Be helpful.")

    def test_api_error_is_handled(self):
        from tirias.providers import openai_provider

        class FakeAPIError(Exception):
            pass

        responses = FakeResponses(error=FakeAPIError("private detail"))
        provider = OpenAIProvider(
            client=FakeClient(responses),
            model="test-model",
        )

        with patch.object(
            openai_provider, "OpenAIError", FakeAPIError
        ):
            with self.assertRaisesRegex(RuntimeError, "OpenAI request failed"):
                provider.generate("Hello", "Be helpful.")


if __name__ == "__main__":
    unittest.main()
