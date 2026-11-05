"""SHENNONG command-line interface (brief §10.5 — frozen names).

    python -m shennong.cli cai   --corpus-dir corpus/processed [--out-passages PATH]
    python -m shennong.cli zhi   --corpus-dir corpus/processed
    python -m shennong.cli pei   --corpus-dir corpus/processed [--out-kg PATH]
    python -m shennong.cli shi   --n 12 [--class CLASS] [--out PATH]
    python -m shennong.cli ask   "question" [--json]
    python -m shennong.cli report [--out eval/report.json]

Unfinished stages never traceback: they emit honest ``{"status": "not_implemented",
"reason": …}`` JSON and exit 0, so integration scripts stay green while modules land.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from shennong import __version__
from shennong.config import CorpusPaths, REPO_ROOT

DEFAULT_KG = REPO_ROOT / "shennong" / "_build" / "kg" / "graph.json"


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _emit(payload: dict, *, as_json: bool = True, indent: int | None = 2) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=indent, default=str))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _paths(args: argparse.Namespace) -> CorpusPaths:
    return CorpusPaths.resolve(args.corpus_dir)


def _not_implemented(stage: str, reason: str) -> dict:
    return {"status": "not_implemented", "stage": stage, "reason": reason, "generated_at": _now()}


def _fail(stage: str, exc: Exception) -> dict:
    return {
        "status": "error",
        "stage": stage,
        "reason": f"{type(exc).__name__}: {exc}",
        "generated_at": _now(),
    }


# --------------------------------------------------------------------------------------
# app-data converters (Workbench contracts)
# --------------------------------------------------------------------------------------


def write_passages(paths: CorpusPaths, out: str | Path) -> dict:
    from shennong.extract.extract import load_corpus

    docs = load_corpus(paths.corpus_jsonl)
    passages = [
        {
            "id": d.get("id", ""),
            "source_id": d.get("source_id", ""),
            "title": d.get("title", ""),
            "year": d.get("year", 0),
            "tradition": d.get("tradition", "unknown"),
            "lang": d.get("lang", "en"),
            "tier": d.get("tier", 0),
            "licence": d.get("licence", ""),
            "text": d.get("text", ""),
        }
        for d in docs
    ]
    payload = {"generated_at": _now(), "fixture": paths.is_fixture(), "passages": passages}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"status": "ok", "stage": "cai", "documents": len(passages), "out": str(out)}


def write_kg(graph, paths: CorpusPaths, out: str | Path) -> dict:
    nodes = []
    for node in graph.nodes.values():
        weight = float(graph.degree(node.id))
        nodes.append({"id": node.id, "label": node.label, "type": node.type, "weight": weight})
    edges = [
        {"source": e.src, "target": e.dst, "rel": e.rel, "weight": float(e.props.get("confidence", 1.0))}
        for e in graph.edges
    ]
    payload = {"generated_at": _now(), "fixture": paths.is_fixture(), "nodes": nodes, "edges": edges}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"status": "ok", "stage": "pei", "nodes": len(nodes), "edges": len(edges), "out": str(out)}


def write_hypotheses(hypotheses: list[dict], paths: CorpusPaths, out: str | Path) -> dict:
    import hashlib

    h = hashlib.sha256()
    if paths.corpus_jsonl.exists():
        h.update(paths.corpus_jsonl.read_bytes())
    payload = {
        "generated_at": _now(),
        "n": len(hypotheses),
        "corpus_hash": h.hexdigest()[:16],
        "fixture": paths.is_fixture(),
        "hypotheses": hypotheses,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"status": "ok", "stage": "shi", "n": len(hypotheses), "out": str(out)}


# --------------------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------------------


def cmd_cai(args: argparse.Namespace) -> int:
    paths = _paths(args)
    if not paths.corpus_jsonl.exists():
        _emit(_not_implemented("cai", f"missing {paths.corpus_jsonl}"), as_json=args.json)
        return 0
    from shennong.kg.build import corpus_stats

    stats = corpus_stats(paths)
    payload = {"status": "ok", "stage": "cai", "fixture": paths.is_fixture(), **stats,
               "generated_at": _now()}
    if args.out_passages:
        payload.update(write_passages(paths, args.out_passages))
    _emit(payload, as_json=args.json)
    return 0


def cmd_zhi(args: argparse.Namespace) -> int:
    paths = _paths(args)
    try:
        from shennong.extract.extract import extract_corpus, load_corpus
        from shennong.extract.lexicons import build_lexicons
        from shennong.kg.build import corpus_stats

        lex = build_lexicons(paths)
        docs = load_corpus(paths.corpus_jsonl)
        result = extract_corpus(docs, lex)
        drug_mentions = sum(1 for d in result.docs for e in d.entities if e.kind == "drug")
        payload = {
            "status": "ok", "stage": "zhi", "fixture": paths.is_fixture(),
            "documents": len(result.docs), "entities": sum(len(d.entities) for d in result.docs),
            "observations": result.counts(), "drug_mentions": drug_mentions,
            "lexicon_drugs": len(lex.drugs), "generated_at": _now(),
        }
        _emit(payload, as_json=args.json)
        return 0
    except Exception as exc:  # honest failure, never a traceback for the integration script
        _emit(_fail("zhi", exc), as_json=args.json)
        return 1


def cmd_pei(args: argparse.Namespace) -> int:
    paths = _paths(args)
    try:
        from shennong.kg.build import build_graph

        graph = build_graph(paths)
        out = Path(args.out_kg) if args.out_kg else DEFAULT_KG
        if args.out_kg:
            summary = write_kg(graph, paths, out)
        else:
            graph.save(out)
            summary = {"status": "ok", "stage": "pei", "graph": str(out)}
        payload = {
            **summary, "fixture": paths.is_fixture(),
            "nodes": len(graph.nodes), "edges": len(graph.edges),
            "node_types": graph.type_counts(), "edge_rels": graph.rel_counts(),
            "generated_at": _now(),
        }
        _emit(payload, as_json=args.json)
        return 0
    except FileNotFoundError as exc:
        _emit(_not_implemented("pei", str(exc)), as_json=args.json)
        return 0
    except Exception as exc:
        _emit(_fail("pei", exc), as_json=args.json)
        return 1


def cmd_shi(args: argparse.Namespace) -> int:
    paths = _paths(args)
    try:
        from shennong.discover.ranking import generate_dossiers

        dossiers, meta = generate_dossiers(
            paths, n=args.n, klass=args.klass, corpus_dir=args.corpus_dir
        )
        if args.out:
            summary = write_hypotheses(dossiers, paths, args.out)
            payload = {**summary, "fixture": paths.is_fixture(), **meta, "generated_at": _now()}
            _emit(payload, as_json=args.json)
        else:
            payload = {"status": "ok", "stage": "shi", "fixture": paths.is_fixture(),
                       "n": len(dossiers), "by_class": meta.get("by_class", {}),
                       "hypotheses": dossiers, "generated_at": _now()}
            _emit(payload, as_json=args.json)
        return 0
    except FileNotFoundError as exc:
        _emit(_not_implemented("shi", str(exc)), as_json=args.json)
        return 0
    except Exception as exc:
        _emit(_fail("shi", exc), as_json=args.json)
        return 1


def cmd_ask(args: argparse.Namespace) -> int:
    paths = _paths(args)
    try:
        from shennong.rag.answer import answer

        result = answer(args.question, corpus_dir=str(paths.root), k=args.k)
        _emit(result, as_json=args.json)
        return 0
    except Exception as exc:
        _emit(_fail("ask", exc), as_json=args.json)
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    paths = _paths(args)
    try:
        from shennong.eval.harness import run_eval

        report = run_eval(paths, out=args.out)
        small = {
            "status": "ok", "stage": "report", "out": args.out or "eval/report.json",
            "generated_at": report.get("generated_at"),
            "corpus": report.get("corpus"),
            "benchmarks": {k: v.get("score") for k, v in report.get("benchmarks", {}).items()},
            "hypotheses": {k: report.get("hypotheses", {}).get(k) for k in ("n", "by_class", "mean_novelty")},
            "drug_discovery": {
                "candidates": report.get("drug_discovery", {}).get("candidates"),
                "mean_novelty": report.get("drug_discovery", {}).get("mean_novelty"),
            },
        }
        _emit(small, as_json=args.json)
        return 0
    except FileNotFoundError as exc:
        _emit(_not_implemented("report", str(exc)), as_json=args.json)
        return 0
    except Exception as exc:
        _emit(_fail("report", exc), as_json=args.json)
        return 1


# --------------------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m shennong.cli",
        description=f"SHENNONG {__version__} — Asian-medicine knowledge graph + drug discovery engine",
    )
    parser.add_argument("--version", action="version", version=f"shennong {__version__}")
    parser.add_argument("--corpus-dir", default=None, help="processed corpus directory (default corpus/processed)")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("cai", help="采 collect: ingest corpus, emit passages")
    p.add_argument("--out-passages", default=None, help="write Workbench passages JSON")
    p.set_defaults(func=cmd_cai)

    p = sub.add_parser("zhi", help="制 prepare: extract entities, resolve drug names, translate processes")
    p.set_defaults(func=cmd_zhi)

    p = sub.add_parser("pei", help="配 combine: build the knowledge graph")
    p.add_argument("--out-kg", default=None, help="write Workbench kg JSON")
    p.set_defaults(func=cmd_pei)

    p = sub.add_parser("shi", help="使 deploy: rank hypotheses and drug candidates")
    p.add_argument("--n", type=int, default=12, help="number of ranked dossiers (default 12)")
    p.add_argument("--class", dest="klass", default=None,
                   help="filter: incompatibility|processing|name_collision|formula_role|understudied|endangered|drug_candidate")
    p.add_argument("--out", default=None, help="write Workbench hypotheses JSON")
    p.set_defaults(func=cmd_shi)

    p = sub.add_parser("ask", help="grounded question answering with refusal")
    p.add_argument("question", help="the question to answer")
    p.add_argument("--k", type=int, default=5, help="retrieval depth (default 5)")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("report", help="run the evaluation harness and write eval/report.json")
    p.add_argument("--out", default=str(REPO_ROOT / "eval" / "report.json"))
    p.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    # allow the global flags to appear after the subcommand, as the Workbench scripts do
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"cai", "zhi", "pei", "shi", "ask", "report"}:
        command = argv[0]
        rest = argv[1:]
        hoisted: list[str] = []
        keep: list[str] = []
        i = 0
        while i < len(rest):
            if rest[i] in {"--corpus-dir", "--json"}:
                hoisted.extend(rest[i : i + 2])
                i += 2
                continue
            keep.append(rest[i])
            i += 1
        argv = [*hoisted, command, *keep]
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
