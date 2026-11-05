"""Pipeline 2 — deterministic physical outcome of a preparation.

Pipeline 1 produces hypotheses from the records. Pipeline 2 asks a different question and answers it
with arithmetic: **given a compound of this structure and a process at this temperature, medium and
duration, what fraction of it survives — and how confident are we?**

Three physical sinks are modelled, each with a stated mechanism:

1. **Volatilisation** — Clausius–Clapeyron vapour pressure at the process temperature, and a
   first-order stripping rate proportional to `P_sat(T)/P_sat(ref)`. Steam or open-dry processes strip
   volatile compounds; sealed or cold processes do not.
2. **Hydrolysis** — Arrhenius rate with a bond-class activation energy (ester < amide < glycoside <
   unreactive), active only when the medium carries water and T ≥ 60 °C.
3. **Thermal degradation** — switches on above a fraction of the boiling point, the usual proxy for
   where organic molecules start to decompose.

The output is a **retention fraction with a sensitivity range**, produced from the same inputs every
time. A hypothesis claiming *enrichment* whose modelled retention is 8 % is not "disagreed with" — it is
shown to be physically backwards, with the arithmetic visible.

What this is not: molecular dynamics or quantum chemistry. It is a lumped kinetic model with published
correlations, and its accuracy is bounded by the ±5 % boiling-point estimator it rests on (validated in
`estimators.py`). It answers "may / may not" at the level of order of magnitude, which is what a
preparation claim actually needs.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shennong.physics.estimators import HYDROLYSIS_EA, PhysicalState, estimate  # noqa: E402

R = 8.314
T_REF = 373.15

# Process conditions (T in K, medium, duration in seconds) — physics, not folklore.
PROCESS = {
    "蒸": (373.15, "steam", 1800),
    "煮": (373.15, "water", 3600),
    "煎": (373.15, "water", 1800),
    "焙": (343.15, "dry", 3600),
    "炒": (443.15, "dry", 900),
    "炒焦": (493.15, "dry", 600),
    "炒炭": (573.15, "dry", 600),
    "炮": (523.15, "dry", 1800),
    "煅": (973.15, "air", 3600),
    "煨": (393.15, "dry", 3600),
    "炙": (393.15, "aqueous_excipient", 1200),
    "蜜炙": (393.15, "aqueous_excipient", 1200),
    "醋炙": (393.15, "acid", 1200),
    "酒炙": (383.15, "ethanol", 1200),
    "淬": (673.15, "quench", 60),
    "研": (298.15, "mechanical", 300),
    "洗": (298.15, "water", 120),
    "浸": (298.15, "solvent", 86400),
    "漬": (298.15, "solvent", 86400),
    "伏": (423.15, "sealed", 1800),
    "麩炒": (443.15, "dry", 900),
    "土炒": (473.15, "dry", 900),
    "水飛": (298.15, "water", 600),
}

# Reference first-order volatilisation constant: a compound with P_sat = 1 kPa at 373 K loses ~half
# its mass in 30 min under an open aqueous/steam process. This is the single calibrated number in the
# model; the sensitivity band below shows how much the verdicts depend on it.
K_VOL_REF = 3.85e-4      # s^-1 at P_sat = 1 kPa, T = 373 K
P_SAT_REF = 1000.0       # Pa
E_VOL = 35_000.0         # J/mol, enthalpy-limited stripping
K_DEG_REF = 1.0e-4       # s^-1 at T = 0.85·Tb
SENSITIVITY = (0.3, 3.0)  # multiplicative band on all rate constants


@dataclass
class Retention:
    smiles: str
    tb_k: float
    psat_pa: float
    k_vol: float
    k_hyd: float
    k_deg: float
    t_seconds: float
    retained: float
    retained_range: tuple[float, float]
    mechanism: str

    def to_dict(self) -> dict:
        return {"smiles": self.smiles, "tb_k": round(self.tb_k, 1),
                "psat_pa": round(self.psat_pa, 2),
                "k_vol_s1": round(self.k_vol, 8), "k_hyd_s1": round(self.k_hyd, 8),
                "k_deg_s1": round(self.k_deg, 8), "seconds": self.t_seconds,
                "retained": round(self.retained, 4),
                "retained_range": [round(self.retained_range[0], 4), round(self.retained_range[1], 4)],
                "dominant_mechanism": self.mechanism}


def _psat(st: PhysicalState, t_k: float) -> float:
    if st.tb_k <= 0 or t_k <= 0:
        return 0.0
    ln_ratio = -(st.dhvap_j_mol / R) * (1.0 / t_k - 1.0 / st.tb_k)
    return 101325.0 * math.exp(max(-50.0, min(50.0, ln_ratio)))


def _hydrolysis_class(st: PhysicalState) -> str:
    """Which hydrolysable bond class dominates this structure, from functional flags."""
    smi = st.smiles
    if "OC=O" in smi or "C(=O)O" in smi and "O" in smi[smi.find("C(=O)O") + 5:]:
        return "ester"
    if "C(=O)N" in smi:
        return "amide"
    if "OC1" in smi and st.mw > 250:
        return "glycoside"
    return "none"


def simulate(smiles: str, process: str, t_seconds: float | None = None) -> Retention | None:
    """Deterministic retention of a compound under one classical preparation."""
    cond = PROCESS.get(process)
    st = estimate(smiles)
    if not cond or not st.valid:
        return None
    t_k, medium, duration = cond
    dur = float(t_seconds if t_seconds is not None else duration)

    psat = _psat(st, t_k)
    open_process = medium in ("steam", "water", "dry", "air", "aqueous_excipient", "acid")
    k_vol = 0.0
    if open_process and psat > 0:
        k_vol = K_VOL_REF * (psat / P_SAT_REF) * math.exp(
            -(E_VOL / R) * (1.0 / t_k - 1.0 / T_REF))
        k_vol = min(k_vol, 5.0)

    k_hyd = 0.0
    if medium in ("water", "steam", "aqueous_excipient", "acid") and t_k >= 333.15:
        lo, hi = HYDROLYSIS_EA[_hydrolysis_class(st)]
        ea = 0.5 * (lo + hi)
        k_hyd = 1.0e-4 * math.exp(-(ea / R) * (1.0 / t_k - 1.0 / T_REF))

    k_deg = 0.0
    t_onset = 0.85 * st.tb_k
    if t_k > t_onset:
        k_deg = K_DEG_REF * math.exp(-(60_000.0 / R) * (1.0 / t_k - 1.0 / t_onset))

    k_tot = k_vol + k_hyd + k_deg
    retained = math.exp(-k_tot * dur)
    lo, hi = SENSITIVITY
    r_hi = math.exp(-k_tot * lo * dur)     # most conservative loss
    r_lo = math.exp(-k_tot * hi * dur)     # most aggressive loss

    mech = max((("volatilisation", k_vol), ("hydrolysis", k_hyd), ("thermal", k_deg)),
               key=lambda x: x[1])[0]
    if k_tot < 1e-9:
        mech = "none (no active sink)"

    return Retention(smiles=smiles, tb_k=st.tb_k, psat_pa=psat, k_vol=k_vol, k_hyd=k_hyd,
                     k_deg=k_deg, t_seconds=dur, retained=retained,
                     retained_range=(r_lo, r_hi), mechanism=mech)


def classify(retained: float) -> str:
    if retained >= 0.90:
        return "RETAINED"
    if retained >= 0.50:
        return "PARTIALLY RETAINED"
    if retained >= 0.10:
        return "LARGELY LOST"
    return "EFFECTIVELY DESTROYED"


def deterministic_verdict(retained: float, claim_says: str = "enrich") -> dict:
    """Turn the number into may / may-not, relative to what the hypothesis claims."""
    cls = classify(retained)
    if claim_says == "enrich":
        if retained >= 0.90:
            verdict = "MAY — the physics allows enrichment (the class is stable under this process)"
        elif retained >= 0.50:
            verdict = ("MAY NOT as stated — partial loss; enrichment of the parent class is "
                       "physically implausible, though a derivative may be enriched")
        else:
            verdict = ("MAY NOT — the class is largely destroyed; a claim of enrichment is "
                       "physically backwards under these conditions")
    else:
        verdict = f"MAY — modelled retention {retained:.0%} ({cls}), consistent with a reduction claim"
    return {"retained": round(retained, 4), "class": cls, "verdict": verdict}


if __name__ == "__main__":
    for proc in ("蒸", "炒", "炮", "煮", "研"):
        r = simulate("CC(=CCC1CC=C(C=C1)C)C", proc)   # limonene, a monoterpene
        if r:
            print(f"{proc} → limonene retained {r.retained:6.1%} "
                  f"(range {r.retained_range[0]:.0%}–{r.retained_range[1]:.0%}), "
                  f"dominant {r.mechanism}")
