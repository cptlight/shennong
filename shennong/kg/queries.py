"""Read-only knowledge-graph queries used by discovery, RAG and the CLI.

All traversal is plain BFS/adjacency over :class:`shennong.kg.schema.Graph`; no graph
library.  The functions here are deliberately small and pure so they can be unit-tested
against fixture graphs.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Iterable, Iterator

from shennong.kg.schema import Edge, Graph, Node, node_id
from shennong.ontology import EvidenceGrade, is_modern_evidence


def neighbours(
    g: Graph, nid: str, rel: str | None = None, depth: int = 1
) -> list[tuple[Node, int, str]]:
    """Breadth-first neighbours as ``(node, distance, first_rel)``."""
    seen = {nid}
    out: list[tuple[Node, int, str]] = []
    frontier = deque([(nid, 0, "")])
    while frontier:
        current, dist, first_rel = frontier.popleft()
        if dist >= depth:
            continue
        for edge in g.out_edges(current, rel) + g.in_edges(current, rel):
            other = edge.dst if edge.src == current else edge.src
            if other in seen:
                continue
            seen.add(other)
            rel_label = edge.rel
            out.append((g.nodes[other], dist + 1, first_rel or rel_label))
            frontier.append((other, dist + 1, first_rel or rel_label))
    return out


def shortest_path(g: Graph, src: str, dst: str, max_depth: int = 5) -> list[tuple[str, str]] | None:
    """Shortest undirected path as ``[(node_id, rel_used), …]`` or ``None``."""
    if src not in g.nodes or dst not in g.nodes:
        return None
    prev: dict[str, tuple[str, str] | None] = {src: None}
    frontier = deque([src])
    while frontier:
        current = frontier.popleft()
        if current == dst:
            break
        depth = 0
        cur = current
        while prev[cur] is not None:
            depth += 1
            cur = prev[cur][0]  # type: ignore[index]
        if depth >= max_depth:
            continue
        for edge in g.out_edges(current) + g.in_edges(current):
            other = edge.dst if edge.src == current else edge.src
            if other not in prev:
                prev[other] = (current, edge.rel)
                frontier.append(other)
    if dst not in prev:
        return None
    path: list[tuple[str, str]] = []
    node = dst
    while prev[node] is not None:
        parent, rel = prev[node]  # type: ignore[misc]
        path.append((node, rel))
        node = parent
    path.append((src, ""))
    return list(reversed(path))


def edges_between(g: Graph, a: str, b: str, rel: str | None = None) -> list[Edge]:
    """All edges connecting two nodes in either direction."""
    out = [e for e in g.out_edges(a, rel) if e.dst == b]
    out += [e for e in g.in_edges(a, rel) if e.src == b]
    return out


def evidence_rollup(g: Graph, binomial: str) -> dict[str, dict]:
    """Per-indication evidence summary for one taxon.

    Returns ``{indication: {"edges": [...], "n": int, "best_grade": str,
    "modern": bool, "traditions": [...], "sources": [...]}}``.
    """
    tid = node_id("taxon", binomial)
    rollup: dict[str, dict] = {}
    for edge in g.out_edges(tid, "treats"):
        ind = g.nodes[edge.dst].label
        entry = rollup.setdefault(
            ind, {"edges": [], "n": 0, "best_grade": "D", "modern": False,
                  "traditions": set(), "sources": set()}
        )
        entry["edges"].append(edge)
        entry["n"] += 1
        grade = str(edge.props.get("evidence_grade", "D"))
        if _grade_rank(grade) > _grade_rank(entry["best_grade"]):
            entry["best_grade"] = grade
        tradition = str(edge.props.get("tradition", "unknown"))
        entry["traditions"].add(tradition)
        if edge.props.get("source_id"):
            entry["sources"].add(str(edge.props["source_id"]))
        if edge.props.get("modern") or is_modern_evidence(tradition, grade):
            entry["modern"] = True
    for entry in rollup.values():
        entry["traditions"] = sorted(entry["traditions"])
        entry["sources"] = sorted(entry["sources"])
        entry["n_traditions"] = len(entry["traditions"])
    return rollup


def _grade_rank(grade: str) -> int:
    order = {EvidenceGrade.D.value: 0, EvidenceGrade.C.value: 1, EvidenceGrade.B.value: 2, EvidenceGrade.A.value: 3}
    return order.get(str(grade).upper(), -1)


def classes_of_taxon(g: Graph, binomial: str) -> dict[str, dict]:
    """Compound classes present in a taxon, with the compounds supporting each."""
    tid = node_id("taxon", binomial)
    classes: dict[str, dict] = {}
    for cedge in g.out_edges(tid, "contains"):
        compound = g.nodes[cedge.dst]
        for medge in g.out_edges(compound.id, "member_of"):
            cls = g.nodes[medge.dst].label
            entry = classes.setdefault(cls, {"compounds": [], "profile": g.nodes[medge.dst].props})
            entry["compounds"].append(compound.label)
    return classes


def taxa_with_use(g: Graph, indication: str) -> list[Node]:
    iid = node_id("indication", indication)
    return g.neighbours(iid, "treats", direction="in") if iid in g.nodes else []


def taxa_with_class(g: Graph, compound_class: str) -> set[str]:
    cid = node_id("compound_class", compound_class)
    out: set[str] = set()
    if cid not in g.nodes:
        return out
    for edge in g.in_edges(cid, "member_of"):
        for ted in g.in_edges(edge.src, "contains"):
            out.add(g.nodes[ted.src].label)
    return out


def co_occurring_taxa(g: Graph, rel: str = "treats", min_shared: int = 1) -> list[tuple[str, str, int]]:
    """Pairs of taxa sharing ≥ ``min_shared`` targets of ``rel``."""
    by_target: dict[str, set[str]] = {}
    for edge in g.edges:
        if edge.rel != rel:
            continue
        by_target.setdefault(edge.dst, set()).add(edge.src)
    shared: Counter[tuple[str, str]] = Counter()
    for taxa in by_target.values():
        ordered = sorted(taxa)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1 :]:
                shared[(a, b)] += 1
    return [(a, b, n) for (a, b), n in shared.items() if n >= min_shared]


def trace_span(g: Graph, edge: Edge, corpus_index: dict[str, dict]) -> bool:
    """Verify an edge's quote is the literal span of its source text."""
    sid = edge.props.get("source_id")
    start = edge.props.get("char_start")
    end = edge.props.get("char_end")
    quote = edge.props.get("quote")
    if sid is None or start is None or end is None or quote is None:
        return False
    doc = corpus_index.get(str(sid))
    if doc is None:
        return False
    text = doc.get("text", "")
    return text[int(start) : int(end)] == str(quote)


def resolve_edges(g: Graph, rel: str | None = None) -> Iterator[Edge]:
    for edge in g.edges:
        if rel is None or edge.rel == rel:
            yield edge


@dataclass(frozen=True)
class PathStep:
    node_id: str
    label: str
    type: str
    rel: str


def describe_path(g: Graph, path: list[tuple[str, str]]) -> list[PathStep]:
    """Turn :func:`shortest_path` output into labelled steps for dossiers."""
    steps: list[PathStep] = []
    for nid, rel in path:
        node = g.nodes[nid]
        steps.append(PathStep(nid, node.label, node.type, rel))
    return steps
