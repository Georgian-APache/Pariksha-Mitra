"""PDF-RAG routes: upload + grounded MCQ generation with citations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import gemini_json
from app.agents.state import QUESTION_OUTPUT_SCHEMA
from app.config import APIKeys, api_keys, get_settings
from app.db import get_session
from app.db import repositories as repo
from app.intelligence.concept_dag import get_dag
from app.rag.ingestion import ingest_pdf, query as rag_query

router = APIRouter(prefix="/rag", tags=["rag"])

log = logging.getLogger("parikshamitra.rag")


class IngestResponse(BaseModel):
    document_id: str
    collection: str
    title: str
    pages: int
    chunks: int


@router.post("/upload", response_model=IngestResponse)
async def upload_pdf(
    user_id: str = Form(...),
    title: str = Form(...),
    pdf: UploadFile = File(...),
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    blob = await pdf.read()
    if not blob:
        raise HTTPException(400, "empty PDF")
    try:
        cname, pages, chunks = await ingest_pdf(keys=keys, user_id=user.id, title=title, pdf_bytes=blob)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as exc:  # noqa: BLE001
        log.exception("ingest failed")
        raise HTTPException(502, f"Ingestion failed: {exc}") from exc

    doc = await repo.record_rag_doc(
        session,
        user_id=user.id,
        title=title,
        collection=cname,
        chunk_count=chunks,
        page_count=pages,
    )
    return IngestResponse(
        document_id=doc.id,
        collection=cname,
        title=title,
        pages=pages,
        chunks=chunks,
    )


class DocsResponse(BaseModel):
    documents: list[dict[str, Any]]


@router.get("/docs/{user_id}", response_model=DocsResponse)
async def list_docs(user_id: str, session: AsyncSession = Depends(get_session)) -> DocsResponse:
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    docs = await repo.list_rag_docs(session, user.id)
    return DocsResponse(
        documents=[
            {
                "id": d.id,
                "title": d.title,
                "collection": d.collection,
                "pages": d.page_count,
                "chunks": d.chunk_count,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]
    )


class GroundedQuizRequest(BaseModel):
    user_id: str
    collection: str
    topic_hint: str | None = None
    n_questions: int = 5


class GroundedQuiz(BaseModel):
    questions: list[dict[str, Any]]
    citations: list[dict[str, Any]]


_GROUNDED_QUIZ_SYSTEM = """You are QuizMaster grounded in a specific PDF.

You will receive numbered EXCERPTS from a chapter. For each excerpt, write
exam-grade MCQs that can be answered using ONLY information in those excerpts.
Cite the relevant excerpt page in the explanation, e.g. 'See p.41'.
Difficulty 1-5. Output JSON matching QuizOutput.
"""


@router.post("/quiz", response_model=GroundedQuiz)
async def grounded_quiz(
    body: GroundedQuizRequest,
    keys: APIKeys = Depends(api_keys),
    session: AsyncSession = Depends(get_session),
) -> GroundedQuiz:
    user = await repo.get_user(session, body.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    seed_query = body.topic_hint or "Key definitions, formulas and worked-example concepts."
    excerpts = await rag_query(
        keys=keys,
        collection=body.collection,
        query_text=seed_query,
        top_k=8,
    )
    if not excerpts:
        raise HTTPException(404, "no excerpts retrieved")

    # Build prompt
    excerpt_block = "\n\n".join(
        f"[Excerpt {i+1} - page {e['page']}]\n{e['text']}" for i, e in enumerate(excerpts)
    )
    prompt = (
        f"Number of MCQs to write: {body.n_questions}.\n"
        f"Topic hint: {body.topic_hint or '(none)'}\n\n"
        f"Excerpts:\n{excerpt_block}"
    )
    s = get_settings()
    payload = await gemini_json(
        keys=keys,
        prompt=prompt,
        schema=QUESTION_OUTPUT_SCHEMA,
        system=_GROUNDED_QUIZ_SYSTEM,
        model=s.gemini_default_model,
        temperature=0.5,
    )

    citations = [
        {"index": i + 1, "page": e["page"], "preview": e["text"][:160] + ("..." if len(e["text"]) > 160 else "")}
        for i, e in enumerate(excerpts)
    ]
    return GroundedQuiz(
        questions=payload.get("questions", []) or [],
        citations=citations,
    )
