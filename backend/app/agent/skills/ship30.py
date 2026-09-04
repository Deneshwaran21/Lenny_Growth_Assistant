"""
Ship 30 for 30-style essay skill.

This encodes the Ship 30 for 30 "atomic essay" principles as structured
rules rather than a one-off prompt, per assignment 4.2:
  - Strong, specific hook in the first 1-2 sentences (no throat-clearing)
  - One core idea per essay, developed with a clear narrative arc
  - Skimmable formatting: short paragraphs, headers, bullets, selective bold
  - Concrete examples over abstraction
  - Ends with one specific, actionable takeaway (not a vague summary)
  - ~1,250 words
All claims must be traceable to the retrieved transcript chunks (grounding
requirement) — the skill reuses the same retrieval call as the Q&A skill so
the essay never drifts from the knowledge base.
"""
from __future__ import annotations

from app.agent.llm_client import generate
from app.agent.rag import KnowledgeBase
from app.config import Settings

SYSTEM_PROMPT = """You are a ghostwriter who writes in the "Ship 30 for 30" atomic essay \
style, applied to product/growth topics from Lenny's Podcast transcripts.

Ship 30 for 30 style rules (follow ALL of them):
1. HOOK: Open with a specific, punchy 1-2 sentence hook. No "In today's fast-paced world..." \
   throat-clearing. Start in the middle of a concrete moment, a surprising claim, or a sharp question.
2. ONE IDEA: The essay develops exactly one core idea end-to-end. Every section should clearly \
   serve that one idea.
3. NARRATIVE ARC: Problem -> insight -> proof/example -> implication -> takeaway. Don't just list facts.
4. SKIMMABLE: Use short paragraphs (2-4 sentences), H2/H3 headers, bullet lists, and **selective bold** \
   on the single most important phrase per section. Do not bold entire sentences.
5. CONCRETE: Prefer specific examples and mechanisms from the transcripts over abstract claims.
6. GROUNDING: Every factual claim must come from the provided transcript excerpts. If the excerpts \
   don't fully support a claim you want to make, soften it or drop it.
7. LENGTH: Target approximately 1,250 words.
8. CLOSE: End with a clearly labeled "## Takeaway" section containing ONE specific, actionable next step \
   the reader can apply this week — not a generic summary of the essay.

Output clean Markdown only.
"""


async def write_ship30_essay(
    settings: Settings,
    kb: KnowledgeBase,
    topic: str,
    provider_override: str | None,
) -> dict:
    results = kb.search(topic, max(settings.TOP_K_CHUNKS, 6))
    relevant = [r for r in results if r.score > 0.0]

    if not relevant:
        return {
            "reply": (
                "I don't have enough grounded material on that topic yet to write a "
                "Ship 30 for 30 essay without risking unsupported claims. Try a topic "
                "closer to what's in the current knowledge base."
            ),
            "provider_used": "none",
            "sources": [],
            "grounded": False,
            "artifact_markdown": None,
        }

    context_block = "\n\n".join(
        f"[Source: {r.chunk.episode_title}]\n{r.chunk.text}" for r in relevant
    )
    prompt = (
        f"Write a Ship 30 for 30-style essay about: {topic}\n\n"
        f"Ground every claim in these transcript excerpts:\n{context_block}\n\n"
        "Remember: ~1,250 words, strong hook, one idea, skimmable formatting, "
        "and a '## Takeaway' section at the end with one specific action."
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
        "reply": f"Here's your Ship 30 for 30 essay on **{topic}** — opened it in the Artifact Viewer.",
        "provider_used": result.provider,
        "sources": sources,
        "grounded": True,
        "artifact_markdown": result.text,
    }
