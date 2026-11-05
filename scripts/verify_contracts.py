#!/usr/bin/env python3
"""Validate the SHENNONG inter-team data contracts (PROJECT_BRIEF.md §10).

This is the guard that keeps a team of agents honest: every artefact that crosses an ownership
boundary is checked here, in CI and before every release. It deliberately fails loudly rather than
silently skipping, and it reports *what it could not check* so nobody mistakes absence for success.

Usage:
    python scripts/verify_contracts.py                # lenient: skip absent optional artefacts
    python scripts/verify_contracts.py --strict       # every declared artefact must exist
    python scripts/verify_contracts.py --json         # machine-readable report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OK, WARN, FAIL = "ok", "warn", "fail"

# Contract limits from PROJECT_BRIEF.md §3
MAX_GGUF_BYTES = 1_000_000_000           # "< 1 GB" — enforced on the flagship/mini GGUF
MAX_GIT_FILE_BYTES = 100 * 1024 * 1024   # GitHub hard limit
MAX_TOKENS_FILE_BYTES = 512 * 1024 * 1024

REQUIRED_REGISTRY_KEYS = {
    "id", "title", "year", "tradition", "lang", "tier", "url",
    "licence", "licence_evidence", "chars", "sha256", "status",
}
VALID_TRADITIONS = {
    "tcm", "ayurveda", "unani", "kampo", "korean", "tibetan", "persian",
    "alchemy", "acupuncture", "foundational", "comparative-control",
}
VALID_LANGS = {"zh-Hant", "zh-Hans", "sa", "sa-Latn", "ar", "fa", "bo", "ja", "ko", "en"}
VALID_STATUS = {"ok", "unverified", "excluded"}
CJK_LANGS = {"zh-Hant", "zh-Hans", "ja", "ko"}


class Report:
    def __init__(self) -> None:
        self.results: list[dict] = []

    def add(self, check: str, status: str, detail: str = "") -> None:
        self.results.append({"check": check, "status": status, "detail": detail})

    def ok(self, check: str, detail: str = "") -> None:
        self.add(check, OK, detail)

    def warn(self, check: str, detail: str) -> None:
        self.add(check, WARN, detail)

    def fail(self, check: str, detail: str) -> None:
        self.add(check, FAIL, detail)

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.results if r["status"] == FAIL]

    @property
    def warnings(self) -> list[dict]:
        return [r for r in self.results if r["status"] == WARN]


def _yaml_load(path: Path):
    try:
        import yaml  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        return None, "pyyaml not installed"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def check_registry(rep: Report, strict: bool) -> None:
    path = ROOT / "corpus" / "registry" / "sources.yaml"
    if not path.exists():
        (rep.fail if strict else rep.warn)("registry.sources_yaml", f"missing {path.relative_to(ROOT)}")
        return
    data, err = _yaml_load(path)
    if err:
        rep.fail("registry.sources_yaml", f"unparseable: {err}")
        return
    if not isinstance(data, list) or not data:
        rep.fail("registry.sources_yaml", "expected a non-empty YAML list of sources")
        return

    ids: set[str] = set()
    ok_sources = 0
    for i, entry in enumerate(data):
        tag = f"registry[{i}]"
        if not isinstance(entry, dict):
            rep.fail(tag, "entry is not a mapping")
            continue
        missing = REQUIRED_REGISTRY_KEYS - set(entry)
        if missing:
            rep.fail(f"{tag}.{entry.get('id', i)}", f"missing keys: {sorted(missing)}")
            continue
        if entry["id"] in ids:
            rep.fail(f"{tag}.{entry['id']}", "duplicate id")
        ids.add(entry["id"])
        if entry["tradition"] not in VALID_TRADITIONS:
            rep.warn(f"{tag}.{entry['id']}", f"unknown tradition {entry['tradition']!r}")
        if entry["lang"] not in VALID_LANGS:
            rep.warn(f"{tag}.{entry['id']}", f"unknown lang {entry['lang']!r}")
        if entry["status"] not in VALID_STATUS:
            rep.fail(f"{tag}.{entry['id']}", f"bad status {entry['status']!r}")
        if entry["status"] == "ok":
            ok_sources += 1
            if not entry.get("licence_evidence"):
                rep.fail(f"{tag}.{entry['id']}", "status ok but no licence_evidence")
            if str(entry.get("licence", "")).upper().startswith("UNVERIFIED"):
                rep.fail(f"{tag}.{entry['id']}", "status ok but licence is UNVERIFIED")
        if entry["status"] == "excluded" and entry["tradition"] != "comparative-control":
            # informational only
            pass
    rep.ok("registry.sources_yaml", f"{len(data)} sources, {ok_sources} trained on, {len(ids)} unique ids")

    # domain directive: western/comparative material must stay a small minority (brief §0)
    cc = [e for e in data if isinstance(e, dict) and e.get("tradition") == "comparative-control"]
    total_chars = sum(int(e.get("chars") or 0) for e in data if isinstance(e, dict))
    cc_chars = sum(int(e.get("chars") or 0) for e in cc)
    if total_chars and cc_chars / total_chars > 0.03:
        rep.fail("registry.domain_directive",
                 f"comparative-control is {cc_chars / total_chars:.1%} of chars (limit 3%)")


def check_corpus_jsonl(rep: Report, strict: bool) -> None:
    path = ROOT / "corpus" / "processed" / "corpus.jsonl"
    if not path.exists():
        (rep.fail if strict else rep.warn)("corpus.jsonl", f"missing {path.relative_to(ROOT)}")
        return
    need = {"id", "source_id", "title", "year", "tradition", "lang", "tier", "licence", "text"}
    n = 0
    chars = 0
    by_lang: dict[str, int] = {}
    by_tradition: dict[str, int] = {}
    bad = 0
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                bad += 1
                if bad <= 5:
                    rep.fail("corpus.jsonl.parse", f"line {lineno}: {exc}")
                continue
            missing = need - set(obj)
            if missing:
                bad += 1
                if bad <= 5:
                    rep.fail("corpus.jsonl.schema", f"line {lineno}: missing {sorted(missing)}")
                continue
            text = obj["text"] or ""
            min_len = 100 if obj["lang"] in CJK_LANGS else 200
            if len(text) < min_len:
                bad += 1
                if bad <= 5:
                    rep.fail("corpus.jsonl.length", f"line {lineno}: {len(text)} chars < {min_len} for {obj['lang']}")
            n += 1
            chars += len(text)
            by_lang[obj["lang"]] = by_lang.get(obj["lang"], 0) + len(text)
            by_tradition[obj["tradition"]] = by_tradition.get(obj["tradition"], 0) + len(text)
    if bad:
        rep.fail("corpus.jsonl", f"{bad} malformed records")
    else:
        rep.ok("corpus.jsonl", f"{n} records, {chars:,} chars, languages={by_lang}")
    if n == 0:
        rep.fail("corpus.jsonl", "empty")
    elif chars < 1_000_000:
        rep.warn("corpus.jsonl", f"only {chars:,} chars — below the 1M target in the brief")
    # the domain must actually be Asian
    tcm_like = sum(v for k, v in by_tradition.items() if k not in {"comparative-control", "foundational"})
    if chars and tcm_like / chars < 0.5:
        rep.warn("corpus.domain_mix",
                 f"Asian-tradition material is {tcm_like / chars:.0%} of chars — the brief wants it dominant")

    # dedupe sanity: identical 13-gram shingles across sources
    seen: dict[int, str] = {}
    dups = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                text = json.loads(line)["text"]
            except Exception:  # noqa: BLE001
                continue
            h = hash(tuple(text.split()[:13]))
            if h in seen and seen[h] != text:
                dups += 1
            seen[h] = text
    if dups > max(10, n * 0.02):
        rep.warn("corpus.dedupe", f"{dups} near-duplicate chunks detected")
    else:
        rep.ok("corpus.dedupe", f"{dups} near-duplicates across {n} chunks")


def check_structured(rep: Report, strict: bool) -> None:
    base = ROOT / "corpus" / "processed" / "structured"
    expected = {
        "plants.csv": {"binomial", "family"},
        "compounds.csv": {"name", "plant_binomial"},
        "uses.csv": {"plant_binomial", "indication", "tradition"},
        "formulas.csv": {"formula_id", "formula_name"},
        "formula_ingredients.csv": {"formula_id", "drug_name", "role"},
        "incompatibilities.csv": {"drug_a", "drug_b", "rule_system"},
        "processing.csv": {"drug_name", "process_term", "process_modern"},
    }
    for name, cols in expected.items():
        p = base / name
        if not p.exists():
            (rep.fail if strict else rep.warn)(f"structured.{name}", "missing")
            continue
        with p.open(encoding="utf-8") as fh:
            header = fh.readline().strip().split(",")
            rows = sum(1 for _ in fh)
        missing = cols - set(header)
        if missing:
            rep.fail(f"structured.{name}", f"missing columns {sorted(missing)}")
        elif rows == 0:
            rep.warn(f"structured.{name}", "header only, no rows")
        else:
            rep.ok(f"structured.{name}", f"{rows} rows")

    lex = ROOT / "corpus" / "processed" / "lexicon_drugs.json"
    if lex.exists():
        try:
            data = json.loads(lex.read_text(encoding="utf-8"))
            entries = data.get("historical", data if isinstance(data, list) else [])
            rep.ok("lexicon_drugs.json", f"{len(entries)} drug-name entries")
        except Exception as exc:  # noqa: BLE001
            rep.fail("lexicon_drugs.json", f"unparseable: {exc}")
    else:
        (rep.fail if strict else rep.warn)("lexicon_drugs.json", "missing")


def check_metrics(rep: Report, strict: bool) -> None:
    runs = sorted((ROOT / "training" / "runs").glob("*/metrics.json"))
    if not runs:
        (rep.fail if strict else rep.warn)("training.metrics", "no training/runs/*/metrics.json")
        return
    required = {"run_id", "params", "tokens_seen", "steps", "final_val_loss", "loss_curve"}
    for p in runs:
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            rep.fail(f"metrics.{p.parent.name}", f"unparseable: {exc}")
            continue
        missing = required - set(m)
        if missing:
            rep.fail(f"metrics.{p.parent.name}", f"missing keys {sorted(missing)}")
            continue
        if not isinstance(m["loss_curve"], list) or len(m["loss_curve"]) < 2:
            rep.fail(f"metrics.{p.parent.name}", "loss_curve must have >= 2 points")
            continue
        if m["params"] > 1_000_000_000:
            rep.fail(f"metrics.{p.parent.name}", f"{m['params']:,} params exceeds the 1 B ceiling")
        curve = [c for c in m["loss_curve"] if c.get("loss") is not None]
        if len(curve) >= 2 and curve[-1]["loss"] >= curve[0]["loss"]:
            rep.warn(f"metrics.{p.parent.name}", "loss did not decrease — check the run")
        rep.ok(f"metrics.{p.parent.name}",
               f"{m['params']:,} params, {m['tokens_seen']:,} tokens, val_loss={m['final_val_loss']}")


def check_eval_report(rep: Report, strict: bool) -> None:
    path = ROOT / "eval" / "report.json"
    if not path.exists():
        (rep.fail if strict else rep.warn)("eval.report_json", "missing")
        return
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        rep.fail("eval.report_json", f"unparseable: {exc}")
        return
    for key in ("generated_at", "corpus", "benchmarks", "hypotheses", "negative_controls"):
        if key not in r:
            rep.fail("eval.report_json", f"missing top-level key {key!r}")
            return
    nc = r["negative_controls"]
    for k in ("quxiangbilei", "ayurveda_rasa", "null_model"):
        if k not in nc:
            rep.warn("eval.report_json", f"negative_controls missing {k!r}")
    if not r["benchmarks"]:
        rep.warn("eval.report_json", "benchmarks table is empty")
    rep.ok("eval.report_json", f"{len(r['benchmarks'])} benchmarks, {r['hypotheses'].get('n', 0)} hypotheses")


def check_artifacts(rep: Report, strict: bool) -> None:
    art = ROOT / "artifacts"
    ggufs = sorted(art.glob("*.gguf")) if art.exists() else []
    if not ggufs:
        (rep.fail if strict else rep.warn)("artifacts.gguf", "no GGUF weights found")
        return
    for g in ggufs:
        size = g.stat().st_size
        digest = hashlib.sha256(g.read_bytes()).hexdigest()
        if size > MAX_GGUF_BYTES:
            rep.fail(f"artifacts.{g.name}", f"{size:,} bytes exceeds the 1 GB ceiling")
        else:
            rep.ok(f"artifacts.{g.name}", f"{size / 1e6:.1f} MB sha256={digest[:16]}…")
        side = g.with_suffix(g.suffix + ".sha256")
        if side.exists():
            declared = side.read_text(encoding="utf-8").split()[0].strip()
            if declared != digest:
                rep.fail(f"artifacts.{g.name}.sha256", "hash mismatch with sidecar file")
        else:
            rep.warn(f"artifacts.{g.name}", "no .sha256 sidecar")


def check_git_limits(rep: Report) -> None:
    big: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "__pycache__", ".tmp", "node_modules"}]
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                if p.stat().st_size > MAX_GIT_FILE_BYTES:
                    big.append(str(p.relative_to(ROOT)))
            except OSError:
                continue
    if big:
        rep.fail("git.file_size", f"files above GitHub's 100 MB limit: {big[:5]}")
    else:
        rep.ok("git.file_size", "no file exceeds 100 MB")


def check_no_placeholders(rep: Report) -> None:
    """A shipped repo must not contain unresolved template markers."""
    markers = re.compile(r"\[\[PENDING|<!--FILL:")
    hits: list[str] = []
    for pattern in ("README.md", "docs/*.md", "submission/*.md", "model/MODEL_CARD.md", "corpus/DATA_CARD.md"):
        for p in ROOT.glob(pattern):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if markers.search(text):
                hits.append(str(p.relative_to(ROOT)))
    if hits:
        rep.warn("content.placeholders", f"unfilled markers in: {hits}")
    else:
        rep.ok("content.placeholders", "no PENDING/FILL markers")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", help="missing optional artefacts are failures")
    ap.add_argument("--json", action="store_true", help="emit a machine-readable report")
    args = ap.parse_args()

    rep = Report()
    check_registry(rep, args.strict)
    check_corpus_jsonl(rep, args.strict)
    check_structured(rep, args.strict)
    check_metrics(rep, args.strict)
    check_eval_report(rep, args.strict)
    check_artifacts(rep, args.strict)
    check_git_limits(rep)
    check_no_placeholders(rep)

    if args.json:
        print(json.dumps({"results": rep.results,
                          "failures": len(rep.failures),
                          "warnings": len(rep.warnings)}, indent=2))
    else:
        width = max(len(r["check"]) for r in rep.results)
        icons = {OK: "\033[32m✓\033[0m", WARN: "\033[33m!\033[0m", FAIL: "\033[31m✗\033[0m"}
        for r in rep.results:
            print(f"  {icons[r['status']]} {r['check']:<{width}}  {r['detail']}")
        print()
        print(f"  {len(rep.results)} checks · {len(rep.failures)} failures · {len(rep.warnings)} warnings")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())
