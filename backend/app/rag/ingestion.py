"""PDF -> chunks -> embeddings -> Chroma."""

from __future__ import annotations

import io
import logging
import re
from typing import Iterable

from pypdf import PdfReader

from app.agents.llm import gemini_embed
from app.config import APIKeys
from app.rag.store import chroma_client, collection_name

log = logging.getLogger("parikshamitra.rag.ingest")


def _split_paragraphs(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        # Prefer to break on sentence boundary near ``end``
        if end < len(text):
            window = text[max(start, end - 120):end]
            m = re.search(r"[.!?]\s", window[::-1])
            if m:
                end = end - m.start()
        chunk = text[start:end].strip()
        if chunk:
            out.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return out


def extract_chunks(pdf_bytes: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    chunks: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            txt = ""
        for c in _split_paragraphs(txt):
            chunks.append((i + 1, c))
    return chunks


async def ingest_pdf(
    *,
    keys: APIKeys,
    user_id: str,
    title: str,
    pdf_bytes: bytes,
    batch_size: int = 50,
) -> tuple[str, int, int]:
    """Returns ``(collection_name, page_count, chunk_count)``."""

    cname = collection_name(user_id, title)
    chunks = extract_chunks(pdf_bytes)
    if not chunks:
        raise ValueError("No extractable text in PDF")

    # Embed in batches
    texts = [c[1] for c in chunks]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        emb = await gemini_embed(keys=keys, inputs=batch)
        embeddings.extend(emb)
        log.info("Embedded %d/%d chunks for %s", i + len(batch), len(texts), cname)

    if len(embeddings) != len(chunks):
        # Pad / truncate defensively
        while len(embeddings) < len(chunks):
            embeddings.append([0.0])
        embeddings = embeddings[: len(chunks)]

    client = chroma_client()
    try:
        client.delete_collection(cname)
    except Exception:  # noqa: BLE001
        pass
    coll = client.create_collection(cname, metadata={"title": title, "user_id": user_id})
    coll.add(
        ids=[f"{cname}-{i}" for i in range(len(chunks))],
        documents=[c[1] for c in chunks],
        metadatas=[{"page": c[0], "title": title} for c in chunks],
        embeddings=embeddings,
    )

    pages = max(c[0] for c in chunks)
    return cname, pages, len(chunks)


async def query(
    *,
    keys: APIKeys,
    collection: str,
    query_text: str,
    top_k: int = 5,
) -> list[dict]:
    emb = (await gemini_embed(keys=keys, inputs=[query_text]))[0]
    client = chroma_client()
    coll = client.get_collection(collection)
    res = coll.query(query_embeddings=[emb], n_results=top_k)
    out: list[dict] = []
    for i in range(len(res["ids"][0])):
        out.append(
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "page": res["metadatas"][0][i].get("page", -1),
                "score": float(res["distances"][0][i]) if "distances" in res else 0.0,
            }
        )
    return out
