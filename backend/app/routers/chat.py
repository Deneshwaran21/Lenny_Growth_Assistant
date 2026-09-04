from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import handle_turn
from app.agent.llm_client import LLMUnavailableError
from app.agent.rag import get_knowledge_base
from app.config import get_settings
from app.database import get_db
from app.models import Artifact, ChatMessage, ChatSession
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger("lenny.chat")
settings = get_settings()
kb = get_knowledge_base(settings)


def _history_to_text(messages: list[ChatMessage], max_turns: int = 8) -> str:
    recent = messages[-max_turns:]
    lines = [f"{m.role.upper()}: {m.content}" for m in recent]
    return "\n".join(lines) if lines else "(no prior turns)"


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Create one via POST /api/sessions first.")

    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
    )
    history = result.scalars().all()
    history_text = _history_to_text(history)

    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_msg)
    await db.flush()

    try:
        outcome = await handle_turn(
            settings,
            kb,
            payload.message,
            history_text,
            payload.skill,
            payload.provider_override,
        )
    except LLMUnavailableError as exc:
        logger.error("LLM unavailable for session %s: %s", session.id, exc)
        await db.rollback()
        raise HTTPException(
            status_code=503,
            detail=(
                "No language model provider is currently reachable (cloud key missing/invalid "
                "and local Ollama unreachable). Check /api/config and your .env, or start Ollama."
            ),
        ) from exc

    artifact_id = None
    if outcome.get("artifact_markdown"):
        artifact = Artifact(
            session_id=session.id,
            kind="markdown",
            title=payload.message[:80],
            content=outcome["artifact_markdown"],
            sanitized=False,
        )
        db.add(artifact)
        await db.flush()
        artifact_id = artifact.id
    elif outcome.get("artifact_content"):
        artifact = Artifact(
            session_id=session.id,
            kind=outcome["artifact_kind"],
            title=payload.message[:80],
            content=outcome["artifact_content"],
            sanitized=outcome.get("artifact_sanitized", False),
        )
        db.add(artifact)
        await db.flush()
        artifact_id = artifact.id

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=outcome["reply"],
        provider_used=outcome.get("provider_used"),
        sources=outcome.get("sources", []),
        skill_used=outcome.get("skill_used"),
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        session_id=session.id,
        message_id=assistant_msg.id,
        reply=outcome["reply"],
        provider_used=outcome.get("provider_used", "unknown"),
        skill_used=outcome.get("skill_used", "qa"),
        sources=outcome.get("sources", []),
        artifact_id=artifact_id,
        grounded=outcome.get("grounded", False),
    )
