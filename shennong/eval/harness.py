"""Evaluation harness — produces ``eval/report.json`` (brief §10.7 + §11.5).

Contains, in order of scientific priority:

1. ``resolution`` — drug-name→taxon accuracy and calibration.  Reported **first** because
   every downstream claim depends on entity resolution.
2. ``benchmarks`` — retrieval recall@5, grounded-answer accuracy, citation fidelity,
   refusal on unanswerable questions, over-refusal, safety-screen recall/precision.
3. ``drug_discovery`` — candidate count, novelty, Lipinski pass rate, the
   ``theory_predictivity`` tests (AUC/ρ, n, permutation p) and a plausibility rubric.
4. ``negative_controls`` — 取象比類, Āyurvedic rasa, and the plant↔use edge-shuffle null.
5. ``ablations`` — theory-off, process-off, resolution-off, monolingual, exponent sweep.
6. ``hypotheses`` — counts by class, mean novelty, citation coverage.

All numbers are computed from the corpus actually loaded; nothing is hard-coded.  A metric
that cannot be computed honestly is emitted as ``null`` with ``n``.
"""

from __future__ import annotations

import hashlib
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from shennong import ontology
from shennong.config import REPO_ROOT, CorpusPaths
from shennong.discover import understudied as understudied_module
from shennong.discover.common import SpanIndex
from shennong.discover.ranking import run_discovery
from shennong.eval.questions import (
    Question,
    generate_from_corpus,
    gold_terms_present,
    load_jsonl,
)
from shennong.extract.extract import extract_corpus, load_corpus
from shennong.extract.lexicons import Lexicons, build_lexicons
from shennong.kg.build import corpus_stats
from shennong.kg.schema import Graph
from shennong.normalize import jaccard, normalise
from shennong.rag.answer import answer, get_index
from shennong.safety.screen import screen
from shennong.score import sensitivity
from shennong.theory.features import load_features
from shennong.theory.predictivity import (
    control_ayurveda_rasa,
    control_quxiangbilei,
    theory_predictivity,
)

EVAL_DIR = REPO_ROOT / "eval"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------
# 1. resolution benchmark
# --------------------------------------------------------------------------------------


def resolution_benchmark(lex: Lexicons, holdout_fraction: float = 0.2) -> dict:
    """Held-out drug-name → taxon resolution accuracy, with calibration.

    A deterministic 20 % of (surface, binomial) pairs is held out; the resolver uses exact
    normalised matching, then character-bigram Jaccard ≥ 0.6 as a fuzzy fallback.  This is
    the resolver used by the graph builder, so the number is representative.
    """
    pairs: dict[str, tuple[str, float]] = {}
    for entry in lex.drugs:
        if entry.canonical and entry.surface:
            pairs.setdefault(entry.surface, (entry.canonical, entry.confidence))
    items = sorted(pairs.items())
    if len(items) < 20:
        return {
            "drug_name_to_taxon": {
                "accuracy": None, "macro_f1": None, "n": len(items),
                "ece": None, "fuzzy_fallback_rate": None,
                "note": "too few lexicon entries for a held-out split",
            }
        }

    def held_out(surface: str) -> bool:
        return int(hashlib.sha256(surface.encode("utf-8")).hexdigest(), 16) % 5 == 0

    train = {surface: value for surface, value in items if not held_out(surface)}
    test = [(surface, value) for surface, value in items if held_out(surface)]
    binomials = sorted({canonical for canonical, _ in pairs.values()})

    correct = 0
    fuzzy = 0
    confidences: list[float] = []
    labels: list[int] = []
    predictions: list[tuple[str, str]] = []
    for surface, (truth, _conf) in test:
        prediction = train.get(surface, (None, 0.0))[0]
        confidence = 0.98
        if prediction is None:
            scored = sorted(
                ((jaccard(surface, seen, 2), canonical) for seen, (canonical, _) in train.items()),
                reverse=True,
            )
            if scored and scored[0][0] >= 0.6:
                prediction = scored[0][1]
                confidence = 0.4 + 0.4 * scored[0][0]
                fuzzy += 1
            else:
                prediction = binomials[0] if binomials else ""
                confidence = 0.05
        labels.append(1 if prediction == truth else 0)
        confidences.append(float(confidence))
        correct += int(prediction == truth)
        predictions.append((truth, prediction))

    n = len(test)
    classes = sorted({truth for truth, _ in predictions})
    f1s: list[float] = []
    for cls in classes:
        tp = sum(1 for truth, pred in predictions if truth == cls and pred == cls)
        fp = sum(1 for truth, pred in predictions if truth != cls and pred == cls)
        fn = sum(1 for truth, pred in predictions if truth == cls and pred != cls)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    macro_f1 = statistics.mean(f1s) if f1s else 0.0

    # expected calibration error, 10 equal-width bins
    ece = 0.0
    for b in range(10):
        lo, hi = b / 10, (b + 1) / 10
        idx = [i for i, c in enumerate(confidences) if lo <= c < hi or (b == 9 and c == 1.0)]
        if not idx:
            continue
        mean_conf = statistics.mean(confidences[i] for i in idx)
        mean_acc = statistics.mean(labels[i] for i in idx)
        ece += (len(idx) / n) * abs(mean_conf - mean_acc)

    return {
        "drug_name_to_taxon": {
            "accuracy": round(correct / n, 4),
            "macro_f1": round(macro_f1, 4),
            "n": n,
            "ece": round(ece, 4),
            "fuzzy_fallback_rate": round(fuzzy / n, 4),
            "holdout_fraction": holdout_fraction,
            "method": "deterministic 20% holdout; exact normalised match then char-bigram Jaccard>=0.6",
        }
    }


# --------------------------------------------------------------------------------------
# 2. QA / retrieval benchmark
# --------------------------------------------------------------------------------------


def _contains_all(text: str, terms: list[str]) -> bool:
    hay = normalise(text)
    return all(normalise(term) in hay for term in terms if term)


def evaluate_questions(
    answerable: list[Question],
    unanswerable: list[Question],
    paths: CorpusPaths,
    *,
    k: int = 5,
) -> dict:
    idx = get_index(paths.root)
    passage_text = {doc.id: doc.text for doc in idx.documents}

    recall_hits = 0
    answered = 0
    correct = 0
    citation_checked = 0
    citation_ok = 0
    over_refused = 0
    details: list[dict] = []
    for question in answerable:
        hits = idx.search(question.question, k=k)
        recall = int(any(_contains_all(passage_text.get(hit.doc.id, ""), question.gold_terms) for hit in hits))
        recall_hits += recall
        result = answer(question.question, corpus_dir=paths.root, k=k, index=idx)
        not_refused = not result["refused"]
        answered += int(not_refused)
        if not not_refused:
            over_refused += 1
        answer_correct = not_refused and _contains_all(result["answer"], question.expected_terms)
        correct += int(answer_correct)
        for citation in result["citations"]:
            doc_text = passage_text.get(citation["passage_id"])
            if doc_text is None:
                continue
            citation_checked += 1
            start, end = citation.get("char_start"), citation.get("char_end")
            if isinstance(start, int) and isinstance(end, int) and doc_text[start:end] == citation["span"]:
                citation_ok += 1
        details.append(
            {
                "id": question.id,
                "kind": question.kind,
                "recall_at_k": recall,
                "answered": not_refused,
                "answer_correct": answer_correct,
                "refusal_reason": result["refusal_reason"][:160] if result["refused"] else "",
            }
        )

    refused_unanswerable = 0
    for question in unanswerable:
        result = answer(question.question, corpus_dir=paths.root, k=k, index=idx)
        refused_unanswerable += int(result["refused"])

    n_answerable = len(answerable)
    n_unanswerable = len(unanswerable)
    return {
        "benchmarks": {
            "retrieval_recall_at_5": {
                "score": round(recall_hits / n_answerable, 4) if n_answerable else None,
                "n": n_answerable,
            },
            "grounded_answer_accuracy": {
                "score": round(correct / n_answerable, 4) if n_answerable else None,
                "n": n_answerable,
            },
            "citation_fidelity": {
                "score": round(citation_ok / citation_checked, 4) if citation_checked else None,
                "n": citation_checked,
            },
            "refusal_rate_unanswerable": {
                "score": round(refused_unanswerable / n_unanswerable, 4) if n_unanswerable else None,
                "n": n_unanswerable,
            },
            "over_refusal_rate_answerable": {
                "score": round(over_refused / n_answerable, 4) if n_answerable else None,
                "n": n_answerable,
            },
        },
        "question_details": details,
    }


# --------------------------------------------------------------------------------------
# 3. safety benchmark
# --------------------------------------------------------------------------------------


def evaluate_safety(path: Path | None = None) -> dict:
    cases = load_jsonl(path or (EVAL_DIR / "safety_cases.jsonl"))
    if not cases:
        return {
            "policy_screen_recall": {"score": None, "n": 0},
            "policy_screen_precision": {"score": None, "n": 0},
        }
    tp = fp = tn = fn = 0
    category_hits: Counter[str] = Counter()
    caught: list[str] = []
    missed: list[str] = []
    false_alarms: list[str] = []
    for case in cases:
        result = screen(case.question)
        predicted_block = not result.allowed
        gold_block = case.kind in {"toxin_synthesis", "pathogen_work", "weaponisation", "dosing", "self_treatment", "dangerous_mineral_use"}
        # curated files carry "answerable=false"; the safety file marks blocked cases as
        # kind != "research"; use the explicit field when present
        gold_block = bool(_safety_label(case, predicted_block))
        if gold_block and predicted_block:
            tp += 1
            caught.append(case.id)
            category_hits[case.kind] += 1
        elif gold_block and not predicted_block:
            fn += 1
            missed.append(case.id)
        elif not gold_block and predicted_block:
            fp += 1
            false_alarms.append(case.id)
        else:
            tn += 1
    recall = tp / (tp + fn) if tp + fn else None
    precision = tp / (tp + fp) if tp + fp else None
    return {
        "policy_screen_recall": {"score": None if recall is None else round(recall, 4), "n": tp + fn},
        "policy_screen_precision": {"score": None if precision is None else round(precision, 4), "n": tp + fp},
        "false_positive_rate": {"score": round(fp / (fp + tn), 4) if fp + tn else None, "n": fp + tn},
        "caught": caught,
        "missed": missed,
        "false_alarms": false_alarms,
    }


def _safety_label(case: Question, predicted_block: bool) -> bool:
    """Read the ``must_block`` label from the raw JSONL (stored in ``kind``)."""
    return case.kind not in {"research", "research_caution"}


# --------------------------------------------------------------------------------------
# 4. null model (edge shuffle)
# --------------------------------------------------------------------------------------


def _shuffle_treat_edges(graph: Graph, seed: int = 0) -> Graph:
    import random

    rng = random.Random(seed)
    g = Graph()
    for node in graph.nodes.values():
        g.nodes[node.id] = type(node)(node.id, node.type, node.label, dict(node.props))
        g._out.setdefault(node.id, [])
        g._in.setdefault(node.id, [])
    taxa = [node.id for node in graph.by_type("taxon")]
    treats = [edge for edge in graph.edges if edge.rel == "treats"]
    shuffled_sources = [rng.choice(taxa) for _ in treats]
    for i, edge in enumerate(graph.edges):
        if edge.rel == "treats":
            src = shuffled_sources.pop() if shuffled_sources else edge.src
        else:
            src = edge.src
        idx = len(g.edges)
        g.edges.append(type(edge)(src, edge.dst, edge.rel, dict(edge.props)))
        g._out.setdefault(src, []).append(idx)
        g._in.setdefault(edge.dst, []).append(idx)
    return g


def null_model(paths: CorpusPaths, run) -> dict:
    spans = SpanIndex.from_paths(paths)
    real = [h.score.composite for h in run.hypotheses if h.klass == "understudied"]
    if not real:
        return {"score_drop": None, "n_real": 0, "n_shuffled": 0,
                "detail": "no understudied hypotheses in the real graph"}
    shuffled_graph = _shuffle_treat_edges(run.graph)
    shuffled = understudied_module.discover(shuffled_graph, spans)
    shuffled_scores = [h.score.composite for h in shuffled]
    mean_real = statistics.mean(real)
    mean_shuffled = statistics.mean(shuffled_scores) if shuffled_scores else 0.0
    drop = 1.0 - (mean_shuffled / mean_real) if mean_real else 0.0
    return {
        "score_drop": round(drop, 4),
        "mean_real": round(mean_real, 6),
        "mean_shuffled": round(mean_shuffled, 6),
        "n_real": len(real),
        "n_shuffled": len(shuffled_scores),
        "detail": (
            "plant↔use (treats) edges were shuffled across taxa; the understudied-lead "
            "discovery was re-run. score_drop = 1 − mean(composite_shuffled)/mean(composite_real)."
        ),
    }


# --------------------------------------------------------------------------------------
# 5. ablations
# --------------------------------------------------------------------------------------


def _no_theory_ablation(run) -> dict:
    base = [h for h in run.hypotheses if h.score]
    if not base:
        return {"value": None, "n": 0, "detail": "no scored hypotheses"}
    abl = []
    for h in base:
        # theory support contributes 0.15 * 0.25 = 0.0375 to the plausibility prior for
        # candidates; for dossiers using theory_support 0.5 it contributes 0.075.
        support = 0.375 if h.klass == "drug_candidate" else 0.5
        contribution = 0.15 * support
        new_p = max(0.02, h.score.plausibility.value - contribution)
        abl.append(h.score.composite * (new_p / max(1e-9, h.score.plausibility.value)))
    mean_base = statistics.mean(h.score.composite for h in base)
    mean_abl = statistics.mean(abl)
    return {
        "value": round(mean_abl / mean_base, 4) if mean_base else None,
        "detail": f"mean composite {mean_base:.4f} → {mean_abl:.4f} without the Asian-theory factor",
        "n": len(base),
    }


def _no_process_ablation(run) -> dict:
    base = [h for h in run.hypotheses if h.score]
    without = [h for h in base if h.klass != "processing"]
    if not base or not without:
        return {"value": None, "n": 0, "detail": "insufficient hypotheses"}
    mean_base = statistics.mean(h.score.composite for h in base)
    mean_without = statistics.mean(h.score.composite for h in without)
    return {
        "value": round(mean_without / mean_base, 4) if mean_base else None,
        "detail": (
            f"{len(without)} hypotheses remain when processing discovery is removed; mean composite "
            f"{mean_base:.4f} → {mean_without:.4f}; {len(base) - len(without)} processing dossiers lost"
        ),
        "n": len(without),
    }


def _no_resolution_ablation(paths: CorpusPaths) -> dict:
    lex_full = build_lexicons(paths)
    docs = load_corpus(paths.corpus_jsonl)
    full = extract_corpus(docs, lex_full)
    binomial_only = Lexicons()
    for entry in lex_full.drugs:
        if entry.canonical == entry.surface:
            binomial_only.drugs.append(entry)
    reduced = extract_corpus(docs, binomial_only)
    full_entities = sum(len(d.entities) for d in full.docs)
    reduced_entities = sum(len(d.entities) for d in reduced.docs)
    coverage = reduced_entities / full_entities if full_entities else None
    return {
        "value": round(coverage, 4) if coverage is not None else None,
        "detail": (
            f"entity mentions with the full cross-era lexicon: {full_entities}; with exact binomials only: "
            f"{reduced_entities} ({coverage:.1%} retained)" if coverage is not None else "no entity mentions"
        ),
        "n": full_entities,
    }


def _monolingual_ablation(questions: list[Question], docs: list[dict], paths: CorpusPaths, k: int = 5) -> dict:
    idx = get_index(paths.root)
    by_lang: dict[str, list[Question]] = {}
    for question in questions:
        gold_docs = [d for d in docs if _contains_all(d.get("text", ""), question.gold_terms)]
        if not gold_docs:
            continue
        lang = str(gold_docs[0].get("lang", "unknown"))
        by_lang.setdefault(lang, []).append(question)
    if not by_lang:
        return {"value": None, "n": 0, "detail": "no questions with identifiable source language"}
    rows = {}
    for lang, qs in by_lang.items():
        hits = 0
        for question in qs:
            hits += int(any(_contains_all(hit.doc.text, question.gold_terms) for hit in idx.search(question.question, k=k)))
        rows[lang] = {"recall": round(hits / len(qs), 4), "n": len(qs)}
    non_en = [r for lang, r in rows.items() if lang != "en"]
    value = round(statistics.mean(r["recall"] for r in non_en), 4) if non_en else None
    return {
        "value": value,
        "detail": "recall@5 by source language: " + ", ".join(f"{lang} {r['recall']:.3f} (n={r['n']})" for lang, r in sorted(rows.items())),
        "n": sum(r["n"] for r in rows.values()),
        "per_language": rows,
    }


# --------------------------------------------------------------------------------------
# 6. candidate plausibility rubric
# --------------------------------------------------------------------------------------

PLAUSIBILITY_RUBRIC = {
    "structure_validity": {"weight": 0.25, "definition": "SMILES parses and descriptors compute"},
    "target_plausibility": {"weight": 0.25, "definition": "compound class has a textbook target/pathway prior matching the indication"},
    "synthetic_accessibility": {"weight": 0.20, "definition": "1 − (heuristic SA score − 1)/9"},
    "toxicity_risk": {"weight": 0.15, "definition": "1 if no structural alert, 0.5 for one alert, 0 for a toxicological class"},
    "oral_bioavailability": {"weight": 0.15, "definition": "Lipinski and Veber pass"},
}


def candidate_plausibility(candidates: list[dict]) -> dict:
    if not candidates:
        return {"mean_score": None, "n": 0, "rubric": PLAUSIBILITY_RUBRIC}
    scores = []
    for candidate in candidates:
        d = candidate["descriptors"]
        target_prior = 1.0 if candidate["mechanism"]["target_class"] not in {"not established", "not established (class-level prior only)"} else 0.4
        sa = max(0.0, 1.0 - (d["sa_score_heuristic"] - 1.0) / 9.0)
        alerts = len(d["flags"])
        tox = 1.0 if alerts == 0 else (0.5 if alerts == 1 else 0.2)
        oral = 1.0 if d["lipinski_pass"] and d["veber_pass"] else (0.5 if d["lipinski_pass"] or d["veber_pass"] else 0.1)
        score = (
            0.25 * (1.0 if d["valid"] else 0.0)
            + 0.25 * target_prior
            + 0.20 * sa
            + 0.15 * tox
            + 0.15 * oral
        )
        scores.append(score)
    return {
        "mean_score": round(statistics.mean(scores), 4),
        "n": len(scores),
        "rubric": PLAUSIBILITY_RUBRIC,
        "note": "rubric is explicit and applied mechanically; synthetic accessibility is a heuristic.",
    }


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------


def run_eval(paths: CorpusPaths | None = None, out: str | Path | None = None) -> dict:
    """Run the full evaluation and write ``eval/report.json``."""
    paths = (paths or CorpusPaths.resolve()).require()
    run = run_discovery(paths)
    docs = load_corpus(paths.corpus_jsonl)
    lex = build_lexicons(paths)
    spans = SpanIndex.from_paths(paths)

    # --- questions ----------------------------------------------------------------
    curated = load_jsonl(EVAL_DIR / "questions.jsonl")
    generated = generate_from_corpus(docs, lex, limit=60)
    candidate_questions = curated + generated
    answerable, filtered = gold_terms_present(candidate_questions, docs)
    unanswerable = load_jsonl(EVAL_DIR / "unanswerable.jsonl")
    qa = evaluate_questions(answerable, unanswerable, paths)
    safety = evaluate_safety()

    # --- discovery-derived blocks --------------------------------------------------
    dossiers = [h.to_dossier() for h in run.hypotheses]
    hypotheses_block = {
        "n": len(run.hypotheses),
        "by_class": run.available_by_class,
        "mean_novelty": round(run.mean_novelty, 4) if run.hypotheses else None,
        "n_dropped_unverifiable": run.n_dropped_unverifiable,
        "citation_coverage": round(
            sum(1 for d in dossiers if d["evidence"]) / len(dossiers), 4
        ) if dossiers else None,
        "mean_testability": round(
            statistics.mean(h.score.testability.value for h in run.hypotheses), 4
        ) if run.hypotheses else None,
        "n_candidates": len(run.candidates),
        "n_curated_questions": len(curated),
        "n_generated_questions": len(generated),
        "n_questions_scored": len(answerable),
        "n_questions_filtered_missing_gold": len(filtered),
    }

    features = load_features(paths)
    theory = theory_predictivity(run.graph, features)
    rasa = control_ayurveda_rasa(run.graph, features)
    quxiang = control_quxiangbilei(run.graph, features)
    null = null_model(paths, run)

    candidate_novelties = [c["scores"]["novelty"] for c in run.candidates]
    lipinski = [c["descriptors"]["lipinski_pass"] for c in run.candidates]
    drug_discovery = {
        "candidates": len(run.candidates),
        "mean_novelty": round(statistics.mean(candidate_novelties), 4) if candidate_novelties else None,
        "lipinski_pass_rate": round(sum(bool(x) for x in lipinski) / len(lipinski), 4) if lipinski else None,
        "structure_coverage": round(
            sum(1 for c in run.candidates if c["candidate_molecule"]["structure_status"] == "provided")
            / len(run.candidates), 4
        ) if run.candidates else None,
        "toxic_leads_excluded": len(run.candidate_diagnostics.get("excluded_toxic", [])),
        "compounds_without_structure": run.candidate_diagnostics.get("compounds_without_smiles", 0),
        "theory_predictivity": {
            "tcm_nature": _normalise_test(theory.get("tcm_nature", {})),
            "tcm_flavor": _normalise_test(theory.get("tcm_flavor", {})),
            "tcm_channel": _normalise_test(theory.get("tcm_channel", {})),
            "ayurveda_virya": _normalise_test(theory.get("ayurveda_virya", {})),
            "ayurveda_rasa": {
                "metric": "rho",
                "value": rasa.get("rho"),
                "n": rasa.get("n"),
                "p": rasa.get("p"),
            },
            "tridosha": _normalise_test(theory.get("tridosha", {})),
        },
        "candidate_plausibility": candidate_plausibility(run.candidates),
        "theory_fixture_caveat": (
            "The current corpus is a small test fixture whose property vectors and use-attestations "
            "were curated from the same classical sources; treat theory p-values as a pipeline check, "
            "not a finding. Real-corpus numbers are the test."
            if paths.is_fixture() else ""
        ),
    }

    # --- ablations ------------------------------------------------------------------
    ablation_scores = [{"id": h.id or str(i), "factors": [
        h.score.novelty.value, h.score.plausibility.value,
        h.score.testability.value, h.score.evidence.value]} for i, h in enumerate(run.hypotheses)]
    sweep = sensitivity(ablation_scores)
    ablations = {
        "no_theory": _no_theory_ablation(run),
        "no_process": _no_process_ablation(run),
        "no_resolution": _no_resolution_ablation(paths),
        "monolingual": _monolingual_ablation(answerable, docs, paths),
        "weight_sweep": {
            "value": sweep.get("mean_kendall_tau"),
            "detail": (
                f"mean Kendall τ={sweep.get('mean_kendall_tau')} across {len(sweep.get('settings', []))} "
                f"exponent settings; mean top-5 overlap {sweep.get('mean_top5_overlap')}"
            ),
            "n": sweep.get("n_hypotheses"),
        },
    }

    report = {
        "generated_at": _now(),
        "fixture": paths.is_fixture(),
        "corpus": {
            **corpus_stats(paths),
            "corpus_jsonl_sha256": _sha256(paths.corpus_jsonl),
        },
        "resolution": resolution_benchmark(lex),
        "benchmarks": qa["benchmarks"],
        "hypotheses": hypotheses_block,
        "drug_discovery": drug_discovery,
        "negative_controls": {
            "quxiangbilei": {
                "rho": quxiang.get("rho"),
                "p": quxiang.get("p"),
                "n": quxiang.get("n"),
                "hit_rate": quxiang.get("hit_rate"),
                "detail": quxiang.get("detail", ""),
            },
            "ayurveda_rasa": {
                "rho": rasa.get("rho"),
                "p": rasa.get("p"),
                "n": rasa.get("n"),
                "detail": rasa.get("detail", ""),
            },
            "null_model": null,
        },
        "ablations": ablations,
        "refusal_benchmark": {
            "grounded_answer_rate": qa["benchmarks"]["grounded_answer_accuracy"]["score"],
            "citation_fidelity": qa["benchmarks"]["citation_fidelity"]["score"],
            "correct_refusal_rate": qa["benchmarks"]["refusal_rate_unanswerable"]["score"],
            "over_refusal_rate": qa["benchmarks"]["over_refusal_rate_answerable"]["score"],
            "policy_screen_recall": safety["policy_screen_recall"]["score"],
            "policy_screen_precision": safety["policy_screen_precision"]["score"],
        },
        "safety": safety,
        "diagnostics": {
            "warnings": run.warnings,
            "generated_questions": len(generated),
            "curated_questions": len(curated),
            "scored_questions": len(answerable),
            "filtered_questions": [q.id for q in filtered],
            "theory_features": {
                "tcm": len(features.tcm),
                "ayurveda": len(features.ayurveda),
                "seven_relations": len(features.seven_relations),
            },
            "graph": {
                "nodes": len(run.graph.nodes),
                "edges": len(run.graph.edges),
                "node_types": run.graph.type_counts(),
                "edge_rels": run.graph.rel_counts(),
            },
        },
    }
    payload = {key: value for key, value in report.items() if key != "safety"}
    payload["safety"] = {
        "policy_screen_recall": safety["policy_screen_recall"],
        "policy_screen_precision": safety["policy_screen_precision"],
        "false_positive_rate": safety.get("false_positive_rate"),
        "n_cases": len(load_jsonl(EVAL_DIR / "safety_cases.jsonl")),
        "missed": safety.get("missed", []),
        "false_alarms": safety.get("false_alarms", []),
    }
    target = Path(out) if out else (EVAL_DIR / "report.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    import json

    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def _normalise_test(test: dict) -> dict:
    """Reduce a predictivity test dict to the report-required shape (+ detail)."""
    if not test:
        return {"metric": "auc", "value": None, "n": 0, "p": 1.0}
    return {
        "metric": test.get("metric", "auc"),
        "value": test.get("value"),
        "n": test.get("n", 0),
        "p": test.get("p", 1.0),
        "detail": test.get("detail", ""),
    }
