"""Discovery class 1 — 配伍禁忌 encoded incompatibility.

The hypothesis class: pre-modern incompatibility rules (TCM 十八反 *shíbā fǎn*,
十九畏 *shíjiǔ wèi*; Āyurvedic *viruddha*) encode real herb–herb or herb–drug
interactions that were never systematically tested.  We bridge each rule pair to a
modern mechanism (CYP/P-gp, chelation/adsorption, shared toxic constituents, additive
pharmacodynamics) and rank by the plausibility of a real pharmacokinetic/toxicological
interaction.

**Failure modes we guard against** — and state in the dossier:

* the classical rule may be empirical avoidance rather than a mechanism (we return
  ``mechanism_kind="pd"`` with low prior, and ``"implausible"`` pairs are reported as
  honest negatives, e.g. 川烏 + 犀角 where the horn is indigestible keratin);
* constituent data may be incomplete (no compounds for one partner → lower confidence);
* class-level mechanisms are priors, not measured affinities.

Evidence gate: a pair is emitted only if the rule or a co-mention can be cited to a real
character span in the corpus.  Rule-list rows without a span are not enough.
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
    taxon_label,
    toxicity_of,
    target_classes_for,
    TOXIC_CLASSES,
)
from shennong.discover.modern_knowledge import literature_prior
from shennong.kg.schema import Graph
from shennong.ontology import infer_pair_mechanism
from shennong.score import (
    evidence_factor,
    falsification_plan,
    novelty_factor,
    plausibility_factor,
    score_hypothesis,
    testability_factor,
)

RULE_GLOSS = {
    "shiba_fan": "十八反 antagonism",
    "shijiu_wei": "十九畏 mutual fear",
    "viruddha": "viruddha incompatibility",
}


def discover(graph: Graph, spans: SpanIndex) -> list[Hypothesis]:
    """Return one scored hypothesis per citable incompatibility pair."""
    groups: dict[frozenset[str], list] = {}
    for edge in graph.edges:
        if edge.rel != "incompatible":
            continue
        groups.setdefault(frozenset({edge.src, edge.dst}), []).append(edge)

    hypotheses: list[Hypothesis] = []
    for key, edges in groups.items():
        span_edges = [e for e in edges if e.props.get("char_start") is not None]
        evidence = dedupe_evidence(
            ev for ev in (evidence_from_edge(graph, e, spans) for e in span_edges) if ev
        )
        if not evidence:
            continue  # unverifiable → dropped, not softened
        representative = sorted(
            span_edges or edges,
            key=lambda e: float(e.props.get("confidence", 0.0)),
            reverse=True,
        )[0]
        props = representative.props
        a_id, b_id = representative.src, representative.dst
        binomials = [graph.nodes[n].label for n in (a_id, b_id)]
        classes_a, classes_b = taxon_classes(graph, binomials[0]), taxon_classes(graph, binomials[1])
        union = classes_a | classes_b
        mechanism_kind = str(props.get("mechanism_kind") or "")
        mechanism_prior = float(props.get("mechanism_prior", 0.1))
        mechanism_text = str(props.get("mechanism", ""))
        if not mechanism_kind:
            # fall back to ontology inference if the builder stored no mechanism
            mech = infer_pair_mechanism(binomials[0], binomials[1], classes_a, classes_b)
            mechanism_kind, mechanism_prior, mechanism_text = mech.kind, mech.prior, mech.evidence
        rule_system = str(props.get("rule_system", "unknown"))
        raw_a = str(props.get("drug_a_raw") or binomials[0])
        raw_b = str(props.get("drug_b_raw") or binomials[1])

        rule_attested = any(str(e.props.get("rule_system")) in RULE_GLOSS for e in edges)
        sources = {e.props.get("source_id") for e in edges if e.props.get("source_id")}
        n_attestations = max(1, len([e for e in edges if e.props.get("char_start") is not None]))
        span_conf = sum(e.confidence for e in evidence) / len(evidence)

        novelty = novelty_factor(
            modern_direct_evidence=False,
            known_drug_overlap=known_drug_overlap(compound_data(graph, binomials[0]) + compound_data(graph, binomials[1])),
            literature_prior=0.7 * max(literature_prior(b) for b in binomials),
            span_confidence=span_conf,
        )
        plausibility = plausibility_factor(
            mechanism_prior=mechanism_prior,
            chemotype_support=1.0 if (classes_a and classes_b) else 0.5,
            process_compatibility=1.0,
            theory_support=1.0 if rule_attested else 0.5,
        )
        testability = testability_factor(
            target_known=mechanism_kind in {"pk", "pd", "toxic", "chemical"},
            assay_available=True,
            structure_available=any(c["smiles"] for b in binomials for c in compound_data(graph, b)),
        )
        evidence_f = evidence_factor(
            n_attestations=n_attestations,
            grade="C" if rule_attested else "D",
            n_traditions=2 if rule_system == "viruddha" else 1,
            span_confidence=span_conf,
        )
        score = score_hypothesis(novelty, plausibility, testability, evidence_f)

        toxic = toxicity_of(union)
        tier, notes = safety_for(union)
        if mechanism_kind == "toxic" and tier != "toxicological":
            tier = "toxicological"
        target_class = next(iter(target_classes_for(union)), "pharmacokinetic interaction")
        indication = "herb–herb / herb–drug interaction"
        chain = {
            "drug": raw_a,
            "drug_modern": binomials[0],
            "part": "co-decoction / combined formula",
            "process": "",
            "process_modern": "",
            "chemotype": sorted(union),
            "target_class": target_class,
            "indication": indication,
        }
        title = f"{raw_a} + {raw_b} ({RULE_GLOSS.get(rule_system, rule_system)}): {mechanism_kind.upper()} interaction hypothesis"
        claim = (
            f"The classical rule pairing {raw_a} ({binomials[0]}) and {raw_b} ({binomials[1]}) "
            f"is explained by a {mechanism_kind} mechanism: {mechanism_text} "
            f"This is falsifiable: if co-administration at the concentrations achieved in a "
            f"traditional co-decoction produces no change in the named mechanism, the rule is "
            f"not chemical/pharmacological and the hypothesis is false."
        )
        hypothesis = Hypothesis(
            klass="incompatibility",
            title=title,
            chain=chain,
            claim=claim,
            evidence=evidence,
            score=score,
            formula_role="",
            safety_tier=tier,
            safety_notes=notes,
            falsification=falsification_plan("incompatibility", chain),
            uncertainty_notes=(
                f"mechanism prior {mechanism_prior:.2f}; constituent data "
                f"{'present' if (classes_a and classes_b) else 'incomplete'}; "
                f"{len(sources)} rule source(s)."
            ),
            extra={
                "pair": sorted((raw_a, raw_b)),
                "rule_system": rule_system,
                "mechanism_kind": mechanism_kind,
                "mechanism_prior": mechanism_prior,
                "honest_negative": mechanism_kind == "implausible",
                "toxic_classes": toxic,
            },
        )
        hypotheses.append(hypothesis)
    return hypotheses
