"""Concept-graph routes - returns the DAG plus per-node mastery overlay."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphResponse(BaseModel):
    exam: str
    subjects: dict[str, float]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    mastery: dict[str, float]
    sm2: dict[str, dict[str, Any]]


@router.get("/{user_id}", response_model=GraphResponse)
async def fetch_graph(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> GraphResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    dag = get_dag(user.target_exam)
    cyto = dag.cytoscape()
    return GraphResponse(
        exam=cyto["exam"],
        subjects=cyto["subjects"],
        nodes=cyto["nodes"],
        edges=cyto["edges"],
        mastery=user.mastery or {},
        sm2=user.sm2 or {},
    )
