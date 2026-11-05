"""The five offline domain experts.

Each is a pure function over data that lives in a different table, with no shared state and no access
to the others' evidence. That independence is the whole point: if two of them agree, the agreement
carries information, because neither could have seen the other's source.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .base import Proposal

ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------------------
# Data loading (once, shared, read-only)
# ---------------------------------------------------------------------------------------
@dataclass
class World:
    """Read-only view of everything the experts may consult."""
    attestation: dict[str, dict]          # drug surface -> {n_sources, n_traditions, ...}
    plant_classes: dict[str, set[str]]    # binomial -> chemotypes
    class_counts: dict[str, dict[str, int]]  # binomial -> {class: n_compounds}
    operators: dict[str, dict]            # process term -> {modern, effects}
    theory: dict[str, dict]               # drug surface -> properties vector
    toxic: set[str]                       # drug surfaces marked 有毒
    tox_classes: set[str]                 # chemotypes with known liability

    @classmethod
    def load(cls) -> "World":
        attestation: dict[str, dict] = {}
        disc = ROOT / "artifacts" / "discoveries.json"
        if disc.exists():
            d = json.loads(disc.read_text(encoding="utf-8"))
            for key in ("F1_cross_tradition_convergence", "F4_corroborated_core"):
                for r in d["findings"][key]["top"]:
                    attestation[r["surface"]] = r

        plant_classes: dict[str, set[str]] = defaultdict(set)
        class_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        comp = ROOT / "corpus/processed/structured/compounds.csv"
        if comp.exists():
            import csv
            with comp.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    p = (r.get("plant_binomial") or "").strip()
                    c = (r.get("compound_class") or "").strip().lower()
                    if p and c and c not in {"", "unclassified"}:
                        plant_classes[p].add(c)
                        class_counts[p][c] += 1

        operators = {}
        onto = ROOT / "artifacts" / "operator_ontology.json"
        if onto.exists():
            o = json.loads(onto.read_text(encoding="utf-8"))
            for t in o.get("operators", []):
                operators[t["term"]] = t

        theory: dict[str, dict] = {}
        props = ROOT / "corpus/processed/structured/properties.csv"
        if props.exists():
            import csv
            with props.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    name = (r.get("drug_name") or "").strip()
                    if name:
                        theory[name] = r

        toxic = {k for k, v in theory.items() if "毒" in (v.get("toxicity") or "")}
        tox_classes = {"alkaloid", "organosulfur", "cardiac_glycoside", "pyrrolizidine"}

        return cls(attestation, dict(plant_classes), {k: dict(v) for k, v in class_counts.items()},
                   operators, theory, toxic, tox_classes)


# ---------------------------------------------------------------------------------------
# Experts
# ---------------------------------------------------------------------------------------
def ethnobotany(w: World, item: dict) -> Proposal:
    """How independently attested is this drug's use across the corpus?"""
    a = w.attestation.get(item.get("drug_surface", ""))
    if not a:
        return Proposal("ethnobotany", 0.20,
                        "drug surface not in the attested set", [])
    n_src = a.get("n_sources", 0)
    n_trad = a.get("n_traditions", 0)
    score = min(1.0, 0.25 + 0.05 * min(n_src, 10) + 0.08 * min(n_trad, 4))
    return Proposal("ethnobotany", score,
                    f"{n_src} independent sources, {n_trad} traditions",
                    [f"source {s}" for s in a.get("sources", [])[:3]])


def phytochemistry(w: World, item: dict) -> Proposal:
    """Is the chemotype actually documented in this plant, and how well?"""
    binomial = item.get("binomial") or ""
    cls = item.get("chemotype") or ""
    counts = w.class_counts.get(binomial) or {}
    if not counts:
        return Proposal("phytochemistry", 0.15, "no documented chemistry for this plant", [])
    n = counts.get(cls, 0)
    if n == 0:
        return Proposal("phytochemistry", 0.10,
                        f"{cls} not among the documented classes ({len(counts)} classes known)", [])
    breadth = len(counts)
    score = min(1.0, 0.45 + 0.05 * min(n, 8) + (0.15 if breadth <= 2 else 0.0))
    return Proposal("phytochemistry", score,
                    f"{n} documented {cls} compounds; {breadth} classes total"
                    + (" (narrow chemotype → sharp prediction)" if breadth <= 2 else ""),
                    [f"{binomial}: {n} × {cls}"])


def operator(w: World, item: dict) -> Proposal:
    """Does the attested preparation physically act on this chemotype?"""
    proc = item.get("process") or ""
    op = w.operators.get(proc)
    if not op:
        return Proposal("operator", 0.20, f"process {proc!r} not in the operator ontology", [])
    modern = op.get("modern") or []
    effects = " ".join(op.get("effects") or [])
    # does the operator's stated effect touch this chemotype's liability?
    cls = (item.get("chemotype") or "").lower()
    touches = cls.split("_")[0] in effects.lower() or cls in effects.lower()
    score = 0.5 + (0.2 if modern else 0.0) + (0.2 if touches else 0.0)
    return Proposal("operator", min(1.0, score),
                    f"{proc} = {'; '.join(modern)[:60] or 'unspecified'}"
                    + (" — effect names this chemotype" if touches else ""),
                    [f"{proc}: {e}" for e in (op.get("effects") or [])[:2]])


def theory(w: World, item: dict) -> Proposal:
    """Does the classical property vector point the same way as the claim?"""
    row = w.theory.get(item.get("drug_surface", ""))
    if not row:
        return Proposal("theory", 0.20, "no classical property vector recorded", [])
    nature = (row.get("nature") or "").strip()
    channels = (row.get("channels") or "").strip()
    tox = (row.get("toxicity") or "").strip()
    filled = sum(bool(x) for x in (nature, channels, tox))
    score = 0.3 + 0.2 * filled
    if tox and "毒" in tox:
        score += 0.1      # a toxicity marking makes the processing claim more meaningful
    return Proposal("theory", min(1.0, score),
                    f"nature {nature or '—'}, channels {channels or '—'}, {tox or 'unmarked'}",
                    [f"{item.get('drug_surface')}: {nature}/{channels}"])


def toxicology(w: World, item: dict) -> Proposal:
    """Is there a safety signal that makes the claim worth (or dangerous to) test?"""
    cls = (item.get("chemotype") or "").lower()
    drug = item.get("drug_surface", "")
    flagged = cls in w.tox_classes
    marked = drug in w.toxic
    if flagged and marked:
        return Proposal("toxicology", 0.85,
                        f"{cls} carries structural liability and the drug is marked 有毒 — "
                        "processing claims are safety-relevant", [f"{drug} 有毒", cls])
    if flagged or marked:
        return Proposal("toxicology", 0.6,
                        f"safety signal: {'class ' + cls if flagged else drug + ' marked 有毒'}",
                        [cls if flagged else drug])
    return Proposal("toxicology", 0.35, "no safety signal recorded", [])


EXPERTS = {
    "ethnobotany": ethnobotany,
    "phytochemistry": phytochemistry,
    "operator": operator,
    "theory": theory,
    "toxicology": toxicology,
}
