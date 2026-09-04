"""
Agent routing layer.

`route_message` decides which skill handles a user turn:
  - "artifact" if the user explicitly asks to generate/export a doc/markdown/html artifact
  - "ship30"   if the user asks for a Ship 30 / atomic essay / blog-style post
  - "qa"       otherwise (default grounded Q&A)

Routing is deliberately simple keyword/intent matching rather than a second
LLM call, per the assignment's push for "clear skill boundaries" and
"sensible failure behavior" — a rules-based router is transparent,
debuggable, zero-latency, and has no failure mode of its own. If this needs
to get smarter later, swap `detect_intent` for a small classifier without
touching the skills themselves.
"""
from __future__ import annotations

import logging

from app.agent.rag import KnowledgeBase
from app.agent.skills import artifact as artifact_skill
from app.agent.skills import qa as qa_skill
from app.agent.skills import ship30 as ship30_skill
from app.config import Settings

logger = logging.getLogger("lenny.agent")

ARTIFACT_KEYWORDS = ["artifact", "generate a doc", "markdown doc", "html snippet", "export this", "render this as"]
SHIP30_KEYWORDS = ["ship 30", "ship30", "atomic essay", "blog post", "newsletter post", "write an essay"]


def detect_intent(message: str, explicit_skill: str) -> str:
    if explicit_skill != "auto":
        return explicit_skill
    lowered = message.lower()
    if any(k in lowered for k in ARTIFACT_KEYWORDS):
        return "artifact"
    if any(k in lowered for k in SHIP30_KEYWORDS):
        return "ship30"
    return "qa"


async def handle_turn(
    settings: Settings,
    kb: KnowledgeBase,
    message: str,
    history_text: str,
    explicit_skill: str,
    provider_override: str | None,
) -> dict:
    intent = detect_intent(message, explicit_skill)
    logger.info("Routed message to skill=%s provider_override=%s", intent, provider_override)

    if intent == "ship30":
        result = await ship30_skill.write_ship30_essay(settings, kb, message, provider_override)
        result["skill_used"] = "ship30"
        return result

    if intent == "artifact":
        kind = "html" if "html" in message.lower() else "markdown"
        art = await artifact_skill.generate_artifact(
            settings, history_text, message, kind, provider_override
        )
        return {
            "reply": f"Generated a {kind} artifact — opened it in the Artifact Viewer.",
            "provider_used": art["provider_used"],
            "sources": [],
            "grounded": False,
            "skill_used": "artifact",
            "artifact_content": art["content"],
            "artifact_kind": art["kind"],
            "artifact_sanitized": art["sanitized"],
        }

    result = await qa_skill.answer_question(settings, kb, message, history_text, provider_override)
    result["skill_used"] = "qa"
    return result
