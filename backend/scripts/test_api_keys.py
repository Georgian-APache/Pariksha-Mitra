"""Smoke-test DEFAULT_GEMINI_API_KEY and DEFAULT_GROQ_API_KEY from backend/.env.

Run from the backend folder:
    python scripts/test_api_keys.py

Does not print secret values — only OK / error messages.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> int:
    from fastapi import HTTPException

    from app.agents.llm import gemini_text, groq_chat
    from app.config import APIKeys, get_settings

    s = get_settings()
    keys = APIKeys(gemini=s.default_gemini_api_key, groq=s.default_groq_api_key)

    print("ParikshaMitra API key smoke test (keys never printed)\n")

    # Gemini
    try:
        keys.require("gemini")
    except HTTPException:
        print("[Gemini] SKIP - DEFAULT_GEMINI_API_KEY not set in backend/.env")
    else:
        try:
            text = await gemini_text(
                keys=keys,
                prompt='Reply with exactly the word "pong" and nothing else.',
                temperature=0,
            )
            snippet = (text or "").strip().replace("\n", " ")[:80]
            print(f"[Gemini] OK — model replied: {snippet!r}")
        except Exception as e:  # noqa: BLE001
            print(f"[Gemini] FAIL — {type(e).__name__}: {e}")

    # Groq
    try:
        keys.require("groq")
    except HTTPException:
        print("[Groq]   SKIP - DEFAULT_GROQ_API_KEY not set in backend/.env")
    else:
        try:
            text = await groq_chat(
                keys=keys,
                messages=[
                    {"role": "user", "content": 'Reply with exactly the word "pong" and nothing else.'},
                ],
                temperature=0,
            )
            snippet = (text or "").strip().replace("\n", " ")[:80]
            print(f"[Groq]   OK — model replied: {snippet!r}")
        except Exception as e:  # noqa: BLE001
            print(f"[Groq]   FAIL — {type(e).__name__}: {e}")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
