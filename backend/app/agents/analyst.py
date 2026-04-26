"""Analyst agent - readiness recompute + prerequisite-gap diagnosis."""

from __future__ import annotations

import logging
import statistics

from app.agents.llm import gemini_json
from app.agents.prompts import ANALYST_SYSTEM, analyst_user_prompt
from app.agents.state import (
    ANALYST_OUTPUT_SCHEMA,
    AgentStep,
    StudentState,
)
from app.config import APIKeys, get_settings
from app.intelligence.concept_dag import get_dag, weak_prerequisites
from app.intelligence.readiness import compute_readiness
from app.intelligence.sm2 import SM2Card

log = logging.getLogger("parikshamitra.analyst")


def _quiz_summary(state: StudentState) -> dict:
    results = state.last_quiz_results or state.diagnostic_results
    if not results:
        return {"avg_score": 1.0, "concept_id": state.last_quiz_concept, "n": 0}
    avg = statistics.fmean([r.score for r in results])
    return {
        "avg_score": avg,
        "concept_id": state.last_quiz_concept,
        "n": len(results),
        "items": [r.model_dump() for r in results],
    }


async def _llm_analysis(
    *,
    state: StudentState,
    keys: APIKeys,
    concept_id: str,
    summary: dict,
    prereqs: list[str],
) -> dict:
    s = get_settings()
    dag = get_dag(state.target_exam)
    name = dag.info(concept_id).get("name", concept_id) if concept_id else "(diagnostic)"
    prompt = analyst_user_prompt(
        concept_id=concept_id or "diagnostic",
        concept_name=name,
        last_results=summary.get("items", []),
        prereqs=prereqs,
        mastery=state.mastery,
    )
    return await gemini_json(
        keys=keys,
        prompt=prompt,
        schema=ANALYST_OUTPUT_SCHEMA,
        system=ANALYST_SYSTEM,
        model=s.gemini_reasoning_model,
        temperature=0.3,
    )


async def analyst_node(state: StudentState, keys: APIKeys) -> StudentState:
    dag = get_dag(state.target_exam)
    summary = _quiz_summary(state)
    concept_id = summary.get("concept_id") or ""
    prereqs = dag.prereqs_of(concept_id) if concept_id else []
    weak_pre = weak_prerequisites(dag, concept_id, state.mastery, threshold=0.6) if concept_id else []

    insight: str
    should_replan = False
    reason = ""
    try:
        ai = await _llm_analysis(state=state, keys=keys, concept_id=concept_id, summary=summary, prereqs=prereqs)
        insight = ai.get("insight", "")
        ai_weak = [w for w in ai.get("weak_prereqs", []) if w in weak_pre or w in prereqs]
        weak_pre = list(dict.fromkeys((ai_weak or []) + weak_pre))
        should_replan = bool(ai.get("should_replan", False))
        reason = ai.get("reason", "")
    except Exception as exc:  # noqa: BLE001
        log.warning("Analyst LLM failed, using heuristic. err=%s", exc)
        avg = summary.get("avg_score", 1.0)
        insight = f"Average score on {concept_id or 'diagnostic'} was {avg:.2f}."
        if concept_id:
            should_replan = avg < 0.5 or bool(weak_pre)
            reason = "Low score" if avg < 0.5 else ("Weak prerequisite" if weak_pre else "")

    # Recompute readiness
    cards = list((state.sm2 or {}).values())
    readiness = compute_readiness(
        dag=dag,
        mastery=state.mastery,
        cards=[SM2Card.model_validate(c) if isinstance(c, dict) else c for c in cards],
        history=state.readiness_history,
    )
    state.readiness = readiness
    state.weak_prereqs = weak_pre

    state.add_trace(
        AgentStep(
            agent="analyst",
            headline=f"Readiness {readiness['readiness']:.0f}/100"
            + (f" - {len(weak_pre)} weak prereq(s)" if weak_pre else ""),
            detail=insight,
            payload={
                "readiness": readiness,
                "weak_prereqs": weak_pre,
                "should_replan": should_replan,
                "reason": reason,
            },
        )
    )
    # Stash decision for the orchestrator's conditional edge
    state.intent = state.intent  # keep
    state.readiness_history = list(state.readiness_history) + [
        {"timestamp": readiness["computed_at"], "readiness": readiness["readiness"]}
    ]
    state.readiness_history = state.readiness_history[-100:]
    state.nudge = state.nudge  # leave for companion
    state.confidence = state.confidence  # leave intact
    state.sm2 = state.sm2  # leave intact

    state.diagnostic_results = state.diagnostic_results
    state.last_quiz_results = state.last_quiz_results
    state.last_quiz_concept = state.last_quiz_concept
    state.plan = state.plan

    state.__dict__["_should_replan"] = should_replan  # informal flag for graph edge
    return state
