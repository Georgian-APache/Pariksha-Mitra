"""Companion agent - bilingual (en + hi) motivation + plan-change explanations."""

from __future__ import annotations

import logging

from app.agents.llm import gemini_json
from app.agents.prompts import COMPANION_SYSTEM, companion_user_prompt
from app.agents.state import COMPANION_OUTPUT_SCHEMA, AgentStep, StudentState
from app.config import APIKeys, get_settings

log = logging.getLogger("parikshamitra.companion")


def _heuristic_nudge(state: StudentState) -> dict:
    weak = ", ".join(state.weak_prereqs[:2]) or state.last_quiz_concept or "your weak topics"
    en = (
        f"I shifted more time to {weak} for the next 3 days - your last quiz showed "
        f"a gap. A 5-question warm-up will get you back on track."
    )
    hi = (
        f"मैंने अगले 3 दिनों के लिए {weak} पर अधिक समय दिया है - आपकी पिछली क्विज़ में "
        f"कमज़ोरी दिखी। 5-प्रश्न का वार्म-अप तुरंत मदद करेगा।"
    )
    return {"en": en, "hi": hi, "tone": "encouraging"}


async def companion_node(state: StudentState, keys: APIKeys) -> StudentState:
    nudge_kind = "replan" if state.weak_prereqs else "checkin"
    context = {
        "concept": state.last_quiz_concept,
        "weak_prereqs": state.weak_prereqs,
        "readiness": state.readiness.get("readiness") if state.readiness else None,
        "focus_concepts": (state.plan or {}).get("focus_concepts", [])[:5],
    }
    payload: dict
    try:
        s = get_settings()
        payload = await gemini_json(
            keys=keys,
            prompt=companion_user_prompt(nudge_kind=nudge_kind, context=context),
            schema=COMPANION_OUTPUT_SCHEMA,
            system=COMPANION_SYSTEM,
            model=s.gemini_default_model,
            temperature=0.7,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Companion LLM failed, using heuristic. err=%s", exc)
        payload = _heuristic_nudge(state)
    state.nudge = {"en": payload.get("en", ""), "hi": payload.get("hi", "")}
    state.add_trace(
        AgentStep(
            agent="companion",
            headline="Bilingual nudge ready",
            detail=payload.get("en", ""),
            payload={"hi": payload.get("hi", ""), "tone": payload.get("tone", "encouraging"), "kind": nudge_kind},
        )
    )
    return state
