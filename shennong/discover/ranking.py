"""Ranking and dossier assembly — the 使 Shǐ stage.

Runs all discovery classes, verifies every evidence span, scores, deduplicates, guarantees
at least one dossier per class where the corpus supports it, and emits the Lead's frozen
dossier schema.

A hypothesis whose evidence cannot be resolved to a literal corpus span is **dropped**
and counted in ``n_dropped_unverifiable``; it is never softened or emitted with an empty
evidence list.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from shennong.config import CorpusPaths
from shennong.discover import (
    drug_candidate,
    endangered,
    formula_role,
    incompatibility,
    name_collision,
    processing,
    understudied,
)
from shennong.discover.common import (
    Hypothesis,
    SpanIndex,
    by_class,
    dedupe_hypotheses,
    require_evidence,
)
from shennong.kg.build import build_graph
from shennong.kg.schema import Graph

#: The order in which classes are guaranteed representation.
CLASS_ORDER: tuple[str, ...] = (
    "incompatibility",
    "processing",
    "drug_candidate",
    "name_collision",
    "formula_role",
    "understudied",
    "endangered",
)

_MODULES = (
    incompatibility,
    processing,
    name_collision,
    formula_role,
    understudied,
    endangered,
)


@dataclass
class DiscoveryRun:
    graph: Graph
    spans: SpanIndex
    hypotheses: list[Hypothesis]
    candidates: list[dict]
    candidate_diagnostics: dict
    warnings: list[str]
    n_dropped_unverifiable: int = 0

    @property
    def available_by_class(self) -> dict[str, int]:
        return by_class(self.hypotheses)

    @property
    def mean_novelty(self) -> float:
        if not self.hypotheses:
            return 0.0
        return float(sum(h.score.novelty.value for h in self.hypotheses if h.score) / len(self.hypotheses))


def run_discovery(paths: CorpusPaths | None = None) -> DiscoveryRun:
    """Generate every hypothesis and candidate, with span verification."""
    paths = (paths or CorpusPaths.resolve()).require()
    graph = build_graph(paths)
    spans = SpanIndex.from_paths(paths)
    warnings: list[str] = []
    hypotheses: list[Hypothesis] = []
    for module in _MODULES:
        try:
            found = module.discover(graph, spans)
        except Exception as exc:  # a broken class must not take down the pipeline
            warnings.append(f"{module.__name__}: {type(exc).__name__}: {exc}")
            continue
        hypotheses.extend(found)
    try:
        candidates, diagnostics = drug_candidate.discover_candidates(graph, spans, paths)
        drug_candidate.write_candidates(candidates, diagnostics, fixture=paths.is_fixture())
        hypotheses.extend(drug_candidate.candidate_hypotheses(candidates))
    except Exception as exc:
        warnings.append(f"drug_candidate: {type(exc).__name__}: {exc}")
        candidates, diagnostics = [], {"error": str(exc)}
    total = len(hypotheses)
    hypotheses = [h for h in hypotheses if require_evidence(h)]
    dropped = total - len(hypotheses)
    hypotheses = dedupe_hypotheses(hypotheses)
    hypotheses.sort(key=lambda h: h.score.composite if h.score else 0.0, reverse=True)
    if dropped:
        warnings.append(f"{dropped} hypothesis(es) dropped because evidence could not be resolved to a span")
    return DiscoveryRun(graph, spans, hypotheses, candidates, diagnostics, warnings,
                        n_dropped_unverifiable=dropped)


def select_dossiers(run: DiscoveryRun, n: int = 12, klass: str | None = None) -> list[Hypothesis]:
    """Select ``n`` dossiers, guaranteeing one per available class unless filtered."""
    if klass:
        pool = [h for h in run.hypotheses if h.klass == klass]
        return pool[: max(0, n)]
    selected: list[Hypothesis] = []
    selected_ids: set[int] = set()
    for cls in CLASS_ORDER:
        pool = [h for h in run.hypotheses if h.klass == cls]
        if pool:
            selected.append(pool[0])
            selected_ids.add(id(pool[0]))
    for hypothesis in run.hypotheses:
        if len(selected) >= n:
            break
        if id(hypothesis) in selected_ids:
            continue
        selected.append(hypothesis)
        selected_ids.add(id(hypothesis))
    selected = selected[:n]
    selected.sort(key=lambda h: h.score.composite if h.score else 0.0, reverse=True)
    for i, hypothesis in enumerate(selected, start=1):
        hypothesis.id = f"H-2026-{i:04d}"
    return selected


def generate_dossiers(
    paths: CorpusPaths | None = None,
    *,
    n: int = 12,
    klass: str | None = None,
    corpus_dir: str | Path | None = None,
) -> tuple[list[dict], dict]:
    """CLI-facing entry point: ranked dossier dicts plus run metadata."""
    corpus = CorpusPaths.resolve(corpus_dir) if corpus_dir else (paths or CorpusPaths.resolve())
    run = run_discovery(corpus)
    selected = select_dossiers(run, n=n, klass=klass)
    dossiers = [h.to_dossier() for h in selected]
    meta = {
        "n_available": len(run.hypotheses),
        "by_class": run.available_by_class,
        "n_dropped_unverifiable": run.n_dropped_unverifiable,
        "candidates": len(run.candidates),
        "warnings": run.warnings,
    }
    return dossiers, meta


def all_dossiers(paths: CorpusPaths | None = None) -> tuple[list[dict], DiscoveryRun]:
    """Every emitted hypothesis as a dossier (used by the eval harness)."""
    run = run_discovery(paths)
    for i, hypothesis in enumerate(run.hypotheses, start=1):
        hypothesis.id = f"H-2026-{i:04d}"
    return [h.to_dossier() for h in run.hypotheses], run
