"""Discovery class 3 — 异名同物 / 同名异物 name collision and adulteration.

The hypothesis class: one drug name has denoted different species across eras, dialects
and trade routes.  When two colliding taxa diverge in toxicity, substitution becomes a
safety event — the canonical case is 木通: 關木通 (*Aristolochia manshuriensis*) was sold
as 木通 and contains aristolochic acid, causing aristolochic-acid nephropathy and
urothelial cancer, while 川木通 (*Clematis armandii*) and 木通 (*Akebia quinata*) do not.

We rank collisions by the *toxicity divergence* between the colliding taxa, using the
compound classes actually present in the graph.  Evidence is a corpus span in which the
collision and its hazard are stated.

Failure modes: the modern trade may already be regulated (so historical risk ≠ current
exposure); a taxon may be misidentified in the corpus; and a toxic marker may be present
below a clinically relevant threshold.  The dossier states which of these applies.
"""

from __future__ import annotations

from shennong.discover.common import (
    Hypothesis,
    SpanIndex,
    compound_data,
    dedupe_evidence,
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

#: Curated collision groups: one name, several taxa, divergent hazard.
COLLISION_GROUPS: tuple[dict, ...] = (
    {
        "shared_name": "木通",
        "safe": ("Akebia quinata", "Clematis armandii"),
        "risky": ("Aristolochia manshuriensis",),
        "marker_class": "aristolochic_acid",
        "hazard": "aristolochic-acid nephropathy and urothelial carcinoma",
    },
    {
        "shared_name": "防己",
        "safe": ("Stephania tetrandra",),
        "risky": ("Aristolochia fangchi",),
        "marker_class": "aristolochic_acid",
        "hazard": "aristolochic-acid nephropathy",
    },
    {
        "shared_name": "三七",
        "safe": ("Panax notoginseng",),
        "risky": ("Gynura segetum",),
        "marker_class": "pyrrolizidine_alkaloid",
        "hazard": "pyrrolizidine-induced hepatic veno-occlusive disease",
    },
    {
        "shared_name": "五加皮",
        "safe": ("Eleutherococcus gracilistylus",),
        "risky": ("Periploca sepium",),
        "marker_class": "cardiac_glycoside",
        "hazard": "cardenolide cardiotoxicity",
    },
    {
        "shared_name": "豆根",
        "safe": ("Menispermum dauricum",),
        "risky": ("Sophora tonkinensis",),
        "marker_class": "alkaloid",
        "hazard": "matrine/oxymatrine neuro- and hepatotoxicity",
    },
    {
        "shared_name": "烏頭",
        "safe": (),
        "risky": ("Aconitum carmichaelii", "Aconitum kusnezoffii"),
        "marker_class": "diester_alkaloid",
        "hazard": "aconitine cardiotoxicity",
    },
    {
        "shared_name": "細辛",
        "safe": (),
        "risky": ("Asarum heterotropoides",),
        "marker_class": "aristolochic_acid",
        "hazard": "trace aristolochic-acid exposure",
    },
)


def _zh_synonyms(graph: Graph, binomial: str) -> list[str]:
    node = graph.get("taxon", binomial)
    if node is None:
        return []
    synonyms = str(node.props.get("synonyms", ""))
    out = []
    for term in synonyms.split(";"):
        term = term.strip()
        if term and any("\u4e00" <= ch <= "\u9fff" for ch in term):
            out.append(term)
    return out


def discover(graph: Graph, spans: SpanIndex) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    binomials = {n.label for n in graph.by_type("taxon")}
    for group in COLLISION_GROUPS:
        risky = [b for b in group["risky"] if b in binomials]
        safe = [b for b in group["safe"] if b in binomials]
        if not risky:
            continue
        risky_classes = set().union(*(taxon_classes(graph, b) for b in risky)) if risky else set()
        safe_classes = set().union(*(taxon_classes(graph, b) for b in safe)) if safe else set()
        marker = group["marker_class"]
        marker_present = marker in risky_classes
        if not marker_present and not toxic_classes_present(risky_classes):
            continue  # no evidenced toxicity divergence → not this class

        # evidence: a clause naming the risky synonym and its hazard
        evidence = []
        for binomial in risky:
            for syn in _zh_synonyms(graph, binomial):
                found = spans.find([syn, "毒"], require_all=True, confidence=0.85)
                if found:
                    evidence.append(found)
                    break
            if not evidence:
                found = spans.find([group["shared_name"]], require_all=True, confidence=0.6)
                if found:
                    evidence.append(found)
        evidence = dedupe_evidence(evidence)
        if not evidence:
            continue

        toxic = toxicity_of(risky_classes)
        span_conf = sum(e.confidence for e in evidence) / len(evidence)
        # mechanism prior rises with the marker being present and the safe species lacking it
        mechanism_prior = 0.9 if (marker_present and marker not in safe_classes) else (0.65 if marker_present else 0.5)
        novelty = novelty_factor(
            modern_direct_evidence=False,
            known_drug_overlap=any(
                known_drug_overlap(compound_data(graph, b)) for b in risky
            ),
            literature_prior=max(literature_prior(b) for b in risky),
            span_confidence=span_conf,
        )
        plausibility = plausibility_factor(
            mechanism_prior=mechanism_prior,
            chemotype_support=1.0 if (risky_classes and safe_classes) else 0.6,
            process_compatibility=1.0,
            theory_support=1.0,
        )
        testability = testability_factor(
            target_known=True,
            assay_available=True,
            structure_available=any(c["smiles"] for b in risky for c in compound_data(graph, b)),
        )
        evidence_f = evidence_factor(
            n_attestations=max(1, len(evidence)),
            grade="C",
            n_traditions=1,
            span_confidence=span_conf,
        )
        score = score_hypothesis(novelty, plausibility, testability, evidence_f)
        tier, notes = safety_for(risky_classes)
        chain = {
            "drug": group["shared_name"],
            "drug_modern": ", ".join(risky),
            "part": "commercial drug material sold under the shared name",
            "process": "",
            "process_modern": "",
            "chemotype": sorted(risky_classes),
            "target_class": next(iter(target_classes_for(risky_classes)), "toxicological"),
            "indication": "adulteration / substitution adverse event",
        }
        title = f"「{group['shared_name']}」collision: {', '.join(risky)} vs safe {', '.join(safe) or 'alternatives'} — {group['hazard']}"
        claim = (
            f"Material sold as {group['shared_name']} can be {', '.join(risky)}, which contains "
            f"{marker} and is associated with {group['hazard']}; the safe collocutor(s) "
            f"{', '.join(safe) or '(none in corpus)'} lack the marker class. If commercial samples "
            f"sold under the shared name contain no {marker} and DNA-barcode to the safe species, "
            f"this collision is historical rather than a current exposure route — a falsifiable claim."
        )
        hypotheses.append(
            Hypothesis(
                klass="name_collision",
                title=title,
                chain=chain,
                claim=claim,
                evidence=evidence,
                score=score,
                formula_role="",
                safety_tier="toxicological" if tier == "research_only" else tier,
                safety_notes=notes,
                falsification=falsification_plan("name_collision", chain),
                uncertainty_notes=(
                    f"marker {marker} {'present' if marker_present else 'not found'} in the risky taxon; "
                    f"toxic classes: {', '.join(toxic) or 'none detected'}."
                ),
                extra={
                    "shared_name": group["shared_name"],
                    "risky_taxa": risky,
                    "safe_taxa": safe,
                    "marker_class": marker,
                    "marker_present": marker_present,
                    "hazard": group["hazard"],
                },
            )
        )
    return hypotheses


def toxic_classes_present(classes: set[str]) -> bool:
    from shennong.discover.common import TOXIC_CLASSES

    return bool(classes & TOXIC_CLASSES)
