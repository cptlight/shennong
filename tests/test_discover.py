"""Discovery classes: citations, mechanisms, candidates and ranking."""

from shennong.discover.ranking import select_dossiers


def _by_class(discovery, klass):
    return [h for h in discovery.hypotheses if h.klass == klass]


def test_discovery_yields_many_classes(discovery):
    assert len(discovery.hypotheses) >= 10
    assert len(discovery.available_by_class) >= 5


def test_every_emitted_evidence_span_is_verbatim(discovery):
    spans = discovery.spans
    checked = 0
    for hypothesis in discovery.hypotheses:
        for evidence in hypothesis.evidence:
            assert spans.verify(evidence.source_id, evidence.char_start, evidence.char_end, evidence.quote)
            checked += 1
    assert checked >= len(discovery.hypotheses)


def test_incompatibility_pair_and_mechanism(discovery):
    pairs = _by_class(discovery, "incompatibility")
    assert pairs
    joined = " ".join(h.chain["drug"] for h in pairs)
    assert "甘草" in joined
    assert all(h.extra.get("mechanism_kind") != "unresolved" for h in pairs)


def test_processing_identifies_aconitum_hydrolysis(discovery):
    processing = _by_class(discovery, "processing")
    assert processing
    aconitum = [h for h in processing if h.chain["drug_modern"] == "Aconitum carmichaelii"]
    assert aconitum
    assert any("hydro" in h.claim.lower() or "diester" in h.claim.lower() for h in aconitum)


def test_name_collision_aristolochia(discovery):
    collisions = _by_class(discovery, "name_collision")
    assert collisions
    assert any("aristolochic_acid" in h.extra.get("marker_class", "") for h in collisions)


def test_candidates_have_real_structures_and_no_toxic_classes(discovery):
    candidates = discovery.candidates
    assert len(candidates) >= 3
    toxic = {"heavy_metal", "aristolochic_acid", "pyrrolizidine_alkaloid",
             "cyanogenic_glycoside", "cardiac_glycoside", "diester_alkaloid"}
    for candidate in candidates:
        assert candidate["descriptors"]["valid"]
        assert candidate["descriptors"]["mw"] > 0
        assert candidate["classical_line"]["verified"]
        assert candidate["name_cn"] in candidate["classical_line"]["text"]
        assert candidate["candidate_molecule"]["compound_class"] not in toxic
        assert candidate["scores"]["composite_percentile"] >= 0.0


def test_ranking_guarantees_class_coverage(discovery):
    selected = select_dossiers(discovery, n=12)
    assert 10 <= len(selected) <= 12
    classes = {h.klass for h in selected}
    available = set(discovery.available_by_class)
    assert classes == available or available <= classes


def test_rule_completeness_counts(discovery, paths):
    from shennong.eval.harness import rule_completeness

    rules = rule_completeness(paths, discovery)
    assert rules["eighteen_fan"]["canonical_total"] == 18
    assert rules["nineteen_wei"]["canonical_total"] == 19
    assert rules["eighteen_fan"]["total"] == rules["eighteen_fan"]["pairs_in_table"]
    assert rules["eighteen_fan"]["pairs_in_table"] == 16
    assert rules["nineteen_wei"]["pairs_in_table"] == 9
    assert rules["eighteen_fan"]["bridged"] >= 1
