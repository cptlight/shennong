"""Five additional experts, each grounded in a different data source.

Chosen for *consequence*, not completeness. Each one answers a question that has actually changed a
verdict in this project, and each is cheap enough to run per item:

| Expert | Question | Why it is consequential here |
|---|---|---|
| `taxonomy` | is the binomial an accepted name with a known family? | drug-name→taxon resolution is the weakest link in the chain (measured at 14.1 % accuracy) |
| `chemotaxonomy` | does this plant family actually produce this chemotype? | catches claims that are chemically impossible for the lineage, and predicts unstudied congeners |
| `extraction` | does this medium/solvent extract this class? | decoction vs tincture vs steam is decided by polarity, not by tradition |
| `adme` | can this molecule be absorbed and survive first pass? | a real compound that cannot reach plasma cannot be the active principle |
| `microbiome` | is this a glycoside prodrug activated by gut flora? | explains why an "inactive in vitro" glycoside works in vivo — a classic missed mechanism |
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shennong.experts.base import Proposal  # noqa: E402

# Solvent polarity handles for the extraction expert (dielectric constant, a physical constant)
MEDIUM_POLARITY = {
    "water": 80.1, "steam": 80.1, "aqueous_excipient": 70.0, "acid": 60.0,
    "ethanol": 24.3, "solvent": 50.0, "dry": 0.0, "air": 0.0,
    "quench": 60.0, "sealed": 0.0, "mechanical": 0.0,
}

# Typical logP window each chemotype needs to be extracted well by a given medium
CLASS_LOGP = {
    "alkaloid": 2.5, "terpenoid": 3.5, "flavonoid": 2.0, "glycoside": -0.5,
    "volatile_oil": 3.8, "phenylpropanoid": 2.5, "polyketide": 2.0,
    "polysaccharide": -1.5, "protein": -1.0, "organosulfur": 2.0, "mineral": 0.0,
}


def taxonomy_expert(world, item: dict) -> Proposal:
    binomial = item.get("binomial") or ""
    if not binomial:
        return Proposal("taxonomy", 0.10, "no binomial — the claim cannot be tied to a taxon", [])
    fam = (getattr(world, "plant_family", {}) or {}).get(binomial)
    if fam:
        return Proposal("taxonomy", 0.90, f"{binomial} resolves to an accepted name in {fam}", [fam])
    return Proposal("taxonomy", 0.45,
                    f"{binomial} has no family on record — resolution is unverified", [])


def chemotaxonomy_expert(world, item: dict) -> Proposal:
    """Does this family plausibly produce this chemotype?"""
    fam = (getattr(world, "plant_family", {}) or {}).get(item.get("binomial") or "")
    cls = (item.get("chemotype") or "").lower()
    if not fam or not cls:
        return Proposal("chemotaxonomy", 0.30, "family or chemotype unknown", [])
    family_classes = (getattr(world, "family_classes", {}) or {}).get(fam)
    if not family_classes:
        return Proposal("chemotaxonomy", 0.45,
                        f"{fam} has no documented chemistry in our table — cannot test lineage "
                        f"plausibility", [])
    if cls in family_classes:
        return Proposal("chemotaxonomy", 0.85,
                        f"{cls} is documented elsewhere in {fam} — phylogenetically expected",
                        [f"{fam}: {len(family_classes)} classes documented"])
    return Proposal("chemotaxonomy", 0.35,
                    f"{cls} is not documented in {fam} — the claim crosses a chemotaxonomic gap and "
                    f"needs an explicit explanation (horizontal transfer, misidentification, or a "
                    f"genuinely novel chemistry)", [f"{fam} classes: {sorted(family_classes)[:4]}"])


def extraction_expert(world, item: dict) -> Proposal:
    """Does the process medium extract this chemotype? Polarity, not tradition, decides."""
    from shennong.physics.simulate import PROCESS

    proc = item.get("process") or ""
    cond = PROCESS.get(proc)
    cls = (item.get("chemotype") or "").lower()
    if not cond or cls not in CLASS_LOGP:
        return Proposal("extraction", 0.30, "process or class unknown for a polarity argument", [])
    medium = cond[1]
    eps = MEDIUM_POLARITY.get(medium, 50.0)
    target_logp = CLASS_LOGP[cls]
    # a medium extracts best when its polarity matches the solute's; water (eps 80) suits polar
    # solutes, ethanol (24) suits medium-polar, dry/steam suits volatiles
    if medium in ("dry", "air"):
        score = 0.8 if cls in ("volatile_oil", "terpenoid", "organosulfur") else 0.35
        note = f"dry thermal medium does not extract; it transforms"
    elif medium == "steam":
        score = 0.85 if cls in ("volatile_oil", "terpenoid") else 0.30
        note = f"steam carries volatiles; {cls} is not steam-volatile"
    elif medium == "ethanol":
        score = 0.85 if 0.0 <= target_logp <= 4.0 else 0.45
        note = f"ethanol (ε 24.3) suits logP~{target_logp}"
    else:  # water / aqueous
        score = 0.85 if target_logp <= 2.5 else 0.40
        note = f"water (ε 80.1) suits polar solutes; {cls} has logP~{target_logp}"
    return Proposal("extraction", score, f"{proc} in {medium}: {note}", [f"ε({medium})={eps}"])


def adme_expert(world, item: dict) -> Proposal:
    """Can a molecule of this class be absorbed and survive first pass?"""
    from shennong.chem import hbd, hba, logp_fragment_estimate, parse_smiles, tpsa

    smis = (getattr(world, "class_smiles", {}) or {}).get(
        (item.get("binomial"), item.get("chemotype"))) or []
    cls = (item.get("chemotype") or "").lower()
    if not smis:
        # class-level reasoning is still possible
        if cls in ("glycoside", "polysaccharide", "protein"):
            return Proposal("adme", 0.30,
                            f"{cls} is too polar/large for passive absorption; activity likely requires "
                            f"hydrolysis first (see microbiome expert)", [])
        return Proposal("adme", 0.45, "no structure; class-level ADME only", [])
    try:
        m = parse_smiles(smis[0])
    except Exception:  # noqa: BLE001
        return Proposal("adme", 0.30, "structure unparseable for ADME", [])
    mw = sum(1 for _ in m.atoms) * 12.0  # rough, only used as a size gate
    tp, lg = tpsa(m), logp_fragment_estimate(m)
    if tp > 140 or lg > 5 or lg < -2:
        return Proposal("adme", 0.30,
                        f"TPSA {tp:.0f} Å², logP {lg:.1f} — poor passive absorption; a"
                        f" systemic mechanism needs a transporter or local action", [])
    return Proposal("adme", 0.80,
                    f"TPSA {tp:.0f} Å², logP {lg:.1f} — within the passive-absorption window", [])


def microbiome_expert(world, item: dict) -> Proposal:
    """Is this an inactive glycoside whose activity requires gut-flora hydrolysis?"""
    cls = (item.get("chemotype") or "").lower()
    proc = item.get("process") or ""
    if cls not in ("glycoside", "flavonoid", "polysaccharide"):
        return Proposal("microbiome", 0.30, "not a glycosidic class; prodrug activation not implicated", [])
    if proc in ("蒸", "煮", "煎", "炙", "蜜炙"):
        return Proposal("microbiome", 0.75,
                        f"{cls} survives aqueous processing partly intact; gut-flora hydrolysis is the "
                        f"plausible activation step — measure the aglycone, not the glycoside", [])
    return Proposal("microbiome", 0.50,
                    f"{cls} present; check whether the aglycone is the active form", [])


EXTRA_EXPERTS = {
    "taxonomy": taxonomy_expert,
    "chemotaxonomy": chemotaxonomy_expert,
    "extraction": extraction_expert,
    "adme": adme_expert,
    "microbiome": microbiome_expert,
}
