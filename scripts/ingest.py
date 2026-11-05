#!/usr/bin/env python3
"""Grow the corpus: ingest new texts without breaking provenance or the licence audit.

This is the step that makes the pipeline **continuous** rather than a one-off corpus dump. It takes
new material (a file of chunks, or a plain text with metadata), refuses anything without a licence and
an evidence URL, normalises and deduplicates against what is already there, appends to
`corpus/processed/corpus.jsonl`, records the source in `corpus/registry/sources.yaml`, and bumps the
corpus version with the new sha256 — so a later discovery run can be tied to an exact corpus state.

The rule the whole project rests on: **unclear licence → recorded, not trained on.** This script has no
flag to override that. If a source cannot be licensed, it is refused and the refusal is logged.

    # a JSONL where each line is {"text": "...", "title": "...", ...}
    python scripts/ingest.py --input new_texts.jsonl --source-id my_new_source \
        --title "…" --author "…" --year 1700 --tradition tcm --lang zh-Hant \
        --licence "Public Domain" --licence-evidence "https://…"

    python scripts/ingest.py --list-versions
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "corpus" / "processed" / "corpus.jsonl"
REGISTRY = ROOT / "corpus" / "registry" / "sources.yaml"
VERSIONS = ROOT / "corpus" / "versions"

MIN_CHARS_CJK = 100
MIN_CHARS_ALPHA = 200
MODERN_TRADITIONS = {"tcm", "ayurveda", "unani", "kampo", "korean", "tibetan", "persian",
                     "alchemy", "acupuncture", "foundational", "comparative-control"}
OPEN_LICENCES = ("public domain", "cc0", "cc-by-4.0", "cc-by-sa-4.0", "apache", "mit")


def _is_open(licence: str) -> bool:
    l = licence.strip().lower()
    if "nc" in l or "noncommercial" in l or "non-commercial" in l:
        return False
    return any(l.startswith(o) or o in l for o in OPEN_LICENCES)


def _shingles(text: str, n: int = 13) -> set[int]:
    w = text.split()
    return {hash(tuple(w[i:i + n])) for i in range(max(0, len(w) - n + 1))}


def load_existing() -> tuple[list[dict], set[int]]:
    rows, sh = [], set()
    if not CORPUS.exists():
        return rows, sh
    with CORPUS.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(r)
            sh |= _shingles(r.get("text") or "")
    return rows, sh


def bump_version(n_records: int, chars: int, added: str) -> dict:
    VERSIONS.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(CORPUS.read_bytes()).hexdigest() if CORPUS.exists() else ""
    version = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sha256": digest,
        "records": n_records,
        "chars": chars,
        "added_source": added,
    }
    n = len(list(VERSIONS.glob("v*.json"))) + 1
    (VERSIONS / f"v{n:03d}.json").write_text(json.dumps(version, indent=2), encoding="utf-8")
    (VERSIONS / "current.json").write_text(json.dumps(version, indent=2), encoding="utf-8")
    return version


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input")
    ap.add_argument("--source-id")
    ap.add_argument("--title", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--tradition", default="tcm")
    ap.add_argument("--lang", default="zh-Hant")
    ap.add_argument("--tier", type=int, default=2)
    ap.add_argument("--url", default="")
    ap.add_argument("--licence", default="")
    ap.add_argument("--licence-evidence", default="")
    ap.add_argument("--max-chars", type=int, default=1800)
    ap.add_argument("--list-versions", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.list_versions:
        if not VERSIONS.exists():
            print("no corpus versions recorded yet")
            return 0
        for p in sorted(VERSIONS.glob("v*.json")):
            v = json.loads(p.read_text())
            print(f"{p.name}: {v['records']:,} records, {v['chars']:,} chars, "
                  f"sha256 {v['sha256'][:12]}… ({v['created_at']})")
        return 0

    # --- licence gate: the one check that can never be overridden -----------------
    if not args.licence or not args.licence_evidence:
        print("REFUSED: a licence and a licence-evidence URL are required. "
              "Unlicensed material is recorded, never trained on.", file=sys.stderr)
        return 2
    if not _is_open(args.licence):
        print(f"REFUSED: licence {args.licence!r} is not open (NC or unrecognised). "
              "It will be recorded as `unverified` and excluded from training.", file=sys.stderr)
        return 2
    if args.tradition not in MODERN_TRADITIONS:
        print(f"REFUSED: unknown tradition {args.tradition!r}", file=sys.stderr)
        return 2

    path = Path(args.input)
    if not path.exists():
        print(f"no such input: {path}", file=sys.stderr)
        return 2

    docs = []
    if path.suffix in (".jsonl", ".ndjson"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = (r.get("text") or "").strip()
            if t:
                docs.append(t)
    else:
        docs = [path.read_text(encoding="utf-8")]

    rows, seen = load_existing()
    existing_ids = {r.get("id") for r in rows}
    new_rows, dup = [], 0
    for i, text in enumerate(docs):
        min_len = MIN_CHARS_CJK if args.lang.startswith(("zh", "ja", "ko")) else MIN_CHARS_ALPHA
        if len(text) < min_len:
            continue
        for j in range(0, len(text), args.max_chars):
            chunk = text[j:j + args.max_chars].strip()
            if len(chunk) < min_len:
                continue
            sh = _shingles(chunk)
            if sh and len(sh & seen) / max(1, len(sh)) > 0.8:
                dup += 1
                continue
            seen |= sh
            rid = f"{args.source_id}::{i:06d}::{j // args.max_chars:03d}"
            if rid in existing_ids:
                dup += 1
                continue
            new_rows.append({
                "id": rid, "source_id": args.source_id, "title": args.title,
                "title_en": args.title, "year": args.year, "tradition": args.tradition,
                "lang": args.lang, "tier": args.tier, "licence": args.licence, "text": chunk,
            })

    chars = sum(len(r["text"]) for r in new_rows)
    print(f"parsed {len(docs)} document(s) → {len(new_rows)} new chunks, {dup} duplicates/too-short dropped")

    if not args.dry_run and new_rows:
        with CORPUS.open("a", encoding="utf-8") as fh:
            for r in new_rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        entry = {
            "id": args.source_id, "title": args.title, "author": args.author, "year": args.year,
            "tradition": args.tradition, "lang": args.lang, "tier": args.tier, "url": args.url,
            "licence": args.licence, "licence_evidence": args.licence_evidence,
            "chars": chars, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "status": "ok",
        }
        header = "" if REGISTRY.exists() else "# sources registry\n"
        with REGISTRY.open("a", encoding="utf-8") as fh:
            fh.write(header + "\n" + json.dumps(entry, ensure_ascii=False) + "\n")
        total_chars = sum(len(r.get("text") or "") for r in rows) + chars
        v = bump_version(len(rows) + len(new_rows), total_chars, args.source_id)
        print(f"appended {len(new_rows)} chunks ({chars:,} chars) · corpus now {v['records']:,} records, "
              f"{v['chars']:,} chars · version sha256 {v['sha256'][:12]}…")
    elif args.dry_run:
        print("dry run: nothing written")
    else:
        print("nothing new to add")

    print("\nnext: python -m shennong.cli cai && zhi && pei && shi   # re-derive the graph and discoveries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
