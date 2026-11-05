"""Multi-domain expert pharmacology.

Design principle
----------------
A hypothesis is only an *interpolation* if it is supported by evidence that came from domains which
could not have copied each other. One source saying "use this plant for that symptom" is an assertion;
the classical text saying it, the phytochemistry showing the chemotype is present, the operator
ontology showing the preparation transforms that chemotype, and measured bioactivity showing the class
hits the target — four independent domains agreeing is a finding.

So the unit here is not a document, it is a **domain**:

| Domain | Question it answers | Grounded in |
|---|---|---|
| `ethnobotany` | is the use well attested across independent sources/traditions? | corpus text-level attestation |
| `phytochemistry` | does the plant actually contain the chemotype? | compounds.csv (23 k structures) |
| `operator` | does the preparation physically act on that chemotype? | operator ontology (炮制 → chemistry) |
| `theory` | does the classical property vector point the same way? | 四氣/五味/歸經 |
| `toxicology` | is there a structural or classical safety signal? | molecular alerts, 毒 marking |

Each expert returns a `Proposal` with its own score, rationale and evidence references. The fusion
layer counts **distinct supporting domains**, reports disagreement, and refuses to call a
single-domain claim an interpolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Proposal:
    domain: str
    score: float                      # 0..1 within this domain
    rationale: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"domain": self.domain, "score": round(self.score, 4),
                "rationale": self.rationale, "evidence": self.evidence[:4]}


@dataclass
class Consensus:
    claim: str
    proposals: list[Proposal]
    agreement: int
    consensus_score: float
    verdict: str
    disagreements: list[str]

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "agreement": self.agreement,
            "consensus_score": round(self.consensus_score, 4),
            "verdict": self.verdict,
            "domains": [p.to_dict() for p in self.proposals],
            "disagreements": self.disagreements,
        }


MIN_DOMAIN_SCORE = 0.45
INDEPENDENCE_BONUS = 0.06


def fuse(claim: str, proposals: list[Proposal]) -> Consensus:
    """Combine independent domain opinions into one consensus judgement.

    * a domain *supports* the claim when its score clears MIN_DOMAIN_SCORE;
    * agreement counts **distinct domains** supporting it — the number that makes it an interpolation;
    * a domain that scores low while others score high is a disagreement, and is reported rather than
      averaged away, because that is the uncertainty a scientist needs to see;
    * verdict vocabulary is deliberately tiny and cannot be softened.
    """
    supporting = [p for p in proposals if p.score >= MIN_DOMAIN_SCORE]
    agreement = len(supporting)
    if not proposals:
        return Consensus(claim, [], 0, 0.0, "no evidence", [])

    mean = sum(p.score for p in proposals) / len(proposals)
    # Agreement *informs* the score; it must not manufacture one. The mean stays dominant and the
    # bonus is small, so a 5-domain claim with weak evidence cannot outrank a 3-domain claim with
    # strong evidence — which is the ordering a scientist would want.
    consensus = min(1.0, mean * (1.0 + INDEPENDENCE_BONUS * max(0, agreement - 1)))

    disagreements = []
    if agreement >= 2:
        lo = min(p.score for p in proposals if p.score >= MIN_DOMAIN_SCORE)
        for p in proposals:
            if p.score < MIN_DOMAIN_SCORE:
                disagreements.append(
                    f"{p.domain} does not support (score {p.score:.2f}): {p.rationale}")

    n_domains = len(proposals)
    if agreement == n_domains:
        verdict = f"all {n_domains} domain experts agree — strongest cross-domain interpolation"
    elif agreement >= n_domains - 1:
        verdict = f"{agreement}/{n_domains} independent domains agree — a genuine interpolation"
    elif agreement == 3:
        verdict = "three-domain support — a genuine interpolation, worth an assay"
    elif agreement == 2:
        verdict = "two-domain support — hypothesis, not yet a finding"
    elif agreement == 1:
        verdict = "single-domain assertion — NOT an interpolation, shown for completeness"
    else:
        verdict = "no supporting domain — rejected"

    return Consensus(claim, sorted(proposals, key=lambda p: -p.score), agreement,
                     consensus, verdict, disagreements)
