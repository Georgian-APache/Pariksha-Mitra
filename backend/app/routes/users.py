"""User CRUD + state hydration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db import repositories as repo

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateRequest(BaseModel):
    display_name: str = Field(default="Student", max_length=120)
    target_exam: str = Field(default="JEE_MAIN", max_length=120)
    exam_date: str | None = Field(default=None, description="YYYY-MM-DD")
    daily_hours: float = Field(default=3.0, ge=0.5, le=16)


class UserResponse(BaseModel):
    id: str
    display_name: str
    target_exam: str
    exam_date: str | None
    daily_hours: float
    streak_days: int
    mastery: dict[str, float]
    confidence: dict[str, float]
    plan: dict[str, Any]
    readiness_history: list[dict[str, Any]]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await repo.upsert_user(
        session,
        display_name=body.display_name,
        target_exam=body.target_exam,
        exam_date=body.exam_date,
        daily_hours=body.daily_hours,
    )
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        target_exam=user.target_exam,
        exam_date=user.exam_date,
        daily_hours=user.daily_hours,
        streak_days=user.streak_days,
        mastery=user.mastery or {},
        confidence=user.confidence or {},
        plan=user.plan or {},
        readiness_history=user.readiness_history or [],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def fetch_user(user_id: str, session: AsyncSession = Depends(get_session)) -> UserResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        target_exam=user.target_exam,
        exam_date=user.exam_date,
        daily_hours=user.daily_hours,
        streak_days=user.streak_days,
        mastery=user.mastery or {},
        confidence=user.confidence or {},
        plan=user.plan or {},
        readiness_history=user.readiness_history or [],
    )
