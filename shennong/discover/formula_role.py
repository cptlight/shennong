"""Discovery class 4 — 君臣佐使 formula roles and the hidden courier.

The hypothesis class: the 使 courier (envoy) in a classical formula is often doing
pharmacokinetics rather than poetry — *Piper* alkaloids (piperine), ginger, liquorice and
cinnamon are all known to modulate CYP450/P-gp or dissolution, and they appear in the
courier position.  We test the claim that the 使 role is enriched for bioenhancers and
emit the strongest courier hypotheses with an in-vitro falsification path.

Failure modes: formula roles are editorial (commentators disagree); the courier may act
by taste, masking, or clinical timing rather than PK; and the principal drug's exposure
may already be saturable.  The dossier states the role source and the disagreement.
"""

from __future__ import annotations

from shennong.discover.common import (
    Hypothesis,
    SpanIndex,
    compound_data,
    dedupe_evidence,
    evidence_from_edge,
    known_drug_overlap,
    safety_for,
    taxon_classes,
    target_classes_for,
)
from shennong.discover.modern_knowledge import literature_prior
from shennong.kg.schema import Graph
from shennong.ontology import COURIER_BIOENHANCERS
from shennong.score import (
    evidence_factor,
    falsification_plan,
    novelty_factor,
    plausibility_factor,
    score_hypothesis,
    testability_factor,
)

#: Prior strength that a courier's classical role is pharmacokinetic.
COURIER_PRIOR: dict[str, float] = {
    "Piper nigrum": 0.80,
    "Piper longum": 0.78,
    "Glycyrrhiza uralensis": 0.72,
    "Glycyrrhiza glabra": 0.72,
    "Zingiber officinale": 0.68,
    "Cinnamomum cassia": 0.50,
}


def discover(graph: Graph, spans: SpanIndex) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    for formula in graph.by_type("formula"):
        ingredients: dict[str, tuple[str, str]] = {}  # taxon label -> (role, drug_name)
        for edge in graph.out_edges(formula.id, "has_ingredient"):
            taxon = graph.nodes[edge.dst]
            ingredients[taxon.label] = (str(edge.props.get("role", "")), str(edge.props.get("drug_name", taxon.label)))
        if len(ingredients) < 2:
            continue
        jun = [label for label, (role, _) in ingredients.items() if role == "jun"]
        couriers = [(label, role, name) for label, (role, name) in ingredients.items() if role == "shi"]

        # evidence: the clause in which the formula is named
        evidence = []
        formula_names = [formula.label]
        for name in formula_names:
            found = spans.find([name], require_all=True, confidence=0.85)
            if found:
                evidence.append(found)
        evidence = dedupe_evidence(evidence)
        if not evidence:
            continue

        for label, role, drug_name in couriers:
            if label not in COURIER_BIOENHANCERS:
                continue
            classes = taxon_classes(graph, label)
            principal = jun[0] if jun else next(iter(ingredients))
            prior = COURIER_PRIOR.get(label, 0.55)
            span_conf = sum(e.confidence for e in evidence) / len(evidence)
            novelty = novelty_factor(
                modern_direct_evidence=False,
                known_drug_overlap=known_drug_overlap(compound_data(graph, label)),
                literature_prior=literature_prior(label),
                span_confidence=span_conf,
            )
            plausibility = plausibility_factor(
                mechanism_prior=prior,
                chemotype_support=1.0 if classes else 0.4,
                process_compatibility=1.0,
                theory_support=1.0,
            )
            testability = testability_factor(
                target_known=True,
                assay_available=True,
                structure_available=any(c["smiles"] for c in compound_data(graph, label)),
            )
            evidence_f = evidence_factor(
                n_attestations=max(1, len(evidence)),
                grade="C",
                n_traditions=1,
                span_confidence=span_conf,
            )
            score = score_hypothesis(novelty, plausibility, testability, evidence_f)
            tier, notes = safety_for(classes)
            chain = {
                "drug": drug_name,
                "drug_modern": label,
                "part": "formula ingredient (courier)",
                "process": "",
                "process_modern": "",
                "chemotype": sorted(classes),
                "target_class": "CYP450 / P-glycoprotein / dissolution",
                "indication": f"systemic exposure of {principal}",
            }
            title = f"{formula.label}: the 使 courier {drug_name} ({label}) is a candidate pharmacokinetic enhancer"
            claim = (
                f"In {formula.label}, {drug_name} occupies the 使 (courier) role while {principal} is the "
                f"principal (君) drug. The courier's constituents ({', '.join(sorted(classes)) or 'uncharacterised'}) "
                f"plausibly modulate CYP450/P-gp or dissolution: {COURIER_BIOENHANCERS[label]} If removing the "
                f"courier does not change the in-vitro permeability or metabolic clearance of {principal}, the "
                f"role is not pharmacokinetic and this hypothesis is false."
            )
            hypotheses.append(
                Hypothesis(
                    klass="formula_role",
                    title=title,
                    chain=chain,
                    claim=claim,
                    evidence=evidence,
                    score=score,
                    formula_role=role,
                    safety_tier=tier,
                    safety_notes=notes,
                    falsification=falsification_plan("formula_role", chain),
                    uncertainty_notes=(
                        f"courier prior {prior:.2f}; formula role from structured formula_ingredients.csv; "
                        "roles are editorial and contested in the commentarial literature."
                    ),
                    extra={
                        "formula_id": formula.props.get("formula_id", formula.label),
                        "formula_name": formula.label,
                        "principal_ingredient": principal,
                        "courier_prior": prior,
                        "courier_evidence": COURIER_BIOENHANCERS[label],
                    },
                )
            )
    return hypotheses
