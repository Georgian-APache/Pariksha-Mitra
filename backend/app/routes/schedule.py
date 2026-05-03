"""Schedule accountability + reality-check quiz routes."""

from __future__ import annotations

from datetime import date as date_t, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.quizmaster import generate_questions, grade_answer
from app.agents.state import GradedAnswer, Question
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.db.models import StudySession
from app.services.whatsapp import cooldown_ok, send_parent_alert

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _today() -> str:
    return date_t.today().isoformat()


@router.get("/{user_id}/today")
async def get_today(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    today = _today()
    existing = await repo.get_study_sessions_for_date(session, user_id, today)
    existing_keys = {(s.concept_id, s.activity) for s in existing}

    # Auto-create from plan
    plan = user.plan or {}
    days: list[dict] = plan.get("days", [])
    today_day = next((d for d in days if d.get("date") == today), None)
    if today_day:
        for block in today_day.get("blocks", []):
            key = (block.get("concept_id", ""), block.get("activity", ""))
            if key not in existing_keys:
                ss = await repo.create_study_session(
                    session,
                    user_id=user_id,
                    plan_date=today,
                    concept_id=block.get("concept_id", ""),
                    subject=block.get("subject", ""),
                    activity=block.get("activity", "learn"),
                    scheduled_minutes=block.get("minutes", 60),
                )
                existing.append(ss)

    return {
        "date": today,
        "sessions": [_ss_dict(s) for s in existing],
        "consecutive_misses": user.consecutive_misses or 0,
        "summary": {
            "total": len(existing),
            "completed": sum(1 for s in existing if s.status in ("completed", "quiz_passed")),
            "skipped": sum(1 for s in existing if s.status == "skipped"),
        },
    }


class MarkRequest(BaseModel):
    user_id: str
    session_id: str
    studied: bool


@router.post("/mark")
async def mark_session(
    body: MarkRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    ss = await repo.get_study_session(session, body.session_id)
    if not ss or ss.user_id != body.user_id:
        raise HTTPException(404, "session not found")

    settings = get_settings()

    if body.studied:
        # Generate reality-check quiz
        questions = await generate_questions(
            keys=keys,
            requests=[{"concept_id": ss.concept_id, "subject": ss.subject, "difficulty": 3}] * 5,
            exam=user.target_exam,
            prefer_seed=True,
        )
        # Deduplicate by stem
        seen_stems: set[str] = set()
        unique_qs: list[Question] = []
        for q in questions:
            if q.stem not in seen_stems:
                seen_stems.add(q.stem)
                unique_qs.append(q)
        unique_qs = unique_qs[:5]

        ss.status = "quiz_pending"
        ss.reality_check_questions = [q.model_dump() for q in unique_qs]
        await session.commit()

        # Reset misses on studying
        user.consecutive_misses = 0
        await session.commit()

        return {
            "status": "quiz_pending",
            "quiz_questions": [q.model_dump() for q in unique_qs],
            "session_id": ss.id,
        }
    else:
        # Mark skipped
        ss.status = "skipped"
        user.consecutive_misses = (user.consecutive_misses or 0) + 1
        await session.commit()

        alert_sent = False
        if (
            user.consecutive_misses >= settings.parent_alert_miss_threshold
            and user.parent_phone
            and cooldown_ok(user.last_parent_alert_date, settings.parent_alert_cooldown_hours)
        ):
            missed = await repo.get_recent_missed_topics(session, body.user_id, limit=5)
            await send_parent_alert(
                parent_phone=user.parent_phone,
                parent_name=user.parent_name or "Parent",
                student_name=user.display_name,
                consecutive_misses=user.consecutive_misses,
                missed_topics=missed,
            )
            user.last_parent_alert_date = _today()
            await session.commit()
            alert_sent = True

        return {
            "status": "skipped",
            "consecutive_misses": user.consecutive_misses,
            "parent_alerted": alert_sent,
            "warning": (
                f"{user.consecutive_misses}/{settings.parent_alert_miss_threshold} misses — parent alert will trigger on next miss."
                if user.consecutive_misses == settings.parent_alert_miss_threshold - 1
                else None
            ),
        }


class RealityCheckSubmit(BaseModel):
    user_id: str
    session_id: str
    answers: list[dict[str, Any]]  # [{question_id, chosen_index}]


@router.post("/submit-reality-check")
async def submit_reality_check(
    body: RealityCheckSubmit,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    ss = await repo.get_study_session(session, body.session_id)
    if not ss or ss.user_id != body.user_id:
        raise HTTPException(404, "session not found")

    questions = {q["id"]: Question.model_validate(q) for q in (ss.reality_check_questions or [])}
    graded: list[dict] = []
    total_score = 0.0

    for ans in body.answers:
        q = questions.get(ans.get("question_id", ""))
        if not q:
            continue
        g = await grade_answer(keys=keys, question=q, chosen_index=int(ans.get("chosen_index", 0)))
        graded.append(g.model_dump())
        total_score += g.score

    n = len(graded) or 1
    avg_score = total_score / n
    passed = avg_score >= 0.6

    ss.quiz_score = round(avg_score, 3)
    ss.status = "quiz_passed" if passed else "quiz_failed"
    ss.completed_at = datetime.now(timezone.utc)
    await session.commit()

    if passed:
        user.consecutive_misses = 0
        await session.commit()

    return {
        "score": round(avg_score, 3),
        "passed": passed,
        "graded_answers": graded,
        "feedback_en": (
            "Great work! You've demonstrated understanding of this concept." if passed
            else "Keep revising! Review the explanations below and try again tomorrow."
        ),
        "feedback_hi": (
            "बहुत अच्छा! आपने इस अवधारणा की समझ दिखाई।" if passed
            else "दोबारा पढ़ो! नीचे दी गई व्याख्याएँ देखें और कल फिर प्रयास करें।"
        ),
    }


@router.get("/{user_id}/weekly-summary")
async def weekly_summary(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    from sqlalchemy import select
    from app.db.models import StudySession as SS
    rows = await session.execute(
        select(SS).where(SS.user_id == user_id).order_by(SS.created_at.desc()).limit(50)
    )
    sessions = list(rows.scalars().all())

    return {
        "completed": sum(1 for s in sessions if s.status == "completed"),
        "skipped": sum(1 for s in sessions if s.status == "skipped"),
        "quiz_passed": sum(1 for s in sessions if s.status == "quiz_passed"),
        "quiz_failed": sum(1 for s in sessions if s.status == "quiz_failed"),
        "consecutive_misses": user.consecutive_misses or 0,
        "parent_alerted": bool(user.last_parent_alert_date),
    }


def _ss_dict(s: StudySession) -> dict[str, Any]:
    return {
        "id": s.id,
        "plan_date": s.plan_date,
        "concept_id": s.concept_id,
        "subject": s.subject,
        "activity": s.activity,
        "scheduled_minutes": s.scheduled_minutes,
        "status": s.status,
        "quiz_score": s.quiz_score,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }
