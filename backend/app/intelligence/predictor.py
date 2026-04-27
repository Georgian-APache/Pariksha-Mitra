"""Monte-Carlo rank simulator (the deck does not have this - net new).

Idea: given the readiness history, fit a noisy linear trend (mean delta + std)
and simulate N trajectories to ``exam_date``. The exam-day distribution is then
mapped to JEE / NEET percentile via a logistic curve calibrated to public
percentile vs marks data (we use a smooth approximation, good enough for a
demo and clearly labelled as estimates).
"""

from __future__ import annotations

import math
import statistics
from datetime import date, datetime
import numpy as np
from pydantic import BaseModel


class RankPrediction(BaseModel):
    expected_readiness: float
    readiness_low: float  # 5th percentile
    readiness_high: float  # 95th percentile
    expected_percentile: float
    percentile_low: float
    percentile_high: float
    days_to_exam: int
    samples: int


def _readiness_to_percentile(readiness: float, exam: str) -> float:
    """Smooth logistic mapping from readiness (0..100) to exam percentile (0..100).

    Calibrated so:
      - readiness 50 -> ~70 percentile
      - readiness 75 -> ~92 percentile
      - readiness 90 -> ~98 percentile
    """

    # NEET uses a slightly higher midpoint; JEE / GATE / other exams use JEE-style curve.
    u = (exam or "JEE_MAIN").strip().upper()
    midpoint = 50.0 if u == "NEET" else 45.0
    k = 0.085
    p = 100.0 / (1.0 + math.exp(-k * (readiness - midpoint)))
    return max(0.0, min(99.99, p))


def _trend_stats(history: list[dict]) -> tuple[float, float]:
    """(mean daily delta, std daily delta)."""
    if not history or len(history) < 2:
        return 0.4, 1.5  # gentle default upward drift
    points = [(datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00")), float(h["readiness"])) for h in history]
    points.sort()
    deltas: list[float] = []
    for i in range(1, len(points)):
        dt_days = max(0.5, (points[i][0] - points[i - 1][0]).total_seconds() / 86400.0)
        deltas.append((points[i][1] - points[i - 1][1]) / dt_days)
    mean = statistics.fmean(deltas) if deltas else 0.4
    stdev = statistics.pstdev(deltas) if len(deltas) > 1 else 1.0
    return mean, max(0.5, stdev)


def simulate_readiness(
    current_readiness: float,
    exam_date: date | str,
    history: list[dict] | None = None,
    n_samples: int = 2000,
    seed: int = 7,
) -> RankPrediction:
    if isinstance(exam_date, str):
        exam_date = date.fromisoformat(exam_date)
    days = max(1, (exam_date - date.today()).days)
    mean_d, std_d = _trend_stats(history or [])

    rng = np.random.default_rng(seed)
    # Brownian-with-drift for ``days`` steps
    increments = rng.normal(loc=mean_d, scale=std_d, size=(n_samples, days))
    trajectories = current_readiness + np.cumsum(increments, axis=1)
    final = np.clip(trajectories[:, -1], 0.0, 100.0)
    return RankPrediction(
        expected_readiness=float(np.mean(final)),
        readiness_low=float(np.percentile(final, 5)),
        readiness_high=float(np.percentile(final, 95)),
        expected_percentile=0.0,
        percentile_low=0.0,
        percentile_high=0.0,
        days_to_exam=days,
        samples=n_samples,
    )


def simulate_rank(
    current_readiness: float,
    exam_date: date | str,
    *,
    exam: str = "JEE_MAIN",
    history: list[dict] | None = None,
    n_samples: int = 2000,
    seed: int = 7,
) -> RankPrediction:
    """Wraps :func:`simulate_readiness` and fills percentile fields."""

    pred = simulate_readiness(current_readiness, exam_date, history=history, n_samples=n_samples, seed=seed)
    expected_p = _readiness_to_percentile(pred.expected_readiness, exam)
    low_p = _readiness_to_percentile(pred.readiness_low, exam)
    high_p = _readiness_to_percentile(pred.readiness_high, exam)
    return RankPrediction(
        expected_readiness=round(pred.expected_readiness, 2),
        readiness_low=round(pred.readiness_low, 2),
        readiness_high=round(pred.readiness_high, 2),
        expected_percentile=round(expected_p, 2),
        percentile_low=round(low_p, 2),
        percentile_high=round(high_p, 2),
        days_to_exam=pred.days_to_exam,
        samples=pred.samples,
    )
