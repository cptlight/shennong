"""Longest-match multi-pattern scanning over normalised text.

A tiny character trie is used instead of a regex alternation so that:

* matches are found greedily by longest surface (甘草 wins over 甘);
* overlapping/adjacent drug names in unsegmented Chinese are found (半夏, 貝母 …);
* a match on alphabetic scripts is only accepted at a token boundary, so "ginseng"
  does not match inside "ginsengs" spuriously (though plurals are handled by folding).

The text passed in MUST be the output of :func:`shennong.normalize.normalise_offsets`,
which is length-preserving, so match indices are valid offsets into the original text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class Match:
    surface: str
    start: int
    end: int
    canonical: str
    confidence: float

    @property
    def span(self) -> tuple[int, int]:
        return self.start, self.end


class Trie:
    """Minimal character trie for longest-match scanning."""

    _END = "\x00"

    def __init__(self, patterns: Mapping[str, tuple[str, float]] | None = None) -> None:
        self.root: dict = {}
        self.count = 0
        if patterns:
            for surface, payload in patterns.items():
                self.add(surface, payload)

    def add(self, surface: str, payload: tuple[str, float]) -> None:
        if not surface:
            return
        node = self.root
        for ch in surface:
            node = node.setdefault(ch, {})
        node[self._END] = (surface, payload)
        self.count += 1

    def match_at(self, text: str, i: int) -> tuple[int, str, tuple[str, float]] | None:
        """Longest match starting exactly at position ``i`` (or ``None``)."""
        node = self.root
        best: tuple[int, str, tuple[str, float]] | None = None
        j = i
        n = len(text)
        while j < n and text[j] in node:
            node = node[text[j]]
            j += 1
            if self._END in node:
                surface, payload = node[self._END]
                best = (j, surface, payload)
        return best

    def find_all(self, text: str, *, boundary: bool = False) -> list[tuple[int, int, str, tuple[str, float]]]:
        """Greedy left-to-right, longest-match, non-overlapping scan."""
        out: list[tuple[int, int, str, tuple[str, float]]] = []
        i, n = 0, len(text)
        while i < n:
            hit = self.match_at(text, i)
            if hit is None:
                i += 1
                continue
            end, surface, payload = hit
            if boundary and not _is_boundary(text, i, end):
                i += 1
                continue
            out.append((i, end, surface, payload))
            i = end
        return out


def _is_boundary(text: str, start: int, end: int) -> bool:
    """Whether a match sits on token boundaries (for alphabetic surfaces)."""
    if start > 0 and _is_wordish(text[start - 1]) and _is_wordish(text[start]):
        return False
    if end < len(text) and _is_wordish(text[end]) and _is_wordish(text[end - 1]):
        return False
    return True


def _is_wordish(ch: str) -> bool:
    return ch.isalnum() and not ("\u4e00" <= ch <= "\u9fff")


def build_drug_trie(entries: Iterable) -> Trie:
    trie = Trie()
    for entry in entries:
        trie.add(entry.surface, (entry.canonical, entry.confidence))
    return trie


def scan_drugs(trie: Trie, text: str) -> list[Match]:
    """Find drug mentions; CJK matches need no boundary, Latin matches do."""
    out: list[Match] = []
    for start, end, surface, (canonical, conf) in trie.find_all(text, boundary=False):
        cjk = any("\u4e00" <= ch <= "\u9fff" for ch in surface)
        if not cjk and not _is_boundary(text, start, end):
            continue
        out.append(Match(surface, start, end, canonical, conf))
    return out


def scan_terms(terms: Mapping[str, str], text: str) -> list[Match]:
    """Scan a simple surface→canonical mapping with longest-first semantics."""
    trie = Trie()
    for surface, canonical in terms.items():
        trie.add(surface, (canonical, 1.0))
    out: list[Match] = []
    for start, end, surface, (canonical, conf) in trie.find_all(text, boundary=False):
        cjk = any("\u4e00" <= ch <= "\u9fff" for ch in surface)
        if not cjk and not _is_boundary(text, start, end):
            continue
        out.append(Match(surface, start, end, canonical, conf))
    return out
