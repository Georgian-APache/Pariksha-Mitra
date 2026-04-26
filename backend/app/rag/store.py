"""Lightweight Chroma wrapper - one collection per (user, doc) pair."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaSettings

from app.config import CHROMA_DIR


@lru_cache(maxsize=1)
def chroma_client() -> ClientAPI:
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def collection_name(user_id: str, title: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()[:30]
    safe = safe or "doc"
    short_user = re.sub(r"[^a-zA-Z0-9]+", "", user_id)[:12].lower()
    return f"u_{short_user}_{safe}"
