"""Span-faithful entity and relation extraction.

The extractor produces :class:`Observation` records that always carry:

* the ``source_id`` of the document;
* ``char_start`` / ``char_end`` offsets into the **original** text;
* the verbatim ``quote`` (``text[char_start:char_end]``);
* a confidence derived from lexicon confidence × pairing ambiguity.

That triple is what makes every downstream claim citable, and what the CLI verifies
before printing a hypothesis (see ``shennong.discover.common``).

Extraction is deliberately rule/lexicon based, not statistical: it is auditable,
CPU-only, needs no model, and cannot hallucinate a span.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from shennong.extract.lexicons import Lexicons, build_lexicons
from shennong.extract.match import Match, build_drug_trie, scan_drugs, scan_terms
from shennong.normalize import normalise_offsets

_CLAUSE_RE = re.compile(r"[^。；！？;.\n]+")

#: Roles are attributed when a role marker occurs shortly after a drug mention.
_ROLE_WINDOW = 8


@dataclass(frozen=True)
class Entity:
    start: int
    end: int
    surface: str        # verbatim text
    normalized: str
    kind: str           # drug | indication | process | role | formula | incompat_marker
    canonical: str
    confidence: float


@dataclass(frozen=True)
class Observation:
    """A single extracted, citable relation or mention."""

    kind: str           # treats | processed_by | ingredient_of | incompatible | role | mentions
    source_id: str
    char_start: int
    char_end: int
    quote: str
    payload: dict
    confidence: float

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "source_id": self.source_id,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "quote": self.quote,
            "payload": self.payload,
            "confidence": self.confidence,
        }


@dataclass
class DocExtraction:
    doc_id: str
    source_id: str
    title: str
    year: int
    tradition: str
    lang: str
    text: str
    entities: list[Entity] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)


@dataclass
class ExtractionResult:
    docs: list[DocExtraction] = field(default_factory=list)

    @property
    def observations(self) -> list[Observation]:
        return [o for d in self.docs for o in d.observations]

    def counts(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for o in self.observations:
            c[o.kind] = c.get(o.kind, 0) + 1
        return dict(sorted(c.items()))


def extract_document(doc: dict, lex: Lexicons) -> DocExtraction:
    """Extract entities and observations from one corpus.jsonl record."""
    text = doc.get("text", "")
    out = DocExtraction(
        doc_id=doc.get("id", ""),
        source_id=doc.get("source_id", ""),
        title=doc.get("title", ""),
        year=int(doc.get("year", 0) or 0),
        tradition=doc.get("tradition", "unknown"),
        lang=doc.get("lang", "en"),
        text=text,
    )
    norm = normalise_offsets(text)

    drugs = scan_drugs(_drug_trie(lex), norm)
    indications = scan_terms(lex.indications, norm)
    processes = scan_terms(lex.processes, norm)
    roles = scan_terms(lex.roles, norm)
    formulas = scan_terms(lex.formula_names, norm)
    incomp = scan_terms(lex.incompat_markers, norm)

    # -- entities -------------------------------------------------------------------
    for group, kind in (
        (drugs, "drug"),
        (indications, "indication"),
        (processes, "process"),
        (roles, "role"),
        (formulas, "formula"),
        (incomp, "incompat_marker"),
    ):
        for m in group:
            out.entities.append(
                Entity(m.start, m.end, text[m.start : m.end], m.surface, kind, m.canonical, m.confidence)
            )

    # whether this document is a rule-list document (raises incompatibility confidence)
    rule_doc = "十八反" in norm or "十九畏" in norm or "viruddha" in norm

    # -- clause-level relations -----------------------------------------------------
    for clause_start, clause_end in _clauses(norm):
        clause_text = text[clause_start:clause_end]
        c_drugs = [m for m in drugs if clause_start <= m.start < clause_end]
        c_inds = [m for m in indications if clause_start <= m.start < clause_end]
        c_procs = [m for m in processes if clause_start <= m.start < clause_end]
        c_roles = [m for m in roles if clause_start <= m.start < clause_end]
        c_formulas = [m for m in formulas if clause_start <= m.start < clause_end]

        # drug → indication (the core use observation)
        if c_drugs and c_inds:
            # ambiguity when several drugs share the clause
            amp = 1.0 / (len(c_drugs) ** 0.5)
            for d in c_drugs:
                for ind in c_inds:
                    out.observations.append(
                        Observation(
                            "treats", out.source_id, clause_start, clause_end, clause_text,
                            {"drug": d.canonical, "drug_surface": text[d.start:d.end],
                             "indication": ind.canonical, "tradition": out.tradition,
                             "year": out.year},
                            round(min(d.confidence, ind.confidence) * amp, 4),
                        )
                    )

        # drug → process (processing observation)
        for d in c_drugs:
            for p in c_procs:
                out.observations.append(
                    Observation(
                        "processed_by", out.source_id, clause_start, clause_end, clause_text,
                        {"drug": d.canonical, "process": p.canonical,
                         "tradition": out.tradition},
                        round(min(d.confidence, 0.9), 4),
                    )
                )

        # formula composition: a formula name in the clause ⇒ its drugs are ingredients
        if c_formulas and c_drugs:
            for f in c_formulas:
                for d in c_drugs:
                    out.observations.append(
                        Observation(
                            "ingredient_of", out.source_id, clause_start, clause_end, clause_text,
                            {"formula_id": f.canonical, "drug": d.canonical},
                            round(min(f.confidence, d.confidence) * 0.9, 4),
                        )
                    )

        # role attribution: role marker within _ROLE_WINDOW chars after a drug name
        for role in c_roles:
            prior_drugs = [d for d in c_drugs if d.end <= role.start <= d.end + _ROLE_WINDOW]
            if prior_drugs:
                d = prior_drugs[-1]
                out.observations.append(
                    Observation(
                        "role", out.source_id, clause_start, clause_end, clause_text,
                        {"drug": d.canonical, "role": role.canonical},
                        round(min(d.confidence, 0.8), 4),
                    )
                )

        # incompatibility: A 反/畏 B、C、D
        out.observations.extend(_extract_incompatibilities(out, norm, text, clause_start, clause_end, c_drugs, incomp, rule_doc))

    return out


def _extract_incompatibilities(
    out: DocExtraction,
    norm: str,
    text: str,
    clause_start: int,
    clause_end: int,
    c_drugs: list[Match],
    markers: list[Match],
    rule_doc: bool,
) -> list[Observation]:
    observations: list[Observation] = []
    # only 反 / 畏 / viruddha markers inside this clause
    c_markers = [m for m in markers if clause_start <= m.start < clause_end
                 and m.surface in {"反", "畏", "viruddha", "不相"}]
    for mi, marker in enumerate(c_markers):
        left = [d for d in c_drugs if d.end <= marker.start]
        # right-hand partners run only until the next marker in the same sentence,
        # so "硫黃畏朴硝，水銀畏砒霜" pairs (硫黃,朴硝) and (水銀,砒霜), not a cross-product
        next_start = c_markers[mi + 1].start if mi + 1 < len(c_markers) else clause_end
        right = [d for d in c_drugs if marker.end <= d.start < next_start]
        if not left or not right:
            continue
        a = left[-1]
        rule = "shiba_fan" if marker.surface == "反" else ("shijiu_wei" if marker.surface == "畏" else "viruddha")
        # If the document declares a rule system, prefer that declaration.
        if rule_doc:
            if "十八反" in norm and marker.surface == "反":
                rule = "shiba_fan"
            elif "十九畏" in norm and marker.surface == "畏":
                rule = "shijiu_wei"
        for b in right:
            observations.append(
                Observation(
                    "incompatible", out.source_id, clause_start, clause_end, text[clause_start:clause_end],
                    {"drug_a": a.canonical, "drug_b": b.canonical, "rule_system": rule,
                     "drug_a_surface": text[a.start:a.end], "drug_b_surface": text[b.start:b.end]},
                    round((0.85 if rule_doc else 0.65) * min(a.confidence, b.confidence), 4),
                )
            )
    return observations


def _clauses(text: str) -> Iterable[tuple[int, int]]:
    for m in _CLAUSE_RE.finditer(text):
        if m.group(0).strip():
            yield m.start(), m.end()


def _drug_trie(lex: Lexicons):
    cache = getattr(lex, "_trie", None)
    if cache is None:
        cache = build_drug_trie(lex.drugs)
        object.__setattr__(lex, "_trie", cache)
    return cache


def extract_corpus(docs: Sequence[dict], lex: Lexicons | None = None) -> ExtractionResult:
    lex = lex or build_lexicons()
    return ExtractionResult([extract_document(d, lex) for d in docs])


def load_corpus(path) -> list[dict]:
    import json
    from pathlib import Path

    docs: list[dict] = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs
