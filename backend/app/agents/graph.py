"""LangGraph 4+1 wiring.

Flow (high level):

  start
    |
    v
  Analyst  -- if should_replan=True -->  Planner
    |                                      |
    +<-------------------------------------+
    |
    v
  Companion -> END

The Orchestrator is implicit: LangGraph itself routes the StudentState dict.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.analyst import analyst_node
from app.agents.companion import companion_node
from app.agents.planner import planner_node
from app.agents.state import StudentState
from app.config import APIKeys


class GraphState(TypedDict, total=False):
    student: StudentState
    keys: APIKeys


async def _analyst(s: GraphState) -> GraphState:
    student = await analyst_node(s["student"], s["keys"])
    return {"student": student}


async def _planner(s: GraphState) -> GraphState:
    student = await planner_node(s["student"], s["keys"])
    return {"student": student}


async def _companion(s: GraphState) -> GraphState:
    student = await companion_node(s["student"], s["keys"])
    return {"student": student}


def _route_after_analyst(s: GraphState) -> str:
    student = s["student"]
    return "planner" if getattr(student, "_should_replan", False) else "companion"


def _route_after_planner(_s: GraphState) -> str:
    return "companion"


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("analyst", _analyst)
    g.add_node("planner", _planner)
    g.add_node("companion", _companion)

    g.set_entry_point("analyst")
    g.add_conditional_edges("analyst", _route_after_analyst, {
        "planner": "planner",
        "companion": "companion",
    })
    g.add_edge("planner", "companion")
    g.add_edge("companion", END)
    return g.compile()


# --- Diagnostic-only sub-graph (Planner without Analyst) ---


async def _planner_only(s: GraphState) -> GraphState:
    student = await planner_node(s["student"], s["keys"])
    return {"student": student}


def build_diagnostic_graph():
    g = StateGraph(GraphState)
    g.add_node("analyst", _analyst)
    g.add_node("planner", _planner)
    g.add_node("companion", _companion)
    g.set_entry_point("analyst")
    g.add_edge("analyst", "planner")
    g.add_edge("planner", "companion")
    g.add_edge("companion", END)
    return g.compile()
