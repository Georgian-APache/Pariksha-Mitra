"""Snap-a-Doubt - multimodal Gemini Vision route."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import gemini_json
from app.agents.prompts import SNAP_DOUBT_SYSTEM, snap_doubt_user_prompt
from app.agents.state import SNAP_DOUBT_OUTPUT_SCHEMA
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag

router = APIRouter(prefix="/doubt", tags=["doubt"])

log = logging.getLogger("parikshamitra.doubt")


class DoubtResponse(BaseModel):
    subject: str
    concept_id: str
    concept_name: str
    answer: str
    steps: list[str]
    confidence: float
    follow_up: str
    matched_concept: bool
    mastery_after: dict[str, float]


@router.post("", response_model=DoubtResponse)
async def snap_doubt(
    user_id: str = Form(...),
    image: UploadFile = File(...),
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> DoubtResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    dag = get_dag(user.target_exam)
    catalogue = [
        {"id": c["id"], "name": c["name"], "subject": c["subject"]}
        for c in dag.all_concepts()
    ]

    blob = await image.read()
    if not blob:
        raise HTTPException(400, "empty image")

    s = get_settings()
    try:
        payload = await gemini_json(
            keys=keys,
            prompt=snap_doubt_user_prompt(catalogue),
            schema=SNAP_DOUBT_OUTPUT_SCHEMA,
            system=SNAP_DOUBT_SYSTEM,
            model=s.gemini_vision_model,
            images=[blob],
            image_mimetypes=[image.content_type or "image/png"],
            temperature=0.3,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Snap-a-Doubt LLM failed: %s", exc)
        raise HTTPException(502, f"Vision agent failed: {exc}") from exc

    cid = payload.get("concept_id") or ""
    matched = cid in dag
    if not matched:
        cid_fallback = next(iter(catalogue), {}).get("id", "")
        cid = cid_fallback

    # Tiny mastery nudge: +0.05 because the student got an explanation.
    new_mastery = dict(user.mastery or {})
    if matched:
        prior = new_mastery.get(cid, 0.4)
        new_mastery[cid] = round(min(1.0, prior + 0.05), 3)
        await repo.update_user_state(session, user, mastery=new_mastery)

    return DoubtResponse(
        subject=payload.get("subject", "") or "",
        concept_id=cid,
        concept_name=payload.get("concept_name", dag.info(cid).get("name", cid)) if cid else "",
        answer=payload.get("answer", ""),
        steps=list(payload.get("steps", []) or []),
        confidence=float(payload.get("confidence", 0.5)),
        follow_up=payload.get("follow_up", ""),
        matched_concept=matched,
        mastery_after=new_mastery if matched else (user.mastery or {}),
    )
