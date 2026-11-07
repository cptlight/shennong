#!/usr/bin/env python3
"""Ingest the jicheng.tw TCM corpus (CC0) into our corpus format.

jicheng.tw publishes ~1,250 classical TCM works with punctuation and editorial work under CC0 — the
cleanest licence available, and the largest single CC0 TCM corpus. Its raw data is the GitLab repo
`gitlab.com/jicheng/jc.data` (the site source); each work is `pages/book/<title>/index.html` with the
title, author (作者), dynasty (朝代), year (年份), base edition (底本) and the punctuated text.

This script extracts the clean text + metadata and writes `corpus/processed/jicheng.jsonl` (compressed),
tagging every span with source=jicheng.tw, licence=CC0. It is kept in a SEPARATE file from corpus.jsonl so
the CC0 provenance is unambiguous and the share-alike Kanripo layer can never contaminate it.

    git clone --depth 1 https://gitlab.com/jicheng/jc.data.git /tmp/jc_data
    python scripts/ingest_jicheng.py --jc /tmp/jc_data
"""
from __future__ import annotations

import argparse
import gzip
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def extract(path: pathlib.Path) -> dict | None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # strip scripts/styles, then tags
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", raw)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r]+", "", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None
    # the first meaningful line is the title
    title = lines[0]
    meta = {"author": "", "dynasty": "", "year": ""}
    body_start = 1
    for i, l in enumerate(lines[1:10], 1):
        m = re.match(r"^作者(.+)$", l)
        if m:
            meta["author"] = m.group(1)
            body_start = i + 1
            continue
        m = re.match(r"^朝代(.+)$", l)
        if m:
            meta["dynasty"] = m.group(1)
            body_start = i + 1
            continue
        m = re.match(r"^年份(?:公元)?(.+)$", l)
        if m:
            meta["year"] = m.group(1)
            body_start = i + 1
            continue
        break
    body = "\n".join(lines[body_start:])
    return {"title": title, "author": meta["author"], "dynasty": meta["dynasty"],
            "year": meta["year"], "text": body}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jc", default="/tmp/jc_data", help="path to the cloned jc.data repo")
    ap.add_argument("--out-prefix", default="corpus/processed/jicheng-part")
    args = ap.parse_args()

    src = pathlib.Path(args.jc)
    # recurse: a few works are multi-volume with nested subdirectories (each holding index.html)
    book_files = sorted((src / "pages" / "book").rglob("index.html"))
    ge_files = sorted((src / "pages" / "ge").glob("*.html"))

    works: list[dict] = []
        for f in book_files:
            rel = f.parent.relative_to(src / "pages" / "book")
            slug = str(rel).replace("/", "_") or f.parent.name
            e = extract(f)
            if not e or len(e["text"]) < 200:
                continue
            rec = {"id": f"jicheng-{slug}", "source_id": "jc_tw", "title": e["title"],
                   "title_en": "", "year": e["year"], "tradition": "tcm", "lang": "zh-Hant",
                   "tier": 2, "licence": "CC0-1.0", "source": "jicheng.tw",
                   "author": e["author"], "dynasty": e["dynasty"], "text": e["text"]}
            works.append(rec)
        for g in ge_files:
            e = extract(g)
            if not e or len(e["text"]) < 100:
                continue
            rec = {"id": f"jicheng-ge-{g.stem}", "source_id": "jc_tw", "title": g.stem,
                   "title_en": "", "year": "", "tradition": "tcm", "lang": "zh-Hant",
                   "tier": 2, "licence": "CC0-1.0", "source": "jicheng.tw", "text": e["text"]}
            works.append(rec)

    half = len(works) // 2 or 1
    chars = sum(len(w["text"]) for w in works)
    for i, part in enumerate((works[:half], works[half:]), 1):
        out = ROOT / f"{args.out_prefix}{i}.jsonl.gz"
        with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as fh:
            for w in part:
                fh.write(json.dumps(w, ensure_ascii=False) + "\n")
        print(f"  {out.name}: {len(part):,} works, {out.stat().st_size/1e6:.1f} MB")
    print(f"jicheng ingest: {len(works):,} works · {chars/1e6:.1f} M characters · CC0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
