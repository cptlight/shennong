"""Benchmark question construction.

Two sources:

* **Curated** (``eval/questions.jsonl``) — hand-written, realistic questions in English,
  Chinese, Sanskrit and Arabic, with gold answer terms.
* **Generated from the corpus** — deterministic questions derived from span-verified
  extraction observations (plant→use, processing, formula composition, rule pairs).
  A generated question is "real" in the only sense that matters here: its answer exists
  verbatim in a cited corpus span.

Questions are filtered at eval time: if a gold term does not occur anywhere in the loaded
corpus (e.g. because a different corpus was supplied), the question is dropped and counted
as ``filtered_missing_gold`` rather than scored as a failure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from shennong.extract.extract import extract_corpus, load_corpus
from shennong.extract.lexicons import Lexicons, build_lexicons
from shennong.kg.schema import Graph
from shennong.normalize import normalise


@dataclass
class Question:
    id: str
    question: str
    answerable: bool
    gold_terms: list[str] = field(default_factory=list)
    expected_terms: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    kind: str = "generated"
    origin: str = "generated"


def load_jsonl(path: str | Path) -> list[Question]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[Question] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(
                Question(
                    id=str(data.get("id", "")),
                    question=str(data.get("question", "")),
                    answerable=bool(data.get("answerable", True)),
                    gold_terms=list(data.get("gold_terms", [])),
                    expected_terms=list(data.get("expected_terms", [])),
                    source_ids=list(data.get("source_ids", [])),
                    kind=str(data.get("kind", "curated")),
                    origin=str(data.get("origin", "curated")),
                )
            )
    return out


def _term_in_quote(quote: str, candidates: list[str]) -> str | None:
    hay = normalise(quote)
    for candidate in candidates:
        if normalise(candidate) and normalise(candidate) in hay:
            return candidate
    return None


def generate_from_corpus(
    docs: list[dict],
    lex: Lexicons | None = None,
    *,
    limit: int = 60,
) -> list[Question]:
    """Build deterministic questions from span-verified extraction observations."""
    lex = lex or build_lexicons()
    extraction = extract_corpus(docs, lex)
    from shennong import ontology

    questions: list[Question] = []
    seen: set[str] = set()

    def add(q: Question) -> None:
        key = normalise(q.question)
        if key in seen:
            return
        seen.add(key)
        questions.append(q)

    for doc in extraction.docs:
        for obs in doc.observations:
            quote = obs.quote
            payload = obs.payload
            if obs.kind == "treats":
                spec = ontology.indication_spec(payload.get("indication", ""))
                if spec is None:
                    continue
                term = _term_in_quote(quote, [*spec.zh, *spec.sa, *spec.en, *spec.ar])
                drug = payload.get("drug_surface", "")
                if not term or not drug:
                    continue
                add(
                    Question(
                        id=f"G-{len(questions)+1:03d}",
                        question=f"What does {doc.title} say {drug} is used for?",
                        answerable=True,
                        gold_terms=[drug],
                        expected_terms=[term],
                        source_ids=[doc.source_id],
                        kind="plant_use",
                    )
                )
            elif obs.kind == "processed_by":
                drug = payload.get("drug_surface", "")
                process = payload.get("process", "")
                semantics = ontology.ALL_PROCESSES.get(process)
                term = None
                if semantics is not None:
                    term = _term_in_quote(quote, [semantics.name_zh, semantics.name, *ontology.PROCESS_SYNONYMS])
                if not drug or not term:
                    continue
                add(
                    Question(
                        id=f"G-{len(questions)+1:03d}",
                        question=f"How is {drug} prepared according to {doc.title}?",
                        answerable=True,
                        gold_terms=[drug],
                        expected_terms=[term],
                        source_ids=[doc.source_id],
                        kind="processing",
                    )
                )
            elif obs.kind == "incompatible":
                a = payload.get("drug_a_surface", "")
                b = payload.get("drug_b_surface", "")
                if not a or not b:
                    continue
                add(
                    Question(
                        id=f"G-{len(questions)+1:03d}",
                        question=f"Which drug does {doc.title} say is incompatible with {a}?",
                        answerable=True,
                        gold_terms=[a],
                        expected_terms=[b],
                        source_ids=[doc.source_id],
                        kind="incompatibility",
                    )
                )
            elif obs.kind == "ingredient_of":
                formula_name = None
                for name in lex.formula_names:
                    if normalise(name) in normalise(quote):
                        formula_name = name
                        break
                if not formula_name:
                    continue
                drug = payload.get("drug_surface", payload.get("drug", ""))
                if not drug:
                    continue
                add(
                    Question(
                        id=f"G-{len(questions)+1:03d}",
                        question=f"Which drug is an ingredient of {formula_name} in {doc.title}?",
                        answerable=True,
                        gold_terms=[formula_name],
                        expected_terms=[drug],
                        source_ids=[doc.source_id],
                        kind="formula",
                    )
                )
            if len(questions) >= limit:
                return questions
    return questions


def gold_terms_present(questions: list[Question], docs: list[dict]) -> tuple[list[Question], list[Question]]:
    """Split into (scorable, filtered) by whether gold terms occur in the corpus at all."""
    corpus_text = "\n".join(d.get("text", "") for d in docs)
    hay = normalise(corpus_text)
    kept: list[Question] = []
    filtered: list[Question] = []
    for question in questions:
        present = all(normalise(term) in hay for term in question.gold_terms) if question.gold_terms else True
        (kept if present else filtered).append(question)
    return kept, filtered
