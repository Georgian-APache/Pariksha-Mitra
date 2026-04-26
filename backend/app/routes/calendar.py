"""ICS calendar export of the active weekly plan."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db import repositories as repo

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _ics_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _format_dt(d: str, hour: int, minute: int) -> str:
    return f"{d.replace('-', '')}T{hour:02d}{minute:02d}00"


def build_ics(user_name: str, plan: dict) -> str:
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ParikshaMitra//Plan//EN",
        "CALSCALE:GREGORIAN",
    ]
    days: Iterable[dict] = plan.get("days", [])
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for d in days:
        date_str = d.get("date")
        if not date_str:
            continue
        cur_h, cur_m = 17, 0  # default start at 5pm local
        for i, b in enumerate(d.get("blocks", [])):
            mins = int(b.get("minutes", 30))
            start = _format_dt(date_str, cur_h, cur_m)
            end_total = cur_m + mins
            end_h = cur_h + end_total // 60
            end_m = end_total % 60
            end = _format_dt(date_str, end_h, end_m)
            cur_h, cur_m = end_h, end_m

            uid = f"pm-{user_name}-{date_str}-{i}@parikshamitra"
            summary = f"PM | {b.get('activity','study').title()} - {b.get('concept_id','')}"
            desc = (
                f"{b.get('subject','')} | {b.get('activity','study')}\\n"
                f"{b.get('note','') or ''}\\n"
                f"Block from your ParikshaMitra weekly plan."
            )
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{now_stamp}",
                    f"DTSTART:{start}",
                    f"DTEND:{end}",
                    f"SUMMARY:{_ics_escape(summary)}",
                    f"DESCRIPTION:{_ics_escape(desc)}",
                    "END:VEVENT",
                ]
            )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


@router.get("/{user_id}.ics", response_class=PlainTextResponse)
async def download_ics(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> PlainTextResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if not user.plan:
        raise HTTPException(404, "no active plan")
    body = build_ics(user_name=user.display_name or "Student", plan=user.plan or {})
    return PlainTextResponse(
        content=body,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="parikshamitra-{user_id}.ics"'},
    )
