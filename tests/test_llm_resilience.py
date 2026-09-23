"""Language clients must degrade to a string when the provider is unreachable."""

from __future__ import annotations

import unittest

from plainpath.llm import GeminiLLM, OllamaLLM, OpenAICompatibleLLM, fallback_text
from plainpath.types import LLMResult

UNREACHABLE = "http://127.0.0.1:1"


class TestLlmResilience(unittest.TestCase):
    def test_openai_compatible_does_not_raise_when_unreachable(self) -> None:
        client = OpenAICompatibleLLM(
            provider_label="openai-compatible",
            base_url=UNREACHABLE,
            api_key="fake-key",
            model="test-model",
            timeout_s=2.0,
        )
        result = client.complete(system="sys", user="hello")
        self.assertIsInstance(result, LLMResult)
        self.assertTrue(result.degraded)
        self.assertIn("could not reach the language model", result.text.lower())
        self.assertIn("openai-compatible:test-model", result.text)

    def test_gemini_does_not_raise_when_unreachable(self) -> None:
        client = GeminiLLM(
            api_key="fake-key",
            model="gemini-2.5-flash",
            timeout_s=2.0,
            base_url=UNREACHABLE,
            fallback_models=(),
        )
        result = client.complete(system="sys", user="hello")
        self.assertIsInstance(result, LLMResult)
        self.assertTrue(result.degraded)
        self.assertIn("could not reach the language model", result.text.lower())

    def test_ollama_does_not_raise_when_unreachable(self) -> None:
        client = OllamaLLM(base_url=UNREACHABLE, model="llama3.2", timeout_s=2.0)
        self.assertFalse(client.is_live())
        result = client.complete(system="sys", user="hello")
        self.assertTrue(result.degraded)
        self.assertIn("ollama:llama3.2", result.text)

    def test_fallback_text_mentions_timeout(self) -> None:
        text = fallback_text("demo", TimeoutError("slow"))
        self.assertIn("timed out", text.lower())
        self.assertIn("demo", text)


if __name__ == "__main__":
    unittest.main()
