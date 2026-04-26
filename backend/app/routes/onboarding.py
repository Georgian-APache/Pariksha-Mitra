"""Onboarding diagnostic flow.

POST /onboard/start - returns 15 calibration MCQs spanning the chosen exam's subjects.
POST /onboard/submit - records answers, runs Analyst+Planner+Companion graph, persists
                       and returns the first plan, readiness, and a run_id for the SSE feed.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_diagnostic
from app.agents.quizmaster import generate_questions
from app.agents.state import GradedAnswer, Question, StudentState
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag
from app.intelligence.sm2 import sm2_update, SM2Card

router = APIRouter(prefix="/onboard", tags=["onboarding"])


class StartRequest(BaseModel):
    user_id: str | None = None
    display_name: str = "Student"
    target_exam: str = "JEE_MAIN"
    exam_date: str | None = None
    daily_hours: float = Field(default=3.0, ge=0.5, le=16)


class StartResponse(BaseModel):
    user_id: str
    questions: list[Question]


class SubmitAnswer(BaseModel):
    question_id: str
    chosen_index: int


class SubmitRequest(BaseModel):
    user_id: str
    questions: list[Question]
    answers: list[SubmitAnswer]


class SubmitResponse(BaseModel):
    user_id: str
    run_id: str
    readiness: dict[str, Any]
    plan: dict[str, Any]
    nudge: dict[str, str]
    mastery: dict[str, float]
    trace_count: int


def _pick_diagnostic_concepts(exam: str, n: int) -> list[dict]:
    dag = get_dag(exam)
    catalogue = dag.all_concepts()
    rng = random.Random(42)
    by_subject: dict[str, list[dict]] = {}
    for c in catalogue:
        by_subject.setdefault(c["subject"], []).append(c)

    out: list[dict] = []
    subjects = list(by_subject.keys())
    rng.shuffle(subjects)
    while len(out) < n:
        for subj in subjects:
            if len(out) >= n:
                break
            pool = [c for c in by_subject[subj] if c not in out]
            if not pool:
                continue
            choice = rng.choice(pool)
            out.append(choice)
    return out


@router.post("/start", response_model=StartResponse)
async def start_diagnostic(
    body: StartRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> StartResponse:
    user = await repo.upsert_user(
        session,
        user_id=body.user_id,
        display_name=body.display_name,
        target_exam=body.target_exam,
        exam_date=body.exam_date,
        daily_hours=body.daily_hours,
    )
    s = get_settings()
    concepts = _pick_diagnostic_concepts(body.target_exam, s.diagnostic_question_count)
    requests = [
        {"concept_id": c["id"], "subject": c["subject"], "difficulty": 2 if i % 2 == 0 else 3}
        for i, c in enumerate(concepts)
    ]
    questions = await generate_questions(
        keys=keys, requests=requests, exam=body.target_exam, prefer_seed=True,
    )
    if len(questions) < s.diagnostic_question_count:
        # Top up with stubs / repeated seeds if anything is missing
        from app.agents.quizmaster import _stub_question  # noqa: WPS437
        while len(questions) < s.diagnostic_question_count:
            c = concepts[len(questions) % len(concepts)]
            questions.append(_stub_question(c["id"], c["subject"], 2))
    return StartResponse(user_id=user.id, questions=questions[: s.diagnostic_question_count])


@router.post("/submit", response_model=SubmitResponse)
async def submit_diagnostic(
    body: SubmitRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> SubmitResponse:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    qs_by_id: dict[str, Question] = {q.id: q for q in body.questions}

    # Grade locally (deterministic for diagnostic - just exact match -> 1.0 / 0.0)
    graded: list[GradedAnswer] = []
    mastery_updates: dict[str, list[float]] = {}
    for ans in body.answers:
        q = qs_by_id.get(ans.question_id)
        if not q:
            continue
        correct = ans.chosen_index == q.correct_index
        score = 1.0 if correct else 0.0
        graded.append(
            GradedAnswer(
                question_id=q.id,
                chosen_index=ans.chosen_index,
                correct=correct,
                score=score,
                rationale=q.explanation,
            )
        )
        mastery_updates.setdefault(q.concept_id, []).append(score)

    # Update mastery: blend prior with diagnostic average (low-confidence prior)
    new_mastery = dict(user.mastery or {})
    sm2_state = dict(user.sm2 or {})
    for cid, scores in mastery_updates.items():
        avg = sum(scores) / len(scores)
        prior = new_mastery.get(cid, 0.5)
        new_mastery[cid] = round(0.3 * prior + 0.7 * avg, 3)
        # Seed an SM-2 card for that concept
        existing = sm2_state.get(cid)
        card = SM2Card.model_validate(existing) if existing else SM2Card(concept_id=cid)
        card = sm2_update(card, avg)
        sm2_state[cid] = card.model_dump()

    # Persist intermediate state (the agents read it)
    await repo.update_user_state(
        session,
        user,
        mastery=new_mastery,
        sm2=sm2_state,
        bump_streak=True,
    )

    # Build StudentState and run the diagnostic graph
    state = StudentState(
        user_id=user.id,
        target_exam=user.target_exam,
        exam_date=user.exam_date,
        daily_hours=user.daily_hours,
        mastery=new_mastery,
        confidence=dict(user.confidence or {}),
        sm2=sm2_state,
        plan=dict(user.plan or {}),
        readiness_history=list(user.readiness_history or []),
        diagnostic_results=graded,
        last_quiz_concept=None,
        intent="diagnostic",
    )
    out_state, run_id = await run_diagnostic(state, keys)

    # Persist agent outputs
    await repo.update_user_state(
        session,
        user,
        mastery=out_state.mastery,
        plan=out_state.plan,
        readiness_value=out_state.readiness.get("readiness") if out_state.readiness else None,
    )

    # Persist trace
    for step in out_state.trace:
        await repo.add_trace(
            session,
            user_id=user.id,
            run_id=run_id,
            agent=step.agent,
            headline=step.headline,
            detail=step.detail,
            payload=step.payload,
        )

    return SubmitResponse(
        user_id=user.id,
        run_id=run_id,
        readiness=out_state.readiness or {},
        plan=out_state.plan or {},
        nudge=out_state.nudge or {},
        mastery=out_state.mastery,
        trace_count=len(out_state.trace),
    )
