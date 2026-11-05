"""Span-faithful extraction on the fixture corpus."""

from shennong.extract.extract import extract_corpus, extract_document


def _obs(extraction, kind):
    return [o for d in extraction.docs for o in d.observations if o.kind == kind]


def test_drug_entity_spans_are_verbatim(lex, docs):
    extraction = extract_corpus(docs[:6], lex)
    checked = 0
    for doc in extraction.docs:
        for entity in doc.entities:
            if entity.kind != "drug":
                continue
            assert entity.surface == doc.text[entity.start:entity.end]
            checked += 1
    assert checked > 0


def test_orthography_robust_matching(lex, docs):
    # corpus is traditional; a simplified query surface must still match
    extraction = extract_corpus(docs, lex)
    drugs = {e.canonical for d in extraction.docs for e in d.entities if e.kind == "drug"}
    assert "Rheum palmatum" in drugs  # 大黃
    assert "Coptis chinensis" in drugs  # 黃連


def test_emits_citable_treats_observations(lex, docs):
    extraction = extract_corpus(docs, lex)
    treats = _obs(extraction, "treats")
    assert treats
    for obs in treats:
        assert obs.source_id
        assert obs.char_start < obs.char_end
        assert obs.quote.strip()
        assert obs.payload["drug"]


def test_incompatibility_pairs_are_parsed_correctly(lex, docs):
    extraction = extract_corpus(docs, lex)
    incompat = _obs(extraction, "incompatible")
    canonical = {(o.payload["drug_a"], o.payload["drug_b"]) for o in incompat}
    assert ("Glycyrrhiza uralensis", "Euphorbia kansui") in canonical
    assert any(a == "Aconitum carmichaelii" for a, _ in canonical)
    for obs in incompat:
        assert obs.payload["rule_system"] in {"shiba_fan", "shijiu_wei", "viruddha"}


def test_processing_observation_for_fuzi(lex, docs):
    extraction = extract_corpus(docs, lex)
    processed = _obs(extraction, "processed_by")
    pairs = {(o.payload["drug"], o.payload["process"]) for o in processed}
    assert ("Aconitum carmichaelii", "pao") in pairs


def test_formula_composition(lex, docs):
    extraction = extract_corpus(docs, lex)
    ingredients = _obs(extraction, "ingredient_of")
    assert ingredients
    drugs = {o.payload["drug"] for o in ingredients}
    assert "Cinnamomum cassia" in drugs
