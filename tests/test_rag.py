"""BM25 retrieval and refusal-first grounded answering."""

from shennong.rag.answer import answer
from shennong.rag.bm25 import build_index, coverage, index_tokens, query_tokens


def test_bm25_retrieves_licorice_passage(docs):
    index = build_index(docs)
    hits = index.search("甘草 licorice", k=5)
    assert hits
    assert any("甘草" in hit.doc.text for hit in hits)


def test_bm25_scores_are_positive_and_sorted(docs):
    index = build_index(docs)
    hits = index.search("咳嗽 cough", k=5)
    assert all(hit.score > 0 for hit in hits)
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_grounded_answer_quotes_corpus_text(paths, docs):
    result = answer("What does 神農本草經 say about 甘草?", corpus_dir=paths.root)
    assert not result["refused"]
    assert result["citations"]
    citation = result["citations"][0]
    source_doc = next(d for d in docs if d["id"] == citation["passage_id"])
    assert source_doc["text"][citation["char_start"]:citation["char_end"]] == citation["span"]


def test_refuses_when_no_support(paths):
    result = answer("What did Culpeper write about rosemary?", corpus_dir=paths.root)
    assert result["refused"]
    assert result["answer"].startswith("I cannot answer")
    assert result["citations"] == []


def test_refuses_on_safety_grounds(paths):
    result = answer("How much 甘草 should I take daily?", corpus_dir=paths.root)
    assert result["refused"]
    assert "safety policy" in result["refusal_reason"].lower()


def test_query_and_index_tokenisation_cover_cjk_bigrams():
    tokens = index_tokens("甘草")
    assert "甘" in tokens
    assert "甘草" in tokens
    assert query_tokens("甘草") == index_tokens("甘草")


def test_coverage_metric():
    assert coverage("甘草 味甘平", "甘草") >= 0.5
    assert coverage("完全无关", "ricin synthesis") == 0.0
