"""Knowledge-graph data model.

The graph is a plain adjacency structure — no networkx, no database.  Nodes carry a
``type`` from :class:`shennong.ontology.EntityType`; edges carry a ``rel`` string and a
free-form property dict (source span, tradition, evidence grade, mechanism …).  Every
edge that encodes a corpus observation stores the ``source_id`` and the character span
of the quoted text so that it can be cited.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from shennong.ontology import EntityType


@dataclass
class Node:
    id: str
    type: str
    label: str
    props: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "label": self.label, "props": self.props}


@dataclass
class Edge:
    src: str
    dst: str
    rel: str
    props: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"src": self.src, "dst": self.dst, "rel": self.rel, "props": self.props}


def node_id(kind: str | EntityType, key: str) -> str:
    """Stable, human-readable node id.  Keys are lower-cased and space→hyphen."""
    kind_value = kind.value if isinstance(kind, EntityType) else str(kind)
    slug = str(key).strip().lower().replace(" ", "-").replace("/", "-")
    return f"{kind_value}:{slug}"


class Graph:
    """A typed, weighted, provenance-carrying knowledge graph."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self._out: dict[str, list[int]] = {}
        self._in: dict[str, list[int]] = {}
        self.edges: list[Edge] = []

    # -- construction ----------------------------------------------------------------
    def add_node(
        self, kind: str | EntityType, key: str, label: str | None = None, **props: Any
    ) -> str:
        nid = node_id(kind, key)
        existing = self.nodes.get(nid)
        if existing is None:
            self.nodes[nid] = Node(nid, kind.value if isinstance(kind, EntityType) else str(kind), label or str(key), dict(props))
            self._out.setdefault(nid, [])
            self._in.setdefault(nid, [])
        elif props:
            existing.props.update(props)
            if label:
                existing.label = label
        return nid

    def add_edge(self, src: str, dst: str, rel: str, **props: Any) -> None:
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError(f"edge endpoint missing: {src} -> {dst}")
        edge = Edge(src, dst, rel, dict(props))
        idx = len(self.edges)
        self.edges.append(edge)
        self._out[src].append(idx)
        self._in[dst].append(idx)

    # -- queries ---------------------------------------------------------------------
    def out_edges(self, nid: str, rel: str | None = None) -> list[Edge]:
        return [self.edges[i] for i in self._out.get(nid, []) if rel is None or self.edges[i].rel == rel]

    def in_edges(self, nid: str, rel: str | None = None) -> list[Edge]:
        return [self.edges[i] for i in self._in.get(nid, []) if rel is None or self.edges[i].rel == rel]

    def neighbours(self, nid: str, rel: str | None = None, direction: str = "out") -> list[Node]:
        edges = self.out_edges(nid, rel) if direction == "out" else self.in_edges(nid, rel)
        other = (lambda e: e.dst) if direction == "out" else (lambda e: e.src)
        return [self.nodes[other(e)] for e in edges]

    def by_type(self, kind: str | EntityType) -> list[Node]:
        value = kind.value if isinstance(kind, EntityType) else str(kind)
        return [n for n in self.nodes.values() if n.type == value]

    def get(self, kind: str | EntityType, key: str) -> Node | None:
        return self.nodes.get(node_id(kind, key))

    def degree(self, nid: str, rel: str | None = None) -> int:
        return len(self.out_edges(nid, rel)) + len(self.in_edges(nid, rel))

    def edge_count(self, rel: str | None = None) -> int:
        return len(self.edges) if rel is None else sum(1 for e in self.edges if e.rel == rel)

    def rel_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.edges:
            counts[e.rel] = counts.get(e.rel, 0) + 1
        return dict(sorted(counts.items()))

    def type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for n in self.nodes.values():
            counts[n.type] = counts.get(n.type, 0) + 1
        return dict(sorted(counts.items()))

    # -- serialisation ---------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {"nodes": len(self.nodes), "edges": len(self.edges),
                      "types": self.type_counts(), "rels": self.rel_counts()},
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Graph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        g = cls()
        for nd in data["nodes"]:
            g.nodes[nd["id"]] = Node(nd["id"], nd["type"], nd["label"], nd.get("props", {}))
            g._out.setdefault(nd["id"], [])
            g._in.setdefault(nd["id"], [])
        for ed in data["edges"]:
            idx = len(g.edges)
            g.edges.append(Edge(ed["src"], ed["dst"], ed["rel"], ed.get("props", {})))
            g._out.setdefault(ed["src"], []).append(idx)
            g._in.setdefault(ed["dst"], []).append(idx)
        return g


def load_or_build(
    graph_path: str | Path,
    corpus_dir: str | Path | None = None,
    *,
    rebuild: bool = False,
) -> Graph:
    """Load the cached graph, building it from the corpus if absent or ``rebuild``."""
    from shennong.config import CorpusPaths
    from shennong.kg.build import build_graph

    path = Path(graph_path)
    if path.exists() and not rebuild:
        return Graph.load(path)
    corpus = CorpusPaths.resolve(corpus_dir)
    graph = build_graph(corpus)
    graph.save(path)
    return graph
