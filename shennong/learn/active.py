"""Active learning: rank corpus documents by expected information gain.

The corpus is large and uneven.  A document is valuable to the *next* learning round when
it (a) contains vocabulary the structured schemas do not yet cover, (b) mentions many
drug names, and (c) contains drug names whose resolution is uncertain.  The score is a
transparent product of those three signals — no model, no training, no hidden weights.

Output is a ranked list with the per-signal breakdown, so a curator can audit why a
document was picked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shennong.config import CorpusPaths
from shennong.extract.extract import load_corpus
from shennong.extract.lexicons import Lexicons, build_lexicons
from shennong.normalize import tokenize


@dataclass
class RankedDocument:
    doc_id: str
    source_id: str
    title: str
    year: int
    lang: str
    information_gain: float
    novelty: float
    drug_density: float
    resolution_uncertainty: float
    n_tokens: int

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "title": self.title,
            "year": self.year,
            "lang": self.lang,
            "information_gain": round(self.information_gain, 6),
            "signals": {
                "novelty": round(self.novelty, 4),
                "drug_density": round(self.drug_density, 4),
                "resolution_uncertainty": round(self.resolution_uncertainty, 4),
            },
            "n_tokens": self.n_tokens,
        }


def _structured_vocabulary(paths: CorpusPaths) -> set[str]:
    """Vocabulary already covered by the structured schemas (indications, properties)."""
    import csv

    vocab: set[str] = set()
    for name in ("uses.csv", "properties.csv", "ayurveda_properties.csv", "processing.csv"):
        path = paths.structured_dir / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                for value in row.values():
                    if value:
                        vocab.update(tokenize(str(value)))
    return vocab


def rank_documents(
    paths: CorpusPaths | None = None,
    *,
    limit: int = 50,
    lex: Lexicons | None = None,
) -> list[RankedDocument]:
    """Rank documents by expected information gain (highest first)."""
    paths = (paths or CorpusPaths.resolve()).require()
    lex = lex or build_lexicons(paths)
    vocab = _structured_vocabulary(paths)
    surfaces = sorted({entry.surface for entry in lex.drugs if entry.surface}, key=len, reverse=True)
    uncertain = {
        entry.surface
        for entry in lex.drugs
        if entry.confidence < 0.9
    }
    docs = load_corpus(paths.corpus_jsonl)
    ranked: list[RankedDocument] = []
    for doc in docs:
        text = doc.get("text", "")
        tokens = tokenize(text)
        if not tokens:
            continue
        novel = sum(1 for token in tokens if token not in vocab) / len(tokens)
        hits = [surface for surface in surfaces if surface in text]
        drug_density = min(1.0, len(hits) / max(1, len(tokens) / 120.0))
        ambiguity = len([h for h in hits if h in uncertain]) / max(1, len(hits)) if hits else 0.0
        # transparent product; log-scaling keeps long documents from dominating
        information_gain = novel * (0.2 + drug_density) * (0.3 + ambiguity) * math.log1p(len(tokens)) / 10.0
        ranked.append(
            RankedDocument(
                doc_id=str(doc.get("id", "")),
                source_id=str(doc.get("source_id", "")),
                title=str(doc.get("title", "")),
                year=int(doc.get("year", 0) or 0),
                lang=str(doc.get("lang", "")),
                information_gain=information_gain,
                novelty=novel,
                drug_density=drug_density,
                resolution_uncertainty=ambiguity,
                n_tokens=len(tokens),
            )
        )
    ranked.sort(key=lambda item: item.information_gain, reverse=True)
    return ranked[:limit]


def active_learning_batch(
    paths: CorpusPaths | None = None, *, limit: int = 50
) -> list[dict]:
    """Serialisable batch for the learning loop."""
    return [item.to_dict() for item in rank_documents(paths, limit=limit)]
