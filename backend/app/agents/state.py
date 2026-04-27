"""Pydantic v2 schemas for the LangGraph state and structured-output payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Generic value objects
# ---------------------------------------------------------------------------


class Question(BaseModel):
    id: str
    concept_id: str
    subject: str
    difficulty: int = Field(ge=1, le=5, default=3)
    stem: str
    options: list[str]  # 4 options A-D
    correct_index: int = Field(ge=0, le=3)
    explanation: str = ""
    bilingual_hint: str | None = None  # short hi-IN nudge
    source: str = "generated"  # "seed" | "generated" | "rag"


class GradedAnswer(BaseModel):
    question_id: str
    chosen_index: int
    correct: bool
    score: float = Field(ge=0.0, le=1.0)  # supports partial credit
    rationale: str = ""
    misconception: str | None = None


class PlanDayBlock(BaseModel):
    subject: str
    concept_id: str
    minutes: int
    activity: Literal["learn", "quiz", "review", "drill"]
    note: str = ""


class PlanDay(BaseModel):
    date: str  # YYYY-MM-DD
    blocks: list[PlanDayBlock]
    total_minutes: int


class WeeklyPlan(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rationale: str = ""
    days: list[PlanDay]
    focus_concepts: list[str] = []


class AgentStep(BaseModel):
    """One step persisted in the agent trace - what the user sees animate."""

    agent: Literal["orchestrator", "planner", "quizmaster", "analyst", "companion", "system"]
    headline: str
    detail: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Graph state - this is the dict LangGraph passes between nodes
# ---------------------------------------------------------------------------


class StudentState(BaseModel):
    """The root state hydrated for every graph run."""

    user_id: str
    target_exam: str = "JEE_MAIN"
    exam_date: str | None = None  # YYYY-MM-DD
    daily_hours: float = 3.0

    # Knowledge graph
    mastery: dict[str, float] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    last_seen: dict[str, str] = Field(default_factory=dict)
    sm2: dict[str, dict[str, Any]] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)
    readiness_history: list[dict[str, Any]] = Field(default_factory=list)

    # Run-scoped scratch
    run_id: str | None = None
    intent: Literal[
        "diagnostic", "plan", "quiz_finished", "snap_doubt", "drill", "rag_quiz", "manual_replan"
    ] = "diagnostic"
    diagnostic_results: list[GradedAnswer] = Field(default_factory=list)
    last_quiz_results: list[GradedAnswer] = Field(default_factory=list)
    last_quiz_concept: str | None = None
    weak_prereqs: list[str] = Field(default_factory=list)
    readiness: dict[str, float] = Field(default_factory=dict)
    nudge: dict[str, str] = Field(default_factory=dict)  # {en: ..., hi: ...}

    # Trace - the SSE feed listens to this
    trace: list[AgentStep] = Field(default_factory=list)

    def add_trace(self, step: AgentStep) -> "StudentState":
        # Pydantic v2 immutable-ish update
        self.trace = list(self.trace) + [step]
        # Publish to the SSE bus if a run is active. Lazy-imported to avoid cycle.
        if self.run_id:
            try:
                from app.agents.orchestrator import bus  # noqa: WPS433

                bus.publish(self.run_id, step)
            except Exception:  # noqa: BLE001
                pass
        return self


# ---------------------------------------------------------------------------
# Structured-output JSON schemas (used by the Gemini ``responseSchema`` API)
# ---------------------------------------------------------------------------

PLANNER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "rationale": {"type": "STRING"},
        "focus_concepts": {"type": "ARRAY", "items": {"type": "STRING"}},
        "days": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "date": {"type": "STRING"},
                    "total_minutes": {"type": "INTEGER"},
                    "blocks": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "subject": {"type": "STRING"},
                                "concept_id": {"type": "STRING"},
                                "minutes": {"type": "INTEGER"},
                                "activity": {
                                    "type": "STRING",
                                    "enum": ["learn", "quiz", "review", "drill"],
                                },
                                "note": {"type": "STRING"},
                            },
                            "required": ["subject", "concept_id", "minutes", "activity"],
                        },
                    },
                },
                "required": ["date", "total_minutes", "blocks"],
            },
        },
    },
    "required": ["rationale", "focus_concepts", "days"],
}


QUESTION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "questions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "concept_id": {"type": "STRING"},
                    "subject": {"type": "STRING"},
                    "difficulty": {"type": "INTEGER"},
                    "stem": {"type": "STRING"},
                    "options": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "correct_index": {"type": "INTEGER"},
                    "explanation": {"type": "STRING"},
                    "bilingual_hint": {"type": "STRING"},
                },
                "required": [
                    "concept_id",
                    "subject",
                    "difficulty",
                    "stem",
                    "options",
                    "correct_index",
                    "explanation",
                ],
            },
        },
    },
    "required": ["questions"],
}


GRADER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "score": {"type": "NUMBER"},
        "rationale": {"type": "STRING"},
        "misconception": {"type": "STRING"},
    },
    "required": ["score", "rationale"],
}


ANALYST_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "insight": {"type": "STRING"},
        "weak_prereqs": {"type": "ARRAY", "items": {"type": "STRING"}},
        "should_replan": {"type": "BOOLEAN"},
        "reason": {"type": "STRING"},
    },
    "required": ["insight", "weak_prereqs", "should_replan"],
}


COMPANION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "en": {"type": "STRING"},
        "hi": {"type": "STRING"},
        "tone": {"type": "STRING"},
    },
    "required": ["en", "hi"],
}


SNAP_DOUBT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "subject": {"type": "STRING"},
        "concept_id": {"type": "STRING"},
        "concept_name": {"type": "STRING"},
        "answer": {"type": "STRING"},
        "steps": {"type": "ARRAY", "items": {"type": "STRING"}},
        "confidence": {"type": "NUMBER"},
        "follow_up": {"type": "STRING"},
    },
    "required": ["subject", "concept_id", "answer", "steps"],
}
