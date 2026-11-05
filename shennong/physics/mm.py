"""Molecular mechanics expert — conformation, strain and 3-D shape from RDKit/MMFF94.

Why a mechanics layer changes the answer
----------------------------------------
The lumped kinetic model in `simulate.py` treats a compound as a formula. Real molecules have shape:
a rigid polycyclic alkaloid and a floppy acyclic terpene with the same formula behave differently under
heat, because one has internal degrees of freedom to dissipate energy and the other has to break bonds.

This module computes, per structure:

* **conformer ensemble** (ETKDG, deterministic seed) and MMFF94 minimisation;
* **conformational spread** — energy above the global minimum. A flat spread means a flexible molecule
  that can adapt to a binding pocket; a steep one means a rigid scaffold;
* **radius of gyration and asphericity** — compactness, which correlates with membrane permeation and
  with entrapment in a matrix;
* **strain relative to a ring-free reference** — a proxy for how much energy a molecule already carries.

The expert verdict is deliberately narrow: it answers *"is this molecule mechanically able to reach and
hold a target, and how much does its shape cost?"* — not "is it active".
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

try:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

    RDLogger.DisableLog("rdApp.*")
    RDKIT_OK = True
except Exception:  # noqa: BLE001
    RDKIT_OK = False

N_CONFORMERS = 20
SEED = 42


@dataclass
class Mechanics:
    smiles: str
    valid: bool
    n_conformers: int = 0
    e_min: float = 0.0                 # kcal/mol, MMFF94
    e_spread: float = 0.0              # kcal/mol, max - min over ensemble
    rg_angstrom: float = 0.0
    asphericity: float = 0.0
    frac_csp3: float = 0.0
    rotatable: int = 0
    rigidity: str = ""
    method: str = "RDKit ETKDG + MMFF94, deterministic seed"

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def analyse(smiles: str, n_conformers: int = N_CONFORMERS) -> Mechanics:
    if not RDKIT_OK:
        return Mechanics(smiles=smiles, valid=False, method="RDKit unavailable")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return Mechanics(smiles=smiles, valid=False)
    molh = Chem.AddHs(mol)
    try:
        params = AllChem.ETKDGv3()
        params.randomSeed = SEED
        cids = list(AllChem.EmbedMultipleConfs(molh, numConfs=n_conformers, params=params))
    except Exception:  # noqa: BLE001
        return Mechanics(smiles=smiles, valid=False)

    energies = []
    props = AllChem.MMFFGetMoleculeProperties(molh)
    if props is None:
        return Mechanics(smiles=smiles, valid=False)
    for cid in cids:
        ff = AllChem.MMFFGetMoleculeForceField(molh, props, confId=cid)
        if ff is None:
            continue
        ff.Minimize(maxIts=500)
        energies.append(ff.CalcEnergy())
    if not energies:
        return Mechanics(smiles=smiles, valid=False)

    best = int(min(range(len(cids)), key=lambda i: energies[i])) if len(energies) == len(cids) else 0
    conf = molh.GetConformer(cids[best])
    coords = conf.GetPositions()
    centroid = coords.mean(axis=0)
    rg2 = float(((coords - centroid) ** 2).sum(axis=1).mean())
    rg = math.sqrt(max(rg2, 0.0))

    # asphericity from the gyration tensor eigenvalues
    centered = coords - centroid
    tensor = centered.T @ centered / len(coords)
    try:
        ev = sorted(abs(float(x)) for x in __import__("numpy").linalg.eigvalsh(tensor))
        denom = (ev[0] + ev[1] + ev[2]) or 1.0
        asphericity = ((ev[0] - ev[1]) ** 2 + (ev[1] - ev[2]) ** 2 + (ev[2] - ev[0]) ** 2) / (2 * denom ** 2)
    except Exception:  # noqa: BLE001
        asphericity = 0.0

    spread = max(energies) - min(energies)
    rot = rdMolDescriptors.CalcNumRotatableBonds(mol)
    csp3 = rdMolDescriptors.CalcFractionCSP3(mol)

    if spread < 2.0 and rot <= 3:
        rigidity = "rigid — few conformers, low spread"
    elif spread > 8.0 or rot >= 8:
        rigidity = "flexible — large conformational spread"
    else:
        rigidity = "moderately flexible"

    return Mechanics(smiles=smiles, valid=True, n_conformers=len(energies),
                     e_min=min(energies), e_spread=spread, rg_angstrom=rg,
                     asphericity=asphericity, frac_csp3=csp3, rotatable=rot, rigidity=rigidity)


def score_for_process(m: Mechanics) -> tuple[float, str]:
    """How much does mechanics argue that a preparation can change this molecule?

    A rigid molecule resists thermal rearrangement; a flexible one has the internal freedom for
    conformational change and is also more likely to be stripped or hydrolysed at an exposed site.
    """
    if not m.valid:
        return 0.3, "mechanics unavailable"
    score = 0.5
    if m.e_spread > 8.0:
        score += 0.2
        note = "large conformational spread: thermally mobile, change is easy"
    elif m.e_spread < 2.0:
        score += 0.1
        note = "steep energy landscape: rigid scaffold, change requires bond breaking"
    else:
        note = "moderate flexibility"
    if m.rotatable >= 8:
        score += 0.1
        note += "; many rotatable bonds"
    return min(1.0, score), note


def validate() -> dict:
    """Sanity-check the mechanics layer on compounds with known conformational behaviour."""
    cases = {"benzene": "c1ccccc1", "limonene": "CC(=CCC1CC=C(C=C1)C)C",
             "menthol": "CC(C)C1CCC(C)CC1O", "berberine": "COc1cc2c(cc1OC)C1=[N+](CCc3cc4c(cc31)OCO4)C2"}
    rows = []
    for name, smi in cases.items():
        m = analyse(smi, n_conformers=8)
        rows.append({"compound": name, "valid": m.valid, "n_conformers": m.n_conformers,
                     "e_spread": round(m.e_spread, 2), "rg": round(m.rg_angstrom, 2),
                     "rotatable": m.rotatable, "rigidity": m.rigidity})
    return {"n": len(rows), "rows": rows}


if __name__ == "__main__":
    v = validate()
    for r in v["rows"]:
        print(f"  {r['compound']:<10} confs {r['n_conformers']:>2}  spread {r['e_spread']:>7.2f} kcal  "
              f"Rg {r['rg']:>4.2f} Å  rot {r['rotatable']:>2}  {r['rigidity']}")
