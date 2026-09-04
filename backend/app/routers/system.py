from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.agent.rag import get_knowledge_base
from app.config import get_settings
from app.database import engine
from app.schemas import ConfigOut, HealthOut, ProviderStatus

router = APIRouter(prefix="/api", tags=["system"])
logger = logging.getLogger("lenny.system")
settings = get_settings()
kb = get_knowledge_base(settings)


@router.get("/health", response_model=HealthOut)
async def health():
    db_ok = True
    detail = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        detail = f"database unreachable: {exc}"
        logger.error(detail)

    status = "ok" if db_ok and kb.size > 0 else "degraded"
    if not db_ok:
        status = "down"

    return HealthOut(
        status=status,
        database=db_ok,
        knowledge_base_chunks=kb.size,
        active_provider=settings.LLM_PROVIDER,
        detail=detail,
    )


@router.post("/kb/refresh")
async def refresh_kb():
    count = kb.refresh()
    return {"chunks_indexed": count}


@router.get("/config", response_model=ConfigOut)
async def get_config():
    providers = []

    providers.append(
        ProviderStatus(
            provider="anthropic",
            configured=bool(settings.ANTHROPIC_API_KEY),
            model=settings.ANTHROPIC_MODEL,
        )
    )
    providers.append(
        ProviderStatus(
            provider="openai",
            configured=bool(settings.OPENAI_API_KEY),
            model=settings.OPENAI_MODEL,
        )
    )

    ollama_reachable = None
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_reachable = resp.status_code == 200
    except Exception:  # noqa: BLE001
        ollama_reachable = False

    providers.append(
        ProviderStatus(
            provider="ollama",
            configured=True,
            reachable=ollama_reachable,
            model=settings.OLLAMA_MODEL,
        )
    )

    return ConfigOut(
        active_provider=settings.LLM_PROVIDER,
        fallback_provider=settings.FALLBACK_PROVIDER,
        providers=providers,
    )
