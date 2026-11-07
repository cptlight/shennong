#!/usr/bin/env python3
"""Ligand-based virtual screening: rank our plant compounds by similarity to a target's known actives.

This is layer 2 of the Track-2 stack ("apply machine learning and cheminformatics to identify promising
plant-derived compounds for specific disease targets"). It is standard, honest cheminformatics:

    target -> ChEMBL known actives (canonical SMILES)
           -> ECFP4 fingerprints (Morgan radius 2, 2048 bits)
           -> Tanimoto similarity to our 23,176 plant compounds
           -> ranked shortlist

ChEMBL is CC BY-SA, so the fetched actives are cached under `corpus/external/chembl/` and are NOT merged into
the permissive training corpus (see docs/CORPUS_PROVENANCE.md).

    python scripts/chembl_screen.py --target COX2            # -> artifacts/chembl_screen_COX2.json
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "corpus" / "external" / "chembl"
COMPOUNDS = ROOT / "corpus" / "processed" / "structured" / "compounds.csv"
BASE = "https://www.ebi.ac.uk/chembl/api/data"


def _get(url: str, timeout: int = 40) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "shennong/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# common drug-target aliases -> canonical gene symbol (ChEMBL resolves gene symbols cleanly)
TARGET_ALIASES = {
    "cox2": "PTGS2", "cox-2": "PTGS2", "cyclooxygenase2": "PTGS2", "cox1": "PTGS1", "cox-1": "PTGS1",
    "egfr": "EGFR", "her2": "ERBB2", "vegfr": "KDR", "vegfr2": "KDR", "hdac": "HDAC1",
    "ache": "ACHE", "bche": "BCHE", "mao": "MAOA", "maoa": "MAOA", "maob": "MAOB",
    "dpp4": "DPP4", "dpp-4": "DPP4", "sglt2": "SLC5A2", "ace": "ACE", "renin": "REN",
    "5ht": "HTR2A", "5-ht": "HTR2A", "d2": "DRD2", "dopamine": "DRD2", "ar": "AR", "er": "ESR1",
    "tubulin": "TUBB", "topoisomerase": "TOP1", "parp": "PARP1", "mtor": "MTOR", "pi3k": "PIK3CA",
}


def resolve_target(query: str) -> list[dict]:
    raw = (query or "").strip().lower().replace(" ", "")
    q = TARGET_ALIASES.get(raw, query)   # e.g. "COX2" -> "PTGS2" (COX-2 = cyclooxygenase-2)
    quoted = urllib.parse.quote(q)
    d = _get(f"{BASE}/target/search.json?q={quoted}&limit=8")
    targets = [{"chembl_id": t["target_chembl_id"], "name": t.get("pref_name") or "",
                "type": t.get("target_type")} for t in d.get("targets", [])]
    # prefer single-protein targets (families/protein-complexes are too broad for screening)
    targets.sort(key=lambda t: 0 if t["type"] == "SINGLE PROTEIN" else 1)
    return targets


def fetch_actives(target_id: str, limit: int = 200) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"{target_id}_actives.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    d = _get(f"{BASE}/activity.json?target_chembl_id={target_id}&standard_type=IC50"
             f"&standard_value__lte=10000&limit={limit}")
    acts = [{"chembl_id": a.get("molecule_chembl_id"), "smiles": a.get("canonical_smiles"),
             "value_nM": a.get("standard_value")} for a in d.get("activities", [])]
    acts = [a for a in acts if a["smiles"]]
    cache.write_text(json.dumps(acts, indent=1), encoding="utf-8")
    return acts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem

    targets = resolve_target(args.target)
    if not targets:
        print(f"no ChEMBL target matched {args.target!r}")
        return 1
    tgt = targets[0]
    print(f"target: {tgt['name']} ({tgt['chembl_id']}, {tgt['type']})")

    acts = fetch_actives(tgt["chembl_id"], args.limit)
    print(f"known actives (IC50 ≤ 10 µM, with SMILES): {len(acts)}")

    def fp(smi):
        m = Chem.MolFromSmiles(smi)
        return AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048) if m else None

    act_fps = [(a, fp(a["smiles"])) for a in acts]
    act_fps = [(a, f) for a, f in act_fps if f is not None]

    rows = list(csv.DictReader(COMPOUNDS.open(encoding="utf-8")))
    scored = []
    t0 = time.time()
    for r in rows:
        smi = (r.get("smiles") or "").strip()
        if not smi:
            continue
        f = fp(smi)
        if f is None:
            continue
        sims = DataStructs.BulkTanimotoSimilarity(f, [x[1] for x in act_fps])
        best = max(sims) if sims else 0.0
        if best > 0:
            j = sims.index(best)
            scored.append({"name": r.get("name"), "smiles": smi,
                           "plant_binomial": r.get("plant_binomial") or "",
                           "compound_class": r.get("compound_class") or "",
                           "tanimoto": round(best, 4),
                           "matched_active": act_fps[j][0]["chembl_id"],
                           "matched_active_nM": act_fps[j][0]["value_nM"]})
    scored.sort(key=lambda x: -x["tanimoto"])

    out = {"target_query": args.target, "target": tgt, "n_actives": len(act_fps),
           "n_compounds_screened": len(rows), "method": "ECFP4 (Morgan r=2, 2048) Tanimoto vs known actives",
           "top": scored[: args.top]}
    p = ROOT / "artifacts" / f"chembl_screen_{args.target.replace(' ', '_')}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\ntop {min(args.top, len(scored))} plant compounds by ECFP similarity to {tgt['name']} actives "
          f"({time.time()-t0:.0f}s):")
    for s in scored[: args.top]:
        print(f"  {s['tanimoto']:.3f}  {s['name'][:38]:<38} [{s['compound_class'] or '?'}]"
              f"  plant={s['plant_binomial'][:24]}")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
