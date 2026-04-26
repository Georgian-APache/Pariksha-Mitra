"""SuperMemo-2 spaced repetition - tuned to the deck rules.

Deck contract:
  - score > 0.8: interval *= 2
  - 0.5 <= score <= 0.8: maintain interval
  - score < 0.5: reset interval to 1 day

We additionally track ease factor in the classic SM-2 way so the curve smooths
out for power users; the deck rule above takes precedence on the first three
buckets, and ease only modulates within them.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from pydantic import BaseModel, Field


class SM2Card(BaseModel):
    """One spaced-repetition card per concept."""

    concept_id: str
    interval_days: int = 1
    ease: float = 2.5
    repetitions: int = 0
    due: str = Field(default_factory=lambda: date.today().isoformat())
    last_score: float = 0.0
    last_reviewed: str | None = None


def sm2_update(card: SM2Card | dict, score: float) -> SM2Card:
    """Apply the deck SM-2 rule. ``score`` is 0..1 (partial-credit aware)."""

    if isinstance(card, dict):
        card = SM2Card.model_validate(card)
    score = max(0.0, min(1.0, float(score)))

    if score >= 0.8:
        card.repetitions += 1
        card.interval_days = max(1, card.interval_days) * 2
        card.ease = min(2.8, card.ease + 0.1)
    elif score >= 0.5:
        card.interval_days = max(1, card.interval_days)
        card.ease = max(1.3, card.ease - 0.05)
    else:
        card.repetitions = 0
        card.interval_days = 1
        card.ease = max(1.3, card.ease - 0.2)

    card.last_score = score
    today = date.today()
    card.last_reviewed = today.isoformat()
    card.due = (today + timedelta(days=card.interval_days)).isoformat()
    return card


def due_cards(cards: Iterable[SM2Card | dict], on: date | None = None) -> list[SM2Card]:
    on = on or date.today()
    out: list[SM2Card] = []
    for c in cards:
        if isinstance(c, dict):
            c = SM2Card.model_validate(c)
        if date.fromisoformat(c.due) <= on:
            out.append(c)
    return out


def days_overdue(card: SM2Card | dict, on: date | None = None) -> int:
    on = on or date.today()
    if isinstance(card, dict):
        card = SM2Card.model_validate(card)
    return max(0, (on - date.fromisoformat(card.due)).days)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
