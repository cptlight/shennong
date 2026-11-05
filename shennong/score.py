"""Composite hypothesis scoring, uncertainty, sensitivity analysis and falsification plans.

The score is the brief's product form::

    composite = novelty^a · plausibility^b · testability^c · evidence^d

Each factor is defined below and carries its own uncertainty.  The composite is reported
with a 95 % interval obtained by Monte-Carlo propagation of those factor uncertainties,
and the ranking is stress-tested over a grid of exponents (``sensitivity``).

No number here is a measurement of nature: every factor is an *explicitly defined
prior/estimate* whose inputs are named.  That is the point — the reader can disagree with
a factor definition and recompute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

DEFAULT_EXPONENTS: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)


@dataclass(frozen=True)
class Factor:
    """One score factor with an explicit definition and uncertainty."""

    value: float
    uncertainty: float
    definition: str

    def clamped(self) -> float:
        return float(min(1.0, max(0.001, self.value)))


@dataclass
class HypothesisScore:
    novelty: Factor
    plausibility: Factor
    testability: Factor
    evidence: Factor
    exponents: tuple[float, float, float, float] = DEFAULT_EXPONENTS
    composite: float = 0.0
    composite_ci: tuple[float, float] = (0.0, 0.0)
    drivers: list[str] = field(default_factory=list)

    def factors(self) -> tuple[Factor, Factor, Factor, Factor]:
        return self.novelty, self.plausibility, self.testability, self.evidence

    def as_scores_dict(self) -> dict[str, float]:
        return {
            "novelty": round(self.novelty.value, 4),
            "plausibility": round(self.plausibility.value, 4),
            "testability": round(self.testability.value, 4),
            "evidence": round(self.evidence.value, 4),
            "composite": round(self.composite, 6),
        }

    def as_uncertainty_dict(self) -> dict:
        return {
            "composite_ci": [round(self.composite_ci[0], 6), round(self.composite_ci[1], 6)],
            "drivers": list(self.drivers),
            "factor_uncertainty": {
                "novelty": round(self.novelty.uncertainty, 4),
                "plausibility": round(self.plausibility.uncertainty, 4),
                "testability": round(self.testability.uncertainty, 4),
                "evidence": round(self.evidence.uncertainty, 4),
            },
            "exponents": list(self.exponents),
            "notes": (
                "composite_ci is a 95% interval from Monte-Carlo propagation of the factor "
                "uncertainties (triangular distribution, seed 0); it is not an experimental "
                "confidence interval."
            ),
        }


def composite(
    novelty: float,
    plausibility: float,
    testability: float,
    evidence: float,
    exponents: Sequence[float] = DEFAULT_EXPONENTS,
) -> float:
    """Product form with clamped factors.  Enforces monotonicity by construction."""
    vals = [min(1.0, max(0.001, float(v))) for v in (novelty, plausibility, testability, evidence)]
    a, b, c, d = exponents
    return float((vals[0] ** a) * (vals[1] ** b) * (vals[2] ** c) * (vals[3] ** d))


def monte_carlo_ci(
    factors: Sequence[Factor],
    exponents: Sequence[float] = DEFAULT_EXPONENTS,
    *,
    n: int = 600,
    seed: int = 0,
) -> tuple[float, float]:
    """95 % interval of the composite under triangular factor uncertainty."""
    rng = np.random.default_rng(seed)
    draws = []
    for factor, exp in zip(factors, exponents):
        low = max(0.001, factor.value - factor.uncertainty)
        high = min(1.0, factor.value + factor.uncertainty)
        draws.append(rng.triangular(low, factor.value, high, size=n) ** exp)
    product = np.prod(np.vstack(draws), axis=0)
    return float(np.percentile(product, 2.5)), float(np.percentile(product, 97.5))


def score_hypothesis(
    novelty: Factor,
    plausibility: Factor,
    testability: Factor,
    evidence: Factor,
    *,
    exponents: Sequence[float] = DEFAULT_EXPONENTS,
    seed: int = 0,
) -> HypothesisScore:
    factors = (novelty, plausibility, testability, evidence)
    value = composite(*(f.value for f in factors), exponents)
    ci = monte_carlo_ci(factors, exponents, seed=seed)
    drivers = sorted(
        (
            ("novelty", novelty.value, novelty.uncertainty),
            ("plausibility", plausibility.value, plausibility.uncertainty),
            ("testability", testability.value, testability.uncertainty),
            ("evidence", evidence.value, evidence.uncertainty),
        ),
        key=lambda item: item[2],
        reverse=True,
    )
    return HypothesisScore(
        novelty=novelty,
        plausibility=plausibility,
        testability=testability,
        evidence=evidence,
        exponents=tuple(exponents),
        composite=value,
        composite_ci=ci,
        drivers=[f"{name} {val:.2f} ± {unc:.2f} is the largest uncertainty driver" for name, val, unc in drivers[:2]],
    )


# --------------------------------------------------------------------------------------
# Sensitivity analysis
# --------------------------------------------------------------------------------------

EXPONENT_GRID: tuple[tuple[float, float, float, float], ...] = (
    (1.0, 1.0, 1.0, 1.0),
    (2.0, 1.0, 1.0, 1.0),
    (1.0, 2.0, 1.0, 1.0),
    (1.0, 1.0, 2.0, 1.0),
    (1.0, 1.0, 1.0, 2.0),
    (0.5, 1.0, 1.0, 1.0),
    (1.0, 0.5, 1.0, 1.0),
    (1.0, 1.0, 0.5, 1.0),
    (2.0, 2.0, 1.0, 1.0),
    (1.0, 2.0, 2.0, 2.0),
)


def _kendall_tau(rank_a: Sequence[int], rank_b: Sequence[int]) -> float:
    """Kendall's τ-b between two rankings (no scipy)."""
    n = len(rank_a)
    if n < 2:
        return 1.0
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            da = rank_a[i] - rank_a[j]
            db = rank_b[i] - rank_b[j]
            if da == 0 or db == 0:
                continue
            if (da > 0) == (db > 0):
                concordant += 1
            else:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else 1.0


def sensitivity(
    scored: Sequence[dict],
    *,
    grid: Iterable[Sequence[float]] = EXPONENT_GRID,
) -> dict:
    """Rank stability of hypotheses across exponent settings.

    ``scored`` items need ``id`` and ``factors`` = [novelty, plausibility, testability,
    evidence].  Returns mean Kendall τ against the default ranking and top-5 overlap.
    """
    base_exps = DEFAULT_EXPONENTS
    base_values = [composite(*item["factors"], base_exps) for item in scored]
    base_rank = _ranks(base_values)
    base_top = set(base_rank[:5])
    results = []
    for exps in grid:
        values = [composite(*item["factors"], exps) for item in scored]
        rank = _ranks(values)
        tau = _kendall_tau(base_rank, rank)
        top = set(rank[:5])
        overlap = len(base_top & top) / max(1, len(base_top))
        results.append({"exponents": list(exps), "kendall_tau": round(tau, 4),
                        "top5_overlap": round(overlap, 4)})
    taus = [r["kendall_tau"] for r in results]
    overlaps = [r["top5_overlap"] for r in results]
    return {
        "n_hypotheses": len(scored),
        "mean_kendall_tau": round(float(np.mean(taus)), 4) if taus else 0.0,
        "min_kendall_tau": round(float(np.min(taus)), 4) if taus else 0.0,
        "mean_top5_overlap": round(float(np.mean(overlaps)), 4) if overlaps else 0.0,
        "settings": results,
    }


def _ranks(values: Sequence[float]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    rank = [0] * len(values)
    for position, index in enumerate(order):
        rank[index] = position
    return rank


# --------------------------------------------------------------------------------------
# Factor definitions used by the discovery modules
# --------------------------------------------------------------------------------------


def novelty_factor(
    *,
    modern_direct_evidence: bool,
    known_drug_overlap: bool,
    literature_prior: float,
    span_confidence: float,
) -> Factor:
    """Novelty against modern chemistry and the literature.

    ``modern_direct_evidence`` — a modern (grade A/B or modern-tradition) use exists.
    ``known_drug_overlap``     — the implicated molecule is a known drug/major lead.
    ``literature_prior``       — curated 0..1 estimate of how heavily the
                                 plant–indication pair is studied (0 = unstudied).
    ``span_confidence``        — confidence of the classical attestation.
    """
    value = 1.0
    if modern_direct_evidence:
        value *= 0.30
    if known_drug_overlap:
        value *= 0.15
    value *= (1.0 - 0.6 * min(1.0, max(0.0, literature_prior)))
    value = max(0.02, min(1.0, value))
    uncertainty = 0.10 + 0.15 * (1.0 - span_confidence)
    return Factor(value, uncertainty, "1 − modern-evidence/known-drug/familiarity overlap")


def plausibility_factor(
    *,
    mechanism_prior: float,
    chemotype_support: float,
    process_compatibility: float,
    theory_support: float = 0.0,
) -> Factor:
    """Mechanistic plausibility from independent, partly-editable priors."""
    raw = 0.35 * mechanism_prior + 0.30 * chemotype_support + 0.20 * process_compatibility + 0.15 * theory_support
    value = min(1.0, max(0.02, raw))
    uncertainty = 0.18
    return Factor(value, uncertainty, "weighted mechanism/chemotype/process/theory priors")


def testability_factor(
    *,
    target_known: bool,
    assay_available: bool,
    structure_available: bool,
) -> Factor:
    """How cheaply and decisively a hypothesis can be killed."""
    value = 0.15
    value += 0.30 if target_known else 0.0
    value += 0.30 if assay_available else 0.0
    value += 0.25 if structure_available else 0.0
    value = min(1.0, value)
    return Factor(value, 0.10, "target × assay × structure availability")


def evidence_factor(
    *,
    n_attestations: int,
    grade: str,
    n_traditions: int,
    span_confidence: float,
) -> Factor:
    """Evidence quality: independent attestations, grade, cross-tradition support, span."""
    grade_value = {"A": 0.95, "B": 0.80, "C": 0.55, "D": 0.35}.get(str(grade).upper(), 0.2)
    corroboration = 1.0 - 0.55 ** max(0, n_attestations)
    tradition_bonus = min(0.2, 0.07 * max(0, n_traditions - 1))
    value = min(1.0, grade_value * (0.5 + 0.5 * corroboration) + tradition_bonus + 0.05 * span_confidence)
    uncertainty = 0.12 + 0.10 * (1.0 - span_confidence)
    return Factor(value, uncertainty, "grade × corroboration × cross-tradition × span confidence")


# --------------------------------------------------------------------------------------
# Falsification plans
# --------------------------------------------------------------------------------------


def falsification_plan(klass: str, chain: dict) -> dict[str, str]:
    """Plain-language experiment, expected result and kill criteria.

    Rules honoured everywhere: no human dosing, no pathogen work, no toxin synthesis
    routes.  Assays are in-vitro or model-organism level and use commercially available
    reference compounds.
    """
    drug = chain.get("drug", "the drug")
    module = chain.get("drug_modern") or drug
    target = chain.get("target_class") or "the proposed target"
    if klass == "incompatibility":
        return {
            "experiment": (
                f"Bench test the {drug} pair in a human liver microsome + Caco-2 system: measure "
                "CYP3A4/2C9 activity and apparent permeability of a reference probe with and without "
                "the partner drug, and quantify any shared toxic constituent (LC-MS) in a simulated "
                "co-decoction."
            ),
            "expected_if_true": (
                "A reproducible change in probe metabolism or permeability, or a rise in the shared "
                "toxic constituent, at concentrations achieved in the co-decoction."
            ),
            "kill_criteria": (
                "No change in CYP activity, permeability or toxic-constituent level across three "
                "independent preparations → the interaction is not pharmacokinetic/chemical and the "
                "hypothesis is refuted unless a pharmacodynamic assay shows synergy."
            ),
        }
    if klass == "processing":
        return {
            "experiment": (
                f"Quantify the target constituent class in raw versus processed {drug} by LC-MS/MS, "
                "and test whether the processed extract still activates the proposed target in a "
                "cell-based assay (patch clamp for ion channels, reporter assay for transcription "
                "factors)."
            ),
            "expected_if_true": (
                "The processing step converts/depletes the specified class and the processed extract's "
                "target activity falls in proportion."
            ),
            "kill_criteria": (
                "The classical process leaves the supposedly destroyed class unchanged, or processed "
                "extract retains full target activity → the process is not the mechanism claimed."
            ),
        }
    if klass == "name_collision":
        return {
            "experiment": (
                "Blind chemical fingerprinting + DNA barcoding of commercial samples sold under the "
                "colliding name; quantify the toxic-marker class by LC-MS and compare against reference "
                "vouchers of each candidate species."
            ),
            "expected_if_true": (
                "A measurable fraction of commercial samples contains the toxic species/marker."
            ),
            "kill_criteria": (
                "All sampled material is the safe species and no toxic marker is detectable → the "
                "collision is historical but not a current exposure route."
            ),
        }
    if klass == "formula_role":
        return {
            "experiment": (
                f"Compare the in-vitro bioavailability of the principal ingredient with and without "
                f"{drug} across Caco-2 monolayers and human liver microsomes; measure the courier's "
                "effect on efflux ratio and intrinsic clearance."
            ),
            "expected_if_true": (
                "The courier increases apparent permeability and/or reduces intrinsic clearance of the "
                "principal ingredient."
            ),
            "kill_criteria": (
                "No change in permeability or clearance → the 使 role is organisational/clinical, not "
                "pharmacokinetic."
            ),
        }
    if klass == "understudied":
        return {
            "experiment": (
                f"Test {module} extract fractions in the pathway assay implied by the traditional "
                f"indication ({chain.get('indication', 'the indication')}) at a bounded concentration "
                "range, with a positive control; then deconvolute active fractions by LC-MS."
            ),
            "expected_if_true": (
                "Concentration-dependent activity in the pathway assay that co-elutes with a defined "
                "compound class."
            ),
            "kill_criteria": (
                "No activity up to the solubility limit with a validated positive control → the "
                "traditional use is not supported by this mechanism."
            ),
        }
    if klass == "endangered":
        return {
            "experiment": (
                "Head-to-head in-vitro comparison of the endangered animal/mineral product and the "
                "text-attested substitute on the claimed bioassay and on chemical fingerprinting; "
                "confirm that the substitute's active class is present."
            ),
            "expected_if_true": (
                "The substitute reproduces the claimed activity in vitro and contains the active class."
            ),
            "kill_criteria": (
                "The substitute lacks the active class or is inactive in the same assay → the "
                "substitution claim fails and a different substitute is needed."
            ),
        }
    if klass == "drug_candidate":
        return {
            "experiment": (
                f"Enzyme- or cell-based dose–response for {target} with the candidate compound "
                "and a reference inhibitor; confirm target engagement by a second orthogonal assay."
            ),
            "expected_if_true": (
                "Reproducible, concentration-dependent target engagement in two orthogonal assays."
            ),
            "kill_criteria": (
                "No engagement below the compound's solubility limit, or activity only in one assay "
                "(assay artefact) → the candidate is dead."
            ),
        }
    return {
        "experiment": "Design a targeted in-vitro assay for the proposed mechanism.",
        "expected_if_true": "Reproducible concentration-dependent activity.",
        "kill_criteria": "No activity below the solubility limit with a validated positive control.",
    }
