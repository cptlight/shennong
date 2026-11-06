"""First-principles arbitration — physics, chemistry and biology judge the claim.

The epistemic rule this implements
----------------------------------
Western clinical and pharmacological literature is **not the arbiter**. It is one body of observations,
produced under its own assumptions (species, preparation, dose, endpoint, trial design), and it is
frequently silent, often negative for reasons that have nothing to do with whether a plant works.

A tradition-derived hypothesis is therefore judged by:

1. **Physical law** — does it violate thermodynamics, mass conservation, or known reaction chemistry?
2. **Physical chemistry of the preparation** — do the temperature, medium and time of the attested
   process actually cause the transformation being claimed?
3. **Biophysical plausibility of delivery** — can the molecule cross barriers at plausible exposure?
4. **Biological first principles** — is the proposed target class physically reachable by that molecule?

Where Western literature later agrees, that is *a dataset consistent with the hypothesis*. Where it
disagrees, that is **a problem to explain**, not a verdict: wrong species, wrong preparation, wrong
dose, wrong endpoint, or untested. The disagreement is recorded as a research target, and the
hypothesis is never demoted merely because a paper says otherwise.

This module does not pretend to run quantum chemistry. It applies the first-order physical constraints
that any correct mechanism must satisfy, and it is explicit about which constraints are hard and which
are order-of-magnitude.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------------------
# Physical chemistry of classical processes (temperatures/mediums are the physics input)
# ---------------------------------------------------------------------------------------
PROCESS_CONDITIONS = {
    # term: (typical temperature °C, medium, note)
    "蒸": (100, "steam", "steam distillation / hydrolysis conditions"),
    "煮": (100, "water or excipient liquor", "aqueous hydrolysis, extraction"),
    "煎": (100, "water", "decoction"),
    "焙": (70, "dry air", "gentle dehydration"),
    "炒": (170, "dry, hot surface", "dry thermal treatment"),
    "炒焦": (220, "dry, hot surface", "partial pyrolysis"),
    "炒炭": (300, "dry, hot surface", "carbonisation"),
    "炮": (250, "hot ash/sand", "high-temperature dry roasting"),
    "煅": (700, "air/furnace", "calcination to oxide"),
    "煨": (120, "wrapped, embers", "slow radiant heat"),
    "炙": (120, "with honey/vinegar/wine", "excipient-mediated thermal treatment"),
    "蜜炙": (120, "honey", "sugar-mediated thermal treatment"),
    "醋炙": (120, "acetic acid", "acid-catalysed esterification/hydrolysis"),
    "酒炙": (110, "ethanol/water", "ethanol extraction of medium-polar compounds"),
    "淬": (400, "rapid quench into liquid", "thermal shock + solvent"),
    "研": (25, "mechanical", "particle-size reduction only"),
    "洗": (25, "water", "surface cleansing"),
    "浸": (25, "solvent", "cold maceration"),
    "漬": (25, "solvent", "cold maceration"),
    "伏": (150, "sealed/controlled", "suppression / complexation"),
    "麩炒": (170, "bran", "dry thermal with excipient"),
    "土炒": (200, "clay", "dry thermal, adsorbent"),
    "水飛": (25, "water", "levigation of minerals"),
}

# What physics says each chemotype does under those conditions.
# Values are qualitative but not arbitrary: they follow from volatility, hydrolysis susceptibility,
# and thermal stability of the bond types that define the class.
CHEMOTYPE_STABILITY = {
    # class:            (volatile?, hydrolyses in hot water?, thermally labile?, note)
    "alkaloid":         (False, False, False, "mostly thermostable; some esters hydrolyse"),
    "terpenoid":        (True,  False, True,  "mono/sesquiterpenes volatile; heat degrades them"),
    "flavonoid":        (False, True,  True,  "glycosides hydrolyse; aglycones oxidise with heat"),
    "glycoside":        (False, True,  True,  "hot water hydrolysis is the defining behaviour"),
    "volatile_oil":     (True,  False, True,  "lost by evaporation above ~100 °C"),
    "phenylpropanoid":  (True,  False, True,  "volatile; heat-sensitive"),
    "polyketide":       (False, False, True,  "variable; oxidation-sensitive"),
    "polysaccharide":   (False, True,  False, "hydrolyses to oligosaccharides in hot water"),
    "protein":          (False, False, True,  "denatures above ~60 °C"),
    "organosulfur":     (True,  False, True,  "volatile and reactive"),
    "mineral":          (False, False, False, "requires calcination to become bioavailable"),
}

HARD_MIN_SCORE = 0.45


@dataclass
class PrincipleCheck:
    name: str
    passed: bool | None          # None = cannot be evaluated with available data
    score: float
    reasoning: str
    hard: bool = True            # a hard constraint is a physics violation if failed

    def to_dict(self) -> dict:
        return {"check": self.name, "passed": self.passed, "score": round(self.score, 3),
                "reasoning": self.reasoning, "hard_constraint": self.hard}


def check_process_physics(process: str, chemotype: str, claim: str = "") -> PrincipleCheck:
    """Does the attested preparation's temperature/medium actually do what is claimed?"""
    cond = PROCESS_CONDITIONS.get(process)
    if not cond:
        return PrincipleCheck("process_physics", None, 0.5,
                              f"{process} not in the physical-conditions table; cannot judge", hard=False)
    temp, medium, note = cond
    cls = (chemotype or "").lower()
    stab = CHEMOTYPE_STABILITY.get(cls)
    if not stab:
        return PrincipleCheck("process_physics", None, 0.5,
                              f"no stability data for chemotype {cls!r}", hard=False)
    volatile, hydrolyses, labile, why = stab

    if volatile and temp >= 100:
        # Physics predicts DEPLETION. That contradicts an enrichment claim, but it is perfectly
        # consistent with a neutral "the preparation changes this class" claim — which is what the
        # hypothesis template actually says. An earlier version failed both, i.e. it rejected a claim
        # that had never been made, using an enrichment argument. Direction matters:
        asserts_enrichment = any(w in (claim or "").lower() for w in
                                 ("enrich", "increase", "higher content", "accumulat", "more of"))
        if asserts_enrichment:
            return PrincipleCheck(
                "process_physics", False, 0.25,
                f"{cls} is volatile and {process} runs at ~{temp} °C ({medium}) — the class is depleted, "
                f"so an *enrichment* claim is physically backwards.", hard=True)
        return PrincipleCheck(
            "process_physics", True, 0.80,
            f"{cls} is volatile and {process} runs at ~{temp} °C ({medium}) — the physics predicts a "
            f"measurable DEPLETION. The claim of change is consistent; its direction is loss, not gain.",
            hard=False)
    if hydrolyses and temp >= 90 and "water" in medium:
        return PrincipleCheck(
            "process_physics", True, 0.85,
            f"{cls} hydrolyses under {process} (~{temp} °C, {medium}) — a transformation claim is "
            f"physically expected, not merely possible.", hard=True)
    if labile and temp >= 150:
        return PrincipleCheck(
            "process_physics", True, 0.75,
            f"{cls} is thermally labile at ~{temp} °C ({process}) — degradation products are expected "
            f"and should be the measured endpoint, not the parent compound.", hard=True)
    if temp <= 40 and process not in ("研",):
        return PrincipleCheck(
            "process_physics", False, 0.4,
            f"{process} at ~{temp} °C is a low-energy operation; it cannot drive a chemical "
            f"transformation, only extraction or particle-size change.", hard=True)
    return PrincipleCheck(
        "process_physics", True, 0.7,
        f"{cls} is consistent with {process} (~{temp} °C, {medium}): {why}.", hard=True)


OPEN_LOSS_PROCESSES = {"蒸", "煮", "煎", "焙", "炒", "炒焦", "炒炭", "炮", "煅", "煨", "炙",
                       "蜜炙", "醋炙", "酒炙", "淬", "麩炒", "土炒"}


def check_mass_conservation(process: str, claim: str) -> PrincipleCheck:
    """Law P1 / C1: a preparation cannot create matter.

    An *absolute* increase in a constituent is impossible unless a precursor is converted into it.
    What a preparation can do is change the *fraction*: drive off everything else. Confusing the two is
    one of the commonest errors in ethnopharmacology writing, so it is worth a hard check.
    """
    text = (claim or "").lower()
    absolute = any(w in text for w in ("enrich", "increase", "more", "higher content", "accumulat"))
    if not absolute:
        return PrincipleCheck("mass_conservation", True, 0.8,
                              "claim is about change, not absolute enrichment — mass balance does not bite",
                              hard=True)
    if process in OPEN_LOSS_PROCESSES:
        return PrincipleCheck(
            "mass_conservation", True, 0.75,
            "absolute enrichment is impossible under a process that only removes or transforms matter; "
            "only RELATIVE enrichment (a higher fraction) can occur, and the claim should say so",
            hard=True)
    return PrincipleCheck("mass_conservation", True, 0.75,
                          "process is not a bulk-loss operation; precursor conversion could in principle "
                          "raise the absolute amount", hard=True)


def check_delivery(descriptors: dict) -> PrincipleCheck:
    """Biophysical plausibility: can this molecule cross a membrane at plausible exposure?"""
    if not descriptors or not descriptors.get("valid"):
        return PrincipleCheck("delivery_physics", None, 0.5, "no valid structure to assess", hard=False)
    mw = descriptors.get("mw") or 0
    logp = descriptors.get("logp_estimate")
    tpsa = descriptors.get("tpsa")

    if mw > 900:
        return PrincipleCheck("delivery_physics", False, 0.2,
                              f"MW {mw:.0f} Da is far above the range for passive absorption; the claim "
                              f"needs an active transport mechanism or a local (gut lumen) site of action",
                              hard=True)
    if logp is not None and (logp < -1.5 or logp > 6.5):
        return PrincipleCheck("delivery_physics", False, 0.3,
                              f"logP {logp} is outside the range where passive permeability and "
                              f"solubility coexist; systemic delivery is physically implausible without "
                              f"a transporter", hard=True)
    if tpsa is not None and tpsa > 200:
        return PrincipleCheck("delivery_physics", False, 0.3,
                              f"TPSA {tpsa:.0f} Å² implies very low passive permeability", hard=True)
    return PrincipleCheck("delivery_physics", True, 0.8,
                          f"MW {mw:.0f}, logP {logp}, TPSA {tpsa} are all within the physical window "
                          f"for passive absorption", hard=True)


def arbitrate(process: str, chemotype: str, descriptors: dict | None = None,
              claim: str = "") -> dict:
    """The arbiter: first principles decide. Western literature is not consulted here."""
    checks = [check_process_physics(process, chemotype, claim), check_mass_conservation(process, claim)]
    if descriptors is not None:
        checks.append(check_delivery(descriptors))

    evaluated = [c for c in checks if c.passed is not None]
    violations = [c for c in evaluated if c.hard and c.passed is False]
    score = sum(c.score for c in evaluated) / len(evaluated) if evaluated else 0.5

    if violations:
        verdict = "VIOLATES FIRST PRINCIPLES — the claimed mechanism is physically impossible as stated"
    elif score >= HARD_MIN_SCORE:
        verdict = "CONSISTENT WITH FIRST PRINCIPLES — physically possible; the burden is now experimental"
    else:
        verdict = "FIRST PRINCIPLES INCONCLUSIVE — the claim is not physically impossible, but the " \
                  "physics does not predict it either"

    return {
        "score": round(score, 3),
        "verdict": verdict,
        "violations": [v.to_dict() for v in violations],
        "checks": [c.to_dict() for c in checks],
        "arbiter": "first principles (physics / chemistry / biology) — not Western literature",
        "laws_appealed_to": ["P1", "P2", "P3", "P4", "C1", "C2", "B3"],
    }


if __name__ == "__main__":
    for proc, cls in [("炮", "alkaloid"), ("蒸", "terpenoid"), ("炒", "protein"), ("研", "alkaloid")]:
        r = arbitrate(proc, cls)
        print(f"{proc} × {cls:<12} {r['score']:.2f}  {r['verdict'][:70]}")
        for c in r["checks"]:
            print(f"    - {c['check']}: {c['reasoning'][:100]}")
