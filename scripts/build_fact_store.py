#!/usr/bin/env python3
"""Build the RAG fact store: every structured fact, rendered as one sentence per row.

The text corpus (45.6 M chars) answers "what does 本草綱目 say about X", but it does not contain the
structured facts we extracted — 人參's 歸經, the 十八反 pairs, the name→binomial map. Those live in CSVs.
For a judge to ask ANY Track-1/Track-2 question and get a grounded answer, the retrieval index must include
both. This script renders every structured table row as a sentence into `artifacts/facts.jsonl`, so the RAG
index is text + facts, and the data pipeline can be re-run ("continuously updated corpus") by re-running
this plus `make corpus`.

    python scripts/build_fact_store.py     # -> artifacts/facts.jsonl
"""
from __future__ import annotations

import csv
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus/processed/structured"


def main() -> int:
    out = []
    def add(kind, text, source_id=""):
        out.append({"kind": kind, "text": text, "source_id": source_id})

    # properties -> nature/flavour/channel facts
    for r in csv.DictReader((STRUCT / "properties.csv").open(encoding="utf-8")):
        if r.get("drug_name"):
            add("property", f"{r['drug_name']} 性 {r.get('nature') or '—'}, 味 {r.get('flavors') or '—'}, "
                            f"歸經 {r.get('channels') or '未載'}, 毒 {r.get('toxicity') or '—'}, 品 {r.get('grade') or '—'}.",
                r.get("source_id", ""))

    # name -> binomial mapping
    lex = json.loads((ROOT / "corpus/processed/lexicon_drugs.json").read_text(encoding="utf-8"))
    for r in lex.get("historical", []):
        if r.get("name") and r.get("modern"):
            add("name_mapping", f"{r['name']} -> {r['modern']}", r.get("source_id", ""))

    # therapeutic uses
    for r in csv.DictReader((STRUCT / "uses.csv").open(encoding="utf-8")):
        d, i = (r.get("drug_name") or "").strip(), (r.get("indication") or "").strip()
        if len(d) >= 2 and len(i) >= 2:
            p = (r.get("preparation") or "").strip()
            add("use", f"{d} 治 {i}" + (f"，製法 {p}" if p else ""), r.get("source_id", ""))

    # incompatibilities (十八反/十九畏)
    for r in csv.DictReader((STRUCT / "incompatibilities.csv").open(encoding="utf-8")):
        if r.get("drug_a") and r.get("drug_b"):
            add("incompatibility", f"{r['drug_a']} 反 {r['drug_b']}（{r.get('classical_label') or r.get('rule_system')}）",
                r.get("source_id", ""))

    # 七情 relations
    SEVEN = {"xiangxu": "相須", "xiangshi": "相使", "xiangwei": "相畏", "xiangfan": "相反", "xiange": "相惡"}
    for r in csv.DictReader((STRUCT / "relations_seven.csv").open(encoding="utf-8")):
        if r.get("drug_a") and r.get("drug_b"):
            add("relation", f"{r['drug_a']} {SEVEN.get(r['relation'], r['relation'])} {r['drug_b']}",
                r.get("source_id", ""))

    # compounds
    seen = set()
    for r in csv.DictReader((STRUCT / "compounds.csv").open(encoding="utf-8")):
        plant, cls = (r.get("plant_binomial") or "").strip(), (r.get("compound_class") or "").strip()
        if plant and cls and (plant, cls) not in seen:
            seen.add((plant, cls))
            add("compound", f"{plant} contains {cls}")

    # pharmacology (plant -> target -> disease)
    for r in csv.DictReader((STRUCT / "pharmacology.csv").open(encoding="utf-8")):
        add("pharmacology", f"{r['plant_binomial']} contains {r['compound_class']} → target {r['molecular_target']} ({r['disease']})")

    # formulas
    from collections import defaultdict
    grp = defaultdict(list)
    for r in csv.DictReader((STRUCT / "formula_ingredients.csv").open(encoding="utf-8")):
        if r.get("formula_id") and r.get("drug_name"):
            grp[r["formula_id"]].append(r["drug_name"])
    for fid, drugs in grp.items():
        add("formula", f"方 {fid}: " + "、".join(drugs))

    path = ROOT / "artifacts/facts.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for i, f in enumerate(out):
            fh.write(json.dumps({"id": i, **f}, ensure_ascii=False) + "\n")

    kinds = {}
    for f in out:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    print(f"fact store: {len(out):,} facts -> artifacts/facts.jsonl")
    print("  by kind:", kinds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
