"""Discovery class 2 — 炮制 processing as chemistry.

The hypothesis class: the classical processing steps (炮, 煅, 煨, 淬, 蒸, 煮, 炒, 醋炙,
蜜炙, 酒炙, 麩炒, 發酵/麴, 水飛, 昇, 伏) and the rasaśāstra operations (bhasma, śodhana,
māraṇa) are not rituals — several are precise chemical protocols (hydrolysis, oxidation,
volatilisation, salt/acetate formation, complexation).  We translate each operation into
an operating window and a list of compound classes it enriches/destroys, then ask:

1. **Is the step necessary?**  e.g. 炮 of *Aconitum* hydrolyses diester diterpene
   alkaloids (aconitine) to far less toxic monoesters.  If the raw drug contains the
   toxic class and the process destroys it, the step is load-bearing for safety.
2. **Is the step ineffective / placebo?**  A short dry-fry (炒) cannot hydrolyse a
   diester; a calcination (煅) of a mercury sulfide does not remove the mercury.  These
   are honest negatives and they score as such.
3. **Could the step destroy the activity?**  If the process depletes the plant's active
   class with no toxicity justification, the modern practice of skipping it may be
   defensible — a testable claim.

Failure modes: the operation might have been applied for taste, storage, religious or
humoral reasons rather than chemistry; our temperature windows are engineering priors;
and a process can be heterogeneous across texts.  The dossier says so.
"""

from __future__ import annotations

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
    toxicity_of,
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

#: Processes whose chemistry can hydrolyse ester-linked alkaloids.
_HYDROLYSIS_PROCESSES = {"pao", "zhu", "zheng", "xianjian"}
#: Dry, short processes that cannot achieve hydrolysis.
_DRY_PROCESSES = {"chao", "bran_fry"}
#: Processes that concentrate rather than remove elemental toxicity.
_CONCENTRATING_PROCESSES = {"duan", "sublimation", "water_flying", "cui", "fu", "bhasma", "marana", "shodhana"}


def discover(graph: Graph, spans: SpanIndex) -> list[Hypothesis]:
    """Return one scored processing hypothesis per (drug, process) pair with a span."""
    groups: dict[tuple[str, str], list] = {}
    for edge in graph.edges:
        if edge.rel != "processed_by":
            continue
        proc_node = graph.nodes.get(edge.dst)
        if proc_node is None or proc_node.type != "process":
            continue
        proc_key = str(proc_node.props.get("process_key") or "")
        groups.setdefault((edge.src, proc_key), []).append(edge)

    hypotheses: list[Hypothesis] = []
    for (taxon_node, process_key), edges in groups.items():
        process_key = process_key if process_key in ontology.ALL_PROCESSES else ontology.canonical_process(process_key)
        if process_key not in ontology.ALL_PROCESSES:
            continue
        sem = ontology.ALL_PROCESSES[process_key]
        binomial = graph.nodes[taxon_node].label
        classes = taxon_classes(graph, binomial)
        if not classes:
            continue
        span_edges = [e for e in edges if e.props.get("char_start") is not None]
        evidence = dedupe_evidence(
            ev for ev in (evidence_from_edge(graph, e, spans) for e in span_edges) if ev
        )
        # processing-table rows carry no span; try to locate the text mention instead
        if not evidence:
            raw = next((str(e.props.get("drug_raw") or "") for e in edges if e.props.get("drug_raw")), "")
            term = next((str(e.props.get("process_term") or "") for e in edges if e.props.get("process_term")), sem.name_zh)
            if raw:
                found = spans.find([raw, term], require_all=True, confidence=0.65)
                if found:
                    evidence = [found]
        if not evidence:
            continue  # unverifiable → dropped

        toxic = set(toxicity_of(classes))
        depletes_present = sorted(classes & set(sem.depletes))
        enriches_present = sorted(classes & set(sem.enriches))
        active = sorted(classes - toxic)
        active_depleted = sorted(set(active) & set(sem.depletes))

        # -- classify the claim ------------------------------------------------------
        if toxic and (set(depletes_present) & toxic):
            pattern = "necessary_for_safety"
            mechanism_prior = 0.88
            headline = f"{sem.name_zh} ({sem.pinyin}) of {binomial} is the detoxification step, not a ritual"
            claim = (
                f"The raw drug contains the toxic class {', '.join(sorted(set(depletes_present) & toxic))}, "
                f"and the classical operation {sem.name_zh} ({sem.modern}) depletes exactly that class "
                f"by the following chemistry: {sem.mechanism} If the classical protocol does not "
                f"produce that conversion, or the processed drug retains the toxic activity, this "
                f"hypothesis is false."
            )
        elif toxic and process_key in _DRY_PROCESSES and (set(toxicity_of(classes)) - {"cardiac_glycoside", "heavy_metal"}):
            pattern = "insufficient_chemistry"
            mechanism_prior = 0.72
            headline = f"{sem.name_zh} ({sem.pinyin}) of {binomial} is probably not enough to remove its toxic class"
            claim = (
                f"{binomial} contains the toxic class {', '.join(sorted(toxic))}, but {sem.name_zh} "
                f"({sem.modern}, {sem.temperature_c}) is a dry/short operation that does not implement "
                f"the hydrolysis needed to detoxify it. If the protocol does in fact abolish the toxic "
                f"activity, this claim is false; if it does not, the safety rule is being applied "
                f"without its chemistry."
            )
        elif toxic and process_key in _CONCENTRATING_PROCESSES:
            pattern = "hazard_not_removed"
            mechanism_prior = 0.80
            headline = f"{sem.name_zh} ({sem.pinyin}) of {binomial} does not remove its elemental toxicity"
            claim = (
                f"{binomial} carries the toxic class {', '.join(sorted(toxic))}. {sem.name_zh} "
                f"({sem.modern}) changes the chemical form/particle size but does not eliminate the "
                f"elemental hazard: {sem.mechanism} If the processed product is shown to be free of "
                f"the toxic element/class at the claimed dose form, this claim is false. This is a "
                f"toxicology and quality-control finding, not a therapeutic recommendation."
            )
        elif active_depleted and not toxic:
            pattern = "may_destroy_activity"
            mechanism_prior = 0.55
            headline = f"{sem.name_zh} ({sem.pinyin}) of {binomial} may destroy its own active class"
            claim = (
                f"The active chemistry of {binomial} includes {', '.join(active_depleted)}, and "
                f"{sem.name_zh} ({sem.modern}) depletes precisely that class ({sem.mechanism}). "
                f"Unless the step removes a counteracting irritant, it should reduce activity — a "
                f"claim that a raw-vs-processed activity comparison can falsify."
            )
        elif enriches_present:
            pattern = "enrichment"
            mechanism_prior = 0.65
            headline = f"{sem.name_zh} ({sem.pinyin}) of {binomial} enriches {', '.join(enriches_present)}"
            claim = (
                f"{sem.name_zh} ({sem.modern}) enriches {', '.join(enriches_present)} from "
                f"{binomial} via {sem.mechanism} If measurement of the processed preparation does not "
                f"show that enrichment, the chemical translation is wrong."
            )
        else:
            continue  # no defensible chemistry for this pair → do not emit

        span_conf = sum(e.confidence for e in evidence) / len(evidence)
        novelty = novelty_factor(
            modern_direct_evidence=False,
            known_drug_overlap=known_drug_overlap(compound_data(graph, binomial)),
            literature_prior=literature_prior(binomial),
            span_confidence=span_conf,
        )
        plausibility = plausibility_factor(
            mechanism_prior=mechanism_prior,
            chemotype_support=1.0 if depletes_present or enriches_present else 0.5,
            process_compatibility=1.0,
            theory_support=0.7,
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

        tier, notes = safety_for(classes)
        chain = {
            "drug": next((str(e.props.get("drug_raw")) for e in edges if e.props.get("drug_raw")), binomial),
            "drug_modern": binomial,
            "part": "processed drug",
            "process": f"{sem.name_zh} ({sem.pinyin})",
            "process_modern": sem.modern,
            "chemotype": sorted(classes),
            "target_class": next(iter(target_classes_for(classes)), "not established"),
            "indication": "processing-dependent activity / safety",
        }
        hypothesis = Hypothesis(
            klass="processing",
            title=headline,
            chain=chain,
            claim=claim,
            evidence=evidence,
            score=score,
            formula_role="",
            safety_tier=tier,
            safety_notes=notes,
            falsification=falsification_plan("processing", chain),
            uncertainty_notes=(
                f"pattern={pattern}; operating window {sem.temperature_c}; "
                f"safety tier {tier}."
            ),
            extra={
                "pattern": pattern,
                "process_key": process_key,
                "temperature_c": list(sem.temperature_c) if sem.temperature_c else None,
                "enriches": sorted(sem.enriches),
                "depletes": sorted(sem.depletes),
                "toxic_classes": sorted(toxic),
                "citation": sem.citation,
            },
        )
        hypotheses.append(hypothesis)
    return hypotheses
