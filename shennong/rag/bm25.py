"""Pure-python BM25 retrieval over corpus passages.

Chinese is indexed as unigrams **and** bigrams (no word segmenter available), IAST and
English are tokenised as words after diacritic folding.  BM25 parameters are deliberately
conservative (``k1=1.5``, ``b=0.75``); the eval harness ablates them in the learning loop.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from shennong.normalize import normalise, tokenize

_EN_STOPWORDS = frozenset(
    "a an and are as at be by did do does for from had has have how in is it its of on "
    "or that the their there these this to was were what when which who why with".split()
)


def _is_cjk(token: str) -> bool:
    return len(token) == 1 and "\u4e00" <= token <= "\u9fff"


def index_tokens(text: str) -> list[str]:
    """Tokens for indexing: word tokens plus CJK unigram+bigram."""
    tokens = tokenize(text)
    out: list[str] = []
    for i, token in enumerate(tokens):
        if token in _EN_STOPWORDS:
            continue
        out.append(token)
        if _is_cjk(token) and i + 1 < len(tokens) and _is_cjk(tokens[i + 1]):
            out.append(token + tokens[i + 1])
    return out


def query_tokens(text: str) -> list[str]:
    tokens = [t for t in tokenize(text) if t not in _EN_STOPWORDS]
    out: list[str] = []
    for i, token in enumerate(tokens):
        out.append(token)
        if _is_cjk(token) and i + 1 < len(tokens) and _is_cjk(tokens[i + 1]):
            out.append(token + tokens[i + 1])
    return out


@dataclass
class Document:
    id: str
    text: str
    meta: dict


@dataclass
class Hit:
    doc: Document
    score: float
    matched_terms: int


class BM25Index:
    """Okapi BM25 with an inverted index."""

    def __init__(self, documents: Sequence[Document], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self.doc_tokens: list[list[str]] = [index_tokens(d.text) for d in self.documents]
        self.doc_len = [len(toks) for toks in self.doc_tokens]
        self.avg_len = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.term_freqs: list[dict[str, int]] = []
        self.df: dict[str, int] = {}
        for toks in self.doc_tokens:
            tf: dict[str, int] = {}
            for tok in toks:
                tf[tok] = tf.get(tok, 0) + 1
            self.term_freqs.append(tf)
            for term in tf:
                self.df[term] = self.df.get(term, 0) + 1
        n = len(self.documents)
        self.idf = {
            term: math.log(1.0 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in self.df.items()
        }

    def search(self, query: str, k: int = 5) -> list[Hit]:
        q_tokens = query_tokens(query)
        if not q_tokens or not self.documents:
            return []
        unique = list(dict.fromkeys(q_tokens))
        scores = [0.0] * len(self.documents)
        matched = [0] * len(self.documents)
        for term in unique:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in enumerate(self.term_freqs):
                freq = tf.get(term, 0)
                if not freq:
                    continue
                norm = self.k1 * (1.0 - self.b + self.b * self.doc_len[i] / max(1e-9, self.avg_len))
                scores[i] += idf * (freq * (self.k1 + 1.0)) / (freq + norm)
                matched[i] += 1
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [
            Hit(self.documents[i], round(scores[i], 4), matched[i])
            for i in order
            if scores[i] > 0.0
        ]


def build_index(passages: Iterable[dict]) -> BM25Index:
    documents = []
    for passage in passages:
        documents.append(
            Document(
                id=str(passage.get("id", "")),
                text=str(passage.get("text", "")),
                meta={
                    "source_id": passage.get("source_id", ""),
                    "title": passage.get("title", ""),
                    "year": passage.get("year", 0),
                    "tier": passage.get("tier", 0),
                    "licence": passage.get("licence", ""),
                },
            )
        )
    return BM25Index(documents)


_SENTENCE_RE = re.compile(r"[^。；！？;.\n]+")


def best_sentence(text: str, query: str) -> tuple[str, int, int, float]:
    """Return the sentence in ``text`` that best matches the query, with offsets."""
    q = set(query_tokens(query))
    if not q:
        return text[:200], 0, min(200, len(text)), 0.0
    best = (text[:200], 0, min(200, len(text)), 0.0)
    for match in _SENTENCE_RE.finditer(text):
        sentence = match.group(0)
        if not sentence.strip():
            continue
        toks = set(query_tokens(sentence))
        overlap = len(q & toks)
        coverage = overlap / len(q)
        if coverage > best[3]:
            best = (sentence, match.start(), match.end(), coverage)
    return best


def coverage(text: str, query: str) -> float:
    q = set(query_tokens(query))
    if not q:
        return 0.0
    toks = set(query_tokens(text))
    return len(q & toks) / len(q)
