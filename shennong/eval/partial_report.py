"""Fallback: emit an honest partial ``eval/report.json`` from cached artefacts.

Used only if the full harness cannot finish inside the submission window.  It publishes
what is computed, marks everything else as ``incomplete``, and never leaves a fixture file
in place of a real one.

    .venv/bin/python -m shennong.eval.partial_report --corpus-dir corpus/processed --out eval/report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from shennong.config import REPO_ROOT, CorpusPaths
from shennong.eval.harness import (
    corpus_stats,
    join_coverage,
    resolution_benchmark,
    rule_completeness,
    EVAL_DIR,
)
from shennong.extract.lexicons import build_lexicons
from shennong.kg.build import corpus_stats as _corpus_stats
from shennong.kg.schema import Graph
from shennong.theory.features import load_features
from shennong.theory.predictivity import (
    control_ayurveda_rasa,
    control_quxiangbilei,
    theory_predictivity,
)


def _sha256(path: Path) -> str | None:
    import hashlib

    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_partial(corpus_dir: str | Path, out: str | Path) -> dict:
    paths = CorpusPaths.resolve(corpus_dir).require()
    graph_path = paths.build_dir / "graph.json"
    incomplete = ["benchmarks", "hypotheses", "negative_controls", "ablations", "null_model"]
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fixture": paths.is_fixture(),
        "incomplete": incomplete,
        "corpus": {**corpus_stats(paths), "corpus_jsonl_sha256": _sha256(paths.corpus_jsonl)},
    }
    lex = build_lexicons(paths)
    report["resolution"] = {
        **resolution_benchmark(lex),
        "join_coverage": join_coverage(paths, lex),
    }
    report["rules"] = _rules_without_discovery(paths, graph_path)
    candidates_path = REPO_ROOT / "artifacts" / "drug_candidates.json"
    candidates: list[dict] = []
    if candidates_path.exists():
        payload = json.loads(candidates_path.read_text(encoding="utf-8"))
        candidates = payload.get("candidates", [])
    report["drug_discovery"] = {
        "candidates": len(candidates),
        "mean_novelty": round(statistics.mean(c["scores"]["novelty"] for c in candidates), 4) if candidates else None,
        "lipinski_pass_rate": round(
            sum(1 for c in candidates if c["descriptors"]["lipinski_pass"]) / len(candidates), 4
        ) if candidates else None,
    }
    if graph_path.exists():
        graph = Graph.load(graph_path)
        features = load_features(paths, lex)
        theory = theory_predictivity(graph, features)
        rasa = control_ayurveda_rasa(graph, features)
        quxiang = control_quxiangbilei(graph, features)
        report["drug_discovery"]["theory_predictivity"] = {
            "tcm_nature": theory.get("tcm_nature"),
            "tcm_flavor": theory.get("tcm_flavor"),
            "tcm_channel": theory.get("tcm_channel"),
            "ayurveda_virya": theory.get("ayurveda_virya"),
            "ayurveda_rasa": {"metric": "rho", "value": rasa.get("rho"), "n": rasa.get("n"), "p": rasa.get("p")},
            "tridosha": theory.get("tridosha"),
        }
        report["negative_controls"] = {
            "quxiangbilei": quxiang,
            "ayurveda_rasa": rasa,
            "null_model": {"score_drop": None, "detail": "not computed in partial report"},
        }
        report["hypotheses"] = {
            "n": None,
            "by_class": {},
            "mean_novelty": None,
            "resolved_evidence_rate": None,
            "dropped_for_unresolved_span": None,
            "note": "discovery did not finish; not computed in partial report",
        }
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return report


def _rules_without_discovery(paths: CorpusPaths, graph_path: Path) -> dict:
    """Rule counts from the CSV + graph spans (no discovery needed)."""
    pairs: dict[str, set[frozenset[str]]] = {}
    if paths.incompatibilities_csv.exists():
        with paths.incompatibilities_csv.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rule = (row.get("rule_system") or "").strip()
                a, b = (row.get("drug_a") or "").strip(), (row.get("drug_b") or "").strip()
                if rule and a and b:
                    pairs.setdefault(rule, set()).add(frozenset({a, b}))
    bridged = {"shiba_fan": 0, "shijiu_wei": 0, "viruddha": 0}
    if graph_path.exists():
        graph = Graph.load(graph_path)
        for edge in graph.edges:
            if edge.rel != "incompatible":
                continue
            rule = str(edge.props.get("rule_system", ""))
            if edge.props.get("char_start") is not None and rule in bridged:
                bridged[rule] += 1
    def block(key: str, canonical: int) -> dict:
        table = pairs.get(key, set())
        return {"bridged": min(bridged.get(key, 0), len(table) * 2), "total": len(table),
                "canonical_total": canonical, "pairs_in_table": len(table)}
    return {
        "eighteen_fan": block("shiba_fan", 18),
        "nineteen_wei": block("shijiu_wei", 19),
        "viruddha": block("viruddha", len(pairs.get("viruddha", set()))),
        "note": "partial: bridged counts span-carrying incompatible edges, may double-count pair directions",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=str(REPO_ROOT / "corpus" / "processed"))
    parser.add_argument("--out", default=str(EVAL_DIR / "report.json"))
    args = parser.parse_args()
    payload = build_partial(args.corpus_dir, args.out)
    print(json.dumps({"status": "ok", "partial": True, "out": args.out,
                      "incomplete": payload.get("incomplete")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
