"""Two additional experts: molecular mechanics and quantum chemistry.

These raise the expertise of the panel without touching the model. The mechanics expert runs RDKit
MMFF94 on a representative structure for the plant×chemotype; the quantum expert maps the chemotype to a
hydrolysable bond class and reads the computed electronic-structure result for that class (cached, so it
costs nothing per call).

Both are assigned to the FIRST_PRINCIPLES stage, because that is what they are: physical arbitration,
not literature.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shennong.experts.base import Proposal  # noqa: E402
from shennong.physics import mm as MM  # noqa: E402

QM_RESULTS = ROOT / "artifacts" / "qm_results.json"

# Which hydrolysable bond class stands in for each compound class.
BOND_CLASS_OF = {
    "alkaloid": "amide_hydrolysis",       # many alkaloids carry amide/ester linkages
    "glycoside": "acetal_hydrolysis",
    "flavonoid": "acetal_hydrolysis",     # O-glycosides dominate
    "terpenoid": "none",
    "volatile_oil": "none",
    "phenylpropanoid": "ester_hydrolysis",  # esters (e.g. cinnamates) common
    "polyketide": "ester_hydrolysis",
    "polysaccharide": "acetal_hydrolysis",
    "protein": "amide_hydrolysis",
    "organosulfur": "none",
    "mineral": "none",
}

# Which chemistry each process demands, so the expert can ask whether the class can supply it.
OXIDATION_PROCESSES = {"煅", "炒炭", "淬", "伏", "炮"}
HYDROLYSIS_PROCESSES = {"蒸", "煮", "煎", "浸", "漬", "炙", "蜜炙", "醋炙", "酒炙"}
DRY_THERMAL = {"炒", "炒焦", "炒炭", "炮", "煨", "焙", "麩炒", "土炒"}


def _qm() -> dict:
    if not QM_RESULTS.exists():
        return {}
    try:
        return json.loads(QM_RESULTS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def mechanics_expert(world, item: dict) -> Proposal:
    """Is the molecule mechanically able to change under this preparation, or to be held by a target?"""
    smis = (getattr(world, "class_smiles", {}) or {}).get(
        (item.get("binomial"), item.get("chemotype"))) or []
    if not smis:
        return Proposal("mechanics", 0.30, "no structure available for a mechanics calculation", [])
    m = MM.analyse(smis[0], n_conformers=10)
    if not m.valid:
        return Proposal("mechanics", 0.30, "mechanics calculation failed", [])
    score, note = MM.score_for_process(m)
    proc = item.get("process") or ""
    if proc in DRY_THERMAL and m.e_spread < 2.0:
        score = min(1.0, score + 0.1)
        note += "; rigid thermophile under dry heat"
    return Proposal("mechanics", score,
                    f"{m.rigidity}; conformational spread {m.e_spread:.1f} kcal, Rg {m.rg_angstrom:.1f} Å, "
                    f"{m.rotatable} rotatable bonds. {note}",
                    [f"{m.method}", f"MMFF94 min {m.e_min:.1f} kcal/mol"])


def quantum_expert(world, item: dict) -> Proposal:
    """Does the electronic structure of this bond class support the claimed transformation?"""
    q = _qm()
    bond = BOND_CLASS_OF.get((item.get("chemotype") or "").lower())
    if not bond or bond == "none" or not q:
        return Proposal("quantum", 0.30,
                        "no hydrolysable bond class for this chemotype (or QM results not computed)",
                        [])
    energy = q.get("hydrolysis", {}).get("energies", {}).get(bond)
    order = q.get("hydrolysis", {}).get("ordering_easiest_first", [])
    mae = q.get("validation", {}).get("mae_ev")
    if not energy:
        return Proposal("quantum", 0.30, f"no computed ΔE for {bond}", [])

    de = energy["delta_e_kj_mol"]
    rank = order.index(bond) if bond in order else None
    proc = item.get("process") or ""

    if proc in HYDROLYSIS_PROCESSES:
        # for a hydrolysis-type process, a smaller ΔE means the class reacts more readily
        score = 0.85 if de < 60 else 0.65 if de < 120 else 0.45
        note = (f"{bond}: computed hydrolysis ΔE {de:.0f} kJ/mol (gas phase); "
                f"rank {rank + 1 if rank is not None else '?'}/{len(order)} easiest-first")
    elif proc in OXIDATION_PROCESSES:
        score = 0.55
        note = f"{proc} is oxidative/thermal; hydrolysis ΔE is not the controlling number for this class"
    else:
        score = 0.5
        note = f"{proc} does not demand hydrolysis; electronic-structure evidence is indirect"

    return Proposal("quantum", score, note,
                    [f"RHF/{q.get('validation', {}).get('basis', '?')} Koopmans IP MAE "
                     f"{mae} eV vs experiment",
                     f"{bond} ΔE {de:.0f} kJ/mol"])


ADVANCED_EXPERTS = {"mechanics": mechanics_expert, "quantum": quantum_expert}
