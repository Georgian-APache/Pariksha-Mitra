"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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
    target_exam: Mapped[str] = mapped_column(String(120), default="JEE_MAIN")
    exam_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    daily_hours: Mapped[float] = mapped_column(Float, default=3.0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # JSON blobs
    mastery: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    confidence: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    last_seen: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    sm2: Mapped[dict[str, dict[str, Any]]] = mapped_column(JSON, default=dict)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    readiness_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Mental health tracking
    parent_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mood_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    stress_level: Mapped[float] = mapped_column(Float, default=5.0)
    mental_health_flags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Schedule accountability
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)
    last_parent_alert_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    traces: Mapped[list["AgentTraceLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    study_sessions: Mapped[list["StudySession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    mental_health_chats: Mapped[list["MentalHealthChat"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="adaptive")
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
    score: Mapped[float] = mapped_column(Float, default=0.0)
    time_taken_s: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="quiz_attempts")


class AgentTraceLog(Base):
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


class MentalHealthChat(Base):
    __tablename__ = "mental_health_chats"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    mood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="mental_health_chats")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_date: Mapped[str] = mapped_column(String(20))
    concept_id: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(80))
    activity: Mapped[str] = mapped_column(String(20))
    scheduled_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reality_check_questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="study_sessions")


class FriendLink(Base):
    __tablename__ = "friend_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    friend_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
