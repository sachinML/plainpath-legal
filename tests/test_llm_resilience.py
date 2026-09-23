"""Language clients must degrade to a string when the provider is unreachable."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

from plainpath.llm import (
    GeminiLLM,
    OllamaLLM,
    OpenAICompatibleLLM,
    ProviderHTTPError,
    fallback_text,
)
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

    def test_fallback_text_uses_provider_http_reason(self) -> None:
        text = fallback_text(
            "groq:dead",
            ProviderHTTPError(403, "The model `dead` has been decommissioned."),
        )
        self.assertIn("decommissioned", text.lower())
        self.assertIn("HTTPError", text)

    def test_openai_compatible_retries_after_403(self) -> None:
        server = _start_model_router()
        try:
            host, port = server.server_address
            client = OpenAICompatibleLLM(
                provider_label="groq",
                base_url=f"http://{host}:{port}/openai/v1",
                api_key="fake-key",
                model="dead-model",
                timeout_s=2.0,
                fallback_models=("alive-model",),
            )
            result = client.complete(system="sys", user="hello")
            self.assertFalse(result.degraded)
            self.assertEqual(result.provider, "groq:alive-model")
            self.assertIn("ok:alive-model", result.text)
        finally:
            server.shutdown()
            server.server_close()

    def test_openai_compatible_does_not_retry_401(self) -> None:
        server = _start_model_router()
        try:
            host, port = server.server_address
            client = OpenAICompatibleLLM(
                provider_label="groq",
                base_url=f"http://{host}:{port}/openai/v1",
                api_key="fake-key",
                model="unauthorized-model",
                timeout_s=2.0,
                fallback_models=("alive-model",),
            )
            result = client.complete(system="sys", user="hello")
            self.assertTrue(result.degraded)
            self.assertIn("401", result.text)
            self.assertEqual(result.provider, "groq:unauthorized-model")
        finally:
            server.shutdown()
            server.server_close()


class _ModelRouter(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        model = payload.get("model")
        if model == "dead-model":
            self._json(
                403,
                {"error": {"message": "The model `dead-model` has been decommissioned."}},
            )
            return
        if model == "unauthorized-model":
            self._json(401, {"error": {"message": "Invalid API Key."}})
            return
        self._json(200, {"choices": [{"message": {"content": f"ok:{model}"}}]})

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _start_model_router() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ModelRouter)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


if __name__ == "__main__":
    unittest.main()
