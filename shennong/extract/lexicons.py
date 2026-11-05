"""Curated lexicons used by span-faithful extraction.

All surfaces are stored in their *normalised* form (see :mod:`shennong.normalize`) and
mapped to a canonical entity.  The lexicon is built from the processed-corpus contracts
(``lexicon_drugs.json``, ``plants.csv``, ``uses.csv``) plus the ontology, so it grows
automatically when ``data-curator`` lands the real corpus.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from shennong import ontology
from shennong.config import CorpusPaths
from shennong.normalize import fold_iast, fold_zh, normalise


@dataclass(frozen=True)
class DrugEntry:
    surface: str          # normalised surface form
    canonical: str        # modern binomial or canonical drug name
    lang: str
    confidence: float
    source: str = "lexicon"


@dataclass
class Lexicons:
    """All matchable vocabularies for extraction."""

    drugs: list[DrugEntry] = field(default_factory=list)
    processes: dict[str, str] = field(default_factory=dict)       # surface → process key
    indications: dict[str, str] = field(default_factory=dict)     # surface → canonical
    roles: dict[str, str] = field(default_factory=dict)           # 君/臣/佐/使 → role
    formula_names: dict[str, str] = field(default_factory=dict)   # surface → formula_id
    incompat_markers: dict[str, str] = field(default_factory=dict)  # surface → rule_system
    process_terms: dict[str, str] = field(default_factory=dict)   # surface → modern text
    warnings: list[str] = field(default_factory=list)

    # -- construction ----------------------------------------------------------------
    @classmethod
    def build(cls, paths: CorpusPaths | None = None, *, with_text: bool = True) -> "Lexicons":
        paths = paths or CorpusPaths.resolve()
        lex = cls()

        # 1. drugs: binomials + synonyms from plants.csv
        binomials: set[str] = set()
        if paths.plants_csv.exists():
            with paths.plants_csv.open(encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    binomial = (row.get("binomial") or "").strip()
                    if not binomial:
                        continue
                    binomials.add(binomial)
                    lex._add_drug(binomial, binomial, "la", 0.99, "plants.csv")
                    for syn in (row.get("synonyms") or "").split(";"):
                        syn = syn.strip()
                        if syn:
                            lex._add_drug(syn, binomial, _lang_of(syn), 0.92, "plants.csv")

        # 2. drugs: cross-era/cross-language resolution from lexicon_drugs.json
        if paths.lexicon_drugs.exists():
            try:
                data = json.loads(paths.lexicon_drugs.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                lex.warnings.append(f"lexicon_drugs.json invalid: {exc}")
                data = {}
            for entry in data.get("historical", []):
                modern = entry.get("modern")
                name = entry.get("name")
                if not modern or not name:
                    continue
                conf = float(entry.get("confidence", 0.8))
                lex._add_drug(name, modern, entry.get("lang", "und"), conf, "lexicon_drugs")
                for reading in entry.get("readings", []):
                    lex._add_drug(reading, modern, "en", conf * 0.95, "lexicon_drugs")

        # 3. indications from the ontology (zh/sa/ar/en surfaces)
        for spec in ontology.INDICATIONS.values():
            for term in (spec.indication, spec.symptom, *spec.zh, *spec.sa, *spec.ar, *spec.en):
                key = normalise(term)
                if key:
                    lex.indications.setdefault(key, spec.indication)

        # 4. indications as attested in uses.csv (the corpus's own wording)
        if with_text and paths.uses_csv.exists():
            with paths.uses_csv.open(encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    ind = (row.get("indication") or "").strip()
                    modern_key = (row.get("indication_modern") or "").strip()
                    canon = ontology.canonical_indication(modern_key) or ontology.canonical_indication(ind)
                    if not canon:
                        # keep the raw attested indication as its own canonical key so the
                        # extractor can still find it in text; the graph infers its organ
                        canon = ind
                    if canon and ind:
                        lex.indications.setdefault(normalise(ind), canon)

        # 5. processes: ontology synonyms + processing.csv terms
        for surface, proc in ontology.PROCESS_SYNONYMS.items():
            lex.processes[normalise(surface)] = proc
        for name in ontology.ALL_PROCESSES:
            lex.processes[normalise(name)] = name
        if paths.processing_csv.exists():
            with paths.processing_csv.open(encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    term = (row.get("process_term") or "").strip()
                    if not term:
                        continue
                    proc = ontology.canonical_process(term)
                    if proc:
                        lex.processes.setdefault(normalise(term), proc)
                        modern = (row.get("process_modern") or "").strip()
                        if modern:
                            lex.process_terms[normalise(term)] = modern

        # 6. formula names
        if paths.formulas_csv.exists():
            with paths.formulas_csv.open(encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    name = (row.get("formula_name") or "").strip()
                    fid = (row.get("formula_id") or "").strip()
                    if name and fid:
                        lex.formula_names[normalise(name)] = fid

        # 7. roles and incompatibility markers
        lex.roles = {"君": "jun", "臣": "chen", "佐": "zuo", "使": "shi"}
        lex.incompat_markers = {
            "十八反": "shiba_fan",
            "十九畏": "shijiu_wei",
            "反": "shiba_fan",
            "畏": "shijiu_wei",
            "viruddha": "viruddha",
            "不相": "viruddha",
        }

        # longest surfaces first for greedy matching
        lex.drugs.sort(key=lambda e: (-len(e.surface), e.surface))
        return lex

    def _add_drug(self, surface: str, canonical: str, lang: str, conf: float, source: str) -> None:
        s = normalise(surface)
        if not s:
            return
        # avoid duplicate surface→same canonical
        for existing in self.drugs:
            if existing.surface == s and existing.canonical == canonical:
                if conf > existing.confidence:
                    self.drugs.remove(existing)
                else:
                    return
        self.drugs.append(DrugEntry(s, canonical, lang, min(1.0, max(0.0, conf)), source))

    # -- helpers ---------------------------------------------------------------------
    def drug_by_surface(self) -> dict[str, DrugEntry]:
        best: dict[str, DrugEntry] = {}
        for e in self.drugs:
            cur = best.get(e.surface)
            if cur is None or e.confidence > cur.confidence:
                best[e.surface] = e
        return best

    def drug_canonicals(self) -> set[str]:
        return {e.canonical for e in self.drugs}


def _lang_of(text: str) -> str:
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    if any("\u0600" <= ch <= "\u06ff" for ch in text):
        return "ar"
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return "sa"
    return "la"


def build_lexicons(paths: CorpusPaths | None = None) -> Lexicons:
    return Lexicons.build(paths)


def drug_surface_regex(lex: Lexicons):
    """Compiled alternation of all drug surfaces, for fast whole-corpus prefiltering."""
    import re

    surfaces = sorted({entry.surface for entry in lex.drugs if entry.surface}, key=len, reverse=True)
    if not surfaces:
        return None
    return re.compile("|".join(re.escape(surface) for surface in surfaces))
