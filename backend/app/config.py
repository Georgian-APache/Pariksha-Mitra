"""Centralised settings + API key resolution.

Keys are resolved in order: per-request headers (``X-Gemini-Key``, ``X-Groq-Key``)
if present, otherwise ``DEFAULT_GEMINI_API_KEY`` / ``DEFAULT_GROQ_API_KEY`` from
the environment. Header keys are never persisted.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import Header, HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "app" / "data"
CHROMA_DIR = BACKEND_ROOT / "chroma_store"


class Settings(BaseSettings):
    """Runtime settings - overridden by environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "ParikshaMitra"
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Persistence ----
    # libsql:// works for Turso; sqlite+aiosqlite:/// for local async SQLite
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_ROOT / 'parikshamitra.db').as_posix()}"

    # ---- Model selection (free tiers) ----
    gemini_default_model: str = "gemini-2.0-flash"
    gemini_reasoning_model: str = "gemini-2.5-flash"
    gemini_vision_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_strong_model: str = "llama-3.3-70b-versatile"
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # ---- Optional server-side fallback keys (dev only) ----
    default_gemini_api_key: str | None = None
    default_groq_api_key: str | None = None

    # ---- Tunables ----
    diagnostic_question_count: int = 15
    quiz_default_count: int = 10
    drill_question_count: int = 5
    sm2_min_interval_days: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ---------------------------------------------------------------------------
# BYOK helpers
# ---------------------------------------------------------------------------

class APIKeys:
    """Bag of per-request API keys."""

    __slots__ = ("gemini", "groq")

    def __init__(self, gemini: str | None, groq: str | None) -> None:
        self.gemini = gemini
        self.groq = groq

    def require(self, provider: Literal["gemini", "groq"]) -> str:
        key = getattr(self, provider)
        if not key:
            raise HTTPException(
                status_code=401,
                detail=(
                    f"Missing {provider} API key. Set DEFAULT_{provider.upper()}_API_KEY "
                    "on the server or send the appropriate X-*-Key header."
                ),
            )
        return key


def api_keys(
    x_gemini_key: str | None = Header(default=None, alias="X-Gemini-Key"),
    x_groq_key: str | None = Header(default=None, alias="X-Groq-Key"),
) -> APIKeys:
    """FastAPI dependency: header keys override server defaults from settings."""

    s = get_settings()
    return APIKeys(
        gemini=x_gemini_key or s.default_gemini_api_key,
        groq=x_groq_key or s.default_groq_api_key,
    )
