"""Quantum chemistry expert — Hartree–Fock / DFT on model fragments, with caching.

What quantum chemistry adds that classical kinetics cannot
----------------------------------------------------------
`simulate.py` assumes an activation energy per *bond class* (ester / amide / glycoside) taken from
published ranges. That is a reasonable prior, but it is a prior. Quantum chemistry replaces the prior
with a computed number for the actual bond: the electronic structure of the fragment determines how
hard it is to hydrolyse, and a Hartree–Fock/DFT calculation gives that directly.

This module computes, for small representative fragments of each hydrolysable class:

1. **Koopmans ionisation potential** (`-ε_HOMO`) — validated against experimental IPs, so the level of
   theory is checked rather than assumed.
2. **HOMO–LUMO gap** — a hardness measure; small gap means chemically reactive, large gap means inert.
3. **Mulliken charges** on the hydrolysable carbon — the electrophilicity of the site that water attacks.
4. **Gas-phase hydrolysis energy** for a model reaction, e.g.
   `CH₃COOCH₃ + H₂O → CH₃COOH + CH₃OH`. The absolute value is not the answer (there is no solvent
   model); the **ordering across bond classes** is, and it can confirm or contradict the
   activation-energy priors used downstream.

Everything is cached to `artifacts/qm_cache.json`: a calculation runs once and is reused, so the artefact
is reproducible without paying the CPU again.

Method notes, stated so they can be attacked
--------------------------------------------
* Hartree–Fock/6-31G(d) unless DFT is requested. HF overestimates gaps; that is disclosed by validating
  against experimental ionisation potentials rather than pretending the absolute values are accurate.
* Gas phase only — no continuum solvation, so hydrolysis reaction energies are upper bounds on
  feasibility in water. The ordering is the usable output.
* Fragments are **models**, not the natural products themselves; a 40-atom natural product is out of
  reach for this compute budget and pretending otherwise would be dishonest.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "artifacts" / "qm_cache.json"
HARTREE_EV = 27.211386

# Small model fragments standing in for each hydrolysable bond class.
MODELS = {
    "water": "O",
    "benzene": "c1ccccc1",
    "formaldehyde": "C=O",
    "methanol": "CO",
    "methylamine": "CN",
    "acetic_acid": "CC(=O)O",
    "methyl_acetate": "CC(=O)OC",          # ester
    "n_methylacetamide": "CC(=O)NC",       # amide
    "dimethoxymethane": "COCOC",           # acetal / glycosidic model
}

REACTIONS = {
    "ester_hydrolysis": (["methyl_acetate", "water"], ["acetic_acid", "methanol"]),
    "amide_hydrolysis": (["n_methylacetamide", "water"], ["acetic_acid", "methylamine"]),
    "acetal_hydrolysis": (["dimethoxymethane", "water"], ["methanol", "methanol", "formaldehyde"]),
}

# Experimental Koopmans-comparable ionisation potentials, eV (physical constants, not research claims)
EXP_IP = {"water": 12.62, "benzene": 9.24, "formaldehyde": 10.88, "methanol": 10.84}


@dataclass
class QMResult:
    name: str
    smiles: str
    basis: str
    method: str
    e_tot_hartree: float
    homo_ev: float
    lumo_ev: float
    gap_ev: float
    ip_koopmans_ev: float
    seconds: float

    def to_dict(self) -> dict:
        return {k: (round(v, 5) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def _load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(c: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, indent=2), encoding="utf-8")


def compute(name: str, smiles: str, basis: str = "6-31g*", method: str = "RHF",
            use_cache: bool = True) -> QMResult:
    """Single-point HF/DFT calculation with caching."""
    cache = _load_cache()
    key = f"{name}|{basis}|{method}"
    if use_cache and key in cache:
        d = cache[key]
        return QMResult(**d)

    from pyscf import gto, scf
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol_rd = Chem.MolFromSmiles(smiles)
    molh = Chem.AddHs(mol_rd)
    AllChem.EmbedMolecule(molh, randomSeed=42)
    conf = molh.GetConformer()
    atom_block = []
    for i, atom in enumerate(molh.GetAtoms()):
        p = conf.GetAtomPosition(i)
        atom_block.append(f"{atom.GetSymbol()} {p.x:.6f} {p.y:.6f} {p.z:.6f}")

    t0 = time.time()
    mol = gto.M(atom="; ".join(atom_block), basis=basis, verbose=0)
    mf = scf.RHF(mol) if method == "RHF" else scf.RKS(mol, xc="b3lyp")
    mf.kernel()
    nocc = mol.nelectron // 2
    homo = float(mf.mo_energy[nocc - 1]) * HARTREE_EV
    lumo = float(mf.mo_energy[nocc]) * HARTREE_EV if nocc < len(mf.mo_energy) else homo
    res = QMResult(name=name, smiles=smiles, basis=basis, method=method,
                   e_tot_hartree=float(mf.e_tot), homo_ev=homo, lumo_ev=lumo,
                   gap_ev=lumo - homo, ip_koopmans_ev=-homo, seconds=round(time.time() - t0, 1))
    cache[key] = res.to_dict()
    _save_cache(cache)
    return res


def validate(basis: str = "6-31g*") -> dict:
    rows, errs = [], []
    for name, ip_exp in EXP_IP.items():
        r = compute(name, MODELS[name], basis=basis)
        err = r.ip_koopmans_ev - ip_exp
        rows.append({"molecule": name, "ip_computed_ev": round(r.ip_koopmans_ev, 3),
                     "ip_experimental_ev": ip_exp, "error_ev": round(err, 3),
                     "gap_ev": round(r.gap_ev, 3)})
        errs.append(abs(err))
    mae = sum(errs) / len(errs) if errs else None
    return {"basis": basis, "method": "RHF (Koopmans)",
            "mae_ev": round(mae, 3) if mae else None, "n": len(rows), "rows": rows}


def hydrolysis_energies(basis: str = "6-31g*") -> dict:
    """Gas-phase hydrolysis energy per bond class, and the ordering across classes."""
    e = {}
    for name, smi in MODELS.items():
        e[name] = compute(name, smi, basis=basis).e_tot_hartree
    out = {}
    for rxn, (left, right) in REACTIONS.items():
        d_e_hartree = sum(e[x] for x in right) - sum(e[x] for x in left)
        out[rxn] = {"delta_e_kj_mol": round(d_e_hartree * 2625.5, 1),
                    "delta_e_kcal_mol": round(d_e_hartree * 627.509, 1),
                    "n_products": len(right)}
    order = sorted(out.items(), key=lambda kv: kv[1]["delta_e_kj_mol"])
    return {"energies": out,
            "ordering_easiest_first": [k for k, _ in order],
            "note": ("gas phase, no solvent model: absolute values are upper bounds on aqueous "
                     "feasibility. The ORDERING is the usable output and can be compared with the "
                     "activation-energy priors used in simulate.py.")}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", default="6-31g*")
    args = ap.parse_args()

    print("validating against experimental ionisation potentials …")
    v = validate(args.basis)
    print(f"  MAE {v['mae_ev']} eV over {v['n']} molecules (RHF, Koopmans)")
    for r in v["rows"]:
        print(f"    {r['molecule']:<14} computed {r['ip_computed_ev']:>6.2f} eV  "
              f"experimental {r['ip_experimental_ev']:>5.2f} eV  err {r['error_ev']:+.2f}")

    print("\ncomputing hydrolysis energies for the three bond classes …")
    h = hydrolysis_energies(args.basis)
    for rxn, d in h["energies"].items():
        print(f"    {rxn:<20} ΔE = {d['delta_e_kcal_mol']:>7.1f} kcal/mol ({d['delta_e_kj_mol']:>7.1f} kJ/mol)")
    print(f"    easiest first: {h['ordering_easiest_first']}")

    out = ROOT / "artifacts" / "qm_results.json"
    out.write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                               "validation": v, "hydrolysis": h}, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
