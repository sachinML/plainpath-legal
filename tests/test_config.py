"""Settings must read the environment at construction time, not at import time."""

from __future__ import annotations

import os
import unittest

from plainpath.config import Settings, get_settings


class TestConfig(unittest.TestCase):
    def test_provider_default_factory_rereads_env(self) -> None:
        old = os.environ.get("LLM_PROVIDER")
        try:
            os.environ["LLM_PROVIDER"] = "mock"
            first = Settings()
            os.environ["LLM_PROVIDER"] = "gemini"
            second = Settings()
            self.assertEqual(first.llm_provider, "mock")
            self.assertEqual(second.llm_provider, "gemini")
        finally:
            if old is None:
                os.environ.pop("LLM_PROVIDER", None)
            else:
                os.environ["LLM_PROVIDER"] = old

    def test_get_settings_returns_settings(self) -> None:
        self.assertIsInstance(get_settings(), Settings)

    def test_timeout_factory_reads_current_env(self) -> None:
        old = os.environ.get("LLM_TIMEOUT_SECONDS")
        try:
            os.environ["LLM_TIMEOUT_SECONDS"] = "12"
            settings = Settings()
            self.assertEqual(settings.llm_timeout_seconds, 12.0)
        finally:
            if old is None:
                os.environ.pop("LLM_TIMEOUT_SECONDS", None)
            else:
                os.environ["LLM_TIMEOUT_SECONDS"] = old

    def test_default_groq_model_is_current_free_tier(self) -> None:
        old = os.environ.pop("GROQ_MODEL", None)
        try:
            self.assertEqual(Settings().groq_model, "openai/gpt-oss-20b")
        finally:
            if old is not None:
                os.environ["GROQ_MODEL"] = old


if __name__ == "__main__":
    unittest.main()
