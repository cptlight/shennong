"""The first-principles core: the laws that every claim must satisfy, across the sciences.

This is the invariant layer of the system. Experts can be added, upgraded or removed; the data pipeline
can ingest new corpora; the model can be retrained. **None of that is allowed to change these.** A
tradition-derived hypothesis is admissible only if it survives them.

Each entry states the law, the domain it constrains, the class of claim it can falsify, and the check
that operationalises it. Keeping the laws as data (rather than as prose in a docstring) means a new
expert can declare which laws it appeals to, and a reviewer can see exactly what the system is
committed to.

Scope note, stated honestly: these are *first-order* constraints — the ones that any correct mechanism
must satisfy. They are not a complete physical theory, and they cannot prove a mechanism; they can only
falsify one. That asymmetry is deliberate: **the arbiter can say no, never yes.**
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Law:
    id: str
    domain: str            # physics | chemistry | biology
    statement: str
    falsifies: str         # the class of claim it can rule out
    check: str             # name of the operational check
    strength: str          # hard = violation is fatal; soft = raises the burden


LAWS: tuple[Law, ...] = (
    # ---------------- physics ----------------
    Law("P1", "physics",
        "Mass is conserved in any preparation. A process can remove, transfer or transform matter; it "
        "cannot create it.",
        "a claim that a process increases the ABSOLUTE mass of a constituent without a precursor",
        "check_mass_conservation", "hard"),
    Law("P2", "physics",
        "Energy is conserved, and a transformation needs an energy source. A low-energy operation "
        "(cold maceration, grinding) cannot drive an endergonic reaction.",
        "claims of chemical conversion under thermodynamically inert conditions",
        "check_process_physics", "hard"),
    Law("P3", "physics",
        "Matter partitions between phases according to chemical potential: vapour pressure governs "
        "volatilisation, and Henry's law governs air–water partitioning.",
        "claims that a volatile constituent is retained or enriched by an open hot process",
        "check_process_physics", "hard"),
    Law("P4", "physics",
        "Passive membrane permeation is bounded by size, lipophilicity and polar surface area; beyond "
        "those windows a mechanism needs a transporter or a local site of action.",
        "systemic-activity claims for molecules outside the passive-permeation window",
        "check_delivery", "hard"),
    Law("P5", "physics",
        "Diffusion and heat transfer set a rate limit: a claimed effect that requires a faster process "
        "than the medium allows is impossible regardless of the mechanism.",
        "claims of instantaneous transformation of a dense matrix by gentle heating",
        "check_process_physics", "soft"),

    # ---------------- chemistry ----------------
    Law("C1", "chemistry",
        "A reaction must conserve atoms and charge; every element must balance across reactants and "
        "products.",
        "transformations whose elemental balance does not close",
        "check_mass_conservation", "hard"),
    Law("C2", "chemistry",
        "Bond-breaking rates follow Arrhenius kinetics: a rate constant is a function of temperature and "
        "an activation energy characteristic of the bond class.",
        "claims that a bond class survives conditions that hydrolyse it, or reacts without energy",
        "check_process_physics", "hard"),
    Law("C3", "chemistry",
        "Electronic structure governs reactivity: a high HOMO–LUMO gap (hard molecule) resists attack; "
        "a low gap is reactive.",
        "reactivity claims inconsistent with the computed electronic structure of the bond class",
        "quantum_expert", "soft"),
    Law("C4", "chemistry",
        "Solvent polarity governs extraction: a solute partitions into a medium whose polarity matches "
        "its own.",
        "extraction claims where the medium cannot dissolve the class",
        "extraction_expert", "hard"),
    Law("C5", "chemistry",
        "Stereochemistry and conformation constrain binding and reactivity; a rigid scaffold and a "
        "flexible chain with the same formula behave differently.",
        "claims that treat a class as a single uniform substance",
        "mechanics_expert", "soft"),

    # ---------------- biology ----------------
    Law("B1", "biology",
        "Phylogeny constrains secondary metabolism: a biosynthetic pathway is inherited, so a chemotype "
        "absent from a lineage needs an explanation (transfer, misidentification, or genuinely novel).",
        "chemotype claims that cross a chemotaxonomic gap silently",
        "chemotaxonomy_expert", "soft"),
    Law("B2", "biology",
        "A systemic effect requires sufficient concentration at the target for sufficient time — "
        "absorption, distribution and first-pass metabolism bound what is achievable.",
        "activity claims that ignore bioavailability",
        "adme_expert", "soft"),
    Law("B3", "biology",
        "Enzymes are catalysts: they accelerate a reaction that is already thermodynamically allowed and "
        "cannot make an impossible one occur.",
        "claims that an enzyme enables a thermodynamically forbidden transformation",
        "check_process_physics", "hard"),
    Law("B4", "biology",
        "Microbial metabolism transforms what the host cannot: glycosides are commonly hydrolysed by gut "
        "flora, so an inactive glycoside can be a prodrug.",
        "claims that a glycoside is unconditionally inactive because an in-vitro assay showed nothing",
        "microbiome_expert", "soft"),
    Law("B5", "biology",
        "Dose–response is monotonic only in a window: many natural products are hormetic or toxic above "
        "a threshold, so 'more' is not 'better'.",
        "unbounded dose-escalation reasoning",
        "toxicology_expert", "soft"),
)


def by_domain() -> dict[str, list[Law]]:
    out: dict[str, list[Law]] = {}
    for law in LAWS:
        out.setdefault(law.domain, []).append(law)
    return out


def summary() -> dict:
    return {
        "n_laws": len(LAWS),
        "by_domain": {d: len(v) for d, v in by_domain().items()},
        "hard": [l.id for l in LAWS if l.strength == "hard"],
        "soft": [l.id for l in LAWS if l.strength == "soft"],
        "principle": ("the core can falsify a claim, never prove one: hard laws are fatal when "
                      "violated, soft laws raise the evidential burden without excluding the claim"),
    }


if __name__ == "__main__":
    s = summary()
    print(f"{s['n_laws']} laws: {s['by_domain']}")
    print(f"hard ({len(s['hard'])}): {' '.join(s['hard'])}")
    print(f"soft ({len(s['soft'])}): {' '.join(s['soft'])}")
    for d, laws in by_domain().items():
        print(f"\n{d.upper()}")
        for l in laws:
            print(f"  {l.id} [{l.strength}] {l.statement[:88]}")
