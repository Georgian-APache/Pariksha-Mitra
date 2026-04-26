"""Voice tutor route - turns a spoken question into a short tutor answer.

The frontend captures speech via the browser's Web Speech API (free, zero-cost)
and POSTs the transcript here. We make ONE Gemini call per query, capped to a
short ~200-token tutor reply, and try to attach a recommended ``concept_id``
from the active concept DAG so the UI can offer a follow-up drill quiz.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import gemini_text
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag

router = APIRouter(prefix="/voice", tags=["voice"])

log = logging.getLogger("parikshamitra.voice")


class VoiceAskRequest(BaseModel):
    user_id: str
    transcript: str = Field(min_length=1, max_length=2000)
    language: Literal["en-IN", "hi-IN"] = "en-IN"


class VoiceAskResponse(BaseModel):
    answer_text: str
    concept_id: str | None
    sources: list[str] = []


_SYSTEM_EN = (
    "You are ParikshaMitra, a warm, concise voice tutor for an Indian competitive-exam "
    "student (JEE / NEET). The student asked their question by voice, so reply in plain "
    "spoken prose - no markdown, no lists, no formulas in LaTeX, no code fences. "
    "Keep it under 120 words. End with one short follow-up question to keep them engaged. "
    "If the topic doesn't match the syllabus, gently steer them back."
)

_SYSTEM_HI = (
    "Aap ParikshaMitra hain - ek warm, concise voice tutor jo Indian competitive-exam "
    "(JEE / NEET) ke students ki madad karte hain. Student ne apna sawaal awaaz se poocha hai, "
    "isliye jawab simple Hinglish (Roman script) mein dijiye - bina markdown, bina list, bina "
    "LaTeX formulas, bina code fences. 120 shabd se kam rakhiye. Antim mein ek chhota follow-up "
    "sawaal poochhiye taaki student engaged rahe."
)


def _guess_concept_id(transcript: str, exam: str) -> str | None:
    """Tiny heuristic concept tag: pick the DAG node whose name shares the most
    word overlap with the transcript. Returns None if there's no signal so the
    UI can degrade gracefully.
    """

    try:
        dag = get_dag(exam)
    except Exception:  # noqa: BLE001
        return None
    text = transcript.lower()
    best: tuple[str | None, int] = (None, 0)
    for node in dag.all_concepts():
        name = str(node.get("name", "")).lower()
        if not name:
            continue
        # Simple token overlap: count name tokens that appear in transcript.
        tokens = [t for t in name.replace("-", " ").split() if len(t) > 2]
        if not tokens:
            continue
        score = sum(1 for t in tokens if t in text)
        if score > best[1]:
            best = (node["id"], score)
    return best[0] if best[1] > 0 else None


@router.post("/ask", response_model=VoiceAskResponse)
async def voice_ask(
    body: VoiceAskRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> VoiceAskResponse:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    system = _SYSTEM_HI if body.language == "hi-IN" else _SYSTEM_EN
    settings = get_settings()
    prompt = (
        f"Student ({user.target_exam}, exam date {user.exam_date or 'TBD'}) asks:\n"
        f"\"{body.transcript.strip()}\"\n\n"
        "Reply as a spoken tutor."
    )

    try:
        text = await gemini_text(
            keys=keys,
            prompt=prompt,
            system=system,
            model=settings.gemini_default_model,
            temperature=0.5,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Voice tutor LLM failed: %s", exc)
        raise HTTPException(502, f"Voice tutor failed: {exc}") from exc

    answer = (text or "").strip()
    if not answer:
        answer = (
            "Sorry, I couldn't generate an answer right now. Please try rephrasing your question."
            if body.language == "en-IN"
            else "Maaf kijiye, abhi jawab nahi bana paaya. Sawaal dobara poochhiye."
        )

    concept_id = _guess_concept_id(body.transcript, user.target_exam)

    return VoiceAskResponse(
        answer_text=answer,
        concept_id=concept_id,
        sources=[],
    )
