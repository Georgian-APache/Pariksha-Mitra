"""Friends / social leaderboard routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db.models import FriendLink, StudySession, User
from app.db import repositories as repo

router = APIRouter(prefix="/friends", tags=["friends"])


class AddFriendRequest(BaseModel):
    user_id: str
    friend_id: str


@router.post("/add")
async def add_friend(
    body: AddFriendRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if body.user_id == body.friend_id:
        raise HTTPException(400, "Cannot add yourself as a friend")

    user = await repo.get_user(session, body.user_id)
    friend = await repo.get_user(session, body.friend_id)
    if not user:
        raise HTTPException(404, "user not found")
    if not friend:
        raise HTTPException(404, "friend user not found — check the ID")

    # Idempotent: skip if already linked
    existing = await session.execute(
        select(FriendLink).where(
            FriendLink.user_id == body.user_id,
            FriendLink.friend_id == body.friend_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_friends", "friend_name": friend.display_name}

    # Mutual link
    session.add(FriendLink(user_id=body.user_id, friend_id=body.friend_id))
    session.add(FriendLink(user_id=body.friend_id, friend_id=body.user_id))
    await session.commit()
    return {"status": "added", "friend_name": friend.display_name}


@router.get("/{user_id}")
async def get_friends(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    links = await session.execute(
        select(FriendLink).where(FriendLink.user_id == user_id)
    )
    friend_ids = [lnk.friend_id for lnk in links.scalars()]

    friends_data = []
    for fid in friend_ids:
        friend = await repo.get_user(session, fid)
        if not friend:
            continue
        friends_data.append(_public_stats(friend))

    # Include self so the page can show "You" in the leaderboard
    my_stats = _public_stats(user)
    my_stats["is_self"] = True

    # Sort by readiness descending
    all_entries = [my_stats] + friends_data
    all_entries.sort(key=lambda x: x["readiness"], reverse=True)

    return {
        "user_id": user_id,
        "my_id": user_id,
        "leaderboard": all_entries,
    }


@router.delete("/{user_id}/{friend_id}")
async def remove_friend(
    user_id: str,
    friend_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    for uid, fid in [(user_id, friend_id), (friend_id, user_id)]:
        row = await session.execute(
            select(FriendLink).where(
                FriendLink.user_id == uid, FriendLink.friend_id == fid
            )
        )
        obj = row.scalar_one_or_none()
        if obj:
            await session.delete(obj)
    await session.commit()
    return {"status": "removed"}


def _public_stats(user: User) -> dict[str, Any]:
    """Extract leaderboard-safe public stats — no mood/mental health data."""
    readiness_hist = list(user.readiness_history or [])
    latest = readiness_hist[-1] if readiness_hist else {}

    mastery: dict = user.mastery or {}

    # readiness_history stores 0-100; normalise to 0-1 for the frontend
    readiness_raw = latest.get("readiness", 0.0) or 0.0
    readiness = readiness_raw / 100.0

    # coverage = fraction of concepts with mastery > 0.1
    if mastery:
        covered = sum(1 for v in mastery.values() if v > 0.1)
        coverage = covered / len(mastery)
        mastery_avg = sum(mastery.values()) / len(mastery)
    else:
        coverage = 0.0
        mastery_avg = 0.0

    # Top 3 strongest subjects
    top_subjects = sorted(mastery.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "target_exam": user.target_exam.replace("_", " "),
        "streak_days": user.streak_days or 0,
        "readiness": round(readiness, 4),
        "coverage": round(coverage, 4),
        "mastery_avg": round(mastery_avg, 4),
        "top_subjects": [{"subject": s, "score": round(v, 2)} for s, v in top_subjects],
        "daily_hours": user.daily_hours,
        "exam_date": user.exam_date,
        "is_self": False,
    }
