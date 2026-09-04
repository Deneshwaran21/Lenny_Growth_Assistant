from __future__ import annotations

import logging

import httpx

from app.config import Settings

logger = logging.getLogger("lenny.llm")


class LLMUnavailableError(Exception):
    pass


class LLMResult:
    def __init__(self, text: str, provider: str, model: str):
        self.text = text
        self.provider = provider
        self.model = model


async def _call_anthropic(settings: Settings, system: str, prompt: str) -> LLMResult:
    if not settings.ANTHROPIC_API_KEY:
        raise LLMUnavailableError("ANTHROPIC_API_KEY not configured")
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 1500,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        return LLMResult(text=text, provider="anthropic", model=settings.ANTHROPIC_MODEL)


async def _call_openai(settings: Settings, system: str, prompt: str) -> LLMResult:
    if not settings.OPENAI_API_KEY:
        raise LLMUnavailableError("OPENAI_API_KEY not configured")
    # Construct the native Gemini endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.OPENAI_MODEL}:generateContent"
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            url,
            headers={"x-goog-api-key": settings.OPENAI_API_KEY},
            json={
                "contents": [{
                    "role": "user",
                    "parts": [{"text": f"{system}\n\n{prompt}"}]
                }]
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return LLMResult(text=text, provider="openai", model=settings.OPENAI_MODEL)


async def _call_ollama(settings: Settings, system: str, prompt: str) -> LLMResult:
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": f"{system}\n\n{prompt}",
                    "stream": False,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Ollama unreachable at {settings.OLLAMA_BASE_URL}: {exc}") from exc
        data = resp.json()
        return LLMResult(text=data.get("response", ""), provider="ollama", model=settings.OLLAMA_MODEL)


_PROVIDER_FNS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "ollama": _call_ollama,
}


async def generate(
    settings: Settings, system: str, prompt: str, provider_override: str | None = None
) -> LLMResult:
    primary = provider_override or settings.LLM_PROVIDER
    fallback = settings.FALLBACK_PROVIDER

    try:
        fn = _PROVIDER_FNS[primary]
        return await fn(settings, system, prompt)
    except Exception as exc:  # noqa: BLE001 - intentionally broad, this is a fallback boundary
        logger.warning(
            "Primary provider '%s' failed (%s). Falling back to '%s'.", primary, exc, fallback
        )
        if fallback == primary:
            raise LLMUnavailableError(str(exc)) from exc
        try:
            fn = _PROVIDER_FNS[fallback]
            return await fn(settings, system, prompt)
        except Exception as fallback_exc:  # noqa: BLE001
            logger.error("Fallback provider '%s' also failed: %s", fallback, fallback_exc)
            raise LLMUnavailableError(
                f"Both '{primary}' and fallback '{fallback}' are unavailable"
            ) from fallback_exc