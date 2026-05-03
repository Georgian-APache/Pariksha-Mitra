"""Planner agent - generates the 7-day study plan."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import date, timedelta
from typing import Literal, cast

from pydantic import ValidationError

from app.agents.llm import gemini_json
from app.agents.prompts import PLANNER_SYSTEM, planner_user_prompt
from app.agents.state import AgentStep, PlanDay, PlanDayBlock, StudentState, WeeklyPlan
from app.agents.state import PLANNER_OUTPUT_SCHEMA
from app.config import APIKeys, get_settings
from app.intelligence.concept_dag import get_dag

log = logging.getLogger("parikshamitra.planner")

_ALLOWED_ACTIVITY = frozenset({"learn", "quiz", "review", "drill"})


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
    if not weakest:
        weakest = catalogue[: max(1, min(14, len(catalogue)))] if catalogue else [
            {"id": "general.review", "subject": "General", "name": "Review", "weight": 1.0},
        ]
    rng = random.Random(7)
    days: list[dict] = []
    for i in range(7):
        d = date.today() + timedelta(days=i)
        span = len(weakest)
        focus = weakest[(i * 2) % span : (i * 2) % span + 2] or weakest[: min(2, span)]
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
        if remaining > 15 and catalogue:
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


def _weekly_plan_from_raw(raw: dict) -> WeeklyPlan:
    """Turn planner JSON into ``WeeklyPlan``, sanitizing common LLM/schema drift."""

    days_out: list[PlanDay] = []
    raw_days = raw.get("days") if isinstance(raw.get("days"), list) else []
    for d in raw_days:
        if not isinstance(d, dict):
            continue
        date_str = str(d.get("date") or date.today().isoformat())
        blocks_in = d.get("blocks") if isinstance(d.get("blocks"), list) else []
        blocks_out: list[PlanDayBlock] = []
        for b in blocks_in:
            if not isinstance(b, dict):
                continue
            act = str(b.get("activity", "learn")).lower().strip()
            if act not in _ALLOWED_ACTIVITY:
                act = "learn"
            try:
                mins = int(float(b.get("minutes", 30)))
            except (TypeError, ValueError):
                mins = 30
            mins = max(5, mins)
            blocks_out.append(
                PlanDayBlock(
                    subject=str(b.get("subject", "Study")),
                    concept_id=str(b.get("concept_id", "general")),
                    minutes=mins,
                    activity=cast(Literal["learn", "quiz", "review", "drill"], act),
                    note=str(b.get("note", "")),
                )
            )
        if not blocks_out:
            continue
        tm_raw = d.get("total_minutes")
        try:
            total_m = int(tm_raw) if tm_raw is not None else sum(x.minutes for x in blocks_out)
        except (TypeError, ValueError):
            total_m = sum(x.minutes for x in blocks_out)
        days_out.append(
            PlanDay(date=date_str, total_minutes=max(total_m, sum(x.minutes for x in blocks_out)), blocks=blocks_out)
        )
    if not days_out:
        raise ValueError("no valid plan days after sanitization")
    return WeeklyPlan(
        rationale=str(raw.get("rationale", "")),
        focus_concepts=[str(x) for x in (raw.get("focus_concepts") or [])],
        days=days_out,
    )


async def planner_node(state: StudentState, keys: APIKeys) -> StudentState:
    raw: dict
    error: str | None = None
    try:
        raw = await _llm_plan(state, keys)
    except Exception as exc:  # noqa: BLE001
        log.warning("Planner LLM failed, using heuristic. err=%s", exc)
        raw = _heuristic_plan(state)
        error = str(exc)

    plan: WeeklyPlan
    try:
        plan = _weekly_plan_from_raw(raw)
    except (ValidationError, ValueError, TypeError, KeyError) as exc:
        log.warning("Planner output invalid after sanitization, using heuristic. err=%s", exc)
        raw = _heuristic_plan(state)
        error = str(exc)
        plan = _weekly_plan_from_raw(raw)
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
