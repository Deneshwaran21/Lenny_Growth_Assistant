"""Grounded conversational Q&A skill.

Strictly answers from retrieved transcript chunks. If retrieval returns
nothing above a relevance floor, the skill returns `grounded=False` and an
explicit "not covered by the transcripts I have" response instead of
letting the model guess — this is the #1 hallucination guardrail called
out in the PRD risk section.
"""
from __future__ import annotations

from app.agent.llm_client import generate
from app.agent.rag import KnowledgeBase
from app.config import Settings

SYSTEM_PROMPT = """You are the Lenny Growth Assistant, an internal assistant that answers \
product management and growth questions STRICTLY using the provided transcript excerpts \
from Lenny's Podcast/Newsletter. Rules:
1. Only use facts present in the excerpts below. Do not use outside knowledge.
2. If the excerpts don't contain enough to answer, say so plainly and suggest what to ask instead.
3. When you make a claim, mention which episode it comes from (by title).
4. Keep answers skimmable: short paragraphs, bullets where useful.
5. Preserve conversation context from the chat history provided.
"""

MIN_RELEVANCE = 0.05  # TF-IDF cosine floor; tune per corpus size


async def answer_question(
    settings: Settings,
    kb: KnowledgeBase,
    question: str,
    history_text: str,
    provider_override: str | None,
) -> dict:
    results = kb.search(question, settings.TOP_K_CHUNKS)
    relevant = [r for r in results if r.score >= MIN_RELEVANCE]

    if not relevant:
        return {
            "reply": (
                "I couldn't find anything in the ingested Lenny's Podcast transcripts "
                "that supports an answer to that question. Try rephrasing, or ask about "
                "a topic covered in the current knowledge base (e.g. PLG fundamentals, "
                "activation metrics, or pricing & packaging)."
            ),
            "provider_used": "none",
            "sources": [],
            "grounded": False,
        }

    context_block = "\n\n".join(
        f"[Source: {r.chunk.episode_title} | chunk {r.chunk.chunk_id}]\n{r.chunk.text}"
        for r in relevant
    )
    prompt = (
        f"Conversation so far:\n{history_text}\n\n"
        f"Transcript excerpts:\n{context_block}\n\n"
        f"User question: {question}\n\n"
        "Answer using only the excerpts above."
    )

    result = await generate(settings, SYSTEM_PROMPT, prompt, provider_override)

    sources = [
        {
            "transcript_id": r.chunk.transcript_id,
            "episode_title": r.chunk.episode_title,
            "chunk_id": r.chunk.chunk_id,
            "excerpt": r.chunk.text[:220] + ("..." if len(r.chunk.text) > 220 else ""),
        }
        for r in relevant
    ]

    return {
        "reply": result.text,
        "provider_used": result.provider,
        "sources": sources,
        "grounded": True,
    }
