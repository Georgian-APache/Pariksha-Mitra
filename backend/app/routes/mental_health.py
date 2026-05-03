"""Mental health (MindMitra) routes."""

from __future__ import annotations

import logging
import uuid
from datetime import date as date_t
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.therapist import detect_crisis, run_therapist, run_therapist_chat
from app.agents.llm import gemini_json
from app.agents.prompts import THERAPIST_SYSTEM
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.services.whatsapp import cooldown_ok, send_crisis_alert

router = APIRouter(prefix="/mental-health", tags=["mental_health"])
log = logging.getLogger("parikshamitra.mental_health")


class CheckinRequest(BaseModel):
    user_id: str
    mood_score: int = Field(ge=1, le=10)
    feeling_text: str = ""
    tags: list[str] = []


class CheckinResponse(BaseModel):
    response_en: str
    response_hi: str
    detected_mood_score: int
    mood_tags: list[str]
    coping_suggestion: str
    escalation_needed: bool
    follow_up_question: str = ""


class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str = ""


class ChatResponse(BaseModel):
    conversation_id: str
    response_en: str
    response_hi: str
    mood_tags: list[str]
    coping_suggestion: str
    escalation_needed: bool = False
    parent_alerted: bool = False


@router.post("/checkin", response_model=CheckinResponse)
async def checkin(
    body: CheckinRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> CheckinResponse:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    result = await run_therapist(
        keys=keys,
        feeling_text=body.feeling_text,
        mood_score=body.mood_score,
        tags=body.tags,
        recent_mood_history=list(user.mood_history or []),
    )

    await repo.add_mood_entry(
        session, user,
        score=body.mood_score,
        tags=body.tags or result.get("mood_tags", []),
        note=body.feeling_text,
    )

    # Check escalation: 3+ consecutive low checkins
    recent = list(user.mood_history or [])[-3:]
    consecutive_low = sum(1 for e in recent if e.get("score", 10) <= 3)
    flags = dict(user.mental_health_flags or {})
    if consecutive_low >= 3:
        flags["consecutive_low_mood"] = consecutive_low
        flags["escalation_sent"] = False
    user.mental_health_flags = flags
    await session.commit()

    return CheckinResponse(
        response_en=result.get("response_en", ""),
        response_hi=result.get("response_hi", ""),
        detected_mood_score=result.get("detected_mood_score", body.mood_score),
        mood_tags=result.get("mood_tags", []),
        coping_suggestion=result.get("coping_suggestion", ""),
        escalation_needed=result.get("escalation_needed", False),
        follow_up_question=result.get("follow_up_question", ""),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    conv_id = body.conversation_id or str(uuid.uuid4())

    # Fetch history BEFORE saving current message so it isn't duplicated
    history_rows = await repo.get_conversation(session, body.user_id, conv_id, limit=10)
    conversation_history = [{"role": m.role, "content": m.content} for m in history_rows]

    student_profile = {
        "display_name": user.display_name,
        "target_exam": user.target_exam,
        "exam_date": user.exam_date,
        "daily_hours": user.daily_hours,
        "streak_days": user.streak_days or 0,
        "mood_history": list(user.mood_history or []),
        "stress_level": user.stress_level or 5.0,
        "consecutive_misses": user.consecutive_misses or 0,
    }

    result = await run_therapist_chat(
        keys=keys,
        user_message=body.message,
        conversation_history=conversation_history,
        student_profile=student_profile,
    )

    # Persist both turns
    await repo.add_chat_message(
        session,
        user_id=body.user_id,
        conversation_id=conv_id,
        role="user",
        content=body.message,
    )
    await repo.add_chat_message(
        session,
        user_id=body.user_id,
        conversation_id=conv_id,
        role="assistant",
        content=result.get("response_en", ""),
        mood_score=result.get("detected_mood_score"),
        mood_tags=result.get("mood_tags", []),
    )

    # Crisis: WhatsApp parent immediately — no cooldown, crisis is always urgent
    is_crisis = detect_crisis(body.message)
    parent_alerted = False
    if is_crisis:
        parent_phone = user.parent_phone
        if parent_phone:
            try:
                await send_crisis_alert(
                    parent_phone=parent_phone,
                    parent_name=user.parent_name or "Parent",
                    student_name=user.display_name,
                    trigger_message=body.message,
                )
                parent_alerted = True
            except Exception as exc:
                log.warning("Crisis WhatsApp failed: %s", exc)
        else:
            log.warning(
                "CRISIS detected for user=%s but no parent_phone on file.",
                user.display_name,
            )

    return ChatResponse(
        conversation_id=conv_id,
        response_en=result.get("response_en", ""),
        response_hi=result.get("response_hi", ""),
        mood_tags=result.get("mood_tags", []),
        coping_suggestion=result.get("coping_suggestion", ""),
        escalation_needed=is_crisis,
        parent_alerted=parent_alerted,
    )


@router.get("/{user_id}/history")
async def get_history(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return {
        "mood_history": list(user.mood_history or []),
        "stress_level": user.stress_level,
        "mental_health_flags": user.mental_health_flags,
    }


@router.get("/{user_id}/insights")
async def get_insights(
    user_id: str,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    history = list(user.mood_history or [])[-14:]
    if not history:
        return {"insight_en": "No mood data yet.", "insight_hi": "अभी कोई डेटा नहीं।", "recommendations": []}

    try:
        s = get_settings()
        prompt = (
            f"Analyze the following 14-day mood history for a JEE student and provide:\n"
            f"1. insight_en: 2-sentence English insight about mood trend and study impact\n"
            f"2. insight_hi: same in Hindi\n"
            f"3. recommendations: list of 3 actionable tips\n\n"
            f"Mood history: {history}"
        )
        schema = {
            "type": "OBJECT",
            "properties": {
                "insight_en": {"type": "STRING"},
                "insight_hi": {"type": "STRING"},
                "recommendations": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["insight_en", "insight_hi", "recommendations"],
        }
        result = await gemini_json(
            keys=keys, prompt=prompt, schema=schema,
            system=THERAPIST_SYSTEM, model=s.gemini_default_model,
        )
        return result
    except Exception:  # noqa: BLE001
        avg = sum(e.get("score", 5) for e in history) / len(history)
        return {
            "insight_en": f"Your average mood over the last {len(history)} days is {avg:.1f}/10.",
            "insight_hi": f"पिछले {len(history)} दिनों का औसत मूड {avg:.1f}/10 रहा।",
            "recommendations": [
                "Take regular breaks during study sessions.",
                "Ensure 7-8 hours of sleep.",
                "Talk to a friend or family member when feeling low.",
            ],
        }
