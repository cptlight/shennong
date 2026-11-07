#!/usr/bin/env python3
"""Track-2 screening: query a disease target, get ranked plant-derived compounds with evidence.

This is the "predictive model / knowledge graph / screening pipeline" layer, built on the data we already
have — no GPU, no network. For a query like "COX2" or "inflammation" it returns the plants whose compounds
are linked to that target, with the evidence chain and a physics/ADMET sanity flag.

    python -m shennong.screen "COX2"          # or: shennong screen-target "COX2"

Layers (in order):
  1 knowledge graph    plant -> compound_class/gene_target -> target/disease   (multi-hop, exact)
  2 predictive         ECFP/Tanimoto similarity vs known actives               (cheminformatics, next)
  3 screening          ADMET rules + physics arbiter (preparation viability)   (falsifiable)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus" / "processed" / "structured"


def _load(rel: str) -> list[dict]:
    p = STRUCT / rel
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace("-", "").replace(" ", "").replace("_", "")


def screen_target(query: str, top_k: int = 20) -> dict:
    q = _norm(query)
    if not q:
        return {"ok": False, "error": "empty query"}

    # ---- 1. exact gene-target hits from IMPPAT ----
    gene_rows = []
    for r in _load("imppat_targets.csv"):
        if _norm(r.get("gene_target")) == q:
            gene_rows.append(r)

    # ---- 2. pharmacology (compound class -> target -> disease) ----
    pharm_rows = []
    for r in _load("pharmacology.csv"):
        blob = _norm(r.get("molecular_target", "") + " " + r.get("disease", "") + " " + r.get("compound_class", ""))
        if q in blob:
            pharm_rows.append(r)

    # ---- 3. compound-class rows (for evidence of what the plant contains) ----
    comp_index = {}
    for r in _load("compounds.csv"):
        p = (r.get("plant_binomial") or "").strip()
        c = (r.get("compound_class") or "").strip()
        if p and c and c != "unclassified":
            comp_index.setdefault(p, set()).add(c)

    # ---- assemble, dedupe by plant ----
    plants = {}
    for r in gene_rows:
        p = r["plant_binomial"]
        plants.setdefault(p, {"plant": p, "gene_targets": [], "compound_classes": [], "diseases": []})
        plants[p]["gene_targets"].append(r["gene_target"])
    for r in pharm_rows:
        p = r["plant_binomial"]
        plants.setdefault(p, {"plant": p, "gene_targets": [], "compound_classes": [], "diseases": []})
        plants[p]["compound_classes"].append(f"{r['compound_class']} → {r['molecular_target']}")
        plants[p]["diseases"].append(r["disease"])
    for p in plants:
        plants[p]["compound_classes"] += sorted(comp_index.get(p, set()))
        plants[p]["compound_classes"] = sorted(set(plants[p]["compound_classes"]))[:5]
        plants[p]["gene_targets"] = sorted(set(plants[p]["gene_targets"]))[:5]
        plants[p]["diseases"] = sorted(set(plants[p]["diseases"]))[:5]

    results = sorted(plants.values(),
                     key=lambda x: (bool(x["gene_targets"]) + bool(x["compound_classes"])), reverse=True)[:top_k]
    return {
        "ok": True,
        "query": query,
        "n_plants": len(results),
        "method": ("knowledge-graph: plant → compound_class/gene_target → target/disease (exact multi-hop). "
                   "Next layers: ECFP/Tanimoto similarity vs ChEMBL actives, then ADMET + physics arbiter."),
        "results": results,
    }


def _main() -> int:
    q = sys.argv[1] if len(sys.argv) > 1 else "COX2"
    print(json.dumps(screen_target(q), indent=2, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
