"""Adaptive quiz runner.

POST /quiz/start  -> create a session, return the FIRST question
POST /quiz/answer -> grade, update mastery + SM-2 + CAT, optionally fetch next question
POST /quiz/finish -> run the full agent graph (Analyst -> [Planner] -> Companion),
                     return run_id for the SSE feed.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_post_quiz
from app.agents.quizmaster import generate_questions, grade_answer
from app.agents.state import GradedAnswer, Question, StudentState
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.cat_lite import CATState, initial_difficulty, next_difficulty, update_history
from app.intelligence.concept_dag import get_dag
from app.intelligence.sm2 import SM2Card, sm2_update

router = APIRouter(prefix="/quiz", tags=["quiz"])


class StartRequest(BaseModel):
    user_id: str
    concept_id: str | None = None
    kind: Literal["adaptive", "drill"] = "adaptive"
    n_questions: int = Field(default=8, ge=1, le=20)


class StartResponse(BaseModel):
    session_id: str
    question: Question
    progress: dict[str, int]
    cat: dict[str, Any]


def _build_cat(user_mastery: dict[str, float], concept_id: str) -> CATState:
    m = user_mastery.get(concept_id, 0.4)
    return CATState(level=initial_difficulty(m))


@router.post("/start", response_model=StartResponse)
async def start_quiz(
    body: StartRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> StartResponse:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")
    dag = get_dag(user.target_exam)

    # Choose target concept: explicit > weakest in user's plan focus > weakest overall
    concept_id = body.concept_id
    if not concept_id:
        focus = (user.plan or {}).get("focus_concepts") or []
        if focus:
            concept_id = focus[0]
    if not concept_id:
        # Pick weakest mastery concept that exists in the DAG
        candidates = [
            (cid, m) for cid, m in (user.mastery or {}).items() if cid in dag
        ] or [(c["id"], 0.5) for c in dag.all_concepts()]
        candidates.sort(key=lambda kv: kv[1])
        concept_id = candidates[0][0]

    if concept_id not in dag:
        raise HTTPException(400, f"unknown concept: {concept_id}")

    cat = _build_cat(user.mastery or {}, concept_id)
    info = dag.info(concept_id)
    questions = await generate_questions(
        keys=keys,
        requests=[
            {
                "concept_id": concept_id,
                "subject": info.get("subject", ""),
                "difficulty": cat.level,
            }
        ],
        exam=user.target_exam,
        prefer_seed=True,
    )
    qs = await repo.create_quiz_session(
        session,
        user_id=user.id,
        kind=body.kind,
        concept_id=concept_id,
        questions=[q.model_dump() for q in questions],
        state={
            "n_questions": body.n_questions,
            "cat": cat.__dict__,
            "asked": 1,
            "answered": 0,
        },
    )
    return StartResponse(
        session_id=qs.id,
        question=questions[0],
        progress={"asked": 1, "answered": 0, "total": body.n_questions},
        cat=cat.__dict__,
    )


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    chosen_index: int
    time_taken_s: int = 0


class AnswerResponse(BaseModel):
    grade: GradedAnswer
    next_question: Question | None
    progress: dict[str, int]
    cat: dict[str, Any]
    session_complete: bool


@router.post("/answer", response_model=AnswerResponse)
async def answer_quiz(
    body: AnswerRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> AnswerResponse:
    qs = await repo.get_quiz_session(session, body.session_id)
    if not qs:
        raise HTTPException(404, "session not found")
    user = await repo.get_user(session, qs.user_id)
    if not user:
        raise HTTPException(404, "user not found")
    dag = get_dag(user.target_exam)

    questions = [Question.model_validate(q) for q in (qs.questions or [])]
    target_q: Question | None = next((q for q in questions if q.id == body.question_id), None)
    if not target_q:
        raise HTTPException(400, "question not in session")

    grade = await grade_answer(keys=keys, question=target_q, chosen_index=body.chosen_index)

    # Update CAT
    cat_dict = (qs.state or {}).get("cat", {})
    cat = CATState(**{k: v for k, v in cat_dict.items() if k in CATState.__dataclass_fields__})
    cat = update_history(cat, correct=grade.correct or grade.score >= 0.5)

    # Update mastery (EMA toward score)
    cid = target_q.concept_id
    new_mastery = dict(user.mastery or {})
    prior = new_mastery.get(cid, 0.5)
    new_mastery[cid] = round(0.7 * prior + 0.3 * grade.score, 3)

    # Update SM-2
    sm2_state = dict(user.sm2 or {})
    existing = sm2_state.get(cid)
    card = SM2Card.model_validate(existing) if existing else SM2Card(concept_id=cid)
    card = sm2_update(card, grade.score)
    sm2_state[cid] = card.model_dump()

    await repo.record_attempt(
        session,
        user_id=user.id,
        session_id=qs.id,
        concept_id=cid,
        difficulty=target_q.difficulty,
        correct=grade.correct,
        score=grade.score,
        time_taken_s=body.time_taken_s,
    )

    answers = list(qs.answers or [])
    answers.append(grade.model_dump())
    qs.answers = answers
    qs.state = {**(qs.state or {}), "cat": cat.__dict__, "answered": len(answers)}
    await session.commit()

    await repo.update_user_state(
        session, user, mastery=new_mastery, sm2=sm2_state, bump_streak=True
    )

    n_total = int((qs.state or {}).get("n_questions", 8))
    asked = int((qs.state or {}).get("asked", 1))
    answered = len(answers)
    complete = answered >= n_total

    next_q: Question | None = None
    if not complete:
        # Generate the next question at the new CAT level
        info = dag.info(cid)
        nq = await generate_questions(
            keys=keys,
            requests=[
                {
                    "concept_id": cid,
                    "subject": info.get("subject", ""),
                    "difficulty": next_difficulty(cat),
                }
            ],
            exam=user.target_exam,
            prefer_seed=True,
        )
        next_q = nq[0] if nq else None
        if next_q:
            questions.append(next_q)
            qs.questions = [q.model_dump() for q in questions]
            qs.state = {**(qs.state or {}), "asked": asked + 1}
            await session.commit()

    return AnswerResponse(
        grade=grade,
        next_question=next_q,
        progress={"asked": asked + (1 if next_q else 0), "answered": answered, "total": n_total},
        cat=cat.__dict__,
        session_complete=complete,
    )


class FinishRequest(BaseModel):
    session_id: str


class FinishResponse(BaseModel):
    user_id: str
    run_id: str
    summary: dict[str, Any]
    plan: dict[str, Any]
    readiness: dict[str, Any]
    nudge: dict[str, str]
    weak_prereqs: list[str]
    replanned: bool
    follow_up_test: dict[str, Any] | None = None


@router.post("/finish", response_model=FinishResponse)
async def finish_quiz(
    body: FinishRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> FinishResponse:
    qs = await repo.get_quiz_session(session, body.session_id)
    if not qs:
        raise HTTPException(404, "session not found")
    user = await repo.get_user(session, qs.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    # Score the session: average of partial-credit answers
    answers = qs.answers or []
    avg_score = (sum(a.get("score", 0.0) for a in answers) / len(answers)) if answers else 0.0
    await repo.finalize_quiz(session, qs, score=round(avg_score, 3))

    # Build StudentState and run the full agent graph
    graded = [GradedAnswer.model_validate(a) for a in answers]
    plan_pre = dict(user.plan or {})
    state = StudentState(
        user_id=user.id,
        target_exam=user.target_exam,
        exam_date=user.exam_date,
        daily_hours=user.daily_hours,
        mastery=dict(user.mastery or {}),
        confidence=dict(user.confidence or {}),
        sm2=dict(user.sm2 or {}),
        plan=plan_pre,
        readiness_history=list(user.readiness_history or []),
        last_quiz_results=graded,
        last_quiz_concept=qs.concept_id,
        intent="quiz_finished",
    )
    out_state, run_id = await run_post_quiz(state, keys)
    replanned = bool(getattr(out_state, "_should_replan", False)) or (
        out_state.plan.get("generated_at") and out_state.plan != plan_pre
    )

    await repo.update_user_state(
        session,
        user,
        mastery=out_state.mastery,
        plan=out_state.plan,
        sm2=out_state.sm2,
        readiness_value=out_state.readiness.get("readiness") if out_state.readiness else None,
    )
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

    return FinishResponse(
        user_id=user.id,
        run_id=run_id,
        summary={
            "session_id": qs.id,
            "n_questions": len(answers),
            "avg_score": round(avg_score, 3),
            "concept_id": qs.concept_id,
        },
        plan=out_state.plan or {},
        readiness=out_state.readiness or {},
        nudge=out_state.nudge or {},
        weak_prereqs=out_state.weak_prereqs,
        replanned=bool(replanned),
        follow_up_test=out_state.follow_up_test or None,
    )
