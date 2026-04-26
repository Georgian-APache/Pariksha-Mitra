"""SQLAlchemy ORM models.

We keep mastery / SM-2 cards / quiz history denormalised as JSON columns - the
read pattern is overwhelmingly "hydrate the whole student state for the
agent graph", so JSON is faster to ship and easy to migrate later.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(120), default="Student")
    target_exam: Mapped[str] = mapped_column(String(32), default="JEE_MAIN")
    exam_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    daily_hours: Mapped[float] = mapped_column(Float, default=3.0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # JSON blobs (concept_id -> value)
    mastery: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    confidence: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    last_seen: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    sm2: Mapped[dict[str, dict[str, Any]]] = mapped_column(JSON, default=dict)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    readiness_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    traces: Mapped[list["AgentTraceLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="adaptive")  # diagnostic|adaptive|drill|rag
    concept_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    answers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    concept_id: Mapped[str] = mapped_column(String(80), index=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    correct: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1, supports partial credit
    time_taken_s: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="quiz_attempts")


class AgentTraceLog(Base):
    """Persisted trace of a single graph run (for the SSE replay + analytics)."""

    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    agent: Mapped[str] = mapped_column(String(40))
    headline: Mapped[str] = mapped_column(String(280))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="traces")


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    collection: Mapped[str] = mapped_column(String(80), index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
