"""Discovery class 5 — 未研究本草 the understudied majority.

The hypothesis class: a drug has repeated, multi-tradition attestation for an indication,
and its documented chemotype plausibly bridges to the pathway behind that indication, yet
the graph contains **no modern direct evidence** for the pair.  That is an abandoned lead.

"Modern direct evidence" is defined strictly: a use edge with a grade A/B evidence level
or a modern-tradition attestation (see ``ontology.is_modern_evidence``).  A drug with
modern *preclinical* work but no clinical evidence is still understudied at the clinical
level, and the dossier says which gap applies.

Failure modes: the traditional indication may be symptom-level and not mechanistically
equivalent to the modern one; the plant's active constituents may not be the ones in the
chemotype table; and absence of modern evidence can reflect commercial irrelevance rather
than genuine neglect.  All three are stated.
"""

from __future__ import annotations

from collections import defaultdict

from shennong import ontology
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
    target_classes_for,
)
from shennong.discover.modern_knowledge import literature_prior
from shennong.kg.schema import Graph, node_id
from shennong.score import (
    evidence_factor,
    falsification_plan,
    novelty_factor,
    plausibility_factor,
    score_hypothesis,
    testability_factor,
)


def discover(graph: Graph, spans: SpanIndex) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    for taxon in graph.by_type("taxon"):
        binomial = taxon.label
        classes = taxon_classes(graph, binomial)
        if not classes:
            continue
        # group this taxon's treat edges by canonical indication
        by_indication: dict[str, list] = defaultdict(list)
        for edge in graph.out_edges(taxon.id, "treats"):
            by_indication[graph.nodes[edge.dst].label].append(edge)
        for indication, edges in by_indication.items():
            _ = edges
            modern = any(
                e.props.get("modern")
                or ontology.is_modern_evidence(
                    str(e.props.get("tradition", "")), str(e.props.get("evidence_grade", "D"))
                )
                for e in edges
            )
            if modern:
                continue
            spec = ontology.indication_spec(indication)
            if spec is not None:
                bridge = sorted(classes & ontology.classes_for_indication(indication))
            else:
                action = ontology.infer_action_class(indication)
                bridge = sorted(classes & ontology.classes_for_action_class(action))
            if not bridge:
                continue
            # require a citable span for this pair
            evidence = dedupe_evidence(
                ev
                for ev in (
                    evidence_from_edge(graph, e, spans)
                    for e in edges
                    if e.props.get("char_start") is not None
                )
                if ev
            )
            if not evidence:
                continue
            traditions = sorted({str(e.props.get("tradition", "unknown")) for e in edges})
            grades = [str(e.props.get("evidence_grade", "D")) for e in edges]
            best_grade = min(grades, key=lambda g: {"A": 0, "B": 1, "C": 2, "D": 3}.get(g, 4))
            span_conf = sum(e.confidence for e in evidence) / len(evidence)
            compounds = compound_data(graph, binomial)
            target = next(iter(target_classes_for(bridge)), next(iter(target_classes_for(classes)), "not established"))
            bridge_fraction = len(bridge) / max(1, len(classes))

            novelty = novelty_factor(
                modern_direct_evidence=False,
                known_drug_overlap=known_drug_overlap(compounds),
                literature_prior=literature_prior(binomial),
                span_confidence=span_conf,
            )
            plausibility = plausibility_factor(
                mechanism_prior=min(0.85, 0.45 + 0.10 * len(bridge)),
                chemotype_support=min(1.0, 0.5 + 0.5 * bridge_fraction),
                process_compatibility=0.8,
                theory_support=0.5,
            )
            testability = testability_factor(
                target_known=bool(target_classes_for(bridge)),
                assay_available=True,
                structure_available=any(c["smiles"] for c in compounds),
            )
            evidence_f = evidence_factor(
                n_attestations=len(edges),
                grade=best_grade,
                n_traditions=len(traditions),
                span_confidence=span_conf,
            )
            score = score_hypothesis(novelty, plausibility, testability, evidence_f)
            tier, notes = safety_for(classes)
            chain = {
                "drug": taxon_label(graph, binomial),
                "drug_modern": binomial,
                "part": "not specified in source",
                "process": "",
                "process_modern": "",
                "chemotype": sorted(classes),
                "target_class": target,
                "indication": indication,
            }
            title = (
                f"Abandoned lead: {binomial} for {indication} "
                f"({len(traditions)} tradition{'s' if len(traditions) != 1 else ''}, no modern direct evidence)"
            )
            claim = (
                f"{binomial} is attested for {indication} in {', '.join(traditions)}, and its chemotype "
                f"({', '.join(bridge)}) plausibly bridges to the {indication} pathway via {target}. "
                f"No modern controlled evidence for this plant–indication pair is present in the graph. "
                f"If the extract shows no pathway activity up to its solubility limit with a validated "
                f"positive control, the traditional use is not supported by this mechanism and the lead "
                f"is dead."
            )
            hypotheses.append(
                Hypothesis(
                    klass="understudied",
                    title=title,
                    chain=chain,
                    claim=claim,
                    evidence=evidence,
                    score=score,
                    formula_role="",
                    safety_tier=tier,
                    safety_notes=notes,
                    falsification=falsification_plan("understudied", chain),
                    uncertainty_notes=(
                        f"{len(edges)} attestation(s) across {len(traditions)} tradition(s); best grade "
                        f"{best_grade}; chemotype bridge covers {len(bridge)}/{len(classes)} classes."
                    ),
                    extra={
                        "traditions": traditions,
                        "n_attestations": len(edges),
                        "bridge_classes": bridge,
                        "best_grade": best_grade,
                        "modern_evidence": False,
                    },
                )
            )
    return hypotheses
