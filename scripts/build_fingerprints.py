#!/usr/bin/env python3
"""Precompute ECFP4 fingerprints for every compound, so the live screen is fast.

The virtual screen fingerprints 23,176 plant compounds on every call. On a 2-vCPU Space that takes long
enough to hit the request timeout. This writes them once to `artifacts/compound_fps.pkl`; `chembl_rank`
loads that instead of recomputing, cutting a screen from ~40 s to ~2 s.

    python scripts/build_fingerprints.py
"""
from __future__ import annotations

import csv
import pathlib
import pickle
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPOUNDS = ROOT / "corpus" / "processed" / "structured" / "compounds.csv"
OUT = ROOT / "artifacts" / "compound_fps.pkl"


def main() -> int:
    try:
        from rdkit import Chem, DataStructs
        from rdkit.Chem import AllChem
    except ImportError:
        print("rdkit not installed — skipping fingerprint cache")
        return 0

    rows = list(csv.DictReader(COMPOUNDS.open(encoding="utf-8")))
    t0 = time.time()
    out = []
    for r in rows:
        smi = (r.get("smiles") or "").strip()
        if not smi:
            continue
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        fp = AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048)
        out.append((r.get("name") or "", smi, r.get("plant_binomial") or "",
                    r.get("compound_class") or "", DataStructs.BitVectToBinaryText(fp)))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("wb") as fh:
        pickle.dump(out, fh, protocol=4)
    print(f"cached {len(out):,} fingerprints -> {OUT} ({OUT.stat().st_size/1e6:.1f} MB, {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
