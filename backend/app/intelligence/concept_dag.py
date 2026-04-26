"""NetworkX wrapper over the concept dependency JSON."""

from __future__ import annotations

import json
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import networkx as nx

from app.config import DATA_DIR


class ConceptDAG:
    """A typed wrapper around a ``networkx.DiGraph`` of exam concepts."""

    def __init__(self, exam: str, payload: dict) -> None:
        self.exam = exam
        self.subjects: dict[str, float] = payload.get("subjects", {})
        self.graph = nx.DiGraph()
        for c in payload.get("concepts", []):
            self.graph.add_node(
                c["id"],
                name=c["name"],
                subject=c["subject"],
                weight=float(c.get("weight", 0.0)),
            )
        for c in payload.get("concepts", []):
            for prereq in c.get("prereqs", []):
                if prereq in self.graph:
                    # edge: prereq -> child  (data flows from prerequisite to dependent)
                    self.graph.add_edge(prereq, c["id"])

    # ---- lookups ----

    def __contains__(self, node: str) -> bool:
        return node in self.graph

    def info(self, node: str) -> dict:
        d = self.graph.nodes.get(node, {})
        return {"id": node, **d}

    def all_concepts(self) -> list[dict]:
        return [{"id": n, **self.graph.nodes[n]} for n in self.graph.nodes]

    def by_subject(self, subject: str) -> list[str]:
        return [n for n, d in self.graph.nodes(data=True) if d.get("subject") == subject]

    def prereqs_of(self, node: str) -> list[str]:
        if node not in self.graph:
            return []
        return list(self.graph.predecessors(node))

    def dependents_of(self, node: str) -> list[str]:
        if node not in self.graph:
            return []
        return list(self.graph.successors(node))

    def ancestors(self, node: str) -> list[str]:
        if node not in self.graph:
            return []
        seen: set[str] = set()
        q = deque([node])
        out: list[str] = []
        while q:
            cur = q.popleft()
            for p in self.graph.predecessors(cur):
                if p in seen:
                    continue
                seen.add(p)
                out.append(p)
                q.append(p)
        return out

    def cytoscape(self) -> dict:
        nodes = [
            {
                "data": {
                    "id": n,
                    "label": d.get("name", n),
                    "subject": d.get("subject"),
                    "weight": d.get("weight", 0.0),
                }
            }
            for n, d in self.graph.nodes(data=True)
        ]
        edges = [
            {"data": {"id": f"{u}->{v}", "source": u, "target": v}}
            for u, v in self.graph.edges
        ]
        return {"nodes": nodes, "edges": edges, "subjects": self.subjects, "exam": self.exam}


@lru_cache(maxsize=4)
def get_dag(exam: str = "JEE_MAIN") -> ConceptDAG:
    fname = "jee_dag.json" if exam.upper() == "JEE_MAIN" else "neet_dag.json"
    path = Path(DATA_DIR) / fname
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ConceptDAG(exam.upper(), payload)


def weak_prerequisites(
    dag: ConceptDAG,
    target: str,
    mastery: dict[str, float],
    threshold: float = 0.6,
) -> list[str]:
    """Return prereq concepts whose mastery is below ``threshold`` (BFS up the DAG)."""

    out: list[str] = []
    for node in dag.ancestors(target):
        if mastery.get(node, 0.0) < threshold:
            out.append(node)
    return out


def coverage(dag: ConceptDAG, mastery: dict[str, float], threshold: float = 0.4) -> float:
    """Fraction of weighted concepts with mastery >= threshold."""

    total_w = 0.0
    seen_w = 0.0
    for n, d in dag.graph.nodes(data=True):
        w = float(d.get("weight", 0.0)) or 0.01
        total_w += w
        if mastery.get(n, 0.0) >= threshold:
            seen_w += w
    return seen_w / total_w if total_w else 0.0


def weighted_mastery(dag: ConceptDAG, mastery: dict[str, float]) -> float:
    total_w = 0.0
    weighted = 0.0
    for n, d in dag.graph.nodes(data=True):
        w = float(d.get("weight", 0.0)) or 0.01
        total_w += w
        weighted += w * float(mastery.get(n, 0.0))
    return weighted / total_w if total_w else 0.0


def topo_concepts(dag: ConceptDAG, of: Iterable[str] | None = None) -> list[str]:
    """Topological order of concepts (or a subset)."""

    order = list(nx.topological_sort(dag.graph))
    if of is None:
        return order
    keep = set(of)
    return [n for n in order if n in keep]
