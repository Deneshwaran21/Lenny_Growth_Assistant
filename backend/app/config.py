"""
Central configuration for The Lenny Growth Assistant.

Design note (see architecture.md #model-toggle):
The evaluator switches providers purely via environment variables / the
/api/config endpoint — no code changes are required. `LLM_PROVIDER` selects
"anthropic", "openai", or "ollama". If the selected provider is unreachable
or misconfigured, the agent layer falls back to OLLAMA (local-first, always
available) and logs a structured warning — see agent/agent.py::get_llm_client.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "The Lenny Growth Assistant"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    # Postgres (Supabase / Railway compatible). Example:
    # postgresql+asyncpg://user:pass@host:5432/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/lenny_assistant"

    # --- LLM provider toggle ---
    LLM_PROVIDER: Literal["anthropic", "openai", "ollama"] = "ollama"
    FALLBACK_PROVIDER: Literal["anthropic", "openai", "ollama"] = "ollama"

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Add this line: base URL for OpenAI-compatible endpoints (e.g., Gemini)
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # --- RAG ---
    TRANSCRIPTS_DIR: str = "app/data/transcripts"
    CHUNK_SIZE_WORDS: int = 220
    CHUNK_OVERLAP_WORDS: int = 40
    TOP_K_CHUNKS: int = 5
    EMBEDDING_BACKEND: Literal["tfidf", "sentence-transformers"] = "tfidf"

    # --- Request timeouts ---
    LLM_TIMEOUT_SECONDS: int = 45

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()