#!/usr/bin/env python3
"""Integrate IMPPAT (Indian Medicinal Plants, Phytochemistry And Therapeutics) into the corpus.

IMPPAT is openly licensed (CC-BY) and covers Ayurveda, Siddha and Unani — the traditions our structured data
was missing entirely (it was 100 % TCM). This converts IMPPAT's TSVs into our structured CSVs:

    imppat_uses.csv      plant_binomial, therapeutic_use, system_of_medicine   (~94k)
    imppat_names.csv     binomial, synonym, common_name, system                (~4k plants)
    imppat_targets.csv   binomial, gene_target                                 (~38k phytochem->gene, joined)

Download the TSVs first (corpus/external/imppat/), then run:

    python scripts/build_imppat.py
"""
from __future__ import annotations

import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPPAT = ROOT / "corpus" / "external" / "imppat"
OUT = ROOT / "corpus" / "processed" / "structured"


def read(name: str) -> list[dict]:
    p = IMPPAT / name
    if not p.exists():
        print(f"  missing {name} — download from https://cb.imsc.res.in/imppat/download first")
        return []
    return list(csv.DictReader(p.open(encoding="utf-8"), delimiter="\t"))


def main() -> int:
    plants = {r["Plant_identifier"]: r for r in read("Plant_Information_IMPPAT.tsv")}
    uses = read("IMPPAT_TherapeuticUse_Plant_Association.tsv")
    targets = read("Target_IMPPAT_Phytochemicals.tsv")
    assoc = read("IMPPAT_Phytochemical_Plant_Association.tsv")

    # plant id -> binomial
    pid_to_bin = {r["Plant_identifier"]: r["Indian_Medicinal_plant"] for r in plants.values()}
    # phytochem id -> gene symbols
    pcid_to_genes = {}
    for t in targets:
        g = (t.get("HGNC_Symbol") or "").strip()
        if g and g.lower() != "null":
            pcid_to_genes.setdefault(t["IMPPAT_Phytochemical_identifier"], set()).add(g)

    # ---- 1. uses ----
    seen_use = set()
    with (OUT / "imppat_uses.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["plant_binomial", "therapeutic_use", "system_of_medicine"])
        for r in uses:
            pid = r.get("IMPPAT_Plant_identifier") or r.get("Plant_identifier")
            binom = pid_to_bin.get(pid)
            use = (r.get("Therapeutic_use") or "").strip()
            if not binom or not use or (binom, use) in seen_use:
                continue
            seen_use.add((binom, use))
            w.writerow([binom, use, plants.get(pid, {}).get("System_of_Medicine", "")])

    # ---- 2. name mapping ----
    with (OUT / "imppat_names.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["plant_binomial", "synonym", "common_name", "system_of_medicine"])
        for r in plants.values():
            binom = r["Indian_Medicinal_plant"]
            syns = (r.get("Synonymous names") or "").split("|")
            common = r.get("Common_name") or ""
            system = r.get("System_of_Medicine") or ""
            for s in syns:
                s = s.strip()
                if s and s.lower() != binom.lower():
                    w.writerow([binom, s, common, system])

    # ---- 3. plant -> gene target (join phytochem association -> target) ----
    seen_tgt = set()
    with (OUT / "imppat_targets.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["plant_binomial", "gene_target"])
        for r in assoc:
            binom = (r.get("Indian_Medicinal_plant") or "").strip()
            pcid = r.get("IMPPAT_Phytochemical_identifier")
            for g in pcid_to_genes.get(pcid, ()):
                if (binom, g) in seen_tgt:
                    continue
                seen_tgt.add((binom, g))
                w.writerow([binom, g])

    print(f"imppat_uses: {len(seen_use):,} rows")
    print(f"imppat_names: {len(plants):,} plants")
    print(f"imppat_targets: {len(seen_tgt):,} plant->gene rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
