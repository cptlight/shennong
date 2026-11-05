"""Build ``corpus/processed/corpus.jsonl`` from the cleaned per-source texts.

Pipeline
--------
1. discover every ``corpus/raw/<id>/meta.json`` whose ``status`` is ``ok`` and whose cleaned
   text passed the quality gate in ``data/clean.py``;
2. split each text into chunks of ~1-3k characters on paragraph/sentence boundaries
   (minimum 100 chars for CJK, 200 for alphabetic scripts, per PROJECT_BRIEF §10.2);
3. drop chunks whose 13-gram shingles substantially overlap a chunk already emitted
   (aggressive cross-source dedupe: a reprinted chapter counts once);
4. emit one JSON object per line with the full provenance block.

    python -m data.build_corpus
    python -m data.build_corpus --report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zlib
from collections import Counter, defaultdict

from . import _net

PROCESSED = _net.PROCESSED
CORPUS_JSONL = PROCESSED / "corpus.jsonl"
STATS_JSON = PROCESSED / "stats.json"

TARGET_CHARS = 1800       # aim here when packing paragraphs
HARD_MAX_CHARS = 3000     # never exceed (contract: ~1-3k)
MIN_CHARS_CJK = 100
MIN_CHARS_ALPHA = 200
SHINGLE_N = 13
DEDUPE_OVERLAP = 0.80     # drop chunk if this share of its 13-grams was already seen

_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\u00c0-\u00dc\"'(])")
_CJK_SENT_END = re.compile(r"(?<=[。！？；])")
_WS = re.compile(r"\s+")


def is_cjk_lang(lang: str) -> bool:
    return lang.startswith("zh") or lang.startswith("ja") or lang.startswith("ko")


def _splitlong(par: str, limit: int, cjk: bool) -> list[str]:
    """Split an over-long paragraph at sentence boundaries, then hard-wrap."""
    if len(par) <= limit:
        return [par]
    pieces = _CJK_SENT_END.split(par) if cjk else _SENT_END.split(par)
    out, buf = [], ""
    for p in pieces:
        if not p:
            continue
        if len(buf) + len(p) + 1 <= limit:
            buf = (buf + p) if cjk else (buf + " " + p if buf else p)
        else:
            if buf:
                out.append(buf.strip())
            while len(p) > limit:
                out.append(p[:limit])
                p = p[limit:]
            buf = p
    if buf.strip():
        out.append(buf.strip())
    return out


def chunk_text(text: str, lang: str, target: int = TARGET_CHARS,
               limit: int = HARD_MAX_CHARS) -> list[str]:
    cjk = is_cjk_lang(lang)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    flat: list[str] = []
    for p in paras:
        p = _WS.sub(" " if not cjk else "", p) if not cjk else re.sub(r"\s+", "", p)
        if not p:
            continue
        flat.extend(_splitlong(p, limit, cjk))
    chunks, buf = [], ""
    for p in flat:
        joined_len = len(buf) + len(p) + (1 if not cjk else 0)
        if buf and joined_len > target:
            chunks.append(buf)
            buf = p
        else:
            buf = (buf + p) if cjk else (buf + "\n" + p if buf else p)
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


def shingles(text: str, cjk: bool) -> set[int]:
    """Set of hashed 13-grams (characters for CJK, whitespace tokens for alphabetic)."""
    if cjk:
        s = re.sub(r"\s+", "", text)
        if len(s) < SHINGLE_N:
            return {zlib.crc32(s.encode("utf-8"))} if s else set()
        return {zlib.crc32(s[i:i + SHINGLE_N].encode("utf-8"))
                for i in range(len(s) - SHINGLE_N + 1)}
    toks = text.split()
    if len(toks) < SHINGLE_N:
        return {zlib.crc32(" ".join(toks).encode("utf-8"))} if toks else set()
    return {zlib.crc32(" ".join(toks[i:i + SHINGLE_N]).encode("utf-8"))
            for i in range(len(toks) - SHINGLE_N + 1)}


def load_sources() -> list[dict]:
    """Every raw source whose meta says status ok and whose cleaned text passed QC."""
    out = []
    for d in sorted(_net.RAW.iterdir()) if _net.RAW.exists() else []:
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        sid = d.name
        meta["id"] = sid
        if meta.get("status") != "ok":
            continue
        clean = PROCESSED / "text" / f"{sid}.txt"
        if not clean.exists():
            continue
        if meta.get("clean_stats") and not meta["clean_stats"].get("clean", False):
            continue
        meta["_text_path"] = str(clean)
        out.append(meta)
    return out


def build(verbose: bool = True) -> dict:
    sources = load_sources()
    if not sources:
        raise SystemExit("no cleaned sources found -- run data.fetch_* and data.clean first")

    seen: set[int] = set()
    per_tier = Counter()
    per_tradition = Counter()
    per_lang = Counter()
    per_source = {}
    dup_dropped = 0
    emitted = 0
    PROCESSED.mkdir(parents=True, exist_ok=True)

    tmp = CORPUS_JSONL.with_suffix(".jsonl.part")
    with open(tmp, "w", encoding="utf-8") as fh:
        for meta in sources:
            sid = meta["id"]
            lang = meta.get("lang", "en")
            cjk = is_cjk_lang(lang)
            text = open(meta["_text_path"], encoding="utf-8").read()
            chunks = chunk_text(text, lang)
            kept = 0
            src_chars = 0
            min_chars = MIN_CHARS_CJK if cjk else MIN_CHARS_ALPHA
            for i, ch in enumerate(chunks):
                if len(ch) < min_chars:
                    continue
                sh = shingles(ch, cjk)
                if sh:
                    overlap = len(sh & seen) / len(sh)
                    if overlap >= DEDUPE_OVERLAP:
                        dup_dropped += 1
                        continue
                    seen |= sh
                rec = {
                    "id": f"{sid}::{i:06d}",
                    "source_id": sid,
                    "title": meta.get("title", ""),
                    "title_en": meta.get("title_en", ""),
                    "year": meta.get("year"),
                    "tradition": meta.get("tradition", ""),
                    "lang": lang,
                    "tier": meta.get("tier"),
                    "licence": meta.get("licence", ""),
                    "text": ch,
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                emitted += 1
                kept += 1
                src_chars += len(ch)
            per_source[sid] = {"chunks": kept, "chars": src_chars,
                               "tradition": meta.get("tradition"),
                               "lang": lang, "tier": meta.get("tier")}
            per_tier[meta.get("tier")] += src_chars
            per_tradition[meta.get("tradition")] += src_chars
            per_lang[lang] += src_chars
            if verbose:
                print(f"  {sid:<44} {kept:>5} chunks {src_chars:>10,} chars "
                      f"({meta.get('tradition')}/{lang})")
    tmp.replace(CORPUS_JSONL)

    # token estimate: ~1 token / 1.4 CJK chars, ~1 token / 3.8 alphabetic chars
    cjk_chars = sum(v for k, v in per_lang.items() if is_cjk_lang(k))
    alpha_chars = sum(per_lang.values()) - cjk_chars
    token_est = int(cjk_chars / 1.4 + alpha_chars / 3.8)

    stats = {
        "generated_at": _now(),
        "sources_total": len(sources),
        "records": emitted,
        "duplicate_chunks_dropped": dup_dropped,
        "chars_total": sum(per_lang.values()),
        "chars_cjk": cjk_chars,
        "chars_non_cjk": alpha_chars,
        "tokens_estimate": token_est,
        "chars_by_tier": {str(k): v for k, v in sorted(per_tier.items(), key=lambda x: str(x[0]))},
        "chars_by_tradition": dict(sorted(per_tradition.items(), key=lambda x: -x[1])),
        "chars_by_lang": dict(sorted(per_lang.items(), key=lambda x: -x[1])),
        "per_source": per_source,
        "corpus_sha256": _net.sha256_file(CORPUS_JSONL),
        "corpus_bytes": CORPUS_JSONL.stat().st_size,
        "params": {"target_chars": TARGET_CHARS, "hard_max_chars": HARD_MAX_CHARS,
                   "shingle_n": SHINGLE_N, "dedupe_overlap": DEDUPE_OVERLAP,
                   "min_chars_cjk": MIN_CHARS_CJK, "min_chars_alpha": MIN_CHARS_ALPHA},
    }
    STATS_JSON.write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    return stats


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def report(stats: dict) -> None:
    print("\n=== SHENNONG corpus ===")
    print(f"records           : {stats['records']:,}")
    print(f"sources           : {stats['sources_total']}")
    print(f"chars total       : {stats['chars_total']:,}")
    print(f"  CJK             : {stats['chars_cjk']:,}")
    print(f"  non-CJK         : {stats['chars_non_cjk']:,}")
    print(f"token estimate    : {stats['tokens_estimate']:,}")
    print(f"dupe chunks dropped: {stats['duplicate_chunks_dropped']:,}")
    print(f"corpus sha256     : {stats['corpus_sha256']}")
    print("\nchars by tier:")
    for k, v in stats["chars_by_tier"].items():
        print(f"  tier {k}: {v:,}")
    print("chars by tradition:")
    for k, v in stats["chars_by_tradition"].items():
        print(f"  {k:<20} {v:,}")
    print("chars by language:")
    for k, v in stats["chars_by_lang"].items():
        print(f"  {k:<10} {v:,}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    stats = build()
    report(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
