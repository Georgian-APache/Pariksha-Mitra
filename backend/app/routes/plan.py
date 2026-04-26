"""Plan + dashboard endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_post_quiz
from app.agents.state import StudentState
from app.config import APIKeys, api_keys
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag
from app.intelligence.predictor import simulate_rank
from app.intelligence.readiness import compute_readiness
from app.intelligence.sm2 import SM2Card

router = APIRouter(prefix="/plan", tags=["plan"])


class DashboardResponse(BaseModel):
    user_id: str
    target_exam: str
    exam_date: str | None
    daily_hours: float
    streak_days: int
    plan: dict[str, Any]
    readiness: dict[str, Any]
    readiness_history: list[dict[str, Any]]
    mastery: dict[str, float]
    subject_mastery: dict[str, float]
    rank_prediction: dict[str, Any] | None
    nudge: dict[str, str]


@router.get("/{user_id}/dashboard", response_model=DashboardResponse)
async def dashboard(user_id: str, session: AsyncSession = Depends(get_session)) -> DashboardResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    dag = get_dag(user.target_exam)
    cards = [SM2Card.model_validate(c) for c in (user.sm2 or {}).values()]
    readiness = compute_readiness(
        dag=dag,
        mastery=user.mastery or {},
        cards=cards,
        history=list(user.readiness_history or []),
    )

    # Per-subject mastery (weighted)
    subj_acc: dict[str, list[tuple[float, float]]] = {}
    for n, d in dag.graph.nodes(data=True):
        subj = d.get("subject", "Other")
        w = float(d.get("weight", 0.0)) or 0.01
        m = float((user.mastery or {}).get(n, 0.0))
        subj_acc.setdefault(subj, []).append((w, m))
    subject_mastery = {
        subj: round(sum(w * m for w, m in items) / max(sum(w for w, _ in items), 1e-9), 3)
        for subj, items in subj_acc.items()
    }

    # Rank prediction (only meaningful if we have a date)
    rank_prediction: dict[str, Any] | None = None
    if user.exam_date:
        try:
            rank_prediction = simulate_rank(
                current_readiness=readiness["readiness"],
                exam_date=user.exam_date,
                exam=user.target_exam,
                history=list(user.readiness_history or []),
            ).model_dump()
        except Exception:  # noqa: BLE001
            rank_prediction = None

    return DashboardResponse(
        user_id=user.id,
        target_exam=user.target_exam,
        exam_date=user.exam_date,
        daily_hours=user.daily_hours,
        streak_days=user.streak_days or 0,
        plan=user.plan or {},
        readiness=readiness,
        readiness_history=list(user.readiness_history or []),
        mastery=user.mastery or {},
        subject_mastery=subject_mastery,
        rank_prediction=rank_prediction,
        nudge={},
    )


class ReplanRequest(BaseModel):
    user_id: str


class ReplanResponse(BaseModel):
    user_id: str
    run_id: str
    plan: dict[str, Any]
    readiness: dict[str, Any]
    nudge: dict[str, str]


@router.post("/replan", response_model=ReplanResponse)
async def replan(
    body: ReplanRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> ReplanResponse:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")
    state = StudentState(
        user_id=user.id,
        target_exam=user.target_exam,
        exam_date=user.exam_date,
        daily_hours=user.daily_hours,
        mastery=dict(user.mastery or {}),
        confidence=dict(user.confidence or {}),
        sm2=dict(user.sm2 or {}),
        plan=dict(user.plan or {}),
        readiness_history=list(user.readiness_history or []),
        intent="manual_replan",
    )
    # Force a replan regardless of analyst's recommendation
    state.__dict__["_should_replan"] = True
    out_state, run_id = await run_post_quiz(state, keys)
    await repo.update_user_state(
        session,
        user,
        mastery=out_state.mastery,
        plan=out_state.plan,
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
    return ReplanResponse(
        user_id=user.id,
        run_id=run_id,
        plan=out_state.plan or {},
        readiness=out_state.readiness or {},
        nudge=out_state.nudge or {},
    )
