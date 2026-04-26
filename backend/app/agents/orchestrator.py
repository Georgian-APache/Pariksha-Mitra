"""High-level orchestration helpers + an in-memory fan-out for the SSE feed.

Routes call e.g. ``await run_diagnostic(...)`` or ``await run_post_quiz(...)``
and pass a ``run_id`` so the SSE endpoint can subscribe and stream each
``AgentStep`` as it happens.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from typing import Any

from app.agents.graph import build_diagnostic_graph, build_graph
from app.agents.state import AgentStep, StudentState
from app.config import APIKeys

log = logging.getLogger("parikshamitra.orchestrator")


# ---------------------------------------------------------------------------
# Pub/sub for SSE
# ---------------------------------------------------------------------------

class TraceBus:
    """Tiny in-process publisher: ``run_id`` -> list[asyncio.Queue]."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue[AgentStep | None]]] = defaultdict(list)
        self._buffer: dict[str, list[AgentStep]] = defaultdict(list)
        self._closed: set[str] = set()

    def subscribe(self, run_id: str) -> asyncio.Queue[AgentStep | None]:
        q: asyncio.Queue[AgentStep | None] = asyncio.Queue()
        # Replay buffered events
        for step in self._buffer.get(run_id, []):
            q.put_nowait(step)
        if run_id in self._closed:
            q.put_nowait(None)
            return q
        self._subs[run_id].append(q)
        return q

    def publish(self, run_id: str, step: AgentStep) -> None:
        self._buffer[run_id].append(step)
        for q in list(self._subs.get(run_id, [])):
            try:
                q.put_nowait(step)
            except Exception:  # noqa: BLE001
                pass

    def close(self, run_id: str) -> None:
        self._closed.add(run_id)
        for q in list(self._subs.get(run_id, [])):
            q.put_nowait(None)
        self._subs.pop(run_id, None)


bus = TraceBus()


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------


def _attach_run_id(state: StudentState, run_id: str) -> StudentState:
    state.run_id = run_id
    return state


_DIAG_GRAPH = None
_FULL_GRAPH = None


def _diag_graph():
    global _DIAG_GRAPH
    if _DIAG_GRAPH is None:
        _DIAG_GRAPH = build_diagnostic_graph()
    return _DIAG_GRAPH


def _full_graph():
    global _FULL_GRAPH
    if _FULL_GRAPH is None:
        _FULL_GRAPH = build_graph()
    return _FULL_GRAPH


async def _run(graph, state: StudentState, keys: APIKeys, run_id: str) -> StudentState:
    state = _attach_run_id(state, run_id)
    try:
        bus.publish(
            run_id,
            AgentStep(
                agent="orchestrator",
                headline="Run started",
                detail=f"intent={state.intent}",
                payload={"intent": state.intent, "user_id": state.user_id},
            ),
        )
        out = await graph.ainvoke({"student": state, "keys": keys})
        result_state: StudentState = out["student"]
        bus.publish(
            run_id,
            AgentStep(
                agent="orchestrator",
                headline="Run complete",
                detail=f"steps={len(result_state.trace)}",
                payload={"steps": len(result_state.trace)},
            ),
        )
        return result_state
    finally:
        bus.close(run_id)


async def run_diagnostic(state: StudentState, keys: APIKeys) -> tuple[StudentState, str]:
    """First-time onboarding flow: Analyst -> Planner -> Companion."""

    state.intent = "diagnostic"
    run_id = str(uuid.uuid4())
    out = await _run(_diag_graph(), state, keys, run_id)
    return out, run_id


async def run_post_quiz(state: StudentState, keys: APIKeys) -> tuple[StudentState, str]:
    """After a quiz/drill: Analyst decides, may call Planner, then Companion."""

    state.intent = "quiz_finished"
    run_id = str(uuid.uuid4())
    out = await _run(_full_graph(), state, keys, run_id)
    return out, run_id


def fresh_run_id() -> str:
    return str(uuid.uuid4())
