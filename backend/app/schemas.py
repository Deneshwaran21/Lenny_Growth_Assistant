from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------- Sessions ----------
class SessionCreate(BaseModel):
    user_id: str = Field(default="anonymous")
    provider: Literal["anthropic", "openai", "ollama"] | None = None
    title: str | None = None


class SessionOut(BaseModel):
    id: str
    user_id: str
    title: str
    provider: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Chat ----------
class SourceCitation(BaseModel):
    transcript_id: str
    episode_title: str
    chunk_id: str
    excerpt: str


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=8000)
    provider_override: Literal["anthropic", "openai", "ollama"] | None = None
    skill: Literal["auto", "qa", "ship30", "artifact"] = "auto"


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    reply: str
    provider_used: str
    skill_used: str
    sources: list[SourceCitation]
    artifact_id: str | None = None
    grounded: bool


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    provider_used: str | None
    sources: list
    skill_used: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Artifacts ----------
class ArtifactOut(BaseModel):
    id: str
    session_id: str
    kind: str
    title: str
    content: str
    sanitized: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Config / health ----------
class ProviderStatus(BaseModel):
    provider: str
    configured: bool
    reachable: bool | None = None
    model: str | None = None


class ConfigOut(BaseModel):
    active_provider: str
    fallback_provider: str
    providers: list[ProviderStatus]


class HealthOut(BaseModel):
    status: Literal["ok", "degraded", "down"]
    database: bool
    knowledge_base_chunks: int
    active_provider: str
    detail: str | None = None
