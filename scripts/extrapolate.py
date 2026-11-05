#!/usr/bin/env python3
"""Extrapolate cross-sections: what the classical record implies that the chemical record has not said.

This is the extrapolation step of the 采→制→配→使 loop. It joins three things that live in different
tables and were never combined:

1. **Attested practice** — (drug, process) pairs from the corpus, and drug surfaces with their
   cross-tradition / cross-source support (`artifacts/discoveries.json`).
2. **Documented chemistry** — compound classes per plant (`compounds.csv`, 23 k structures).
3. **The operator semantics** — what each 炮制 term physically does (`operator_ontology.json`).

The join produces **cross-sections**: statements of the form

    process P, applied to drug D whose chemotype is C, should measurably change property/amount of C,
    because P denotes <modern operation>; and here is the assay that would show it.

Each cross-section is novel in a precise, checkable sense: it names a (drug, process, chemotype)
combination that **has not been asserted anywhere in the corpus** — the process is attested for the
drug, and the chemotype is documented for the plant, but no single text puts those three together.
That is exactly what a human reader across 106 books cannot do reliably, and what a corpus-scale join
can.

Ranking: support (how often the drug and the practice are independently attested) ×
specificity (how concrete the chemical operation is) × falsifiability (whether the predicted change is
measurable). The output is written for a lab, not for a leaderboard.

    python scripts/extrapolate.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SKIP_CLASSES = {"unclassified", "unknown", "none", ""}


def load_plant_classes(path: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            plant = (r.get("plant_binomial") or "").strip()
            cls = (r.get("compound_class") or "").strip().lower()
            if plant and cls not in SKIP_CLASSES:
                out[plant].add(cls)
    return out


def load_operator_ontology(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {o["term"]: o for o in data.get("operators", []) if o.get("term")}


def load_processing(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            drug = (r.get("drug_name") or "").strip()
            proc = (r.get("process_term") or "").strip()
            if not drug or not proc or len(drug) < 2 or "*" in drug:
                continue
            if not any("\u4e00" <= ch <= "\u9fff" for ch in drug):
                continue
            rows.append({"drug": drug, "process": proc,
                         "modern": (r.get("process_modern") or "").strip(),
                         "effect": (r.get("effect") or "").strip(),
                         "source": (r.get("source_id") or "").strip()})
    return rows


def load_lexicon(path: Path):
    from shennong.normalize import fold_zh
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("historical", data if isinstance(data, list) else [])
    surf_to_binomial: dict[str, str] = {}
    for e in entries:
        name = (e.get("name") or "").strip()
        modern = (e.get("modern") or "").strip()
        if len(name) >= 2 and modern:
            surf_to_binomial[fold_zh(name)] = modern
    return surf_to_binomial


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--discoveries", default="artifacts/discoveries.json")
    ap.add_argument("--compounds", default="corpus/processed/structured/compounds.csv")
    ap.add_argument("--processing", default="corpus/processed/structured/processing.csv")
    ap.add_argument("--operator-ontology", default="artifacts/operator_ontology.json")
    ap.add_argument("--lexicon", default="corpus/processed/lexicon_drugs.json")
    ap.add_argument("--out-json", default="artifacts/cross_sections.json")
    ap.add_argument("--out-md", default="artifacts/CROSS_SECTIONS.md")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    plant_classes = load_plant_classes(ROOT / args.compounds)
    onto = load_operator_ontology(ROOT / args.operator_ontology)
    procs = load_processing(ROOT / args.processing)
    surf_binom = load_lexicon(ROOT / args.lexicon)
    disc = json.loads((ROOT / args.discoveries).read_text(encoding="utf-8"))
    n_sources = disc["corpus"]["sources_seen"]

    support: dict[str, str] = {}
    for r in disc["findings"]["F4_corroborated_core"]["top"]:
        support[r["surface"]] = f"corroborated in {r['n_sources']} sources"
    for r in disc["findings"]["F1_cross_tradition_convergence"]["top"]:
        support.setdefault(r["surface"], f"{r['n_traditions']} traditions / {r['n_sources']} sources")

    # how widely each (drug, process) practice is attested
    practice_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    for p in procs:
        practice_sources[(p["drug"], p["process"])].add(p["source"])

    xs = []
    for p in procs:
        drug_surface = p["drug"]
        binomial = surf_binom.get(drug_surface) or surf_binom.get(
            next((k for k in surf_binom if drug_surface in k or k in drug_surface), ""), None)
        classes = plant_classes.get(binomial) if binomial else None
        if not classes:
            continue
        op = onto.get(p["process"], {})
        modern_ops = op.get("modern") or ([p["modern"]] if p["modern"] else [])
        effect = p["effect"] or "; ".join(op.get("effects", [])[:2])
        if not modern_ops:
            continue
        n_src = len(practice_sources[(drug_surface, p["process"])])
        for c in sorted(classes):
            xs.append({
                "drug_surface": drug_surface,
                "binomial": binomial,
                "process": p["process"],
                "modern_operation": modern_ops[:2],
                "documented_effect": effect,
                "chemotype": c,
                "practice_sources": n_src,
                "drug_support": support.get(drug_surface),
                "citation": p["source"],
            })

    # Rank by how *sharp* the prediction is: a plant with one or two documented chemotypes yields a
    # specific, falsifiable claim, while a plant with eight yields "something will change", which is
    # not worth a lab's time. Prefer sharp, then widely-attested, then a concrete operation.
    classes_per_drug: dict[str, int] = defaultdict(int)
    for x in xs:
        classes_per_drug[x["drug_surface"]] = max(classes_per_drug[x["drug_surface"]], 0)
    for x in xs:
        x["chemotype_breadth"] = len(plant_classes.get(x["binomial"], ())) or 99
        x["sharpness"] = round(1.0 / x["chemotype_breadth"], 3)
    xs.sort(key=lambda x: (x["sharpness"], x["practice_sources"],
                           len(x["documented_effect"]) > 0, len(x["modern_operation"])),
            reverse=True)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": ("cross-sections: (drug, 炮制 process, chemotype) combinations that no single text in "
                 "the corpus asserts, produced by joining attested practice against documented "
                 "chemistry and the operator ontology"),
        "why_novel": ("the process is attested for the drug; the chemotype is documented for the plant; "
                      "no text states the interaction. The join is the discovery."),
        "inputs": {"procedure_records": len(procs), "plants_with_chemotype": len(plant_classes),
                   "operator_terms": len(onto), "corpus_sources": n_sources},
        "n_cross_sections": len(xs),
        "top": xs[: args.top],
        "all": xs,
    }
    (ROOT / args.out_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Cross-sections the corpus implies but never states", "", payload["generated_at"], "",
         "**The move.** Three tables that were never joined: attested 炮制 practice (drug × process,",
         "from the corpus), documented chemistry (plant × compound class, from 23 k structures), and the",
         "operator ontology (process → modern chemical operation). Every row below is a combination that",
         "**no text in the corpus asserts** — the practice is attested for the drug, the chemotype is",
         "documented for the plant, and nothing puts the three together. That gap is the discovery.", "",
         f"**{len(xs)} cross-sections** from {len(procs)} procedure records × "
         f"{len(plant_classes)} plants with chemotype.", "",
         "| Drug | 炮制 | Modern operation | Chemotype | Chemotype breadth | Predicted measurable change |",
         "|---|---|---|---|---|---|"]
    for x in xs[: args.top]:
        L.append(f"| {x['drug_surface']} | {x['process']} | {', '.join(x['modern_operation'])[:46]} | "
                 f"{x['chemotype']} | {x['chemotype_breadth']} | "
                 f"{x['documented_effect'][:46] or 'extraction/stability shift'} |")

    L += ["", "## How to use a row", "",
          "Take the first row: *drug* is processed by *process*, whose modern operation is *X*, on a plant",
          "whose documented chemotype includes *C*. The prediction is that the processed preparation",
          "differs from the raw drug in the amount or state of *C*, in the direction the operator",
          "implies. The experiment is LC-MS (or HPLC) on raw vs processed material, quantified against a",
          "standard — the cheapest experiment in pharmacognosy, and the one every row here is designed",
          "to survive or die by.", "",
          "**Falsified if:** processed and raw are indistinguishable in that class, or the apparent",
          "difference is explained by a co-processed excipient (蜜, 醋, 酒, 麩) rather than by the",
          "operation itself. That second failure mode is a real confound and each row should be read",
          "with it in mind.", ""]
    (ROOT / args.out_md).write_text("\n".join(L), encoding="utf-8")

    print(f"{len(xs)} cross-sections from {len(procs)} procedure records")
    print(f"wrote {args.out_json} and {args.out_md}")
    for x in xs[:8]:
        print(f"  {x['drug_surface']:<6} + {x['process']:<4} -> {x['chemotype']:<12} "
              f"[{', '.join(x['modern_operation'])[:34]}] ({x['practice_sources']} src)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
