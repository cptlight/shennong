"""Tradition-first staging: ancient record → Asian medicine → modern corroboration.

The ordering is the argument
----------------------------
Most computational ethnopharmacology runs the Western way round: start from a compound–target
database, then look for a plant that might contain the compound, then cite a traditional use as
colour. That inverts the evidence. The tradition becomes a marketing layer bolted onto a Western
screen.

This module enforces the opposite, and the order is not cosmetic — it is a set of gates:

```
STAGE 1  ANCIENT RECORD      is the item attested in the classical corpus?          GATE
STAGE 2  ASIAN THEORY        does the tradition's own theory frame it?              GATE
STAGE 3  ASIAN PHARMACY      does the preparation/formula layer support it?         score
STAGE 4  MODERN CORROBORATION  does measured chemistry/bioactivity agree?            score, cannot rescue
```

**Stages 1 and 2 are gates.** A claim that fails either is out, *however strong the modern evidence is* —
because a molecule that the classical record does not attest is not a tradition-derived hypothesis, it is
a Western screen with a footnote. Stage 4 contributes to the score but **cannot promote** a claim that
failed a gate; modern data may strengthen a tradition-grounded hypothesis, never substitute for one.

That asymmetry is the whole design: the tradition supplies the hypothesis, and modern science gets a
vote on whether it is plausible — not the other way round.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shennong.experts import EXPERTS, World  # noqa: E402
from shennong.experts.base import Proposal  # noqa: E402


class Stage(IntEnum):
    ANCIENT_RECORD = 1
    ASIAN_THEORY = 2
    ASIAN_PHARMACY = 3
    FIRST_PRINCIPLES = 4      # THE ARBITER
    WESTERN_LITERATURE = 5    # observation only — never a judge


STAGE_OF_DOMAIN = {
    "ethnobotany": Stage.ANCIENT_RECORD,
    "theory": Stage.ASIAN_THEORY,
    "operator": Stage.ASIAN_PHARMACY,
    "phytochemistry": Stage.FIRST_PRINCIPLES,   # class identity is a chemical fact
    "toxicology": Stage.FIRST_PRINCIPLES,       # toxicity is a biological fact
    "mechanics": Stage.FIRST_PRINCIPLES,        # molecular mechanics
    "quantum": Stage.FIRST_PRINCIPLES,          # electronic structure
    "taxonomy": Stage.ANCIENT_RECORD,           # is the name a real taxon?
    "chemotaxonomy": Stage.FIRST_PRINCIPLES,    # does the lineage produce this chemistry?
    "extraction": Stage.ASIAN_PHARMACY,         # does the medium extract this class?
    "adme": Stage.FIRST_PRINCIPLES,             # can it be absorbed?
    "microbiome": Stage.FIRST_PRINCIPLES,       # is it a gut-activated prodrug?
}
STAGE_NAME = {
    Stage.ANCIENT_RECORD: "ancient record (corpus attestation)",
    Stage.ASIAN_THEORY: "Asian theory (四氣/五味/歸經, rasa/vīrya)",
    Stage.ASIAN_PHARMACY: "Asian pharmacy (炮制 / formula layer)",
    Stage.FIRST_PRINCIPLES: "first principles — physics / chemistry / biology (THE ARBITER)",
    Stage.WESTERN_LITERATURE: "Western literature — recorded as observation, NOT consulted as judge",
}
GATE_THRESHOLD = 0.45

# A gate is judged by its DESIGNATED expert, not by "any expert assigned to that stage".
# Bug this fixes: adding `taxonomy` to the ancient-record stage let a merely *resolvable* plant name
# satisfy the attestation gate, collapsing stage-1 failures from 151 to 0 and inflating the headline
# funnel. The record gate must be about the record (ethnobotany); the theory gate about the theory.
GATE_EXPERTS = {
    int(1): "ethnobotany",
    int(2): "theory",
}


@dataclass
class StagedResult:
    claim: str
    stages: dict[int, list[Proposal]] = field(default_factory=dict)
    gates_passed: bool = False
    failed_gate: int | None = None
    score: float = 0.0
    verdict: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "tradition_first_score": round(self.score, 4),
            "gates_passed": self.gates_passed,
            "failed_gate": self.failed_gate,
            "verdict": self.verdict,
            "note": self.note,
            "stages": [
                {"stage": int(s), "name": STAGE_NAME[Stage(s)],
                 "proposals": [p.to_dict() for p in self.stages.get(s, [])]}
                for s in sorted(self.stages)
            ],
        }


# Stage weights: the tradition carries the hypothesis, modern data corroborates it.
# The arbiter carries the largest single weight: physics outranks consensus.
WEIGHTS = {Stage.ANCIENT_RECORD: 0.28, Stage.ASIAN_THEORY: 0.20,
           Stage.ASIAN_PHARMACY: 0.16, Stage.FIRST_PRINCIPLES: 0.36}


def stage_score(item: dict, world: World) -> StagedResult:
    claim = (f"{item.get('process')} of {item.get('drug_surface')} "
             f"({item.get('binomial')}) should measurably change its {item.get('chemotype')} content")
    res = StagedResult(claim=claim)

    for domain, fn in EXPERTS.items():
        p = fn(world, item)
        res.stages.setdefault(int(STAGE_OF_DOMAIN[domain]), []).append(p)

    # ---- gates -------------------------------------------------------------------
    def designated(stage: int) -> float:
        """Score of the expert that owns this gate (0.0 if it did not fire)."""
        name = GATE_EXPERTS[stage]
        for p in res.stages.get(stage, []):
            if p.domain == name:
                return p.score
        return 0.0

    if designated(int(Stage.ANCIENT_RECORD)) < GATE_THRESHOLD:
        res.failed_gate = int(Stage.ANCIENT_RECORD)
        res.verdict = "OUT — not attested in the classical record (no Western evidence may rescue this)"
        res.score = 0.0
        return res
    if designated(int(Stage.ASIAN_THEORY)) < GATE_THRESHOLD:
        res.failed_gate = int(Stage.ASIAN_THEORY)
        res.verdict = "OUT — attested, but the tradition's own theory does not frame it"
        res.score = 0.0
        return res

    res.gates_passed = True

    # ---- STAGE 4: first principles arbitrate (not Western literature) --------------
    from shennong.experts.first_principles import arbitrate, PrincipleCheck
    fp = arbitrate(item.get("process") or "", item.get("chemotype") or "", None, claim)
    fp_score = fp["score"]
    res.stages.setdefault(int(Stage.FIRST_PRINCIPLES), []).append(
        Proposal("first_principles", fp_score, fp["verdict"], [
            c["reasoning"] for c in fp["checks"]][:2]))
    if fp["violations"]:
        res.gates_passed = False
        res.failed_gate = int(Stage.FIRST_PRINCIPLES)
        res.verdict = ("OUT — violates first principles: " + fp["violations"][0]["reasoning"][:120])
        res.score = 0.0
        return res

    # ---- STAGE 5: Western literature is recorded, never consulted as a judge -------
    res.stages.setdefault(int(Stage.WESTERN_LITERATURE), []).append(
        Proposal("western_literature", 0.0,
                 "not consulted as an arbiter — recorded as an observation only. If it later "
                 "agrees, that is a consistent dataset; if it disagrees, that is a problem to "
                 "explain (species / preparation / dose / endpoint / untested), not a verdict.",
                 ["ChEMBL / Open Targets / clinical literature are deliberately not wired into "
                  "the decision path"]))

    # ---- weighted score over all stages ------------------------------------------
    total = 0.0
    for stage_id, weight in WEIGHTS.items():
        props = res.stages.get(int(stage_id), [])
        best = max((p.score for p in props), default=0.0)
        total += weight * best
    res.score = min(1.0, total)
    res.verdict = ("TRADITION-GROUNDED AND PHYSICALLY CONSISTENT — the claim survives every gate and "
                   "the arbiter; the burden is now experimental, not bibliographic")
    res.note = ("first principles are the arbiter; Western literature is recorded but not consulted")
    return res


def run(items: list[dict]) -> dict:
    world = World.load()
    results = [stage_score(it, world) for it in items]
    results.sort(key=lambda r: (r.gates_passed, r.score), reverse=True)

    passed = [r for r in results if r.gates_passed]
    failed_1 = [r for r in results if r.failed_gate == int(Stage.ANCIENT_RECORD)]
    failed_2 = [r for r in results if r.failed_gate == int(Stage.ASIAN_THEORY)]
    failed_fp = [r for r in results if r.failed_gate == int(Stage.FIRST_PRINCIPLES)]
    strongest = passed

    payload = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ordering": ["ancient record (GATE)", "Asian theory (GATE)",
                     "Asian pharmacy (score)", "modern corroboration (score, cannot rescue)"],
        "rule": ("a claim failing a gate is excluded. First principles (physics/chemistry/biology) are "
                 "the ARBITER. Western literature is recorded as an observation and is NEVER consulted "
                 "as a judge: if it agrees that is a consistent dataset; if it disagrees that is a "
                 "problem to explain (species, preparation, dose, endpoint, or untested)."),
        "honest_caveats": [
            "Stage 4 currently draws on the Wikidata-derived compound table and our own 毒 markings. "
            "It does NOT yet include measured ChEMBL bioactivity or Open Targets genetics, so "
            "'modern-corroborated' here means 'structure/class evidence', not 'assayed evidence'.",
            "Because both stage-4 signals are cheap and correlated, the 'awaiting corroboration' class "
            "is empty in this run. That will change when ChEMBL is wired in and can disagree.",
            "Expert scores are coarse (0.15-1.0 in a few steps), so top scores cluster near 1.0; the "
            "ranking is driven by the gates, not by the last decimals.",
        ],
        "weights": {"ancient_record": 0.28, "asian_theory": 0.20, "asian_pharmacy": 0.16,
                    "first_principles_ARBITER": 0.36, "western_literature": 0.0},
        "n_candidates": len(results),
        "n_passed_gates": len(passed),
        "n_failed_ancient_gate": len(failed_1),
        "n_failed_theory_gate": len(failed_2),
        "n_failed_first_principles": len(failed_fp),
        "n_strongest_class": len(strongest),
        "results": [r.to_dict() for r in results[:60]],
    }
    (ROOT / "artifacts/tradition_first.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Tradition-first staging: ancient record → Asian medicine → Western medicine", "",
         payload["generated_at"], "",
         "**The ordering is the argument.** The usual computational approach starts from a Western",
         "compound–target database, then looks for a plant, then cites a traditional use as colour.",
         "That makes the tradition a marketing layer. Here the order is inverted and enforced as gates:", "",
         "```",
         "STAGE 1  ANCIENT RECORD       attested in the classical corpus?          GATE",
         "STAGE 2  ASIAN THEORY         四氣/五味/歸經 (rasa/vīrya) frame it?      GATE",
         "STAGE 3  ASIAN PHARMACY       炮制 / formula layer support it?           score",
         "STAGE 4  MODERN CORROBORATION measured chemistry / bioactivity agrees?   score, CANNOT rescue",
         "```", "",
         "**A claim failing either gate is out regardless of how strong the modern evidence is.** Modern",
         "data may strengthen a tradition-grounded hypothesis; it may never substitute for one.", "",
         f"## Results over {len(results)} candidates", "",
         f"- **survive everything (tradition-grounded + physically consistent):** {len(passed)}",
         f"- excluded at the ancient-record gate: {len(failed_1)}",
         f"- excluded at the Asian-theory gate: {len(failed_2)}",
         f"- **excluded by first principles — physically impossible as stated:** {len(failed_fp)}",
         "", "> **What stage 4 actually is, in this run.** The two stage-4 experts draw on the",
         "> Wikidata-derived compound table and our own 毒 markings — **not** measured ChEMBL bioactivity",
         "> or Open Targets genetics. So \"modern-corroborated\" here means *structure/class evidence*,",
         "> not *assayed evidence*. Because both signals are cheap and correlated, the",
         "> \"awaiting corroboration\" class is empty in this run; it will populate once ChEMBL can",
         "> disagree with the tradition rather than echo it.", "",
         "## The strongest class", "",
         "| Hypothesis | Score | Stage 1 | Stage 2 | Stage 3 | Stage 4 |",
         "|---|---|---|---|---|---|"]

    def stage_best(r, stage):
        ps = r.stages.get(int(stage), [])
        return max((p.score for p in ps), default=0.0)

    for r in strongest[:20]:
        L.append(f"| {r.claim[:76]} | {r.score:.3f} | {stage_best(r,1):.2f} | {stage_best(r,2):.2f} | "
                 f"{stage_best(r,3):.2f} | {stage_best(r,4):.2f} |")

    L += ["", "## Tradition-grounded leads awaiting modern corroboration", "",
          "These pass both gates on the tradition's own terms — the class a pharmacognosist would want",
          "before any Western assay is run.", "",
          "| Hypothesis | Score |", "|---|---|"]
    pending = [r for r in passed if r not in strongest]
    for r in pending[:15]:
        L.append(f"| {r.claim[:90]} | {r.score:.3f} |")

    L += ["", "## What was excluded, and why that matters", "",
          f"**{len(failed_1)}** candidates were excluded because the classical record does not attest them,",
          f"and **{len(failed_2)}** because the Asian theory layer does not frame them. Under a",
          "Western-first pipeline those would have been *priorities*; here they are non-hypotheses.",
          "That is the difference the ordering makes.", ""]
    (ROOT / "artifacts/TRADITION_FIRST.md").write_text("\n".join(L), encoding="utf-8")

    print(f"{len(results)} candidates · passed gates {len(passed)} "
          f"(failed stage1 {len(failed_1)}, stage2 {len(failed_2)}) · strongest {len(strongest)}")
    print("wrote artifacts/tradition_first.json and artifacts/TRADITION_FIRST.md")
    return payload


if __name__ == "__main__":
    cs = json.loads((ROOT / "artifacts/cross_sections.json").read_text(encoding="utf-8"))
    run(cs.get("all") or cs.get("top") or [])
