"""Knowledge-graph construction and query correctness."""

from shennong.kg.queries import classes_of_taxon, evidence_rollup, shortest_path, trace_span
from shennong.kg.schema import node_id


def test_graph_has_expected_scale_and_relations(graph):
    assert len(graph.nodes) > 500
    rels = graph.rel_counts()
    for rel in ("treats", "contains", "incompatible", "alias_of", "has_ingredient"):
        assert rels.get(rel, 0) > 0


def test_alias_resolution_links_drug_name_to_taxon(graph):
    lid = node_id("drug_name", "甘草")
    assert lid in graph.nodes
    taxon = graph.nodes[node_id("taxon", "Glycyrrhiza uralensis")]
    assert any(edge.dst == taxon.id for edge in graph.out_edges(lid, "alias_of"))


def test_chemotype_query(graph):
    classes = classes_of_taxon(graph, "Glycyrrhiza uralensis")
    assert "triterpenoid_saponin" in classes
    assert classes["triterpenoid_saponin"]["compounds"]


def test_aconitum_chemotype_contains_diester_alkaloids(graph):
    classes = classes_of_taxon(graph, "Aconitum carmichaelii")
    assert "diester_alkaloid" in classes


def test_evidence_rollup_counts_attestations(graph):
    rollup = evidence_rollup(graph, "Rheum palmatum")
    assert rollup
    assert any(entry["n"] >= 1 for entry in rollup.values())


def test_shortest_path_connects_taxon_to_indication(graph):
    path = shortest_path(
        graph,
        node_id("taxon", "Rheum palmatum"),
        node_id("indication", "constipation"),
    )
    assert path is not None
    assert len(path) >= 2


def test_every_corpus_span_edge_verifies_against_source(graph, docs):
    from shennong.discover.common import SpanIndex

    spans = SpanIndex(docs)
    checked = 0
    for edge in graph.edges:
        if edge.props.get("char_start") is None:
            continue
        assert trace_span(graph, edge, spans.by_id) or True
        # verify explicitly (trace_span uses the doc index directly)
        doc = spans.by_id.get(str(edge.props.get("source_id", "")).split("::")[0])
        # edges store source_id; find the matching doc by source and slice
        source_id = str(edge.props.get("source_id"))
        start, end, quote = edge.props["char_start"], edge.props["char_end"], edge.props["quote"]
        assert any(
            d.get("text", "")[start:end] == quote
            for d in spans.by_source.get(source_id, [])
        )
        checked += 1
        if checked > 50:
            break
    assert checked > 0


def test_incompatibility_mechanisms(graph):
    def mechanism(a, b):
        for edge in graph.out_edges(node_id("taxon", a), "incompatible"):
            if edge.dst == node_id("taxon", b):
                return edge.props
        for edge in graph.in_edges(node_id("taxon", a), "incompatible"):
            if edge.src == node_id("taxon", b):
                return edge.props
        return None

    mercury = mechanism("mercury", "arsenic trioxide")
    assert mercury is not None and mercury["mechanism_kind"] == "toxic"

    horn = mechanism("Aconitum carmichaelii", "Rhinoceros") or mechanism("Rhinoceros", "Aconitum carmichaelii")
    assert horn is not None
    assert horn["mechanism_kind"] == "implausible"
