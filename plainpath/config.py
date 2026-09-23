"""Runtime settings. Environment is read when Settings() is constructed, not at import."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import sys
from typing import Callable


def _env(name: str, default: str = "") -> str:
    """Return a stripped environment variable, or default if unset/blank."""
    raw = os.getenv(name)
    if raw is None:
        return default
    stripped = raw.strip()
    return stripped if stripped else default


def _secret(name: str) -> str | None:
    """Read a secret from the process environment, then Streamlit secrets if loaded."""
    env_val = os.getenv(name)
    if env_val and env_val.strip():
        return env_val.strip()
    if "streamlit" not in sys.modules:
        return None
    try:
        import streamlit as st

        if name in st.secrets:
            value = st.secrets.get(name)
            if value is None:
                return None
            text = str(value).strip()
            return text or None
    except Exception:
        return None
    return None


def _secret_factory(name: str) -> Callable[[], str | None]:
    return lambda: _secret(name)


def _env_factory(name: str, default: str) -> Callable[[], str]:
    return lambda: _env(name, default)


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded per instantiation."""

    app_title: str = "PlainPath"
    app_tagline: str = "See through legal documents. Facts stay local. Language comes from a live model."

    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "auto").lower())
    llm_timeout_seconds: float = field(
        default_factory=lambda: float(_env("LLM_TIMEOUT_SECONDS", "45") or "45")
    )

    gemini_api_key: str | None = field(default_factory=_secret_factory("GEMINI_API_KEY"))
    google_api_key: str | None = field(default_factory=_secret_factory("GOOGLE_API_KEY"))
    gemini_model: str = field(default_factory=_env_factory("GEMINI_MODEL", "gemini-2.5-flash"))

    groq_api_key: str | None = field(default_factory=_secret_factory("GROQ_API_KEY"))
    groq_model: str = field(default_factory=_env_factory("GROQ_MODEL", "llama-3.1-8b-instant"))
    groq_base_url: str = field(
        default_factory=_env_factory("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    )

    openai_api_key: str | None = field(default_factory=_secret_factory("OPENAI_API_KEY"))
    openai_base_url: str = field(
        default_factory=_env_factory("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_model: str = field(default_factory=_env_factory("OPENAI_MODEL", "gpt-4o-mini"))

    ollama_base_url: str = field(
        default_factory=_env_factory("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(default_factory=_env_factory("OLLAMA_MODEL", "llama3.2"))

    def gemini_key(self) -> str | None:
        """Gemini accepts either GEMINI_API_KEY or GOOGLE_API_KEY."""
        return self.gemini_api_key or self.google_api_key


def get_settings() -> Settings:
    """Build a fresh Settings object from the current environment."""
    return Settings()
