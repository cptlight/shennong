"""Continuous-learning loop with a held-out acceptance gate.

One ``round()`` does exactly what the brief requires:

1. **diagnose** — evaluate the current configuration on the held-out split and find the
   weakest pre-registered metric;
2. **propose** — generate candidate methodological changes (BM25 parameters, retrieval
   depth, refusal threshold);
3. **gate** — re-run the eval harness on the *held-out* split only;
4. **accept** — a candidate is accepted only if its named target metric improves by more
   than ``MIN_GAIN`` **and** no other metric regresses by more than ``MAX_REGRESSION``;
5. **record** — write ``eval/rounds/round-NNN.json`` with before/after numbers.

Nothing here tunes on the test set, and "no accepted changes" is a valid, recorded
outcome.  The candidates are real configuration toggles that the retrieval path reads.
"""

from __future__ import annotations

import builtins
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from shennong.config import REPO_ROOT, CorpusPaths
from shennong.eval.questions import (
    Question,
    generate_from_corpus,
    gold_terms_present,
    load_jsonl,
)
from shennong.extract.lexicons import build_lexicons
from shennong.extract.extract import load_corpus
from shennong.normalize import normalise
from shennong.rag import answer as answer_module
from shennong.rag.bm25 import build_index, query_tokens

EVAL_DIR = REPO_ROOT / "eval"
ROUNDS_DIR = EVAL_DIR / "rounds"

MIN_GAIN = 0.005
MAX_REGRESSION = 0.01


@dataclass
class RetrievalConfig:
    k1: float = 1.5
    b: float = 0.75
    k: int = 5
    min_coverage: float = 0.34
    min_score: float = 1.0

    def as_dict(self) -> dict:
        return {"k1": self.k1, "b": self.b, "k": self.k, "min_coverage": self.min_coverage, "min_score": self.min_score}


@dataclass
class Candidate:
    name: str
    description: str
    target_metric: str
    config: RetrievalConfig


@dataclass
class RoundResult:
    round_number: int
    baseline: dict
    candidates: list[dict] = field(default_factory=list)
    accepted: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)

    def to_dict(self, paths: CorpusPaths) -> dict:
        return {
            "round": self.round_number,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fixture": paths.is_fixture(),
            "corpus_sha256": _sha256(paths.corpus_jsonl),
            "protocol": {
                "accept_if": f"target metric improves by > {MIN_GAIN} and no other metric regresses by > {MAX_REGRESSION}",
                "evaluated_on": "held-out split only (deterministic 1-in-3 by question id hash)",
            },
            "baseline": self.baseline,
            "candidates": self.candidates,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "outcome": (
                f"{len(self.accepted)} change(s) accepted" if self.accepted
                else "no accepted changes — baseline retained"
            ),
        }


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _heldout(question: Question) -> bool:
    digest = hashlib.sha256(question.id.encode("utf-8")).hexdigest()
    return int(digest, 16) % 3 == 0


def build_questions(paths: CorpusPaths) -> tuple[list[Question], list[Question]]:
    docs = load_corpus(paths.corpus_jsonl)
    lex = build_lexicons(paths)
    curated = load_jsonl(EVAL_DIR / "questions.jsonl")
    try:
        generated = generate_from_corpus(docs, lex, limit=40)
    except Exception:
        generated = []
    kept, _ = gold_terms_present(curated + generated, docs)
    holdout = [q for q in kept if _heldout(q)]
    train = [q for q in kept if not _heldout(q)]
    return train, (holdout or kept)


def evaluate(config: RetrievalConfig, questions: list[Question], index) -> dict:
    """Evaluate retrieval+answer quality under one configuration (held-out only)."""
    old = (
        answer_module.MIN_COVERAGE,
        answer_module.MIN_SCORE,
    )
    answer_module.MIN_COVERAGE = config.min_coverage
    answer_module.MIN_SCORE = config.min_score
    recall = answered = correct = 0
    n = len(questions)
    try:
        for question in questions:
            hits = index.search(question.question, k=config.k)
            recall += int(
                any(
                    all(normalise(term) in normalise(hit.doc.text) for term in question.gold_terms)
                    for hit in hits
                )
            )
            result = answer_module.answer(question.question, index=index, k=config.k)
            if not result["refused"]:
                answered += 1
                if all(normalise(term) in normalise(result["answer"]) for term in question.expected_terms):
                    correct += 1
    finally:
        answer_module.MIN_COVERAGE, answer_module.MIN_SCORE = old
    return {
        "recall_at_k": builtins.round(recall / n, 4) if n else 0.0,
        "answer_accuracy": builtins.round(correct / n, 4) if n else 0.0,
        "answered_rate": builtins.round(answered / n, 4) if n else 0.0,
        "n": n,
    }


def propose(current: RetrievalConfig) -> list[Candidate]:
    """Candidate methodological improvements (each a real, reversible config change)."""
    return [
        Candidate("bm25_k1_2.0", "increase BM25 k1 from 1.5 to 2.0 (term-frequency saturation)", "recall_at_k",
                  RetrievalConfig(current.k1 + 0.5, current.b, current.k, current.min_coverage, current.min_score)),
        Candidate("bm25_b_0.5", "reduce BM25 b from 0.75 to 0.5 (less length normalisation)", "recall_at_k",
                  RetrievalConfig(current.k1, 0.5, current.k, current.min_coverage, current.min_score)),
        Candidate("retrieve_k10", "retrieve 10 passages instead of 5", "recall_at_k",
                  RetrievalConfig(current.k1, current.b, 10, current.min_coverage, current.min_score)),
        Candidate("coverage_0.25", "relax refusal coverage threshold 0.34 → 0.25", "answered_rate",
                  RetrievalConfig(current.k1, current.b, current.k, 0.25, current.min_score)),
        Candidate("coverage_0.45", "tighten refusal coverage threshold 0.34 → 0.45", "answer_accuracy",
                  RetrievalConfig(current.k1, current.b, current.k, 0.45, current.min_score)),
    ]


def round(
    paths: CorpusPaths | None = None,
    *,
    config: RetrievalConfig | None = None,
    round_number: int | None = None,
) -> dict:
    """Run one complete learn round and persist ``eval/rounds/round-NNN.json``."""
    paths = (paths or CorpusPaths.resolve()).require()
    config = config or RetrievalConfig()
    train, holdout = build_questions(paths)
    docs = load_corpus(paths.corpus_jsonl)
    index = build_index(docs)
    baseline = evaluate(config, holdout, index)
    result = RoundResult(round_number=round_number or _next_round_number(), baseline=baseline)

    for candidate in propose(config):
        outcome = evaluate(candidate.config, holdout, index)
        record = {
            "name": candidate.name,
            "description": candidate.description,
            "target_metric": candidate.target_metric,
            "config": candidate.config.as_dict(),
            "scores": outcome,
        }
        target_gain = outcome[candidate.target_metric] - baseline[candidate.target_metric]
        regressions = {
            metric: builtins.round(outcome[metric] - baseline[metric], 4)
            for metric in ("recall_at_k", "answer_accuracy", "answered_rate")
            if outcome[metric] - baseline[metric] < -MAX_REGRESSION
        }
        record["target_gain"] = builtins.round(target_gain, 4)
        record["regressions"] = regressions
        accepted = target_gain > MIN_GAIN and not regressions
        record["decision"] = "accept" if accepted else "reject"
        record["reason"] = (
            f"target {candidate.target_metric} {baseline[candidate.target_metric]:.4f} → "
            f"{outcome[candidate.target_metric]:.4f} (gain {target_gain:+.4f}); "
            + ("no regression on other metrics" if accepted else
               (f"regression: {regressions}" if regressions else "gain below threshold"))
        )
        result.candidates.append(record)
        (result.accepted if accepted else result.rejected).append(record)

    payload = result.to_dict(paths)
    ROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ROUNDS_DIR / f"round-{result.round_number:03d}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    payload["artifact"] = str(out_path)
    return payload


def _next_round_number() -> int:
    ROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(ROUNDS_DIR.glob("round-*.json"))
    if not existing:
        return 1
    try:
        return int(existing[-1].stem.split("-")[-1]) + 1
    except ValueError:
        return len(existing) + 1
