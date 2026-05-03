"""Thin repository helpers used by the routes / agents."""

from __future__ import annotations

from datetime import date as date_t
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentTraceLog, MentalHealthChat, QuizAttempt, QuizSession,
    RagDocument, StudySession, User,
)


# ---------- Users ----------

async def get_user(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def upsert_user(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    display_name: str | None = None,
    target_exam: str | None = None,
    exam_date: str | None = None,
    daily_hours: float | None = None,
    parent_phone: str | None = None,
    parent_name: str | None = None,
) -> User:
    if user_id:
        user = await session.get(User, user_id)
        if user:
            if display_name is not None:
                user.display_name = display_name
            if target_exam is not None:
                user.target_exam = target_exam
            if exam_date is not None:
                user.exam_date = exam_date
            if daily_hours is not None:
                user.daily_hours = daily_hours
            if parent_phone is not None:
                user.parent_phone = parent_phone
            if parent_name is not None:
                user.parent_name = parent_name
            await session.commit()
            await session.refresh(user)
            return user

    user = User(
        display_name=display_name or "Student",
        target_exam=target_exam or "JEE_MAIN",
        exam_date=exam_date,
        daily_hours=daily_hours if daily_hours is not None else 3.0,
        parent_phone=parent_phone,
        parent_name=parent_name,
        mastery={},
        confidence={},
        last_seen={},
        sm2={},
        plan={},
        readiness_history=[],
        mood_history=[],
        mental_health_flags={},
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_state(
    session: AsyncSession,
    user: User,
    *,
    mastery: dict[str, float] | None = None,
    confidence: dict[str, float] | None = None,
    sm2: dict[str, dict[str, Any]] | None = None,
    plan: dict[str, Any] | None = None,
    last_seen: dict[str, str] | None = None,
    readiness_value: float | None = None,
    bump_streak: bool = False,
) -> User:
    if mastery is not None:
        user.mastery = mastery
    if confidence is not None:
        user.confidence = confidence
    if sm2 is not None:
        user.sm2 = sm2
    if plan is not None:
        user.plan = plan
    if last_seen is not None:
        user.last_seen = last_seen

    if readiness_value is not None:
        history = list(user.readiness_history or [])
        history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "readiness": float(readiness_value),
            }
        )
        # Cap at 100 most recent entries
        user.readiness_history = history[-100:]

    if bump_streak:
        today = date_t.today().isoformat()
        if user.last_active_date != today:
            # If yesterday active, increment; else reset to 1
            from datetime import timedelta
            yesterday = (date_t.today() - timedelta(days=1)).isoformat()
            user.streak_days = (user.streak_days or 0) + 1 if user.last_active_date == yesterday else 1
            user.last_active_date = today

    user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return user


# ---------- Quiz sessions / attempts ----------

async def create_quiz_session(
    session: AsyncSession,
    *,
    user_id: str,
    kind: str,
    concept_id: str | None = None,
    questions: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
) -> QuizSession:
    qs = QuizSession(
        user_id=user_id,
        kind=kind,
        concept_id=concept_id,
        questions=questions or [],
        answers=[],
        state=state or {},
    )
    session.add(qs)
    await session.commit()
    await session.refresh(qs)
    return qs


async def get_quiz_session(session: AsyncSession, session_id: str) -> QuizSession | None:
    return await session.get(QuizSession, session_id)


async def append_answer(
    session: AsyncSession,
    qs: QuizSession,
    answer: dict[str, Any],
) -> QuizSession:
    answers = list(qs.answers or [])
    answers.append(answer)
    qs.answers = answers
    await session.commit()
    await session.refresh(qs)
    return qs


async def finalize_quiz(
    session: AsyncSession,
    qs: QuizSession,
    *,
    score: float,
    state_update: dict[str, Any] | None = None,
) -> QuizSession:
    qs.finished_at = datetime.now(timezone.utc)
    qs.score = score
    if state_update:
        qs.state = {**(qs.state or {}), **state_update}
    await session.commit()
    await session.refresh(qs)
    return qs


async def record_attempt(
    session: AsyncSession,
    *,
    user_id: str,
    session_id: str | None,
    concept_id: str,
    difficulty: int,
    correct: bool,
    score: float,
    time_taken_s: int = 0,
) -> QuizAttempt:
    attempt = QuizAttempt(
        user_id=user_id,
        session_id=session_id,
        concept_id=concept_id,
        difficulty=difficulty,
        correct=correct,
        score=score,
        time_taken_s=time_taken_s,
    )
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)
    return attempt


async def recent_attempts(
    session: AsyncSession,
    user_id: str,
    limit: int = 50,
) -> list[QuizAttempt]:
    rows = await session.execute(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(limit)
    )
    return list(rows.scalars().all())


# ---------- Agent traces ----------

async def add_trace(
    session: AsyncSession,
    *,
    user_id: str,
    run_id: str,
    agent: str,
    headline: str,
    detail: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AgentTraceLog:
    log = AgentTraceLog(
        user_id=user_id,
        run_id=run_id,
        agent=agent,
        headline=headline,
        detail=detail,
        payload=payload or {},
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def list_trace(session: AsyncSession, run_id: str) -> list[AgentTraceLog]:
    rows = await session.execute(
        select(AgentTraceLog).where(AgentTraceLog.run_id == run_id).order_by(AgentTraceLog.created_at)
    )
    return list(rows.scalars().all())


# ---------- RAG documents ----------

async def record_rag_doc(
    session: AsyncSession,
    *,
    user_id: str,
    title: str,
    collection: str,
    chunk_count: int,
    page_count: int,
) -> RagDocument:
    doc = RagDocument(
        user_id=user_id,
        title=title,
        collection=collection,
        chunk_count=chunk_count,
        page_count=page_count,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def list_rag_docs(session: AsyncSession, user_id: str) -> list[RagDocument]:
    rows = await session.execute(
        select(RagDocument).where(RagDocument.user_id == user_id).order_by(RagDocument.created_at.desc())
    )
    return list(rows.scalars().all())


# ---------- Mental health ----------

async def add_mood_entry(
    session: AsyncSession,
    user: User,
    *,
    score: int,
    tags: list[str],
    note: str = "",
) -> User:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "tags": tags,
        "note": note,
    }
    history = list(user.mood_history or [])
    history.append(entry)
    user.mood_history = history[-90:]  # keep 90 entries
    # running EMA for stress_level
    user.stress_level = round(0.8 * (user.stress_level or 5.0) + 0.2 * (10 - score + 1), 2)
    await session.commit()
    await session.refresh(user)
    return user


async def add_chat_message(
    session: AsyncSession,
    *,
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    mood_score: int | None = None,
    mood_tags: list[str] | None = None,
) -> MentalHealthChat:
    msg = MentalHealthChat(
        user_id=user_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        mood_score=mood_score,
        mood_tags=mood_tags or [],
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def get_conversation(
    session: AsyncSession, user_id: str, conversation_id: str, limit: int = 20
) -> list[MentalHealthChat]:
    rows = await session.execute(
        select(MentalHealthChat)
        .where(MentalHealthChat.user_id == user_id, MentalHealthChat.conversation_id == conversation_id)
        .order_by(MentalHealthChat.created_at)
        .limit(limit)
    )
    return list(rows.scalars().all())


# ---------- Study sessions ----------

async def get_study_sessions_for_date(
    session: AsyncSession, user_id: str, plan_date: str
) -> list[StudySession]:
    rows = await session.execute(
        select(StudySession)
        .where(StudySession.user_id == user_id, StudySession.plan_date == plan_date)
        .order_by(StudySession.created_at)
    )
    return list(rows.scalars().all())


async def create_study_session(
    session: AsyncSession,
    *,
    user_id: str,
    plan_date: str,
    concept_id: str,
    subject: str,
    activity: str,
    scheduled_minutes: int,
) -> StudySession:
    ss = StudySession(
        user_id=user_id,
        plan_date=plan_date,
        concept_id=concept_id,
        subject=subject,
        activity=activity,
        scheduled_minutes=scheduled_minutes,
    )
    session.add(ss)
    await session.commit()
    await session.refresh(ss)
    return ss


async def get_study_session(session: AsyncSession, session_id: str) -> StudySession | None:
    return await session.get(StudySession, session_id)


async def get_recent_missed_topics(
    session: AsyncSession, user_id: str, limit: int = 5
) -> list[str]:
    rows = await session.execute(
        select(StudySession)
        .where(StudySession.user_id == user_id, StudySession.status == "skipped")
        .order_by(StudySession.created_at.desc())
        .limit(limit)
    )
    return [s.concept_id for s in rows.scalars().all()]
