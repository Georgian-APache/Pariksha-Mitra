"""Personalizer agent - adapts learning with follow-up tests."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.llm import gemini_json
from app.agents.prompts import (
    PERSONALIZER_SYSTEM,
    personalizer_user_prompt,
)
from app.agents.quizmaster import generate_questions
from app.agents.state import (
    AgentStep,
    PERSONALIZER_OUTPUT_SCHEMA,
    Question,
    StudentState,
)
from app.config import APIKeys, get_settings
from app.intelligence.concept_dag import ConceptDAG, get_dag

log = logging.getLogger("parikshamitra.personalizer")


def _build_default_requests(
    state: StudentState,
    dag: ConceptDAG,
) -> list[dict[str, Any]]:
    focus = list(state.plan.get("focus_concepts", [])) if isinstance(state.plan, dict) else []
    weak = sorted(
        [cid for cid, m in (state.mastery or {}).items() if cid in dag],
        key=lambda cid: (state.mastery.get(cid, 0.0), cid),
    )
    if not focus:
        focus = weak[:3]
    if not focus and dag:
        catalog = dag.all_concepts()
        if catalog:
            focus = [catalog[0]["id"]]
    score = sum((r.score for r in state.last_quiz_results or []), 0.0)
    n = len(state.last_quiz_results or [])
    avg = (score / n) if n else 1.0
    difficulty = 2 if avg < 0.6 else 3
    requests: list[dict[str, Any]] = []
    for cid in focus[:4]:
        info = dag.info(cid)
        requests.append(
            {
                "concept_id": cid,
                "subject": info.get("subject", ""),
                "difficulty": difficulty,
            }
        )
    return requests


async def _llm_recommendation(
    state: StudentState,
    keys: APIKeys,
    dag: ConceptDAG,
) -> dict[str, Any]:
    s = get_settings()
    prompt = personalizer_user_prompt(
        exam=state.target_exam,
        concept_id=state.last_quiz_concept or "(none)",
        concept_name=dag.info(state.last_quiz_concept).get("name", state.last_quiz_concept)
        if state.last_quiz_concept and state.last_quiz_concept in dag
        else "diagnostic",
        last_results=[r.model_dump() for r in state.last_quiz_results or []],
        weak_prereqs=state.weak_prereqs,
        plan_focus=(state.plan or {}).get("focus_concepts", []),
        mastery=state.mastery,
    )
    return await gemini_json(
        keys=keys,
        prompt=prompt,
        schema=PERSONALIZER_OUTPUT_SCHEMA,
        system=PERSONALIZER_SYSTEM,
        model=s.gemini_reasoning_model,
        temperature=0.4,
    )


async def personalizer_node(state: StudentState, keys: APIKeys) -> StudentState:
    dag = get_dag(state.target_exam)
    request_payload: list[dict[str, Any]] = []
    rationale = "Generated adaptive follow-up test."
    focus_concepts: list[str] = []
    try:
        payload = await _llm_recommendation(state=state, keys=keys, dag=dag)
        focus_concepts = list(payload.get("focus_concepts") or [])
        request_payload = [
            {
                "concept_id": str(item["concept_id"]),
                "subject": str(item.get("subject", "")),
                "difficulty": int(item.get("difficulty", 3)),
            }
            for item in payload.get("test_requests", [])
            if item.get("concept_id")
        ]
        rationale = str(payload.get("rationale", rationale))
    except Exception as exc:  # noqa: BLE001
        log.warning("Personalizer LLM failed, using fallback test requests. err=%s", exc)

    if not request_payload:
        request_payload = _build_default_requests(state, dag)
        rationale = "Fallback adaptive test selected from weak concepts."
        focus_concepts = [r["concept_id"] for r in request_payload]

    questions: list[Question] = []
    try:
        questions = await generate_questions(
            keys=keys,
            requests=request_payload,
            exam=state.target_exam,
            prefer_seed=True,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Personalizer question generation failed: %s", exc)

    state.plan = dict(state.plan or {})
    state.plan["follow_up_test"] = {
        "rationale": rationale,
        "focus_concepts": focus_concepts,
        "test_requests": request_payload,
        "questions": [q.model_dump() for q in questions],
    }
    state.follow_up_test = state.plan["follow_up_test"]
    state.add_trace(
        AgentStep(
            agent="system",
            headline="Personalized follow-up test created",
            detail=rationale,
            payload={
                "focus_concepts": focus_concepts,
                "n_questions": len(questions),
                "test_requests": request_payload,
            },
        )
    )
    return state
