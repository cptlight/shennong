"""Grounded, refusal-first question answering.

``answer(question)`` — the RAG entry point used by the CLI and the Workbench — retrieves
from the corpus with BM25 and only then answers.  The contract is:

* **Answer only from a retrieved span.**  The response quotes the best-matching corpus
  sentence verbatim, with source id, title, year, licence and character offsets.
* **Refuse when unsupported.**  If the safety screen blocks the question, or if the best
  passage does not cover enough of the query, the function returns ``refused=True`` with
  an explicit reason and no answer.  A weak answer is never emitted.
* **No generation.**  There is no language model in this path, so there is nothing that
  could hallucinate.  The trade-off — it cannot paraphrase — is stated in the result.

The refusal is the scientifically important behaviour: for the hallucination benchmark,
N questions with no corpus answer must produce N refusals, and the report says so.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shennong.config import CorpusPaths
from shennong.rag.bm25 import BM25Index, best_sentence, build_index, coverage
from shennong.safety.screen import DISCLAIMER, screen

#: Minimum BM25 score and query-token coverage for a grounded answer.
MIN_SCORE = 1.0
MIN_COVERAGE = 0.34

_INDEX_CACHE: dict[tuple[str, int, int], BM25Index] = {}
_PASSAGE_CACHE: dict[tuple[str, int, int], list[dict]] = {}


def load_passages(corpus_dir: str | Path | None = None) -> list[dict]:
    """Load corpus passages, cached by (path, mtime, size)."""
    paths = CorpusPaths.resolve(corpus_dir)
    path = paths.corpus_jsonl
    if not path.exists():
        return []
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key in _PASSAGE_CACHE:
        return _PASSAGE_CACHE[key]
    passages: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                passages.append(json.loads(line))
    _PASSAGE_CACHE[key] = passages
    return passages


def get_index(corpus_dir: str | Path | None = None) -> BM25Index:
    paths = CorpusPaths.resolve(corpus_dir)
    path = paths.corpus_jsonl
    if not path.exists():
        return BM25Index([])
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key not in _INDEX_CACHE:
        _INDEX_CACHE[key] = build_index(load_passages(corpus_dir))
    return _INDEX_CACHE[key]


def _refusal(question: str, reason: str, *, safety: dict | None = None, retrieval: list | None = None) -> dict:
    return {
        "query": question,
        "answer": f"I cannot answer this from the corpus. {reason}",
        "citations": [],
        "refused": True,
        "refusal_reason": reason,
        "confidence": 0.0,
        "safety": safety or screen(question).to_dict(),
        "retrieval": retrieval or [],
        "disclaimer": DISCLAIMER,
    }


def answer(
    question: str,
    corpus_dir: str | Path | None = None,
    k: int = 5,
    *,
    index: BM25Index | None = None,
) -> dict[str, Any]:
    """Retrieve-then-answer with an explicit refusal path."""
    question = (question or "").strip()
    if not question:
        return _refusal(question, "The question is empty.")

    # 1) safety gate — a blocked question never reaches retrieval
    safety = screen(question)
    if not safety.allowed:
        return _refusal(
            question,
            "This request is blocked by the safety policy: "
            + "; ".join(r["detail"] for r in safety.reasons),
            safety=safety.to_dict(),
        )

    # 2) retrieval
    idx = index or get_index(corpus_dir)
    if not idx.documents:
        return _refusal(question, "No corpus is available to retrieve from.", safety=safety.to_dict())
    hits = idx.search(question, k=k)
    if not hits:
        return _refusal(question, "No passage in the corpus shares vocabulary with the question.", safety=safety.to_dict())

    retrieval = [
        {
            "passage_id": hit.doc.id,
            "source_id": hit.doc.meta.get("source_id", ""),
            "title": hit.doc.meta.get("title", ""),
            "year": hit.doc.meta.get("year", 0),
            "score": hit.score,
            "matched_terms": hit.matched_terms,
        }
        for hit in hits
    ]
    best = hits[0]
    cov = coverage(best.doc.text, question)
    if best.score < MIN_SCORE or cov < MIN_COVERAGE:
        return _refusal(
            question,
            (
                f"Retrieval found no passage that supports an answer "
                f"(best BM25 score {best.score:.2f}, query-term coverage {cov:.2f}; "
                f"thresholds {MIN_SCORE:.1f}/{MIN_COVERAGE:.2f})."
            ),
            safety=safety.to_dict(),
            retrieval=retrieval,
        )

    # 3) grounded answer: a verbatim sentence from the best passage
    sentence, start, end, sentence_cov = best_sentence(best.doc.text, question)
    if sentence_cov < MIN_COVERAGE:
        return _refusal(
            question,
            (
                f"The best passage scores {best.score:.2f} but no single sentence supports the "
                f"question (sentence coverage {sentence_cov:.2f})."
            ),
            safety=safety.to_dict(),
            retrieval=retrieval,
        )
    title = best.doc.meta.get("title", best.doc.id)
    year = best.doc.meta.get("year", "")
    answer_text = f"According to {title} ({year}): “{sentence.strip()}”"
    citations = [
        {
            "source_id": best.doc.meta.get("source_id", ""),
            "title": title,
            "year": year,
            "tier": best.doc.meta.get("tier", 0),
            "licence": best.doc.meta.get("licence", ""),
            "passage_id": best.doc.id,
            "span": sentence.strip(),
            "char_start": start,
            "char_end": end,
            "score": best.score,
        }
    ]
    for hit in hits[1:]:
        if hit.score < 0.5 * best.score:
            continue
        sent, s0, s1, _ = best_sentence(hit.doc.text, question)
        citations.append(
            {
                "source_id": hit.doc.meta.get("source_id", ""),
                "title": hit.doc.meta.get("title", ""),
                "year": hit.doc.meta.get("year", 0),
                "tier": hit.doc.meta.get("tier", 0),
                "licence": hit.doc.meta.get("licence", ""),
                "passage_id": hit.doc.id,
                "span": sent.strip(),
                "char_start": s0,
                "char_end": s1,
                "score": hit.score,
            }
        )
    return {
        "query": question,
        "answer": answer_text,
        "citations": citations,
        "refused": False,
        "refusal_reason": "",
        "confidence": round(min(1.0, 0.5 * cov + 0.5 * min(1.0, best.score / 5.0)), 4),
        "safety": safety.to_dict(),
        "retrieval": retrieval,
        "disclaimer": DISCLAIMER,
    }


#: The name the Workbench expects.
grounded_answer = answer
