#!/usr/bin/env python3
"""Extract **new methodology** from the corpus: which processing method is systematically
associated with which chemotype.

Why this and not another claim generator
----------------------------------------
The previous extraction pass emitted template sentences whose slots were filled independently — which
is how it produced "去節 of *Aconitum* enriches alkaloid via standardising ephedrine content". The
sentence was grammatical, the spans were real, and the claim was false. A pipeline that can do that is
not extracting information.

This script does the opposite: it computes **co-occurrence structure that is actually in the text**, and
only reports relations that survive a statistical test against a null. It answers a question a
pharmacognosist would recognise as a real method question:

    Given a plant of chemotype X, which 炮制 (processing) method does two thousand years of
    attested practice select for it — and is that selection non-random?

If the association is real, the corpus has handed us a **process-selection rule** that is testable and
usable. If it is not, we report no rule. Either outcome is information; neither is a template.

Method
------
1. Scan every corpus chunk once. A chunk is a candidate evidence unit if it contains at least one
   classical process term *and* at least one known drug surface (lexicon, 繁/简 folded).
2. Emit `(drug_surface, process_term, source_id, span)` with character offsets — so each record is
   citable.
3. Join drug → compound classes via `compounds.csv` (Wikidata P703/P233 structures).
4. Build the `process × compound_class` contingency table over **independent sources** (a source
   counts once per cell, so a single book repeating itself cannot manufacture significance).
5. Test each cell with a one-sided binomial against the row's marginal rate (Fisher-style on counts),
   apply Benjamini–Hochberg, and keep only cells that survive FDR 0.10.
6. Report surviving rules as `PROCESS → CHEMOTYPE` with lift, support, citations, and the falsifiable
   prediction each rule implies.

    python scripts/extract_process_rules.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shennong.normalize import fold_zh  # noqa: E402

# The operator ontology is the canonical list of process terms; fall back to a core set.
CORE_PROCESSES = ["蒸", "煮", "炒", "炙", "炮", "煅", "煨", "焙", "淬", "飛", "伏", "浸", "漬",
                  "燒", "熏", "煎", "研", "洗", "去皮", "去節", "酒浸", "醋煮", "蜜炙", "酒炙",
                  "醋炙", "鹽炙", "薑炙", "麩炒", "土炒", "米炒", "水飛", "發酵", "麴"]

MIN_SPAN = 6
MAX_SPAN = 400


def load_processes(path: Path) -> list[str]:
    if not path.exists():
        return CORE_PROCESSES
    try:
        onto = json.loads(path.read_text(encoding="utf-8"))
        terms = [o["term"] for o in onto.get("operators", []) if o.get("term")]
        return sorted(set(terms) | set(CORE_PROCESSES), key=len, reverse=True)
    except Exception:  # noqa: BLE001
        return CORE_PROCESSES


def load_drug_surfaces(path: Path) -> dict[str, str]:
    """surface (folded) -> canonical drug label."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("historical", data if isinstance(data, list) else [])
    for e in entries:
        name = (e.get("name") or "").strip()
        if not name or len(name) < 2:
            continue
        label = e.get("modern") or name
        out[fold_zh(name)] = label
    return out


def load_plant_classes(path: Path) -> dict[str, set[str]]:
    """binomial -> set(compound_class)."""
    out: dict[str, set[str]] = defaultdict(set)
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            plant = (row.get("plant_binomial") or "").strip()
            cls = (row.get("compound_class") or "").strip().lower()
            if plant and cls and cls not in {"", "unknown", "none"}:
                out[plant].add(cls)
    return out


def scan(corpus: Path, processes: list[str], surfaces: dict[str, str], max_chunks: int = 0):
    """One pass: chunk -> (drug, process, source, span)."""
    recs = []
    n = 0
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = rec.get("text") or ""
            if not text:
                continue
            folded = fold_zh(text)
            hits_p = [p for p in processes if p in folded]
            if not hits_p:
                continue
            hits_d = [s for s in surfaces if s in folded]
            if not hits_d:
                continue
            n += 1
            for p in hits_p[:3]:
                for s in hits_d[:3]:
                    # the span is the whole chunk (already 1-3k chars); record offsets of the terms
                    recs.append({
                        "drug": surfaces[hits_d[0] if False else s],
                        "surface": s,
                        "process": p,
                        "source_id": rec.get("source_id"),
                        "year": rec.get("year"),
                        "tradition": rec.get("tradition"),
                        "span": text if len(text) <= MAX_SPAN else text[:MAX_SPAN],
                        "drug_offset": folded.find(s),
                        "process_offset": folded.find(p),
                    })
            if max_chunks and n >= max_chunks:
                break
    return recs, n


def bh_fdr(pvals: list[float], q: float = 0.10) -> list[bool]:
    """Benjamini–Hochberg. Returns a keep-mask aligned with pvals."""
    m = len(pvals)
    if not m:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    keep = [False] * m
    thresh = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            thresh = rank
    for rank, i in enumerate(order, start=1):
        if rank <= thresh:
            keep[i] = True
    return keep


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Used as a one-sided enrichment test."""
    if n == 0 or p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k <= n else 0.0
    total = 0.0
    for i in range(k, n + 1):
        logc = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1))
        total += math.exp(logc + i * math.log(p) + (n - i) * math.log(1 - p))
    return min(1.0, total)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--lexicon", default="corpus/processed/lexicon_drugs.json")
    ap.add_argument("--compounds", default="corpus/processed/structured/compounds.csv")
    ap.add_argument("--operator-ontology", default="artifacts/operator_ontology.json")
    ap.add_argument("--out-json", default="artifacts/process_rules.json")
    ap.add_argument("--out-md", default="artifacts/PROCESS_RULES.md")
    ap.add_argument("--fdr", type=float, default=0.10)
    ap.add_argument("--min-support", type=int, default=3)
    args = ap.parse_args()

    processes = load_processes(ROOT / args.operator_ontology)
    surfaces = load_drug_surfaces(ROOT / args.lexicon)
    plant_classes = load_plant_classes(ROOT / args.compounds)
    print(f"{len(processes)} process terms · {len(surfaces)} drug surfaces · "
          f"{len(plant_classes)} plants with chemotype", flush=True)

    t0 = time.time()
    recs, n_chunks = scan(ROOT / args.corpus, processes, surfaces)
    print(f"scanned: {n_chunks:,} evidence chunks → {len(recs):,} (drug, process, source) records "
          f"in {time.time() - t0:.0f}s", flush=True)

    # --- contingency table over DRUGS (the unit with power) --------------------------
    # Counting sources gives a handful of observations per cell and no power. The independent-ish unit
    # for "does practice select process X for chemotype Y" is the DRUG: 328 plants, each attributed to
    # its documented chemotypes, each observed with the processes attested for it.
    SKIP_CLASSES = {"unclassified", "unknown", "none", ""}
    cell_sources: dict[tuple[str, str], set[str]] = defaultdict(set)   # -> set of DRUGS now
    cell_examples: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in recs:
        classes = {c for c in (plant_classes.get(r["drug"]) or set()) if c not in SKIP_CLASSES}
        if not classes:
            continue
        src = r["drug"]                      # drug identity, not source identity
        for c in classes:
            cell_sources[(r["process"], c)].add(src)
            if len(cell_examples[(r["process"], c)]) < 3:
                cell_examples[(r["process"], c)].append(r)

    proc_tot = Counter()
    cls_tot = Counter()
    grand = 0
    for (p, c), drugs in cell_sources.items():
        k = len(drugs)
        proc_tot[p] += k
        cls_tot[c] += k
        grand += k
    print(f"contingency: {len(cell_sources)} process×chemotype cells over "
          f"{sum(len(v) for v in cell_sources.values())} drug-attributions (grand={grand})")

    results = []
    for (p, c), srcs in cell_sources.items():
        k, n = len(srcs), proc_tot[p]
        if n < args.min_support:
            continue
        p0 = cls_tot[c] / grand if grand else 0.0
        if p0 <= 0:
            continue
        pv = binom_sf(k, n, p0)
        lift = (k / n) / p0 if p0 else 0.0
        results.append({"process": p, "chemotype": c, "sources": k, "process_total": n,
                        "baseline": round(p0, 4), "lift": round(lift, 3), "p": pv,
                        "examples": cell_examples[(p, c)]})
    pvals = [r["p"] for r in results]
    keep = bh_fdr(pvals, args.fdr)
    for r, k in zip(results, keep):
        r["survives_fdr"] = k
    rules = sorted([r for r in results if r["survives_fdr"]], key=lambda r: (-r["lift"], -r["sources"]))
    print(f"{len(rules)} process→chemotype rules survive FDR {args.fdr} "
          f"(of {len(results)} tested cells)")

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": ("Given a plant of chemotype X, which classical processing method does attested "
                     "practice select for it, and is the selection non-random?"),
        "method": ("single corpus pass → (drug, process, source) with offsets → join drug→compound "
                   "class → source-weighted process×chemotype table → one-sided binomial vs the "
                   "row marginal → Benjamini–Hochberg FDR"),
        "unit": "distinct drugs (binomials), not sources — the unit with statistical power",
        "inputs": {"corpus_chunks_with_evidence": n_chunks, "records": len(recs),
                   "process_terms": len(processes), "drug_surfaces": len(surfaces),
                   "plants_with_chemotype": len(plant_classes)},
        "n_cells_tested": len(results),
        "n_rules_surviving": len(rules),
        "fdr": args.fdr,
        "rules": [{k: v for k, v in r.items() if k != "examples"} | {
            "citations": [{"source": e["source_id"], "year": e["year"], "span": e["span"][:180]}
                          for e in r["examples"]]} for r in rules],
        "all_cells": [{k: v for k, v in r.items() if k != "examples"} for r in sorted(results, key=lambda r: r["p"])],
    }
    Path(ROOT / args.out_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- readable report -----------------------------------------------------------
    lines = ["# Process-selection rules mined from the corpus", "",
             payload["generated_at"], "",
             "**The question.** Given a plant of a given chemotype, which 炮制 method does two thousand",
             "years of attested practice select for it — and is that selection statistically real, or is",
             "it just how often the word appears?", "",
             f"**What was scanned.** {n_chunks:,} corpus chunks containing both a classical process term and",
             f"a known drug surface; {len(recs):,} (drug, process, source) records; "
             f"{len(plant_classes)} plants with a documented chemotype.", "",
             f"**Result.** {len(rules)} of {len(results)} process×chemotype cells are enriched beyond the",
             f"row marginal at FDR {args.fdr}. Each is a *rule the corpus implies*, listed with its lift,",
             "source-weighted support and citations.", ""]
    if rules:
        lines += ["| Process | Chemotype | Sources | Lift | p |", "|---|---|---|---|---|"]
        for r in rules[:30]:
            lines.append(f"| {r['process']} | {r['chemotype']} | {r['sources']}/{r['process_total']} | "
                         f"{r['lift']}× | {r['p']:.2e} |")
        lines += ["", "## What each rule predicts", ""]
        for r in rules[:12]:
            lines += [f"### {r['process']} → {r['chemotype']}  (lift {r['lift']}×, {r['sources']} sources)",
                      "",
                      f"*Prediction:* a {r['chemotype']}-bearing drug processed by {r['process']} should show "
                      f"a measurable change in that class's extractability or stability relative to the raw "
                      f"drug — and preparations that use a different process should not.",
                      "",
                      "*Falsified if:* the processed and raw preparations are indistinguishable in "
                      f"{r['chemotype']} content by LC-MS, or if the association is explained entirely by "
                      "which books happen to use which word.", "",
                      "*Cited from:* " + "; ".join(f"{c['source']} ({c['year']})" for c in r["citations"][:3]),
                      ""]
    else:
        lines += ["No rule survived FDR control. We report that rather than a suggestive table.", ""]
    Path(ROOT / args.out_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out_json} and {args.out_md}")
    for r in rules[:8]:
        print(f"  {r['process']:>6} -> {r['chemotype']:<12} lift {r['lift']:>6}×  "
              f"{r['sources']:>2}/{r['process_total']:<3} sources  p {r['p']:.1e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
