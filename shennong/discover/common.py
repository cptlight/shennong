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
from shennong.normalize import normalise, normalise_offsets
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
        self._clauses: dict[str, list[tuple[str, int, int, str, str]]] = {}
        self._verify_cache: dict[tuple[str, int, int], bool] = {}
        self._term_cache: dict[str, list[int]] = {}
        self._corpus_norm: str | None = None
        self._doc_ranges: list[tuple[int, int, dict]] = []

    @classmethod
    def from_paths(cls, paths: CorpusPaths) -> "SpanIndex":
        docs = load_corpus(paths.corpus_jsonl) if paths.corpus_jsonl.exists() else []
        return cls(docs)

    # -- low-level ------------------------------------------------------------------
    def _build_corpus_index(self) -> None:
        """One length-preserving normalisation of the whole corpus.

        ``normalise_offsets`` preserves character positions, so a global string lets us
        locate terms with ``str.find`` (C speed) instead of re-normalising every clause on
        every call — the difference between minutes and seconds on a 45M-char corpus.
        """
        from shennong.normalize import normalise_offsets

        if self._corpus_norm is not None:
            return
        pieces: list[str] = []
        offset = 0
        for doc in self.docs:
            text = doc.get("text", "")
            norm = normalise_offsets(text).casefold()
            self._doc_ranges.append((offset, offset + len(norm), doc))
            pieces.append(norm)
            offset += len(norm)
        self._corpus_norm = "".join(pieces)

    def _doc_at(self, position: int) -> tuple[dict, int] | None:
        """Return ``(doc, local_position)`` for a global corpus position."""
        import bisect

        starts = [r[0] for r in self._doc_ranges]
        idx = bisect.bisect_right(starts, position) - 1
        if idx < 0 or idx >= len(self._doc_ranges):
            return None
        start, end, doc = self._doc_ranges[idx]
        if not (start <= position < end):
            return None
        return doc, position - start

    def _term_positions(self, term: str, limit: int = 5000) -> list[int]:
        cache_key = f"{term}\x00{limit}"
        cached = self._term_cache.get(cache_key)
        if cached is not None:
            return cached
        self._build_corpus_index()
        assert self._corpus_norm is not None
        needle = normalise_offsets(term).casefold() if term else ""
        if not needle:
            return []
        out: list[int] = []
        start = 0
        assert self._corpus_norm is not None
        while len(out) < limit:
            idx = self._corpus_norm.find(needle, start)
            if idx < 0:
                break
            out.append(idx)
            start = idx + 1
        self._term_cache[cache_key] = out
        return out

    def _clause_bounds(self, doc: dict, position: int) -> tuple[int, int]:
        text = doc.get("text", "")
        start = position
        while start > 0 and text[start - 1] not in "。；！？;.\n":
            start -= 1
        end = position
        n = len(text)
        while end < n and text[end] not in "。；！？;.\n":
            end += 1
        if end < n:
            end += 1
        return start, end

    def clauses(self, source_id: str) -> list[tuple[str, int, int, str, str]]:
        """Clauses of a source as ``(doc_id, start, end, text)``.

        Offsets are per-document.  A source may contain several documents, so every
        clause must carry its doc_id — using the first document's text with a later
        document's offsets is exactly how misattributed evidence is produced.
        """
        if source_id in self._clauses:
            return self._clauses[source_id]
        out: list[tuple[str, int, int, str, str]] = []
        for doc in self.by_source.get(source_id, []):
            text = doc.get("text", "")
            doc_id = str(doc.get("id", ""))
            for match in _CLAUSE_RE.finditer(text):
                if match.group(0).strip():
                    out.append((doc_id, match.start(), match.end(), match.group(0), normalise(match.group(0))))
        self._clauses[source_id] = out
        return out

    def verify(self, source_id: str, start: int, end: int, quote: str) -> bool:
        cache_key = (source_id, start, end)
        cached = self._verify_cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._verify_uncached(source_id, start, end, quote)
        self._verify_cache[cache_key] = result
        return result

    def _verify_uncached(self, source_id: str, start: int, end: int, quote: str) -> bool:
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
        """Find a clause containing the terms, using the global term index."""
        wanted = [term for term in terms if term]
        if not wanted:
            return None
        wanted_norm = [normalise_offsets(term).casefold() for term in wanted]
        # iterate the rarest term's occurrences; verify all terms in the clause
        occurrences = sorted(
            ((len(self._term_positions(term, limit=400)), term) for term in wanted),
        )
        _, anchor = occurrences[0]
        for position in self._term_positions(anchor, limit=400):
            located = self._doc_at(position)
            if located is None:
                continue
            doc, local = located
            if source_id and str(doc.get("source_id", "")) != source_id:
                continue
            start, end = self._clause_bounds(doc, local)
            clause = doc.get("text", "")[start:end]
            hay = normalise(clause)
            ok = all(term in hay for term in wanted_norm) if require_all else any(term in hay for term in wanted_norm)
            if ok:
                found = self.evidence_at(str(doc.get("id", "")), start, end, confidence)
                if found is not None:
                    return found
        return None

    def find_any(self, terms: Iterable[str], **kwargs) -> Evidence | None:
        return self.find(terms, require_all=False, **kwargs)

    def find_use_context(
        self,
        drug_terms: Iterable[str],
        indication_terms: Iterable[str],
        *,
        window: int = 180,
        confidence: float = 0.7,
    ) -> Evidence | None:
        """Locate a drug-entry window in which the drug and an indication co-occur.

        Classical entries put the drug name in one clause and its indications in the next
        (``大黃，味苦寒。主下瘀血…``), so clause-level matching is too narrow: we scan a
        forward window from each drug-name occurrence.  The global term index makes this
        O(occurrences), not O(corpus).
        """
        indication_norms = [normalise(term) for term in indication_terms if term]
        if not indication_norms:
            return None
        for drug_term in drug_terms:
            for position in self._term_positions(drug_term, limit=400):
                located = self._doc_at(position)
                if located is None:
                    continue
                doc, local = located
                text = doc.get("text", "")
                end = min(len(text), local + window)
                segment = text[local:end]
                segment_norm = normalise(segment)
                if any(ind in segment_norm for ind in indication_norms):
                    cut = segment.rfind("。")
                    if cut > 0:
                        end = local + cut + 1
                    found = self.evidence_at(str(doc.get("id", "")), local, end, confidence)
                    if found is not None:
                        return found
        return None


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
            or {"experiment": "", "expected_if_true": "", "kill_criteria": ""},
            "safety": {
                "tier": self.safety_tier,
                "notes": self.safety_notes
                or SAFETY_PROTOCOLS.get(self.safety_tier, SAFETY_PROTOCOLS["research_only"]),
            },
            **({"extra": self.extra} if self.extra else {}),
        }


def taxon_label(graph: Graph, binomial: str) -> str:
    node = graph.get("taxon", binomial)
    return node.label if node else binomial


def compound_data(graph: Graph, binomial: str) -> list[dict]:
    """Compounds of a taxon with their class and SMILES (may be null)."""
    from shennong.kg.schema import node_id as _nid

    out: list[dict] = []
    tid = _nid("taxon", binomial)
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
    counts: dict[str, int] = {}
    for cls in classes:
        profile = ontology.compound_class_profile(cls)
        if profile is None:
            continue
        for target in profile.targets:
            counts[target] = counts.get(target, 0) + 1
    return [target for target, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]


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
        if edge.dst == iid and (
            edge.props.get("modern")
            or ontology.is_modern_evidence(
                str(edge.props.get("tradition", "")), str(edge.props.get("evidence_grade", "D"))
            )
        ):
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
    """Final gate: a hypothesis survives only with >=1 verified span."""
    return len([e for e in hypothesis.evidence if e.quote and e.char_start < e.char_end]) > 0


def dedupe_hypotheses(hypotheses: Iterable[Hypothesis]) -> list[Hypothesis]:
    seen: set[tuple[str, str, str]] = set()
    out: list[Hypothesis] = []
    for hypothesis in hypotheses:
        key = (
            hypothesis.klass,
            str(hypothesis.chain.get("drug", "")),
            str(hypothesis.chain.get("indication", "")),
            # incompatibility pairs share a fixed indication string, so the title (which
            # names both partners) must participate in the dedupe key
            hypothesis.title if hypothesis.klass == "incompatibility" else "",
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(hypothesis)
    return out


def by_class(hypotheses: Iterable[Hypothesis]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for hypothesis in hypotheses:
        counts[hypothesis.klass] = counts.get(hypothesis.klass, 0) + 1
    return dict(sorted(counts.items()))


def zh_synonyms(graph: Graph, binomial: str) -> list[str]:
    """Chinese/other native-script surface names of a taxon.

    Two sources: the ``synonyms`` column (which in the real corpus holds Latin authority
    names) and the graph's ``drug_name --alias_of--> taxon`` edges built from
    ``lexicon_drugs.json`` (which hold the actual classical Chinese names).
    """
    node = graph.get("taxon", binomial)
    out: list[str] = []
    if node is not None:
        for term in str(node.props.get("synonyms", "")).split(";"):
            term = term.strip()
            if term and any("\u4e00" <= ch <= "\u9fff" for ch in term):
                out.append(term)
        taxon_id = node.id
        for edge in graph.in_edges(taxon_id, "alias_of"):
            label = graph.nodes[edge.src].label
            if label and any("\u4e00" <= ch <= "\u9fff" for ch in label):
                out.append(label)
    seen: set[str] = set()
    deduped: list[str] = []
    for term in out:
        if term not in seen:
            seen.add(term)
            deduped.append(term)
    return deduped


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
    return spans.find_use_context(drug_terms, indication_terms, confidence=0.7)
