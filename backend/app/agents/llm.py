"""Thin async wrappers around Gemini and Groq, with retries + JSON guard."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Iterable

from google import genai
from google.genai import types as gtypes
from groq import AsyncGroq
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.config import APIKeys, get_settings

log = logging.getLogger("parikshamitra.llm")


class LLMError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def _gemini_client(keys: APIKeys) -> genai.Client:
    api_key = keys.require("gemini")
    return genai.Client(api_key=api_key)


async def gemini_json(
    *,
    keys: APIKeys,
    prompt: str,
    schema: dict[str, Any],
    model: str | None = None,
    system: str | None = None,
    images: Iterable[bytes] | None = None,
    image_mimetypes: Iterable[str] | None = None,
    temperature: float = 0.4,
) -> dict[str, Any]:
    """Run Gemini with structured-JSON output and return the parsed dict."""

    s = get_settings()
    model = model or s.gemini_default_model
    client = _gemini_client(keys)

    parts: list[Any] = [prompt]
    if images:
        mimetypes = list(image_mimetypes or [])
        for i, blob in enumerate(images):
            mt = mimetypes[i] if i < len(mimetypes) else "image/png"
            parts.append(gtypes.Part.from_bytes(data=blob, mime_type=mt))

    contents = [gtypes.Content(role="user", parts=[
        gtypes.Part.from_text(text=p) if isinstance(p, str) else p for p in parts
    ])]

    config = gtypes.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=schema,
        system_instruction=system,
    )

    last_exc: Exception | None = None
    async for attempt in AsyncRetrying(
        wait=wait_random_exponential(multiplier=0.5, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=False,
    ):
        with attempt:
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=config,
                )
                text = response.text or ""
                return json.loads(text)
            except json.JSONDecodeError as e:
                # Try to recover from malformed JSON by stripping markdown fences
                text = (response.text or "").strip().strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    last_exc = e
                    raise
            except Exception as e:  # noqa: BLE001
                last_exc = e
                raise
    raise LLMError(f"Gemini call failed after retries: {last_exc}")


async def gemini_text(
    *,
    keys: APIKeys,
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    temperature: float = 0.4,
) -> str:
    s = get_settings()
    model = model or s.gemini_default_model
    client = _gemini_client(keys)
    config = gtypes.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
    )
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text or ""


async def gemini_chat(
    *,
    keys: APIKeys,
    system: str,
    history: list[dict[str, str]],
    message: str,
    model: str | None = None,
    temperature: float = 0.75,
) -> str:
    """Multi-turn Gemini conversation. history items have role='user'|'assistant'."""
    s = get_settings()
    model = model or s.gemini_default_model
    client = _gemini_client(keys)

    contents: list[Any] = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(gtypes.Content(role=role, parts=[gtypes.Part.from_text(text=turn["content"])]))
    contents.append(gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=message)]))

    config = gtypes.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
    )
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=contents,
        config=config,
    )
    return response.text or ""


async def gemini_embed(
    *,
    keys: APIKeys,
    inputs: list[str],
    model: str | None = None,
) -> list[list[float]]:
    s = get_settings()
    model = model or s.gemini_embedding_model
    client = _gemini_client(keys)
    response = await asyncio.to_thread(
        client.models.embed_content,
        model=model,
        contents=inputs,
    )
    # New SDK returns ``embeddings`` as a list of EmbedContentEmbedding
    embeddings = getattr(response, "embeddings", None) or []
    out: list[list[float]] = []
    for e in embeddings:
        values = getattr(e, "values", None)
        if values is None and isinstance(e, dict):
            values = e.get("values")
        out.append(list(values or []))
    return out


# ---------------------------------------------------------------------------
# Groq (used for fast/cheap nudges + voice transcription)
# ---------------------------------------------------------------------------


def _groq_client(keys: APIKeys) -> AsyncGroq:
    api_key = keys.require("groq")
    return AsyncGroq(api_key=api_key)


async def groq_chat(
    *,
    keys: APIKeys,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.5,
) -> str:
    s = get_settings()
    model = model or s.groq_fast_model
    client = _groq_client(keys)
    res = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return res.choices[0].message.content or ""


async def groq_transcribe(*, keys: APIKeys, audio: bytes, filename: str = "audio.webm") -> str:
    s = get_settings()
    client = _groq_client(keys)
    # Groq accepts bytes-like; the SDK exposes audio.transcriptions.create
    res = await client.audio.transcriptions.create(
        file=(filename, audio),
        model=s.groq_whisper_model,
    )
    return res.text or ""
