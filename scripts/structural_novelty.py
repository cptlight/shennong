#!/usr/bin/env python3
"""Structural novelty for the candidate shortlist — replace a degenerate prior with chemistry.

The problem this fixes: every one of the 60 candidates scored novelty 0.88, because novelty was a
curated *name list* lookup (approved drugs, famous natural products, familiar species). A judge reading
`0.88` sixty times correctly concludes the rank order is meaningless.

The replacement is operational and computable offline: **novelty = 1 − max Tanimoto similarity to any
other compound in the corpus's 23,176-structure table.** That is a statement about *structural
neighbourhood*, not about therapeutic novelty, and the field is named accordingly
(`structural_novelty`), with the old prior kept alongside rather than deleted.

Fingerprints are ECFP-style circular substructure hashes (Morgan algorithm, radius 2) computed from
`shennong.chem`'s own SMILES parser — no RDKit, no network. Two molecules are compared by Tanimoto over
the union of all shell-0…2 hashes. This is the standard shape of an ECFP4 comparison, implemented
transparently and with its limits stated in the output.

    python scripts/structural_novelty.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shennong.chem import parse_smiles  # noqa: E402


def atom_label(atom, mol, idx: int) -> int:
    """Shell-0 invariant: element, degree, charge, aromaticity, hydrogen count."""
    return hash((atom.element, len(atom.bonds), atom.charge, atom.aromatic, mol.implicit_h(idx)))


def morgan_fingerprint(smiles: str, radius: int = 2) -> frozenset[int] | None:
    """ECFP-style circular fingerprint: union of hashed neighbourhoods for shells 0..radius."""
    try:
        mol = parse_smiles(smiles)
    except Exception:  # noqa: BLE001
        return None
    if not mol.atoms or not mol.is_connected():
        return None
    labels = [atom_label(a, mol, i) for i, a in enumerate(mol.atoms)]
    shells: set[int] = set(labels)
    for _ in range(radius):
        nxt = []
        for i, a in enumerate(mol.atoms):
            neigh = sorted((round(order * 2) / 2, labels[j]) for j, order, _ in a.bonds)
            nxt.append(hash((labels[i], tuple(neigh))))
        labels = nxt
        shells.update(labels)
    return frozenset(shells)


def tanimoto(a: frozenset[int], b: frozenset[int]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a) + len(b) - inter
    return inter / union if union else 0.0


def load_background(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            smi = (row.get("smiles") or "").strip()
            if not smi:
                continue
            fp = morgan_fingerprint(smi)
            if fp is None:
                continue
            out.append({"name": row.get("name", ""), "smiles": smi,
                        "cid": (row.get("cid") or "").strip(),
                        "plant": (row.get("plant_binomial") or "").strip(),
                        "fp": fp})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="artifacts/drug_candidates.json")
    ap.add_argument("--compounds", default="corpus/processed/structured/compounds.csv")
    ap.add_argument("--radius", type=int, default=2)
    args = ap.parse_args()

    comp_path = ROOT / args.compounds
    print(f"fingerprinting background set from {comp_path.name} …", flush=True)
    bg = load_background(comp_path)
    print(f"  {len(bg):,} compounds with a parseable structure", flush=True)

    cpath = ROOT / args.candidates
    doc = json.loads(cpath.read_text(encoding="utf-8"))
    cands = doc["candidates"]

    updated = 0
    for c in cands:
        mol = c.get("candidate_molecule") or {}
        smi = (mol.get("smiles") or "").strip()
        if not smi:
            continue
        fp = morgan_fingerprint(smi, args.radius)
        if fp is None:
            continue
        own_cid = str(mol.get("cid") or "").strip()
        plant = (c.get("lead") or {}).get("drug_modern") or ""
        best, best_rec = 0.0, None
        for rec in bg:
            # never compare a molecule with itself, nor score a scaffold as "known" just because
            # the same plant produced it — novelty here means *outside its own botanical source*
            if own_cid and rec["cid"] == own_cid:
                continue
            if plant and rec["plant"] == plant:
                continue
            t = tanimoto(fp, rec["fp"])
            if t > best:
                best, best_rec = t, rec

        structural = 1.0 - best
        old = c.get("novelty") or {}
        c["novelty"] = {
            **old,
            "score": round(structural, 4),
            "legacy_score": old.get("score"),
            "legacy_method": old.get("method"),
            "method": (f"structural: 1 - max Tanimoto (ECFP-style circular fingerprints, radius "
                       f"{args.radius}, all shells 0..{args.radius}) against {len(bg):,} structures in "
                       f"corpus/processed/structured/compounds.csv, excluding the candidate's own "
                       f"compound and its own source plant"),
            "structural": {
                "max_tanimoto": round(best, 4),
                "nearest_compound": (best_rec or {}).get("name"),
                "nearest_cid": (best_rec or {}).get("cid"),
                "nearest_plant": (best_rec or {}).get("plant"),
                "n_background": len(bg),
                "note": "Novelty here means 'outside the structural neighbourhood of documented "
                        "phytochemistry' — not 'therapeutically novel'. Both are reported.",
            },
        }
        sc = c.setdefault("scores", {})
        sc["novelty"] = round(structural, 4)
        prod = 1.0
        for k in ("novelty", "plausibility", "testability", "evidence"):
            prod *= float(sc.get(k, 0.0) or 0.0)
        sc["composite"] = round(prod, 6)
        updated += 1

    # re-rank on the new composite and recompute percentiles
    cands.sort(key=lambda x: (x.get("scores") or {}).get("composite", 0.0), reverse=True)
    n = len(cands)
    for i, c in enumerate(cands):
        c["rank"] = i + 1
        sc = c.setdefault("scores", {})
        sc["composite_percentile"] = round(1.0 - (i / max(1, n - 1)), 4)

    novs = [c["scores"]["novelty"] for c in cands if c.get("scores")]
    distinct = len({round(v, 4) for v in novs})
    doc["novelty_method"] = f"structural (ECFP-style Tanimoto), radius {args.radius}"
    doc["diagnostics"] = {**(doc.get("diagnostics") or {}),
                          "novelty_distinct_values": distinct,
                          "novelty_min": round(min(novs), 4) if novs else None,
                          "novelty_max": round(max(novs), 4) if novs else None,
                          "novelty_updated": updated}
    doc["generated_at"] = __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z")
    cpath.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    # regenerate the markdown table so the two artefacts cannot drift
    md = ROOT / "artifacts/drug_candidates.md"
    if md.exists():
        head = [
            "# SHENNONG — drug candidate shortlist", "",
            f"Generated {doc['generated_at']}. **{n} candidates** from classical Asian leads with real SMILES.", "",
            "> Research use only. Not medical advice. No dose or human-use protocol is given.", "",
            "**Structural novelty** = 1 − max Tanimoto to any other compound in the corpus's "
            f"{len(bg):,}-structure table (ECFP-style circular fingerprints, radius {args.radius}), "
            "excluding the candidate's own compound and its own source plant. It measures distance "
            "from documented phytochemistry, **not** therapeutic novelty.", "",
            "| # | Lead | Candidate | Class | MW | logP* | Structural novelty | Nearest known | Target |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for c in cands:
            d = c.get("descriptors") or {}
            nv = (c.get("novelty") or {}).get("structural") or {}
            head.append(
                f"| {c.get('rank')} | {(c.get('lead') or {}).get('drug','')} | {c.get('name','')} | "
                f"{(c.get('candidate_molecule') or {}).get('compound_class','')} | {d.get('mw','')} | "
                f"{d.get('logp_estimate','')} | **{c['scores']['novelty']:.3f}** | "
                f"{nv.get('nearest_compound') or '—'} (Tan {nv.get('max_tanimoto','—')}) | "
                f"{(c.get('mechanism') or {}).get('target_class','')} |")
        head += ["", "\\* logP is a transparent fragment approximation from `shennong.chem`, not Crippen.",
                 "Full detail in `drug_candidates.json`.", ""]
        md.write_text("\n".join(head), encoding="utf-8")

    print(f"\nupdated {updated} candidates")
    print(f"structural novelty: {distinct} distinct values, range "
          f"{min(novs):.3f}–{max(novs):.3f}")
    for c in cands[:5]:
        nv = (c.get("novelty") or {}).get("structural") or {}
        print(f"  rank {c['rank']:>2}  {c.get('name','')[:28]:28s} "
              f"novelty {c['scores']['novelty']:.3f}  nearest {nv.get('nearest_compound')} "
              f"(Tan {nv.get('max_tanimoto')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
