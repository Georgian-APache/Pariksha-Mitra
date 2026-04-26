"""Server-Sent Events for live agent trace.

GET /stream/agent-trace/{run_id} streams JSON events of shape
``{agent, headline, detail, payload, timestamp}`` until the run completes.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator import bus

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/agent-trace/{run_id}")
async def agent_trace(request: Request, run_id: str) -> EventSourceResponse:
    queue = bus.subscribe(run_id)

    async def gen() -> AsyncIterator[dict]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    step = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                if step is None:
                    yield {"event": "done", "data": "{}"}
                    break
                yield {
                    "event": "step",
                    "data": json.dumps(step.model_dump()),
                }
        finally:
            return

    return EventSourceResponse(gen(), ping=15)
