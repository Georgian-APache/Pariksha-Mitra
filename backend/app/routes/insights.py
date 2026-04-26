"""AI-generated dashboard insight blurb (bilingual EN + HI).

Produces a tight, opinionated 2-sentence English insight + 2-sentence Hindi
mirror that names the weakest concept and the single most useful next action,
based on the student's current mastery, readiness and weak prerequisites.

The route is cached in-memory per ``(user_id, day)`` so a normal dashboard
visit makes at most one Gemini call per day per student. Cache resets when
the process restarts.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import gemini_text
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag, weak_prerequisites
from app.intelligence.readiness import compute_readiness
from app.intelligence.sm2 import SM2Card

router = APIRouter(prefix="/insights", tags=["insights"])

log = logging.getLogger("parikshamitra.insights")


class InsightRequest(BaseModel):
    user_id: str


class InsightResponse(BaseModel):
    insight_en: str
    insight_hi: str
    generated_at: str


# In-memory cache: {(user_id, YYYY-MM-DD): InsightResponse}
_CACHE: dict[tuple[str, str], InsightResponse] = {}


INSIGHT_SYSTEM = """You are the Companion agent inside ParikshaMitra, a study coach
for Indian competitive-exam aspirants (JEE / NEET).

Given a JSON brief of the student's current state, write a punchy, motivating
insight that:
- Is exactly 2 sentences in English, then exactly 2 sentences in Hindi
  (Devanagari, with at most a couple of unavoidable English technical terms).
- Names the single weakest concept by its human name (not the ID).
- Recommends ONE concrete next action (e.g. "drill 5 questions on <concept>",
  "review your <subject> SR cards before lunch", "watch a 10-minute lesson on
  <concept>").
- Does not exceed ~60 words total across both languages.
- Avoids emojis, headings, bullets and JSON. Plain prose only.
- Tone: warm senior friend, evidence-based, no hype, no fluff.

Return STRICTLY this JSON shape and nothing else:
{"insight_en": "...", "insight_hi": "..."}
"""


def _build_brief(
    *,
    target_exam: str,
    daily_hours: float,
    exam_date: str | None,
    streak_days: int,
    readiness: dict[str, Any],
    subject_mastery: dict[str, float],
    weakest: list[dict[str, Any]],
    weak_prereqs: list[dict[str, Any]],
) -> str:
    payload = {
        "target_exam": target_exam,
        "daily_hours": daily_hours,
        "exam_date": exam_date,
        "streak_days": streak_days,
        "readiness_score_0_100": readiness.get("readiness"),
        "readiness_breakdown": {
            k: round(float(readiness.get(k, 0.0)), 3)
            for k in ("coverage", "mastery", "revision", "mock_trend")
        },
        "subject_mastery": {k: round(float(v), 3) for k, v in subject_mastery.items()},
        "weakest_concepts": weakest[:5],
        "weak_prerequisites_blocking_progress": weak_prereqs[:5],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_insight(raw: str) -> tuple[str, str]:
    """Best-effort parse of the model's JSON response."""

    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
        en = str(data.get("insight_en", "")).strip()
        hi = str(data.get("insight_hi", "")).strip()
        if en or hi:
            return en, hi
    except json.JSONDecodeError:
        pass
    # Fallback: split on a blank line / language marker
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    en = parts[0] if parts else ""
    hi = parts[1] if len(parts) > 1 else ""
    return en, hi


@router.post("/dashboard", response_model=InsightResponse)
async def dashboard_insight(
    body: InsightRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> InsightResponse:
    today = date.today().isoformat()
    cache_key = (body.user_id, today)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    dag = get_dag(user.target_exam)
    mastery: dict[str, float] = dict(user.mastery or {})
    cards = [SM2Card.model_validate(c) for c in (user.sm2 or {}).values()]
    readiness = compute_readiness(
        dag=dag,
        mastery=mastery,
        cards=cards,
        history=list(user.readiness_history or []),
    )

    # Per-subject mastery (weighted) - mirrors /plan/{user}/dashboard.
    subj_acc: dict[str, list[tuple[float, float]]] = {}
    for n, d in dag.graph.nodes(data=True):
        subj = d.get("subject", "Other")
        w = float(d.get("weight", 0.0)) or 0.01
        m = float(mastery.get(n, 0.0))
        subj_acc.setdefault(subj, []).append((w, m))
    subject_mastery = {
        subj: round(sum(w * m for w, m in items) / max(sum(w for w, _ in items), 1e-9), 3)
        for subj, items in subj_acc.items()
    }

    # Weakest concepts: prefer high-weight, low-mastery nodes the student has
    # actually been exposed to (or, failing that, the high-weight syllabus nodes).
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for n, d in dag.graph.nodes(data=True):
        w = float(d.get("weight", 0.0)) or 0.01
        m = float(mastery.get(n, 0.0))
        # gap score: high weight + low mastery -> bigger gap
        gap = w * (1.0 - m)
        scored.append((gap, n, {
            "id": n,
            "name": d.get("name", n),
            "subject": d.get("subject", "Other"),
            "mastery": round(m, 3),
            "weight": round(w, 3),
        }))
    scored.sort(key=lambda t: t[0], reverse=True)
    weakest = [info for _, _, info in scored[:5]]

    # Weak prereqs feeding the worst concept (up to 3, avoid duplicates).
    weak_prereqs: list[dict[str, Any]] = []
    if weakest:
        seen: set[str] = set()
        for w in weakest[:2]:
            for prereq in weak_prerequisites(dag, w["id"], mastery, threshold=0.5):
                if prereq in seen or prereq == w["id"]:
                    continue
                seen.add(prereq)
                info = dag.info(prereq)
                weak_prereqs.append({
                    "id": prereq,
                    "name": info.get("name", prereq),
                    "subject": info.get("subject", "Other"),
                    "mastery": round(float(mastery.get(prereq, 0.0)), 3),
                })
                if len(weak_prereqs) >= 5:
                    break
            if len(weak_prereqs) >= 5:
                break

    brief = _build_brief(
        target_exam=user.target_exam,
        daily_hours=float(user.daily_hours or 0.0),
        exam_date=user.exam_date,
        streak_days=int(user.streak_days or 0),
        readiness=readiness,
        subject_mastery=subject_mastery,
        weakest=weakest,
        weak_prereqs=weak_prereqs,
    )

    s = get_settings()
    try:
        raw = await gemini_text(
            keys=keys,
            prompt=brief,
            model=s.gemini_reasoning_model,
            system=INSIGHT_SYSTEM,
            temperature=0.5,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("Insight LLM call failed: %s", exc)
        # Heuristic fallback so the dashboard still shows something useful.
        weak_name = weakest[0]["name"] if weakest else "your weakest topic"
        en = (
            f"Your readiness is sitting at {readiness.get('readiness', 0):.0f}/100, "
            f"and {weak_name} is the biggest gap right now. "
            f"Run a 5-question drill on {weak_name} today before anything else."
        )
        hi = (
            f"\u0906\u092a\u0915\u0940 \u0924\u0948\u092f\u093e\u0930\u0940 \u0905\u092d\u0940 "
            f"{readiness.get('readiness', 0):.0f}/100 \u092a\u0930 \u0939\u0948, \u0914\u0930 "
            f"{weak_name} \u0938\u092c\u0938\u0947 \u092c\u095c\u093e \u0917\u0948\u092a \u0939\u0948\u0964 "
            f"\u0906\u091c {weak_name} \u092a\u0930 5 \u092a\u094d\u0930\u0936\u094d\u0928\u094b\u0902 "
            f"\u0915\u093e \u0921\u094d\u0930\u093f\u0932 \u0915\u0930\u0947\u0902\u0964"
        )
        out = InsightResponse(
            insight_en=en,
            insight_hi=hi,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        _CACHE[cache_key] = out
        return out

    en, hi = _parse_insight(raw)
    if not en and not hi:
        raise HTTPException(502, "Insight agent returned empty response")
    out = InsightResponse(
        insight_en=en,
        insight_hi=hi,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    _CACHE[cache_key] = out
    return out
