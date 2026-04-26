"""Readiness scoring - per the deck.

Readiness = 0.4 * coverage + 0.3 * mastery + 0.2 * revision + 0.1 * mock_trend
All inputs are 0..1 floats; the output is in 0..100.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from app.intelligence.concept_dag import ConceptDAG, coverage, weighted_mastery
from app.intelligence.sm2 import SM2Card


def compute_coverage(dag: ConceptDAG, mastery: dict[str, float]) -> float:
    return coverage(dag, mastery, threshold=0.4)


def compute_mastery(dag: ConceptDAG, mastery: dict[str, float]) -> float:
    return weighted_mastery(dag, mastery)


def compute_revision(cards: Iterable[SM2Card | dict], horizon_days: int = 14) -> float:
    """How well the student is keeping up with their spaced-repetition queue.

    1.0 = no overdue cards and most have a healthy interval; 0.0 = everything overdue.
    """
    total = 0
    on_track = 0
    today = date.today()
    for c in cards:
        if isinstance(c, dict):
            c = SM2Card.model_validate(c)
        total += 1
        due = date.fromisoformat(c.due)
        if due >= today:
            on_track += 1
        else:
            # Heavy penalty if overdue beyond the horizon
            overdue = (today - due).days
            if overdue <= horizon_days:
                on_track += 0.5
    return on_track / total if total else 0.5


def compute_mock_trend(history: list[dict]) -> float:
    """Slope of recent readiness history, normalised to 0..1.

    ``history`` is the persisted ``user.readiness_history`` list of
    ``{timestamp, readiness}`` dicts.
    """

    if not history:
        return 0.5
    recent = history[-7:]
    if len(recent) < 2:
        return 0.5
    first = recent[0]["readiness"] / 100.0
    last = recent[-1]["readiness"] / 100.0
    delta = last - first
    # Map delta in [-0.3, 0.3] to [0, 1]
    return max(0.0, min(1.0, 0.5 + delta / 0.6))


def compute_readiness(
    *,
    dag: ConceptDAG,
    mastery: dict[str, float],
    cards: Iterable[SM2Card | dict],
    history: list[dict],
) -> dict[str, float]:
    cov = compute_coverage(dag, mastery)
    mas = compute_mastery(dag, mastery)
    rev = compute_revision(cards)
    trend = compute_mock_trend(history)
    score = 100.0 * (0.4 * cov + 0.3 * mas + 0.2 * rev + 0.1 * trend)
    return {
        "coverage": cov,
        "mastery": mas,
        "revision": rev,
        "mock_trend": trend,
        "readiness": round(score, 2),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
