"""Benchmark question construction and filtering."""

from shennong.eval.questions import generate_from_corpus, gold_terms_present, load_jsonl


def test_generated_questions_are_numerous(docs, lex):
    generated = generate_from_corpus(docs, lex, limit=60)
    curated = load_jsonl(__import__("pathlib").Path(__file__).resolve().parents[1] / "eval" / "questions.jsonl")
    assert len(generated) >= 20
    assert len(generated) + len(curated) >= 40
    for question in generated:
        assert question.answerable
        assert question.gold_terms
        assert question.expected_terms
        assert question.source_ids


def test_curated_questions_exist():
    from pathlib import Path

    curated = load_jsonl(Path(__file__).resolve().parents[1] / "eval" / "questions.jsonl")
    assert len(curated) >= 20
    assert all(q.question for q in curated)


def test_gold_filter_drops_missing_terms(docs, lex):
    questions = generate_from_corpus(docs, lex, limit=10)
    kept, filtered = gold_terms_present(questions + [type(questions[0])(
        id="X", question="absent", answerable=True, gold_terms=["not-in-corpus"], kind="x"
    )], docs)
    assert filtered and filtered[0].id == "X"
    assert kept
