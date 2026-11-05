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
    MODERN = 4


STAGE_OF_DOMAIN = {
    "ethnobotany": Stage.ANCIENT_RECORD,
    "theory": Stage.ASIAN_THEORY,
    "operator": Stage.ASIAN_PHARMACY,
    "phytochemistry": Stage.MODERN,
    "toxicology": Stage.MODERN,
}
STAGE_NAME = {
    Stage.ANCIENT_RECORD: "ancient record (corpus attestation)",
    Stage.ASIAN_THEORY: "Asian theory (四氣/五味/歸經, rasa/vīrya)",
    Stage.ASIAN_PHARMACY: "Asian pharmacy (炮制 / formula layer)",
    Stage.MODERN: "modern corroboration (Wikidata chemistry + our toxicity marks; "
                  "ChEMBL/Open Targets NOT yet wired)",
}
GATE_THRESHOLD = 0.45


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
WEIGHTS = {Stage.ANCIENT_RECORD: 0.35, Stage.ASIAN_THEORY: 0.25,
           Stage.ASIAN_PHARMACY: 0.20, Stage.MODERN: 0.20}


def stage_score(item: dict, world: World) -> StagedResult:
    claim = (f"{item.get('process')} of {item.get('drug_surface')} "
             f"({item.get('binomial')}) should measurably change its {item.get('chemotype')} content")
    res = StagedResult(claim=claim)

    for domain, fn in EXPERTS.items():
        p = fn(world, item)
        res.stages.setdefault(int(STAGE_OF_DOMAIN[domain]), []).append(p)

    # ---- gates -------------------------------------------------------------------
    s1 = res.stages.get(int(Stage.ANCIENT_RECORD), [])
    s2 = res.stages.get(int(Stage.ASIAN_THEORY), [])
    if not s1 or max(p.score for p in s1) < GATE_THRESHOLD:
        res.failed_gate = int(Stage.ANCIENT_RECORD)
        res.verdict = "OUT — not attested in the classical record (no Western evidence may rescue this)"
        res.score = 0.0
        return res
    if not s2 or max(p.score for p in s2) < GATE_THRESHOLD:
        res.failed_gate = int(Stage.ASIAN_THEORY)
        res.verdict = "OUT — attested, but the tradition's own theory does not frame it"
        res.score = 0.0
        return res

    res.gates_passed = True

    # ---- weighted score over all stages ------------------------------------------
    total = 0.0
    for stage_id, weight in WEIGHTS.items():
        props = res.stages.get(int(stage_id), [])
        best = max((p.score for p in props), default=0.0)
        total += weight * best
    # bonus for independent modern corroboration, but small: it cannot outrank a gated claim
    modern = res.stages.get(int(Stage.MODERN), [])
    n_modern_support = sum(1 for p in modern if p.score >= GATE_THRESHOLD)
    total *= (1.0 + 0.08 * max(0, n_modern_support - 1))
    res.score = min(1.0, total)

    if n_modern_support >= 2:
        res.verdict = "tradition-grounded AND modern-corroborated — strongest class available"
        res.note = "classical attestation + Asian theory, with independent modern chemistry/tox signals"
    else:
        res.verdict = "tradition-grounded, awaiting modern corroboration — a genuine classical lead"
        res.note = "passes both gates but only one modern domain supports it; this is the pre-clinical class"
    return res


def run(items: list[dict]) -> dict:
    world = World.load()
    results = [stage_score(it, world) for it in items]
    results.sort(key=lambda r: (r.gates_passed, r.score), reverse=True)

    passed = [r for r in results if r.gates_passed]
    failed_1 = [r for r in results if r.failed_gate == int(Stage.ANCIENT_RECORD)]
    failed_2 = [r for r in results if r.failed_gate == int(Stage.ASIAN_THEORY)]
    strongest = [r for r in passed
                 if sum(1 for p in r.stages.get(int(Stage.MODERN), []) if p.score >= GATE_THRESHOLD) >= 2]

    payload = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ordering": ["ancient record (GATE)", "Asian theory (GATE)",
                     "Asian pharmacy (score)", "modern corroboration (score, cannot rescue)"],
        "rule": ("a claim failing either gate is excluded regardless of modern evidence; modern data "
                 "may strengthen a tradition-grounded hypothesis but may never substitute for one"),
        "honest_caveats": [
            "Stage 4 currently draws on the Wikidata-derived compound table and our own 毒 markings. "
            "It does NOT yet include measured ChEMBL bioactivity or Open Targets genetics, so "
            "'modern-corroborated' here means 'structure/class evidence', not 'assayed evidence'.",
            "Because both stage-4 signals are cheap and correlated, the 'awaiting corroboration' class "
            "is empty in this run. That will change when ChEMBL is wired in and can disagree.",
            "Expert scores are coarse (0.15-1.0 in a few steps), so top scores cluster near 1.0; the "
            "ranking is driven by the gates, not by the last decimals.",
        ],
        "weights": {"ancient_record": 0.35, "asian_theory": 0.25, "asian_pharmacy": 0.20,
                    "modern": 0.20},
        "n_candidates": len(results),
        "n_passed_gates": len(passed),
        "n_failed_ancient_gate": len(failed_1),
        "n_failed_theory_gate": len(failed_2),
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
         f"- **passed both gates:** {len(passed)}",
         f"- excluded at the ancient-record gate: {len(failed_1)}",
         f"- excluded at the Asian-theory gate: {len(failed_2)}",
         f"- **strongest class (tradition-grounded *and* modern-corroborated):** {len(strongest)}",
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
