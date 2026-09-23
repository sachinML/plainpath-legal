"""HTTP language-model clients. Every network path degrades to a string; nothing raises to the UI."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol
import urllib.error
import urllib.request

from plainpath.config import Settings
from plainpath.types import LLMResult


class LLMClient(Protocol):
    """Minimal chat interface used by the pipeline."""

    def name(self) -> str:
        ...

    def is_live(self) -> bool:
        ...

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> LLMResult:
        ...


def _reason(error: Exception) -> tuple[str, str]:
    """Return (error_kind, human reason) without leaking internals."""
    kind = type(error).__name__
    if isinstance(error, TimeoutError):
        return kind, "The request timed out."
    if isinstance(error, urllib.error.HTTPError):
        return kind, f"The provider returned HTTP {error.code}."
    if isinstance(error, urllib.error.URLError):
        return kind, "Could not connect to the language-model provider."
    return kind, f"Unexpected error ({kind})."


def fallback_text(provider: str, error: Exception) -> str:
    """Honest degradation copy. Facts stay available in the other lane."""
    kind, reason = _reason(error)
    return (
        "PlainPath could not reach the language model, so the plain-language lane "
        "is paused. The facts, scores, clause flags, and briefing pack are still "
        f"computed on this device.\n\nProvider: {provider}\nIssue: {reason} "
        f"({kind})\n\nTry again in a moment, or continue with the structured findings."
    )


class MockLLM:
    """Offline narrator used only when no live provider is configured."""

    def name(self) -> str:
        return "mock"

    def is_live(self) -> bool:
        return False

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> LLMResult:
        _ = system, temperature
        return LLMResult(
            text=(
                "Mock language mode is on because no live API key was found. "
                "Structured facts are still complete. Add a GEMINI_API_KEY, GROQ_API_KEY, "
                "or OPENAI_API_KEY (or run Ollama) to enable a live rewrite.\n\n"
                f"Prompt preview (first 400 characters):\n{user[:400]}"
            ),
            provider=self.name(),
            live=False,
            degraded=True,
            error_kind="mock",
        )


class GeminiLLM:
    """Google AI Studio generateContent client."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_s: float,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        fallback_models: tuple[str, ...] = (
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-flash-latest",
            "gemini-3.5-flash-lite",
        ),
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._base_url = base_url.rstrip("/")
        self._fallback_models = fallback_models

    def name(self) -> str:
        return f"gemini:{self._model}"

    def is_live(self) -> bool:
        return bool(self._api_key)

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> LLMResult:
        models = (self._model,) + tuple(m for m in self._fallback_models if m != self._model)
        last_error: Exception | None = None
        last_name = self.name()
        for model in models:
            last_name = f"gemini:{model}"
            try:
                text = self._call(model=model, system=system, user=user, temperature=temperature)
                if text.strip():
                    return LLMResult(text=text.strip(), provider=last_name, live=True, degraded=False)
                last_error = RuntimeError("empty model response")
            except Exception as exc:  # noqa: BLE001 — must not crash the demo
                last_error = exc
                kind, _ = _reason(exc)
                if kind == "HTTPError" and getattr(exc, "code", None) == 404:
                    continue
                return LLMResult(
                    text=fallback_text(last_name, exc),
                    provider=last_name,
                    live=True,
                    degraded=True,
                    error_kind=kind,
                )
        if last_error is None:
            last_error = RuntimeError("no model attempted")
        return LLMResult(
            text=fallback_text(last_name, last_error),
            provider=last_name,
            live=True,
            degraded=True,
            error_kind=type(last_error).__name__,
        )

    def _call(self, *, model: str, system: str, user: str, temperature: float) -> str:
        url = f"{self._base_url}/models/{model}:generateContent?key={self._api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": float(temperature)},
        }
        data = _post_json(url, payload, timeout_s=self._timeout_s, headers={})
        return _gemini_text(data)


class OpenAICompatibleLLM:
    """Chat Completions client for Groq, OpenAI, OpenRouter, and local gateways."""

    def __init__(
        self,
        *,
        provider_label: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float,
    ) -> None:
        self._label = provider_label
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s

    def name(self) -> str:
        return f"{self._label}:{self._model}"

    def is_live(self) -> bool:
        return bool(self._api_key)

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> LLMResult:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "temperature": float(temperature),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
        }
        try:
            data = _post_json(url, payload, timeout_s=self._timeout_s, headers=headers)
            text = _openai_text(data)
            if not text.strip():
                raise RuntimeError("empty model response")
            return LLMResult(text=text.strip(), provider=self.name(), live=True, degraded=False)
        except Exception as exc:  # noqa: BLE001
            kind, _ = _reason(exc)
            return LLMResult(
                text=fallback_text(self.name(), exc),
                provider=self.name(),
                live=True,
                degraded=True,
                error_kind=kind,
            )


class OllamaLLM:
    """Local Ollama /api/chat client."""

    def __init__(self, *, base_url: str, model: str, timeout_s: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    def name(self) -> str:
        return f"ollama:{self._model}"

    def is_live(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=min(5.0, self._timeout_s)) as resp:
                return 200 <= getattr(resp, "status", 200) < 300
        except Exception:
            return False

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> LLMResult:
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "stream": False,
            "options": {"temperature": float(temperature)},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            data = _post_json(url, payload, timeout_s=self._timeout_s, headers={})
            message = data.get("message") if isinstance(data, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("empty model response")
            return LLMResult(text=content.strip(), provider=self.name(), live=True, degraded=False)
        except Exception as exc:  # noqa: BLE001
            kind, _ = _reason(exc)
            return LLMResult(
                text=fallback_text(self.name(), exc),
                provider=self.name(),
                live=True,
                degraded=True,
                error_kind=kind,
            )


def build_llm(settings: Settings) -> LLMClient:
    """Pick a provider from settings. 'auto' prefers Gemini, then Groq, OpenAI, Ollama, mock."""
    provider = (settings.llm_provider or "auto").lower().strip()
    if provider == "mock":
        return MockLLM()
    if provider == "gemini":
        key = settings.gemini_key()
        if not key:
            return MockLLM()
        return GeminiLLM(api_key=key, model=settings.gemini_model, timeout_s=settings.llm_timeout_seconds)
    if provider == "groq":
        if not settings.groq_api_key:
            return MockLLM()
        return OpenAICompatibleLLM(
            provider_label="groq",
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            timeout_s=settings.llm_timeout_seconds,
        )
    if provider == "openai":
        if not settings.openai_api_key:
            return MockLLM()
        return OpenAICompatibleLLM(
            provider_label="openai-compatible",
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_s=settings.llm_timeout_seconds,
        )
    if provider == "ollama":
        return OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_s=settings.llm_timeout_seconds,
        )
    # auto
    gemini_key = settings.gemini_key()
    if gemini_key:
        return GeminiLLM(
            api_key=gemini_key,
            model=settings.gemini_model,
            timeout_s=settings.llm_timeout_seconds,
        )
    if settings.groq_api_key:
        return OpenAICompatibleLLM(
            provider_label="groq",
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            timeout_s=settings.llm_timeout_seconds,
        )
    if settings.openai_api_key:
        return OpenAICompatibleLLM(
            provider_label="openai-compatible",
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_s=settings.llm_timeout_seconds,
        )
    ollama = OllamaLLM(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_s=settings.llm_timeout_seconds,
    )
    if ollama.is_live():
        return ollama
    return MockLLM()


def _post_json(
    url: str,
    payload: dict,
    *,
    timeout_s: float,
    headers: dict[str, str],
) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        # Drain the body so the socket is not leaked, then re-raise.
        try:
            error.read()
        except Exception:
            pass
        raise
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("provider returned non-JSON") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("provider JSON was not an object")
    return parsed


def _gemini_text(data: dict) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        prompt_feedback = data.get("promptFeedback")
        if isinstance(prompt_feedback, dict):
            raise RuntimeError("model blocked the prompt")
        raise RuntimeError("empty model response")
    first = candidates[0]
    if not isinstance(first, dict):
        raise RuntimeError("empty model response")
    content = first.get("content")
    if not isinstance(content, dict):
        raise RuntimeError("empty model response")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise RuntimeError("empty model response")
    texts = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            texts.append(part["text"])
    return "\n".join(texts).strip()


def _openai_text(data: dict) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("empty model response")
    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("empty model response")
    message = first.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("empty model response")
    content = message.get("content")
    if isinstance(content, str):
        return content
    raise RuntimeError("empty model response")


@dataclass(frozen=True)
class ProviderStatus:
    """UI banner fields."""

    label: str
    live: bool
    detail: str


def provider_status(client: LLMClient) -> ProviderStatus:
    """Describe the active client for the status banner."""
    name = client.name()
    live = client.is_live()
    if name == "mock" or not live:
        return ProviderStatus(
            label="Mock (no live model)",
            live=False,
            detail="Language output is a placeholder until an API key or Ollama is available.",
        )
    return ProviderStatus(
        label=f"Live · {name}",
        live=True,
        detail="The language lane calls a real model. Numbers and flags still come from local code.",
    )
