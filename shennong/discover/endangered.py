"""Discovery class 6 — 濒危代用品 endangered species and conservation-safe substitutes.

The hypothesis class: classical texts and modern regulation both name substitutes for
CITES-listed materia medica.  Two very different cases exist and we must not blur them:

* **Animal/mineral products with no unique pharmacology.**  Rhino horn, tiger bone,
  pangolin scales and bear bile are keratin/collagen/bile acid.  Keratin is largely
  indigestible; ursodeoxycholic acid is synthesised.  The honest finding is that the
  pharmacological need for the endangered product is absent — which is a conservation
  result, not a therapeutic recommendation.
* **Plants whose cultivated supply is chemically equivalent.**  For *Dendrobium*,
  *Gastrodia*, *Bletilla*, *Cibotium*, cultivation of the same species is the substitute;
  conservation is a supply-chain problem, not a pharmacology problem.

Failure modes: a substitute may share a class but not the active congener; cultivated
material may differ in chemotype; and "no unique pharmacology" must be demonstrated, not
asserted.  Each dossier carries the comparison assay that would settle it.
"""

from __future__ import annotations

from shennong import ontology
from shennong.discover.common import (
    Hypothesis,
    SpanIndex,
    compound_data,
    dedupe_evidence,
    safety_for,
    taxon_classes,
    target_classes_for,
)
from shennong.discover.modern_knowledge import literature_prior
from shennong.kg.schema import Graph
from shennong.score import (
    evidence_factor,
    falsification_plan,
    novelty_factor,
    plausibility_factor,
    score_hypothesis,
    testability_factor,
)

#: Classes that indicate an animal/mineral product with no unique receptor pharmacology.
_NO_UNIQUE_PHARMACOLOGY = frozenset({"protein", "mineral_salt"})
#: Classes that are cheaply available as synthetic drugs.
_SYNTHETIC_AVAILABLE = frozenset({"bile_acid", "ketone"})


def _first_zh(graph: Graph, binomial: str) -> str | None:
    node = graph.get("taxon", binomial)
    if node is None:
        return None
    for term in str(node.props.get("synonyms", "")).split(";"):
        term = term.strip()
        if term and any("\u4e00" <= ch <= "\u9fff" for ch in term):
            return term
    return None


def discover(graph: Graph, spans: SpanIndex) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    taxa = {n.label for n in graph.by_type("taxon")}
    for binomial, status in ontology.CONSERVATION_STATUS.items():
        if binomial not in taxa:
            continue
        zh = _first_zh(graph, binomial)
        if not zh:
            continue
        # evidence: a clause naming the drug and either substitution or endangerment
        evidence = []
        for terms in ([zh, "代"], [zh, "瀕危"], [zh, "濒危"], [zh, "代用品"]):
            found = spans.find(terms, require_all=True, confidence=0.8)
            if found:
                evidence.append(found)
                break
        evidence = dedupe_evidence(evidence)
        if not evidence:
            continue

        classes = taxon_classes(graph, binomial)
        substitutes = ontology.ATTESTED_SUBSTITUTES.get(binomial, ())
        substitute_taxa = [s.split(" (")[0] for s in substitutes]
        present_substitutes = [s for s in substitute_taxa if s in taxa]
        shared_classes = set()
        for sub in present_substitutes:
            shared_classes |= taxon_classes(graph, sub) & classes

        if classes & _NO_UNIQUE_PHARMACOLOGY:
            substitution_logic = "no_unique_pharmacology"
            prior = 0.90
            rationale = (
                "The product is keratin/collagen/mineral with no unique receptor pharmacology: "
                "it is largely indigestible and its identifiable constituents are available "
                "elsewhere. The conservation argument does not depend on finding a pharmacological "
                "equivalent — it depends on there being no unique activity to lose."
            )
        elif classes & _SYNTHETIC_AVAILABLE:
            substitution_logic = "synthetic_equivalent"
            prior = 0.85
            rationale = (
                "The pharmacologically relevant class is available as a defined synthetic "
                "compound (e.g. muscone, ursodeoxycholic acid), so the endangered source has no "
                "supply justification."
            )
        elif present_substitutes and shared_classes:
            substitution_logic = "shared_chemotype"
            prior = 0.80
            rationale = (
                f"The text-attested substitute(s) {', '.join(present_substitutes)} share the class "
                f"{', '.join(sorted(shared_classes))} with the endangered drug."
            )
        else:
            substitution_logic = "cultivated_same_species"
            prior = 0.75
            rationale = (
                "The text-attested substitute is cultivated material of the same species or a close "
                "congener, so the chemotype is expected to be equivalent."
            )

        span_conf = sum(e.confidence for e in evidence) / len(evidence)
        target = next(iter(target_classes_for(classes)), "no unique pharmacological target")
        novelty = novelty_factor(
            modern_direct_evidence=False,
            known_drug_overlap=any(c["name"] in {"muscone", "ursodeoxycholic_acid"} for c in compound_data(graph, binomial)),
            literature_prior=literature_prior(binomial),
            span_confidence=span_conf,
        )
        plausibility = plausibility_factor(
            mechanism_prior=prior,
            chemotype_support=1.0 if classes else 0.5,
            process_compatibility=1.0 if substitution_logic in {"cultivated_same_species", "shared_chemotype"} else 0.8,
            theory_support=0.9,
        )
        testability = testability_factor(
            target_known=bool(target_classes_for(classes)),
            assay_available=True,
            structure_available=any(c["smiles"] for c in compound_data(graph, binomial)),
        )
        evidence_f = evidence_factor(
            n_attestations=max(1, len(evidence)),
            grade="C",
            n_traditions=1,
            span_confidence=span_conf,
        )
        score = score_hypothesis(novelty, plausibility, testability, evidence_f)
        chain = {
            "drug": zh,
            "drug_modern": binomial,
            "part": "animal/mineral/plant drug as traded",
            "process": "",
            "process_modern": "",
            "chemotype": sorted(classes),
            "target_class": target,
            "indication": "conservation-safe substitution",
        }
        title = f"{zh} ({binomial}, {status['cites']}): {substitution_logic.replace('_', ' ')} → {', '.join(substitutes[:2])}"
        claim = (
            f"{binomial} is listed {status['cites']} ({status['status']}). {rationale} "
            f"A head-to-head in-vitro comparison of the endangered product with the substitute "
            f"on the claimed bioassay can falsify this: if the endangered product shows unique "
            f"activity that the substitute does not reproduce, the substitution claim fails."
        )
        hypotheses.append(
            Hypothesis(
                klass="endangered",
                title=title,
                chain=chain,
                claim=claim,
                evidence=evidence,
                score=score,
                formula_role="",
                safety_tier="conservation",
                safety_notes=(
                    "Conservation/ethics framing. This proposes a substitute for comparative testing; "
                    "it does not support continued use of the endangered product and gives no dose."
                ),
                falsification=falsification_plan("endangered", chain),
                uncertainty_notes=(
                    f"cites={status['cites']}; substitution logic={substitution_logic}; "
                    f"substitute taxa present in graph: {len(present_substitutes)}."
                ),
                extra={
                    "cites": status["cites"],
                    "status": status["status"],
                    "attested_substitutes": list(substitutes),
                    "substitution_logic": substitution_logic,
                    "note": status["note"],
                },
            )
        )
    return hypotheses
