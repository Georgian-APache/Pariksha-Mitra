"""Computer-Adaptive-Testing-lite difficulty controller.

Deck contract:
  - 3 consecutive correct -> level += 1
  - 2 (any rolling-window) wrong -> level -= 1
  - clamp to [1, 5]
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class CATState:
    """Persistable state for an adaptive quiz session."""

    level: int = 3
    streak_correct: int = 0
    streak_wrong: int = 0
    history: list[bool] | None = None

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = []


def next_difficulty(state: CATState | dict) -> int:
    if isinstance(state, dict):
        state = CATState(**state)
    return max(1, min(5, state.level))


def update_history(state: CATState | dict, *, correct: bool) -> CATState:
    """Apply +3-correct / -2-wrong rule and return updated state."""

    if isinstance(state, dict):
        state = CATState(**state)
    state.history = (state.history or []) + [bool(correct)]

    if correct:
        state.streak_correct += 1
        state.streak_wrong = 0
        if state.streak_correct >= 3:
            state.level = min(5, state.level + 1)
            state.streak_correct = 0
    else:
        state.streak_wrong += 1
        state.streak_correct = 0
        if state.streak_wrong >= 2:
            state.level = max(1, state.level - 1)
            state.streak_wrong = 0
    return state


def initial_difficulty(mastery: float) -> int:
    """Pick a starting difficulty from a 0..1 mastery score."""

    if mastery < 0.2:
        return 1
    if mastery < 0.4:
        return 2
    if mastery < 0.65:
        return 3
    if mastery < 0.85:
        return 4
    return 5


def difficulty_window(history: list[bool], window: int = 4) -> deque[bool]:
    return deque(history[-window:], maxlen=window)
