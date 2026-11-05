"""Build the SHENNONG knowledge graph from the processed-corpus contracts.

Streams ``corpus.jsonl`` (span extraction), the structured CSVs (plants, compounds,
uses, formulas, incompatibilities, processing) and the drug-name lexicon into one
typed graph.  The graph is a derived artefact: it is rebuilt, never edited by hand.

Every corpus-derived edge keeps ``source_id`` + ``char_start``/``char_end`` + ``quote``
so that a hypothesis can be traced to a real span (and dropped if it cannot be).
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from shennong import ontology
from shennong.config import CorpusPaths
from shennong.extract.extract import extract_corpus, load_corpus
from shennong.extract.lexicons import Lexicons, build_lexicons
from shennong.kg.schema import Graph, node_id


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh)]


def _s(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _canonical_name_map(lex: Lexicons) -> dict[str, str]:
    """Raw drug-name text → modern binomial (for CSV rows that use Chinese/IAST names)."""
    return {e.surface: e.canonical for e in lex.drugs}


def _resolve_taxon(
    name: str, binomials: set[str], name_map: dict[str, str]
) -> str | None:
    """Resolve a drug name from a CSV column to a binomial, if possible."""
    if not name:
        return None
    direct = {b.lower(): b for b in binomials}
    if name.lower() in direct:
        return direct[name.lower()]
    from shennong.normalize import normalise

    key = normalise(name)
    if key in name_map:
        return name_map[key]
    for surface, binomial in name_map.items():
        if surface == key:
            return binomial
    return None


def corpus_stats(paths: CorpusPaths) -> dict[str, Any]:
    """Honest corpus counters used by eval/report.json (brief §10.7)."""
    docs = load_corpus(paths.corpus_jsonl) if paths.corpus_jsonl.exists() else []
    languages: Counter[str] = Counter()
    traditions: Counter[str] = Counter()
    chars = 0
    sources: set[str] = set()
    for doc in docs:
        languages[str(doc.get("lang", "unknown"))] += 1
        traditions[str(doc.get("tradition", "unknown"))] += 1
        chars += len(doc.get("text", ""))
        sources.add(str(doc.get("source_id", "")))
    return {
        "sources": len(sources),
        "documents": len(docs),
        "chars": chars,
        "languages": dict(sorted(languages.items())),
        "traditions": dict(sorted(traditions.items())),
    }


def build_graph(paths: CorpusPaths | None = None, lex: Lexicons | None = None) -> Graph:
    """Build the full knowledge graph from a processed corpus directory."""
    paths = (paths or CorpusPaths.resolve()).require()
    lex = lex or build_lexicons(paths)
    g = Graph()

    # traditions are referenced by several edge builders, so create them up front
    for tradition in ontology.Tradition:
        g.add_node("tradition", tradition.value, tradition.value,
                   **ontology.tradition_metadata(tradition.value))

    # -- sources + corpus text extraction -------------------------------------------
    docs = load_corpus(paths.corpus_jsonl)
    sources_meta: dict[str, dict[str, str]] = {}
    for doc in docs:
        sid = str(doc.get("source_id", ""))
        sources_meta.setdefault(
            sid,
            {
                "title": str(doc.get("title", sid)),
                "title_en": str(doc.get("title_en", "")),
                "year": str(doc.get("year", "")),
                "tradition": str(doc.get("tradition", "unknown")),
                "lang": str(doc.get("lang", "en")),
                "tier": str(doc.get("tier", "")),
                "licence": str(doc.get("licence", "")),
                "quote": str(doc.get("text", ""))[:80],
            },
        )
    for sid, meta in sources_meta.items():
        g.add_node("source", sid, meta["title"], **meta)

    # -- taxa -----------------------------------------------------------------------
    plants = _read_csv(paths.plants_csv)
    binomials: set[str] = set()
    for row in plants:
        binomial = _s(row, "binomial")
        if not binomial:
            continue
        binomials.add(binomial)
        g.add_node(
            "taxon", binomial, binomial,
            family=_s(row, "family"),
            synonyms=_s(row, "synonyms"),
            tradition=_s(row, "tradition"),
            source_id=_s(row, "source_id"),
        )
        if _s(row, "tradition"):
            g.add_edge(node_id("taxon", binomial), node_id("tradition", _s(row, "tradition")), "belongs_to_tradition")

    name_map = _canonical_name_map(lex)
    binomials_in_graph = set(binomials)

    # -- drug names (cross-era/cross-language aliases) ------------------------------
    seen_alias: set[tuple[str, str]] = set()
    for entry in lex.drugs:
        canonical = entry.canonical
        if canonical not in binomials_in_graph:
            # A drug may resolve to a canonical not listed in plants.csv; add it.
            if canonical and canonical[0].isupper() and " " in canonical:
                g.add_node("taxon", canonical, canonical)
                binomials_in_graph.add(canonical)
            else:
                continue
        label = entry.surface
        g.add_node("drug_name", entry.surface, label, lang=entry.lang, confidence=entry.confidence, source=entry.source)
        key = (entry.surface, canonical)
        if key in seen_alias:
            continue
        seen_alias.add(key)
        g.add_edge(
            node_id("drug_name", entry.surface),
            node_id("taxon", canonical),
            "alias_of",
            confidence=entry.confidence,
            lang=entry.lang,
            source=entry.source,
        )

    # -- compounds + classes --------------------------------------------------------
    compounds = _read_csv(paths.compounds_csv)
    class_by_taxon: dict[str, set[str]] = {}
    classes_in_graph: set[str] = set()
    unknown_classes: set[str] = set()
    for row in compounds:
        name = _s(row, "name")
        binomial = _s(row, "plant_binomial")
        cls = _s(row, "compound_class")
        if not name or not binomial:
            continue
        if binomial not in binomials_in_graph:
            g.add_node("taxon", binomial, binomial, family=_s(row, "family"))
            binomials_in_graph.add(binomial)
        g.add_node(
            "compound", name, name,
            smiles=_s(row, "smiles"),
            cid=_s(row, "cid"),
            compound_class=cls,
            source_id=_s(row, "source_id"),
        )
        g.add_edge(node_id("taxon", binomial), node_id("compound", name), "contains",
                   source_id=_s(row, "source_id"))
        if cls:
            profile = ontology.compound_class_profile(cls)
            if profile is None:
                unknown_classes.add(cls)
                cls = cls.lower().replace("-", "_").replace(" ", "_")
                profile = ontology.compound_class_profile(cls)
            if profile is None:
                unknown_classes.add(cls)
                continue
            classes_in_graph.add(cls)
            class_by_taxon.setdefault(binomial, set()).add(cls)
            g.add_node("compound_class", cls, cls,
                       polarity=profile.polarity, volatility=profile.volatility,
                       thermolability=profile.thermolability, citation=profile.citation)
            g.add_edge(node_id("compound", name), node_id("compound_class", cls), "member_of")

    # class-level prior edges (mechanism hypotheses, not evidence)
    for cls in sorted(classes_in_graph):
        profile = ontology.COMPOUND_CLASSES[cls]
        cid = node_id("compound_class", cls)
        for target in profile.targets:
            g.add_node("target", target, target)
            g.add_edge(cid, node_id("target", target), "class_target_prior",
                       citation=profile.citation)
        for pathway in profile.pathways:
            g.add_node("pathway", pathway, pathway)
            g.add_edge(cid, node_id("pathway", pathway), "class_pathway_prior",
                       citation=profile.citation)
        for ind in profile.indications:
            spec = ontology.indication_spec(ind)
            canonical = spec.indication if spec else ind
            g.add_node("indication", canonical, canonical,
                       organ=spec.organ if spec else "", action_class=spec.action_class if spec else "")
            g.add_edge(cid, node_id("indication", canonical), "class_indication_prior",
                       citation=profile.citation)

    # -- uses.csv (structured evidence) ---------------------------------------------
    uses = _read_csv(paths.uses_csv)
    for row in uses:
        binomial = _s(row, "plant_binomial")
        ind = _s(row, "indication_modern") or _s(row, "indication")
        spec = ontology.indication_spec(ind) or ontology.indication_spec(_s(row, "indication"))
        if not binomial or spec is None:
            continue
        if binomial not in binomials_in_graph:
            g.add_node("taxon", binomial, binomial)
            binomials_in_graph.add(binomial)
        tradition = _s(row, "tradition") or "unknown"
        grade = (_s(row, "evidence_grade") or "D").upper()
        preparation = _s(row, "preparation")
        modern = ontology.is_modern_evidence(tradition, grade)
        g.add_node("indication", spec.indication, spec.indication, organ=spec.organ, action_class=spec.action_class)
        g.add_node("tradition", tradition, tradition)
        g.add_edge(
            node_id("taxon", binomial), node_id("indication", spec.indication), "treats",
            tradition=tradition, preparation=preparation, evidence_grade=grade,
            modern=modern, source_id=_s(row, "source_id"), origin="structured",
        )
        g.add_edge(node_id("taxon", binomial), node_id("tradition", tradition), "used_in_tradition")

    # -- corpus-extracted observations (span-carrying evidence) ---------------------
    extraction = extract_corpus(docs, lex)
    for obs in extraction.observations:
        payload = obs.payload
        if obs.kind == "treats":
            binomial = payload.get("drug")
            if binomial not in binomials_in_graph:
                continue
            spec = ontology.indication_spec(payload.get("indication", ""))
            if spec is None:
                continue
            g.add_node("indication", spec.indication, spec.indication, organ=spec.organ, action_class=spec.action_class)
            g.add_edge(
                node_id("taxon", binomial), node_id("indication", spec.indication), "treats",
                tradition=payload.get("tradition", "unknown"),
                evidence_grade="C" if payload.get("tradition") == "modern" else "D",
                modern=payload.get("tradition") == "modern",
                source_id=obs.source_id, char_start=obs.char_start, char_end=obs.char_end,
                quote=obs.quote, confidence=obs.confidence, origin="corpus",
                drug_surface=payload.get("drug_surface", ""), year=payload.get("year", 0),
            )
        elif obs.kind == "processed_by":
            binomial = payload.get("drug")
            proc = payload.get("process")
            if binomial not in binomials_in_graph or not proc:
                continue
            sem = ontology.ALL_PROCESSES.get(proc)
            g.add_node("process", proc, sem.name_zh if sem else proc, process_key=proc,
                       modern=sem.modern if sem else "", mechanism=sem.mechanism if sem else "",
                       citation=sem.citation if sem else "")
            g.add_edge(
                node_id("taxon", binomial), node_id("process", proc), "processed_by",
                source_id=obs.source_id, char_start=obs.char_start, char_end=obs.char_end,
                quote=obs.quote, confidence=obs.confidence, origin="corpus",
            )
        elif obs.kind == "incompatible":
            a = _resolve_taxon(payload.get("drug_a", ""), binomials_in_graph, name_map)
            b = _resolve_taxon(payload.get("drug_b", ""), binomials_in_graph, name_map)
            rule = payload.get("rule_system", "unknown")
            mech = _mechanism_for(a, b, rule, class_by_taxon)
            for node_binomial in (a, b):
                if node_binomial and node_binomial not in binomials_in_graph:
                    g.add_node("taxon", node_binomial, node_binomial)
                    binomials_in_graph.add(node_binomial)
            if a and b:
                g.add_edge(
                    node_id("taxon", a), node_id("taxon", b), "incompatible",
                    rule_system=rule, mechanism_kind=mech.kind, mechanism_prior=mech.prior,
                    mechanism=mech.evidence, source_id=obs.source_id,
                    char_start=obs.char_start, char_end=obs.char_end, quote=obs.quote,
                    confidence=obs.confidence, origin="corpus",
                    drug_a_raw=payload.get("drug_a_surface", ""),
                    drug_b_raw=payload.get("drug_b_surface", ""),
                )

    # -- incompatibilities.csv (rule lists are authoritative even without extracted text)
    incompat_rows = _read_csv(paths.incompatibilities_csv)
    for row in incompat_rows:
        raw_a = _s(row, "drug_a")
        raw_b = _s(row, "drug_b")
        rule = _s(row, "rule_system") or "unknown"
        a = _resolve_taxon(raw_a, binomials_in_graph, name_map)
        b = _resolve_taxon(raw_b, binomials_in_graph, name_map)
        for raw, resolved in ((raw_a, a), (raw_b, b)):
            if resolved and resolved not in binomials_in_graph:
                g.add_node("taxon", resolved, resolved)
                binomials_in_graph.add(resolved)
        if not a or not b:
            # keep unresolved rule pairs as drug_name nodes so the rule is not lost
            for raw in (raw_a, raw_b):
                if raw and ontology.canonical_process(raw) is None:
                    g.add_node("drug_name", raw, raw, unresolved=True, lang=_guess_lang(raw))
            a_id = node_id("taxon", a) if a else node_id("drug_name", raw_a)
            b_id = node_id("taxon", b) if b else node_id("drug_name", raw_b)
            g.add_edge(a_id, b_id, "incompatible", rule_system=rule,
                       mechanism_kind="unresolved", mechanism_prior=0.0,
                       mechanism="Drug name could not be resolved to a taxon.",
                       source_id=_s(row, "source_id"))
            continue
        mech = _mechanism_for(a, b, rule, class_by_taxon)
        g.add_edge(
            node_id("taxon", a), node_id("taxon", b), "incompatible",
            rule_system=rule, mechanism_kind=mech.kind, mechanism_prior=mech.prior,
            mechanism=mech.evidence, source_id=_s(row, "source_id"), origin="rule_list",
            drug_a_raw=raw_a, drug_b_raw=raw_b,
        )

    # -- formulas + ingredients -----------------------------------------------------
    formulas = _read_csv(paths.formulas_csv)
    for row in formulas:
        fid = _s(row, "formula_id")
        if not fid:
            continue
        g.add_node("formula", fid, _s(row, "formula_name") or fid, source_id=_s(row, "source_id"))
    for row in _read_csv(paths.formula_ingredients_csv):
        fid = _s(row, "formula_id")
        drug = _s(row, "drug_name")
        binomial = _s(row, "plant_binomial")
        role = _s(row, "role")
        if not fid or not binomial:
            continue
        if binomial not in binomials_in_graph:
            g.add_node("taxon", binomial, binomial)
            binomials_in_graph.add(binomial)
        g.add_node("role", role, role, **({"zh": ontology.ROLES[ontology.Role(role)]["zh"]} if role in {r.value for r in ontology.Role} else {}))
        g.add_edge(node_id("formula", fid), node_id("taxon", binomial), "has_ingredient",
                   role=role, drug_name=drug)

    # -- processing.csv -------------------------------------------------------------
    for row in _read_csv(paths.processing_csv):
        raw = _s(row, "drug_name")
        proc = ontology.canonical_process(_s(row, "process_term"))
        binomial = _resolve_taxon(raw, binomials_in_graph, name_map)
        if not proc or not binomial:
            continue
        sem = ontology.ALL_PROCESSES[proc]
        g.add_node("process", proc, sem.name_zh, process_key=proc, modern=sem.modern,
                   mechanism=sem.mechanism, citation=sem.citation)
        g.add_edge(
            node_id("taxon", binomial), node_id("process", proc), "processed_by",
            process_term=_s(row, "process_term"), process_modern=_s(row, "process_modern"),
            effect=_s(row, "effect"), source_id=_s(row, "source_id"), origin="processing_table",
            drug_raw=raw,
        )

    # bookkeeping
    stats = {
        "unknown_compound_classes": sorted(unknown_classes),
        "sources": len(sources_meta),
        "documents": len(docs),
    }
    g._build_stats = stats  # type: ignore[attr-defined]
    return g


def _mechanism_for(a: str | None, b: str | None, rule: str, class_by_taxon: dict[str, set[str]]):
    classes_a = class_by_taxon.get(a, set()) if a else set()
    classes_b = class_by_taxon.get(b, set()) if b else set()
    return ontology.infer_pair_mechanism(
        a or "", b or "", classes_a, classes_b
    )


def _guess_lang(text: str) -> str:
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    if any("\u0600" <= ch <= "\u06ff" for ch in text):
        return "ar"
    return "und"


def build_and_save(
    paths: CorpusPaths | None = None,
    out: str | Path | None = None,
) -> tuple[Graph, Path, dict[str, Any]]:
    """Build the graph, persist it, and return (graph, path, stats)."""
    paths = (paths or CorpusPaths.resolve()).require()
    lex = build_lexicons(paths)
    g = build_graph(paths, lex)
    target = Path(out) if out else paths.build_dir / "graph.json"
    g.save(target)
    stats = corpus_stats(paths)
    stats.update(getattr(g, "_build_stats", {}))
    return g, target, stats
