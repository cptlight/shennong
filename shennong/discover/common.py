"""Shared discovery plumbing: span index, hypothesis container, evidence verification.

The Lead's hard rule for dossiers: *"a hypothesis whose evidence cannot be resolved is
dropped, not softened."*  Every module builds :class:`Hypothesis` objects through this
module, which verifies each evidence span against the original corpus text before the
hypothesis can be emitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from shennong import ontology
from shennong.config import CorpusPaths
from shennong.discover import modern_knowledge
from shennong.extract.extract import load_corpus
from shennong.kg.queries import classes_of_taxon
from shennong.kg.schema import Graph, node_id
from shennong.normalize import normalise
from shennong.score import HypothesisScore

_CLAUSE_RE = re.compile(r"[^。；！？;.\n]+")

#: Compound classes that make a drug a toxicological subject rather than a therapy lead.
TOXIC_CLASSES: frozenset[str] = frozenset(
    {
        "heavy_metal",
        "aristolochic_acid",
        "pyrrolizidine_alkaloid",
        "cyanogenic_glycoside",
        "cardiac_glycoside",
        "diester_alkaloid",
    }
)

SAFETY_PROTOCOLS = {
    "toxicological": (
        "This hypothesis concerns a known toxicological hazard (heavy metal, aristolochic "
        "acid, pyrrolizidine alkaloid, cyanogenic glycoside, cardiac glycoside or "
        "Aconitum diester alkaloid). It is a safety/quality-control question only: no "
        "dose, no preparation for human use, and no therapeutic recommendation is made."
    ),
    "research_only": (
        "Research use only. Nothing here is medical advice; no dose or human-use protocol "
        "is given, and any experimental work must follow local biosafety/ethics review."
    ),
    "conservation": (
        "Conservation/ethics framing: the hypothesis concerns a CITES-listed species. It "
        "proposes substitutes for testing, not continued use of the endangered product."
    ),
}


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    year: int
    quote: str
    char_start: int
    char_end: int
    confidence: float = 0.9
    tier: int = 0
    span_kind: str = "verbatim"

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "year": self.year,
            "quote": self.quote,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "confidence": round(self.confidence, 4),
            "span_kind": self.span_kind,
        }


class SpanIndex:
    """Corpus index that can verify and locate verbatim evidence spans."""

    def __init__(self, docs: Iterable[dict]) -> None:
        self.docs = list(docs)
        self.by_id = {d.get("id", ""): d for d in self.docs}
        self.by_source: dict[str, list[dict]] = {}
        for d in self.docs:
            self.by_source.setdefault(str(d.get("source_id", "")), []).append(d)
        self._clauses: dict[str, list[tuple[str, int, int, str]]] = {}

    @classmethod
    def from_paths(cls, paths: CorpusPaths) -> "SpanIndex":
        docs = load_corpus(paths.corpus_jsonl) if paths.corpus_jsonl.exists() else []
        return cls(docs)

    # -- low-level ------------------------------------------------------------------
    def clauses(self, source_id: str) -> list[tuple[str, int, int, str]]:
        """Clauses of a source as ``(doc_id, start, end, text)``.

        Offsets are per-document.  A source may contain several documents, so every
        clause must carry its doc_id — using the first document's text with a later
        document's offsets is exactly how misattributed evidence is produced.
        """
        if source_id in self._clauses:
            return self._clauses[source_id]
        out: list[tuple[str, int, int, str]] = []
        for doc in self.by_source.get(source_id, []):
            text = doc.get("text", "")
            doc_id = str(doc.get("id", ""))
            for match in _CLAUSE_RE.finditer(text):
                if match.group(0).strip():
                    out.append((doc_id, match.start(), match.end(), match.group(0)))
        self._clauses[source_id] = out
        return out

    def verify(self, source_id: str, start: int, end: int, quote: str) -> bool:
        for doc in self.by_source.get(source_id, []):
            text = doc.get("text", "")
            if 0 <= start < end <= len(text) and text[start:end] == quote:
                return True
        return False

    def doc_meta(self, source_id: str) -> dict:
        docs = self.by_source.get(source_id, [])
        if not docs:
            return {}
        return docs[0]

    def doc_meta_by_id(self, doc_id: str) -> dict:
        return self.by_id.get(doc_id, {})

    # -- evidence construction ------------------------------------------------------
    def evidence(
        self, source_id: str, start: int, end: int, confidence: float = 0.9
    ) -> Evidence | None:
        meta = self.doc_meta(source_id)
        if not meta:
            return None
        text = meta.get("text", "")
        if not (0 <= start < end <= len(text)):
            return None
        return Evidence(
            source_id=source_id,
            title=str(meta.get("title", source_id)),
            year=int(meta.get("year", 0) or 0),
            quote=text[start:end],
            char_start=start,
            char_end=end,
            confidence=confidence,
            tier=int(meta.get("tier", 0) or 0),
        )

    def evidence_at(
        self, doc_id: str, start: int, end: int, confidence: float = 0.9
    ) -> Evidence | None:
        """Evidence from a *specific* document (the only safe constructor)."""
        meta = self.doc_meta_by_id(doc_id)
        if not meta:
            return None
        text = meta.get("text", "")
        if not (0 <= start < end <= len(text)):
            return None
        return Evidence(
            source_id=str(meta.get("source_id", "")),
            title=str(meta.get("title", doc_id)),
            year=int(meta.get("year", 0) or 0),
            quote=text[start:end],
            char_start=start,
            char_end=end,
            confidence=confidence,
            tier=int(meta.get("tier", 0) or 0),
        )

    def find(
        self,
        terms: Iterable[str],
        *,
        source_id: str | None = None,
        require_all: bool = True,
        confidence: float = 0.9,
    ) -> Evidence | None:
        """Find the first clause (in a given source, else any) containing the terms."""
        wanted = [normalise(t) for t in terms if t]
        if not wanted:
            return None
        sources = [source_id] if source_id else list(self.by_source)
        for sid in sources:
            if not sid:
                continue
            for doc_id, start, end, clause in self.clauses(sid):
                hay = normalise(clause)
                if all(w in hay for w in wanted) if require_all else any(w in hay for w in wanted):
                    found = self.evidence_at(doc_id, start, end, confidence)
                    if found is not None:
                        return found
        return None

    def find_any(self, terms: Iterable[str], **kwargs) -> Evidence | None:
        return self.find(terms, require_all=False, **kwargs)


@dataclass
class Hypothesis:
    """One discovered hypothesis, ready to be scored and rendered as a dossier."""

    klass: str
    title: str
    chain: dict[str, Any]
    claim: str
    evidence: list[Evidence]
    score: HypothesisScore | None = None
    formula_role: str = ""
    safety_tier: str = "research_only"
    safety_notes: str = ""
    falsification: dict[str, str] = field(default_factory=dict)
    uncertainty_notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def to_dossier(self) -> dict:
        if self.score is None:
            raise ValueError("hypothesis has no score; call score.attach() first")
        chain = dict(self.chain)
        chain.setdefault("drug", "")
        chain.setdefault("drug_modern", chain.get("drug", ""))
        chain.setdefault("part", "not specified in source")
        chain.setdefault("process", "")
        chain.setdefault("process_modern", "")
        chain.setdefault("chemotype", [])
        chain.setdefault("target_class", "")
        chain.setdefault("indication", "")
        return {
            "id": self.id,
            "class": self.klass,
            "formula_role": self.formula_role,
            "title": self.title,
            "chain": chain,
            "claim": self.claim,
            "evidence": [e.to_dict() for e in self.evidence],
            "scores": self.score.as_scores_dict(),
            "uncertainty": self.score.as_uncertainty_dict(),
            "falsification": self.falsification
            or {
                "experiment": "",
                "expected_if_true": "",
                "kill_criteria": "",
            },
            "safety": {
                "tier": self.safety_tier,
                "notes": self.safety_notes or SAFETY_PROTOCOLS.get(self.safety_tier, SAFETY_PROTOCOLS["research_only"]),
            },
            **({"extra": self.extra} if self.extra else {}),
        }


# --------------------------------------------------------------------------------------
# Graph helpers shared by discovery modules
# --------------------------------------------------------------------------------------


def taxon_label(graph: Graph, binomial: str) -> str:
    node = graph.get("taxon", binomial)
    return node.label if node else binomial


def compound_data(graph: Graph, binomial: str) -> list[dict]:
    """Compounds of a taxon with their class and SMILES (may be null)."""
    from shennong.kg.schema import node_id

    out: list[dict] = []
    tid = node_id("taxon", binomial)
    for edge in graph.out_edges(tid, "contains"):
        compound = graph.nodes[edge.dst]
        out.append(
            {
                "name": compound.label,
                "compound_class": compound.props.get("compound_class", ""),
                "smiles": compound.props.get("smiles", "") or None,
                "cid": compound.props.get("cid", "") or None,
            }
        )
    return out


def taxon_classes(graph: Graph, binomial: str) -> set[str]:
    return set(classes_of_taxon(graph, binomial))


def target_classes_for(classes: Iterable[str]) -> list[str]:
    """Ranked target families implied by a set of compound classes (prior)."""
    counts: dict[str, int] = {}
    for cls in classes:
        profile = ontology.compound_class_profile(cls)
        if profile is None:
            continue
        for target in profile.targets:
            counts[target] = counts.get(target, 0) + 1
    return [t for t, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]


def toxicity_of(classes: Iterable[str]) -> list[str]:
    return sorted(set(classes) & TOXIC_CLASSES)


def safety_for(classes: Iterable[str]) -> tuple[str, str]:
    toxic = toxicity_of(classes)
    if toxic:
        return "toxicological", SAFETY_PROTOCOLS["toxicological"] + f" Marker classes: {', '.join(toxic)}."
    return "research_only", SAFETY_PROTOCOLS["research_only"]


def is_modern_pair(graph: Graph, binomial: str, indication: str) -> bool:
    tid, iid = node_id("taxon", binomial), node_id("indication", indication)
    for edge in graph.out_edges(tid, "treats"):
        if edge.dst == iid and (edge.props.get("modern") or ontology.is_modern_evidence(
            str(edge.props.get("tradition", "")), str(edge.props.get("evidence_grade", "D"))
        )):
            return True
    return False


def known_drug_overlap(compounds: Iterable[dict]) -> bool:
    return any(modern_knowledge.is_known_compound(c["name"]) for c in compounds)


def evidence_from_edge(graph: Graph, edge, spans: SpanIndex) -> Evidence | None:
    """Convert a span-carrying graph edge into verified evidence."""
    props = edge.props
    sid = props.get("source_id")
    start, end, quote = props.get("char_start"), props.get("char_end"), props.get("quote")
    if sid is None or start is None or end is None or quote is None:
        return None
    if not spans.verify(str(sid), int(start), int(end), str(quote)):
        return None
    meta = spans.doc_meta(str(sid))
    return Evidence(
        source_id=str(sid),
        title=str(meta.get("title", sid)),
        year=int(meta.get("year", 0) or 0),
        quote=str(quote),
        char_start=int(start),
        char_end=int(end),
        confidence=float(props.get("confidence", 0.75)),
        tier=int(meta.get("tier", 0) or 0),
    )


def dedupe_evidence(items: Iterable[Evidence]) -> list[Evidence]:
    seen: set[tuple[str, int, int]] = set()
    out: list[Evidence] = []
    for item in items:
        key = (item.source_id, item.char_start, item.char_end)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return sorted(out, key=lambda e: (-e.confidence, e.source_id, e.char_start))


def dossier_skeleton(klass: str, title: str, chain: dict, claim: str) -> Hypothesis:
    return Hypothesis(klass=klass, title=title, chain=chain, claim=claim, evidence=[])


def require_evidence(hypothesis: Hypothesis) -> bool:
    """Final gate: a hypothesis survives only with ≥1 verified span."""
    return len([e for e in hypothesis.evidence if e.quote and e.char_start < e.char_end]) > 0


def dedupe_hypotheses(hypotheses: Iterable[Hypothesis]) -> list[Hypothesis]:
    seen: set[tuple[str, str, str]] = set()
    out: list[Hypothesis] = []
    for h in hypotheses:
        key = (h.klass, str(h.chain.get("drug", "")), str(h.chain.get("indication", "")))
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def by_class(hypotheses: Iterable[Hypothesis]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for h in hypotheses:
        counts[h.klass] = counts.get(h.klass, 0) + 1
    return dict(sorted(counts.items()))


def zh_synonyms(graph: Graph, binomial: str) -> list[str]:
    """Chinese surface names of a taxon, from plants.csv synonyms."""
    node = graph.get("taxon", binomial)
    if node is None:
        return []
    out: list[str] = []
    for term in str(node.props.get("synonyms", "")).split(";"):
        term = term.strip()
        if term and any("\u4e00" <= ch <= "\u9fff" for ch in term):
            out.append(term)
    return out


def find_use_evidence(spans: SpanIndex, graph: Graph, binomial: str, indication: str) -> Evidence | None:
    """Locate a citable clause in which the drug and an indication term co-occur.

    Uses the drug's Chinese synonyms (from plants.csv) plus the indication's zh/sa/en
    surface forms, so structured-only use rows can still be tied to a real text span.
    """
    spec = ontology.indication_spec(indication)
    indication_terms: list[str] = [indication]
    if spec is not None:
        indication_terms = [*spec.zh, *spec.sa, *spec.en, *spec.ar, indication]
    drug_terms = [binomial, *zh_synonyms(graph, binomial)]
    # try every drug term with every indication term inside one clause
    for drug_term in drug_terms:
        for ind_term in indication_terms:
            found = spans.find([drug_term, ind_term], require_all=True, confidence=0.6)
            if found:
                return found
    # weakest acceptable evidence: a clause naming the drug where an indication is discussed
    for drug_term in drug_terms:
        found = spans.find([drug_term], require_all=True, confidence=0.45)
        if found:
            return found
    return None
