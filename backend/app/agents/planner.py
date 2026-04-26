"""Planner agent - generates the 7-day study plan."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import date, timedelta

from app.agents.llm import gemini_json
from app.agents.prompts import PLANNER_SYSTEM, planner_user_prompt
from app.agents.state import AgentStep, PlanDay, PlanDayBlock, StudentState, WeeklyPlan
from app.agents.state import PLANNER_OUTPUT_SCHEMA
from app.config import APIKeys, get_settings
from app.intelligence.concept_dag import get_dag

log = logging.getLogger("parikshamitra.planner")


async def _llm_plan(state: StudentState, keys: APIKeys) -> dict:
    dag = get_dag(state.target_exam)
    catalogue = [
        {"id": c["id"], "name": c["name"], "subject": c["subject"], "weight": c["weight"]}
        for c in dag.all_concepts()
    ]
    flagged = [cid for cid, m in (state.mastery or {}).items() if m < 0.5]
    if not flagged:
        # First-run heuristic: lowest-weight concepts get the bias
        flagged = sorted(catalogue, key=lambda c: c["weight"], reverse=True)[:5]
        flagged = [c["id"] for c in flagged]
    prompt = planner_user_prompt(
        exam=state.target_exam,
        exam_date=state.exam_date,
        daily_hours=state.daily_hours,
        today_iso=date.today().isoformat(),
        catalogue=catalogue,
        mastery=state.mastery or {},
        flagged=flagged,
    )
    s = get_settings()
    return await gemini_json(
        keys=keys,
        prompt=prompt,
        schema=PLANNER_OUTPUT_SCHEMA,
        system=PLANNER_SYSTEM,
        model=s.gemini_reasoning_model,
        temperature=0.5,
    )


def _heuristic_plan(state: StudentState) -> dict:
    """Deterministic fallback if the LLM is unavailable - keeps the demo robust."""

    dag = get_dag(state.target_exam)
    catalogue = dag.all_concepts()
    daily_minutes = int(state.daily_hours * 60)
    mastery = state.mastery or {}
    weakest = sorted(
        catalogue,
        key=lambda c: (mastery.get(c["id"], 0.0), -c["weight"]),
    )[:14]
    rng = random.Random(7)
    days: list[dict] = []
    for i in range(7):
        d = date.today() + timedelta(days=i)
        focus = weakest[(i * 2) % len(weakest):(i * 2) % len(weakest) + 2] or weakest[:2]
        # Ensure we have 3-4 blocks
        blocks = []
        remaining = daily_minutes
        for j, c in enumerate(focus):
            mins = max(20, remaining // (len(focus) - j) if len(focus) - j else 30)
            activity = ["learn", "quiz", "drill", "review"][(i + j) % 4]
            blocks.append(
                {
                    "subject": c["subject"],
                    "concept_id": c["id"],
                    "minutes": mins,
                    "activity": activity,
                    "note": "Auto-generated fallback block",
                }
            )
            remaining -= mins
        # Filler review slot if leftover > 15
        if remaining > 15:
            extra = rng.choice(catalogue)
            blocks.append(
                {
                    "subject": extra["subject"],
                    "concept_id": extra["id"],
                    "minutes": remaining,
                    "activity": "review",
                    "note": "Spaced revision",
                }
            )
        days.append(
            {
                "date": d.isoformat(),
                "total_minutes": sum(b["minutes"] for b in blocks),
                "blocks": blocks,
            }
        )
    return {
        "rationale": "Fallback plan biased toward weakest concepts and high-weight subjects.",
        "focus_concepts": [c["id"] for c in weakest[:6]],
        "days": days,
    }


async def planner_node(state: StudentState, keys: APIKeys) -> StudentState:
    raw: dict
    error: str | None = None
    try:
        raw = await _llm_plan(state, keys)
    except Exception as exc:  # noqa: BLE001
        log.warning("Planner LLM failed, using heuristic. err=%s", exc)
        raw = _heuristic_plan(state)
        error = str(exc)

    # Normalise to WeeklyPlan
    days = [
        PlanDay(
            date=d["date"],
            total_minutes=int(d.get("total_minutes") or sum(b.get("minutes", 0) for b in d.get("blocks", []))),
            blocks=[PlanDayBlock(**b) for b in d.get("blocks", [])],
        )
        for d in raw.get("days", [])
    ]
    plan = WeeklyPlan(
        rationale=raw.get("rationale", ""),
        focus_concepts=list(raw.get("focus_concepts", [])),
        days=days,
    )
    state.plan = plan.model_dump()
    state.add_trace(
        AgentStep(
            agent="planner",
            headline=("Replanned week" if state.plan and state.intent != "diagnostic" else "First weekly plan"),
            detail=plan.rationale[:240],
            payload={
                "focus_concepts": plan.focus_concepts,
                "days": len(plan.days),
                "fallback": bool(error),
            },
        )
    )
    return state


# Sync helper for unit tests
def heuristic_plan_sync(state: StudentState) -> dict:
    return asyncio.get_event_loop().run_until_complete(  # pragma: no cover
        asyncio.coroutine(lambda: _heuristic_plan(state))()
    )
