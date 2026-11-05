"""Discovery class 7 (top of the pyramid) — classical lead → drug candidate → development path.

For each promising classical lead we emit a *molecule-level* candidate:

    classical lead (drug, part, 炮制, formula role, Asian property vector)
      → chemotype (compound classes with real structures)
      → candidate molecule with computed descriptors (MW, logP, HBD/HBA, TPSA, rings,
        rotatable bonds, Lipinski/Veber flags) — computed by shennong.chem, no RDKit
      → novelty against the curated modern exclusion list
      → proposed mechanism + the Asian-theory justification that generated it
      → development path (assay, model system, what would make it a real lead)
      → residual risk (toxicity class, PAINS/assay-interference, solubility)

**Honesty rules**

* A compound with no SMILES is never given an invented structure; it is reported as
  ``"structure_status": "null"`` and cannot become a molecule-level candidate.
* Toxicological classes (heavy metals, aristolochic acid, pyrrolizidine alkaloids,
  cyanogenic glycosides, cardiac glycosides, Aconitum diester alkaloids) are **excluded
  from the candidate list** and counted in ``excluded_toxic`` — they are safety data, not
  leads.  This is deliberate and is stated in the artefact.
* ``logP`` and ``TPSA`` are labelled fragment approximations; novelty is an upper bound
  against a curated list.  The artefact says so per row.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from shennong import ontology
from shennong.chem import describe_smiles
from shennong.config import REPO_ROOT, CorpusPaths
from shennong.discover.common import (
    Hypothesis,
    SpanIndex,
    TOXIC_CLASSES,
    compound_data,
    dedupe_evidence,
    evidence_from_edge,
    find_use_evidence,
    known_drug_overlap,
    zh_synonyms,
    safety_for,
    taxon_classes,
    toxicity_of,
    target_classes_for,
)
from shennong.discover.modern_knowledge import (
    NOVELTY_METHOD,
    is_known_compound,
    literature_prior,
)
from shennong.kg.schema import Graph, node_id
from shennong.normalize import normalise as _normalise
from shennong.score import (
    evidence_factor,
    falsification_plan,
    novelty_factor,
    plausibility_factor,
    score_hypothesis,
    testability_factor,
)

ARTIFACTS_DIR = REPO_ROOT / "artifacts"

#: Assay and model system per target family (BSL-1 / cell-free only — no pathogen work).
ASSAY_BY_TARGET: dict[str, dict[str, str]] = {
    "NF-kB": {"assay": "THP-1 NF-κB luciferase reporter + IL-6/TNF-α ELISA", "model": "human monocytic cell line"},
    "IL-6": {"assay": "IL-6 ELISA in LPS-stimulated macrophages", "model": "mouse macrophage line"},
    "TNF-alpha": {"assay": "TNF-α ELISA in LPS-stimulated macrophages", "model": "mouse macrophage line"},
    "COX-1/2": {"assay": "COX-1/COX-2 colourimetric inhibitor assay (cell-free)", "model": "purified enzymes"},
    "LOX": {"assay": "5-LOX cell-free inhibitor assay", "model": "purified enzyme"},
    "Nrf2": {"assay": "ARE-luciferase reporter (Nrf2 translocation)", "model": "HepG2 cells"},
    "GABA_A": {"assay": "membrane-potential dye assay on GABA_A-expressing cells", "model": "recombinant cell line"},
    "TRPA1": {"assay": "Ca2+ flux (FLIPR) on TRPA1-expressing cells", "model": "recombinant cell line"},
    "TRPV1": {"assay": "Ca2+ flux (FLIPR) with capsaicin positive control", "model": "recombinant cell line"},
    "AChE": {"assay": "Ellman colorimetric AChE assay", "model": "purified enzyme"},
    "opioid receptor": {"assay": "GTPγS binding at μ-opioid receptor", "model": "membrane preparation"},
    "Na+ channel": {"assay": "patch-clamp (Nav1.5/Nav1.7) with hERG counter-screen", "model": "recombinant cell line"},
    "Na+/K+-ATPase": {"assay": "ouabain-sensitive ATPase assay", "model": "membrane preparation"},
    "11beta-HSD2": {"assay": "11β-HSD2 enzyme assay (cortisol→cortisone)", "model": "purified enzyme"},
    "CNR1": {"assay": "cAMP accumulation assay at CB1", "model": "recombinant cell line"},
    "CNR2": {"assay": "cAMP accumulation assay at CB2", "model": "recombinant cell line"},
    "5-HT reuptake": {"assay": "serotonin uptake assay (SERT)", "model": "recombinant cell line"},
    "PAF receptor": {"assay": "platelet-activating-factor receptor binding", "model": "membrane preparation"},
    "vitamin K epoxide reductase": {"assay": "VKOR activity assay", "model": "microsomal preparation"},
    "membrane sterols": {"assay": "haemolysis / membrane-permeability assay", "model": "erythrocyte suspension"},
    "protein kinase C": {"assay": "PKC kinase activity assay", "model": "purified enzyme"},
    "bacterial membrane": {"assay": "cell-free membrane-permeability assay (no pathogen culture)", "model": "liposome model"},
    "thiol groups": {"assay": "thiol-reactivity (DTNB) assay", "model": "cell-free"},
    "immune receptors (dectin-1, TLR)": {"assay": "reporter assay in TLR-transfected cells", "model": "recombinant cell line"},
}


#: English translations for classical lines we can translate with confidence.
_TRANSLATIONS: dict[str, str] = {
    "大黃，味苦寒": "Rhubarb (大黃): bitter, cold in nature.",
    "陳皮，味辛苦，溫，無毒": "Tangerine peel (陳皮): pungent and bitter, warm, non-toxic.",
    "桂枝，味辛甘，溫，無毒": "Cinnamon twig (桂枝): pungent and sweet, warm, non-toxic.",
    "薄荷，味辛，涼，無毒": "Field mint (薄荷): pungent, cool, non-toxic.",
    "生薑，味辛，微溫，無毒": "Fresh ginger (生薑): pungent, slightly warm, non-toxic.",
    "當歸，味甘辛，溫，無毒": "Dong quai (當歸): sweet and pungent, warm, non-toxic.",
    "黃連，味苦寒": "Coptis (黃連): bitter, cold.",
    "甘草，味甘，氣平，無毒": "Licorice (甘草): sweet, neutral in qi, non-toxic.",
}


def _tcm_with_original_name(tcm, binomial: str, graph: Graph) -> dict:
    """TCM property dict with the *traditional-character* drug name for provenance checks."""
    data = tcm.to_dict()
    names = zh_synonyms(graph, binomial)
    if names:
        data["drug_name"] = names[0]
    return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_theory_features(paths: CorpusPaths):
    try:
        from shennong.theory.features import load_features

        return load_features(paths)
    except Exception:
        return None


def _best_target(compound_class: str, indication: str) -> tuple[str, float]:
    """Pick the target that best matches the indication's mechanism, with a prior score."""
    profile = ontology.compound_class_profile(compound_class)
    spec = ontology.indication_spec(indication)
    if profile is None:
        return "not established", 0.3
    if spec is not None:
        # exact indication match inside the class prior
        if spec.indication in profile.indications:
            return (profile.targets[0] if profile.targets else "not established"), 0.85
        if set(spec.pathways) & set(profile.pathways):
            return (profile.targets[0] if profile.targets else "not established"), 0.7
    return (profile.targets[0] if profile.targets else "not established"), 0.45


def _theory_justification(features, binomial: str, indication: str, classes: list[str]) -> str:
    """Generate the Asian-theory prediction that motivated this candidate (labelled)."""
    organ = ontology.organ_for_indication(indication) or "systemic"
    parts: list[str] = []
    tcm = features.tcm.get(binomial) if features else None
    ayu = features.ayurveda.get(binomial) if features else None
    if tcm:
        nature = tcm.nature or "unclassified"
        flavours = "/".join(tcm.flavors) or "unclassified"
        channels = "/".join(tcm.channels) or "unclassified"
        parts.append(
            f"四氣五味: {nature}, {flavours}. 歸經: {channels}. "
            f"The classical prediction is that a {nature} {flavours} drug entering the "
            f"{channels} channel reaches {organ}-related patterns."
        )
    if ayu:
        parts.append(
            f"Āyurveda: rasa {'/'.join(ayu.rasa) or '—'}, vīrya {ayu.virya or '—'}, "
            f"vipāka {ayu.vipaka or '—'}, doṣa effect {ayu.dosha_effect or '—'}."
        )
    if not parts:
        return (
            "No Asian property vector is available for this drug in the current corpus, so the "
            "candidate is generated from chemotype and indication only; theory-consistency cannot "
            "be stated."
        )
    parts.append(
        f"Chemotype {'/'.join(classes) or '—'}. This is a theory-generated prediction, not evidence: "
        "it is tested against chemistry and target biology in eval/report.json → drug_discovery.theory_predictivity."
    )
    return " ".join(parts)


def _select_indication(graph: Graph, binomial: str, spans: SpanIndex):
    """Pick the historical indication with the strongest chemotype bridge and a real span."""
    classes = taxon_classes(graph, binomial)
    best = None
    tid = node_id("taxon", binomial)
    for edge in graph.out_edges(tid, "treats"):
        indication = graph.nodes[edge.dst].label
        bridge = sorted(classes & ontology.classes_for_indication(indication))
        if not bridge:
            continue
        evidence = None
        if edge.props.get("char_start") is not None:
            evidence = evidence_from_edge(graph, edge, spans)
        if evidence is None:
            evidence = find_use_evidence(spans, graph, binomial, indication)
        if evidence is None:
            continue
        # integrity gate: the span must name the drug and, where possible, the indication
        from shennong.normalize import normalise as _normalise

        spec = ontology.indication_spec(indication)
        quote_norm = _normalise(evidence.quote)
        drug_terms = [binomial, *zh_synonyms(graph, binomial)]
        if not any(_normalise(term) and _normalise(term) in quote_norm for term in drug_terms):
            continue
        if spec is not None:
            indication_terms = [*spec.zh, *spec.sa, *spec.en, *spec.ar, indication]
            if not any(_normalise(term) in quote_norm for term in indication_terms if term):
                continue
        score = (len(bridge), not bool(edge.props.get("modern")), float(evidence.confidence))
        if best is None or score > best[0]:
            best = (score, indication, bridge, evidence, edge)
    return best


def discover_candidates(graph: Graph, spans: SpanIndex, paths: CorpusPaths | None = None) -> tuple[list[dict], dict]:
    """Build molecule-level candidates from the graph.

    Returns ``(candidates, diagnostics)`` where diagnostics counts excluded/toxic leads
    and structures that were null.
    """
    features = _load_theory_features(paths) if paths else None
    candidates: list[dict] = []
    diagnostics = {
        "taxa_considered": 0,
        "taxa_without_structure": 0,
        "excluded_toxic": [],
        "compounds_without_smiles": 0,
        "invalid_smiles": [],
        "theory_features_available": features is not None,
    }
    for taxon in graph.by_type("taxon"):
        binomial = taxon.label
        compounds = compound_data(graph, binomial)
        if not compounds:
            continue
        diagnostics["taxa_considered"] += 1
        classes = taxon_classes(graph, binomial)
        toxic = toxicity_of(classes)
        if toxic or (classes & TOXIC_CLASSES):
            diagnostics["excluded_toxic"].append({"taxon": binomial, "toxic_classes": toxic})
            continue
        selected = _select_indication(graph, binomial, spans)
        if selected is None:
            continue
        _, indication, bridge, evidence, use_edge = selected
        lead_evidence = [evidence]
        # every candidate compound with a real structure
        for compound in compounds:
            if not compound.get("smiles"):
                diagnostics["compounds_without_smiles"] += 1
                continue
            descriptors = describe_smiles(compound["smiles"])
            if not descriptors.valid:
                diagnostics["invalid_smiles"].append(compound["name"])
                continue
            cls_profile = ontology.compound_class_profile(compound.get("compound_class", ""))
            target, target_prior = _best_target(compound.get("compound_class", ""), indication)
            assay = ASSAY_BY_TARGET.get(target, {"assay": "cell-free target-binding screen", "model": "purified protein or recombinant cell line"})
            pain_flags = sorted(k for k, v in descriptors.flags.items() if v)
            pair_modern = any(
                e.props.get("modern")
                for e in graph.out_edges(node_id("taxon", binomial), "treats")
                if graph.nodes[e.dst].label == indication
            )
            span_conf = evidence.confidence
            novelty = novelty_factor(
                modern_direct_evidence=bool(pair_modern),
                known_drug_overlap=is_known_compound(compound["name"]),
                literature_prior=literature_prior(binomial),
                span_confidence=span_conf,
            )
            plausibility = plausibility_factor(
                mechanism_prior=target_prior,
                chemotype_support=1.0 if (compound.get("compound_class") in bridge) else 0.6,
                process_compatibility=1.0,
                theory_support=0.25 if features and (binomial in features.tcm or binomial in features.ayurveda) else 0.0,
            )
            testability = testability_factor(
                target_known=bool(cls_profile and cls_profile.targets),
                assay_available=bool(assay),
                structure_available=descriptors.valid,
            )
            evidence_f = evidence_factor(
                n_attestations=1,
                grade=str(use_edge.props.get("evidence_grade", "D")),
                n_traditions=1,
                span_confidence=span_conf,
            )
            score = score_hypothesis(novelty, plausibility, testability, evidence_f)
            risk_notes = []
            if descriptors.logp_estimate > 5:
                risk_notes.append("logP_estimate > 5: low aqueous solubility / high promiscuity risk")
            if descriptors.lipinski_violations:
                risk_notes.append(f"{descriptors.lipinski_violations} Lipinski violation(s)")
            if pain_flags:
                risk_notes.append(f"structural alerts: {', '.join(pain_flags)}")
            if not descriptors.veber_pass:
                risk_notes.append("fails Veber oral-bioavailability criteria")
            if not risk_notes:
                risk_notes.append("no structural red flag from the heuristic filter; safety data still pending")
            candidate = {
                "id": "",  # assigned at ranking
                "class": "drug_candidate",
                "lead": {
                    "drug": taxon.label,
                    "drug_modern": binomial,
                    "part": "not specified in source",
                    "process": next(
                        (str(e.props.get("process_term", "")) for e in graph.out_edges(taxon.id, "processed_by")),
                        "none attested",
                    ),
                    "formula_role": next(
                        (
                            str(e.props.get("role", ""))
                            for e in graph.in_edges(taxon.id, "has_ingredient")
                        ),
                        "",
                    ),
                    "indication": indication,
                    "asian_properties": (
                        {
                            "tcm": _tcm_with_original_name(features.tcm[binomial], binomial, graph)
                            if features and binomial in features.tcm
                            else None,
                            "ayurveda": features.ayurveda[binomial].to_dict()
                            if features and binomial in features.ayurveda
                            else None,
                        }
                        if features
                        else None
                    ),
                },
                "candidate_molecule": {
                    "name": compound["name"],
                    "compound_class": compound.get("compound_class", ""),
                    "smiles": compound["smiles"],
                    "cid": compound.get("cid"),
                    "structure_status": "provided",
                    "resolution_method": (
                        "SMILES supplied in corpus/processed/structured/compounds.csv "
                        "(source_id: "
                        + str(
                            graph.nodes[node_id("compound", compound["name"])].props.get("source_id", "unknown")
                        )
                        + "); descriptors computed by shennong.chem"
                    ),
                },
                "descriptors": descriptors.to_dict(),
                "novelty": {
                    "score": round(novelty.value, 4),
                    "method": NOVELTY_METHOD,
                    "known_compound": is_known_compound(compound["name"]),
                    "modern_evidence_for_pair": bool(pair_modern),
                    "literature_prior": literature_prior(binomial),
                },
                "mechanism": {
                    "target_class": target,
                    "pathway": ", ".join(cls_profile.pathways) if cls_profile else "",
                    "rationale": cls_profile.notes if cls_profile else "compound class prior unavailable",
                    "class_citation": cls_profile.citation if cls_profile else "",
                },
                "asian_theory_justification": _theory_justification(features, binomial, indication, sorted(classes)),
                "development_path": {
                    "assay": assay["assay"],
                    "model_system": assay["model"],
                    "what_would_make_it_a_real_lead": (
                        "reproducible sub-micromolar target engagement in two orthogonal assays, "
                        "selectivity over the closest paralogue, and measurable exposure without "
                        "the structural alerts above"
                    ),
                },
                "residual_risk": {
                    "toxicity_class": "none detected in the compound-class map",
                    "structural_alerts": pain_flags,
                    "solubility_risk": "high" if descriptors.logp_estimate > 4.5 else "moderate",
                    "notes": "; ".join(risk_notes),
                },
                "scores": score.as_scores_dict(),
                "uncertainty": score.as_uncertainty_dict(),
                "evidence": [evidence.to_dict()],
                "falsification": falsification_plan(
                    "drug_candidate",
                    {"drug": binomial, "drug_modern": binomial, "target_class": target},
                ),
                "safety": {
                    "tier": "research_only",
                    "notes": (
                        "Research use only. Not medical advice; no dose or human-use protocol is given. "
                        "The lead plant is excluded from the toxicological class list for this candidate."
                    ),
                },
            }
            # ---- Workbench compatibility block (story-builder contract) -----------
            tcm = features.tcm.get(binomial) if features else None
            ayu = features.ayurveda.get(binomial) if features else None
            traditional_names = zh_synonyms(graph, binomial)
            name_cn = traditional_names[0] if traditional_names else (tcm.drug_name if tcm else taxon.label)
            candidate["name"] = compound["name"]
            candidate["name_cn"] = name_cn
            candidate["discovery_class"] = "drug_candidate"
            candidate["classical_lead"] = {
                "drug": taxon.label,
                "drug_en": binomial,
                "part": candidate["lead"]["part"],
                "processing": candidate["lead"]["process"],
                "formula_role": candidate["lead"]["formula_role"],
                "source": evidence.source_id,
            }
            candidate["formula"] = None
            candidate["mw"] = descriptors.mw
            candidate["smiles"] = compound["smiles"]
            candidate["structure_status"] = "provided"
            candidate["structure_note"] = candidate["candidate_molecule"]["resolution_method"]
            candidate["theory"] = {
                "nature": tcm.nature if tcm else None,
                "flavors": list(tcm.flavors) if tcm else [],
                "channels": list(tcm.channels) if tcm else [],
                "direction": tcm.direction if tcm else None,
                "grade": tcm.grade if tcm else None,
                "rasa": list(ayu.rasa) if ayu else [],
                "virya": ayu.virya if ayu else None,
            }
            candidate["mechanism"]["evidence_level"] = "class-level prior (textbook pharmacology)"
            candidate["novelty"]["basis"] = "curated exclusion list + graph modern evidence"
            candidate["novelty"]["prior_art"] = (
                "known approved/lead compound" if is_known_compound(compound["name"]) else "no prior art flagged offline"
            )
            candidate["theory_justification"] = candidate["asian_theory_justification"]
            candidate["development_path"] = [
                {"step": "assay", "kind": assay["assay"]},
                {"step": "model system", "kind": assay["model"]},
                {"step": "go/no-go", "kind": candidate["development_path"]["what_would_make_it_a_real_lead"]},
            ]
            candidate["residual_risk"] = risk_notes
            candidate["safety"] = {
                "flags": pain_flags,
                "severity": "caution" if pain_flags else "none",
                "notes": candidate["safety"]["notes"],
            }
            candidate["status"] = "proposed"
            candidate["classical_line"] = {
                "source": evidence.title,
                "year": evidence.year,
                "locator": f"{evidence.source_id}:{evidence.char_start}-{evidence.char_end}",
                "text": evidence.quote,
                "translation": _TRANSLATIONS.get(evidence.quote.strip(), ""),
                "span_kind": "verbatim",
                "names_drug": name_cn,
                "verified": _normalise(name_cn) in _normalise(evidence.quote),
            }
            candidates.append(candidate)
    candidates.sort(key=lambda c: c["scores"]["composite"], reverse=True)
    # one row per molecule: keep the best lead, record the alternatives
    deduped: list[dict] = []
    seen_molecules: dict[str, dict] = {}
    for candidate in candidates:
        molecule = candidate["candidate_molecule"]["name"]
        if molecule in seen_molecules:
            seen_molecules[molecule].setdefault("alternative_leads", []).append(
                candidate["lead"]["drug_modern"]
            )
            continue
        seen_molecules[molecule] = candidate
        deduped.append(candidate)
    for i, candidate in enumerate(deduped, start=1):
        candidate["id"] = f"C-2026-{i:04d}"
        candidate["rank"] = i
    diagnostics["candidates"] = len(deduped)
    diagnostics["duplicate_molecules_collapsed"] = len(candidates) - len(deduped)
    return deduped, diagnostics


def write_candidates(candidates: list[dict], diagnostics: dict, out_dir: str | Path | None = None, *, fixture: bool | None = None) -> tuple[Path, Path]:
    """Write ``artifacts/drug_candidates.json`` and ``.md``."""
    out = Path(out_dir) if out_dir else ARTIFACTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now(),
        "fixture": bool(fixture) if fixture is not None else False,
        "n": len(candidates),
        "method": NOVELTY_METHOD,
        "candidate_schema": "lead → chemotype → molecule → mechanism → development path → risk",
        "diagnostics": diagnostics,
        "candidates": candidates,
    }
    json_path = out / "drug_candidates.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "# SHENNONG — drug candidate shortlist",
        "",
        f"Generated {payload['generated_at']}. **{len(candidates)} candidates** from "
        "classical Asian leads with real SMILES.",
        "",
        "> Research use only. Not medical advice. No dose or human-use protocol is given. "
        "Toxicological drugs (heavy metals, aristolochic acid, pyrrolizidine alkaloids, "
        "cyanogenic glycosides, cardiac glycosides, Aconitum diesters) are excluded by design.",
        "",
        f"**Novelty method.** {NOVELTY_METHOD}",
        "",
        "| # | Lead (drug) | Candidate | Class | MW | logP* | TPSA* | Target | Indication | Composite |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in candidates[:20]:
        d = c["descriptors"]
        lines.append(
            f"| {c['id']} | {c['lead']['drug_modern']} | {c['candidate_molecule']['name']} | "
            f"{c['candidate_molecule']['compound_class']} | {d['mw']:.1f} | {d['logp_estimate']:.2f} | "
            f"{d['tpsa']:.1f} | {c['mechanism']['target_class']} | {c['lead']['indication']} | "
            f"{c['scores']['composite']:.4f} |"
        )
    lines += [
        "",
        "\\* `logP` and `TPSA` are transparent fragment approximations from `shennong.chem`, "
        "not validated Crippen/Ertl calculations. MW, HBD/HBA, rings and rotatable bonds are exact "
        "given the SMILES parse.",
        "",
        f"Excluded toxicological leads: {len(diagnostics.get('excluded_toxic', []))}; "
        f"compounds with null structure: {diagnostics.get('compounds_without_smiles', 0)} "
        "(never invented). Full detail in `drug_candidates.json`.",
        "",
    ]
    md_path = out / "drug_candidates.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def candidate_hypotheses(candidates: list[dict]) -> list[Hypothesis]:
    """Convert candidate dicts into dossiers so `shi` can rank them with the rest."""
    from shennong.score import HypothesisScore, Factor

    hypotheses: list[Hypothesis] = []
    for candidate in candidates:
        d = candidate["descriptors"]
        score = HypothesisScore(
            novelty=Factor(candidate["scores"]["novelty"], 0.1, "candidate novelty"),
            plausibility=Factor(candidate["scores"]["plausibility"], 0.18, "candidate plausibility"),
            testability=Factor(candidate["scores"]["testability"], 0.1, "candidate testability"),
            evidence=Factor(candidate["scores"]["evidence"], 0.15, "candidate evidence"),
            composite=candidate["scores"]["composite"],
            composite_ci=tuple(candidate["uncertainty"]["composite_ci"]),
            drivers=list(candidate["uncertainty"]["drivers"]),
        )
        from shennong.discover.common import Evidence

        evidence = [
            Evidence(
                source_id=e["source_id"], title=e["title"], year=e["year"], quote=e["quote"],
                char_start=e["char_start"], char_end=e["char_end"], confidence=e["confidence"],
                span_kind=e.get("span_kind", "verbatim"),
            )
            for e in candidate["evidence"]
        ]
        chain = {
            "drug": candidate["lead"]["drug"],
            "drug_modern": candidate["lead"]["drug_modern"],
            "part": candidate["lead"]["part"],
            "process": candidate["lead"]["process"],
            "process_modern": "",
            "chemotype": [candidate["candidate_molecule"]["compound_class"]],
            "target_class": candidate["mechanism"]["target_class"],
            "indication": candidate["lead"]["indication"],
        }
        hypotheses.append(
            Hypothesis(
                klass="drug_candidate",
                title=f"Candidate {candidate['candidate_molecule']['name']} from {candidate['lead']['drug_modern']}: {candidate['mechanism']['target_class']}",
                chain=chain,
                claim=(
                    f"{candidate['candidate_molecule']['name']} ({candidate['candidate_molecule']['compound_class']}) "
                    f"from {candidate['lead']['drug_modern']} engages {candidate['mechanism']['target_class']} and "
                    f"is proposed for {candidate['lead']['indication']}. {candidate['mechanism']['rationale']} "
                    f"Falsified if no target engagement below the compound's solubility limit."
                ),
                evidence=evidence,
                score=score,
                formula_role=candidate["lead"]["formula_role"],
                safety_tier="research_only",
                safety_notes=candidate["safety"]["notes"],
                falsification=candidate["falsification"],
                uncertainty_notes="; ".join(candidate["residual_risk"]),
                extra={
                    "candidate": {
                        "id": candidate["id"],
                        "molecule": candidate["candidate_molecule"]["name"],
                        "descriptors": {k: d[k] for k in ("mw", "logp_estimate", "tpsa", "hbd", "hba", "rings", "rotatable_bonds", "lipinski_pass", "veber_pass")},
                        "development_path": candidate["development_path"],
                        "asian_theory_justification": candidate["asian_theory_justification"],
                        "resolution_method": candidate["candidate_molecule"]["resolution_method"],
                    }
                },
            )
        )
    return hypotheses
