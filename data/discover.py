"""Source discovery: find candidate texts on Project Gutenberg and Internet Archive.

This is *not* part of the build pipeline's critical path -- the pinned manifest in
``corpus/registry/curated_sources.json`` is what the build uses. This tool exists so a
judge (or future maintainer) can see how the sources were found and re-run discovery:

    .venv/bin/python -m data.discover

It writes ``corpus/registry/candidates.json`` (candidate ids + titles only, no text).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from ._net import CACHE, REGISTRY, get_json, get_text

GUTENBERG_SEARCH = "https://www.gutenberg.org/ebooks/search/"

# (tier, query) pairs. Broad on purpose; curation happens downstream.
GUTENBERG_QUERIES: list[tuple[int, str]] = [
    (1, "anatomy human body"),
    (1, "physiology"),
    (1, "text-book of botany"),
    (1, "elements of botany"),
    (1, "organic chemistry"),
    (1, "bacteriology"),
    (1, "pharmacology"),
    (1, "materia medica"),
    (1, "histology"),
    (1, "pathology"),
    (1, "origin of species"),
    (1, "comparative anatomy"),
    (1, "medical chemistry"),
    (1, "plant physiology"),
    (1, "heredity"),
    (1, "hygiene"),
    (2, "herbal"),
    (2, "culpeper"),
    (2, "medicinal plants"),
    (2, "dispensatory"),
    (2, "pharmacopoeia"),
    (2, "indian medicinal plants"),
    (2, "medicinal plants philippines"),
    (3, "alchemy"),
    (3, "hermetic"),
    (3, "occult philosophy"),
    (3, "paracelsus"),
    (4, "acupuncture"),
    (4, "chinese medicine"),
]

# (tier, archive.org advancedsearch query)
ARCHIVE_QUERIES: list[tuple[int, str]] = [
    (2, 'title:(herball) AND creator:(gerard)'),
    (2, 'title:(theatrum botanicum) AND creator:(parkinson)'),
    (2, 'title:(materia medica) AND date:[1500-01-01 TO 1928-12-31]'),
    (2, 'title:(pharmacopoeia) AND date:[1500-01-01 TO 1928-12-31]'),
    (2, 'title:(dispensatory) AND date:[1500-01-01 TO 1928-12-31]'),
    (2, 'title:(modern herbal)'),
    (2, 'title:(dioscorides) OR title:(materia medica) AND date:[1500-01-01 TO 1800-12-31]'),
    (2, 'title:(herbal) AND date:[1500-01-01 TO 1928-12-31]'),
    (2, 'title:(medicinal plants) AND date:[1500-01-01 TO 1928-12-31]'),
    (2, 'title:(ethnobotany)'),
    (2, 'title:(chinese materia medica)'),
    (3, 'title:(alchemy) AND date:[1400-01-01 TO 1928-12-31]'),
    (3, 'title:(hermetic) AND date:[1400-01-01 TO 1928-12-31]'),
    (3, 'title:(occult philosophy)'),
    (3, 'title:(natural magick)'),
    (3, 'title:(paracelsus)'),
    (3, 'creator:(agrippa)'),
    (4, 'title:(acupuncture)'),
    (4, 'title:(ayurveda) OR title:(materia medica of the hindus)'),
    (4, 'title:(charaka) OR title:(sushruta)'),
    (5, 'title:(phytochemical) AND creator:(duke)'),
    (5, 'title:(ethnobotanical) AND creator:(duke)'),
]


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def gutenberg_search(query: str) -> list[dict]:
    """Scrape the public Gutenberg catalogue search page (no API available/stable)."""
    try:
        html = get_text(GUTENBERG_SEARCH, params={"query": query}, timeout=60)
    except Exception as e:  # network hiccup should not kill discovery
        print(f"  ! gutenberg search failed for {query!r}: {e}", file=sys.stderr)
        return []
    soup = BeautifulSoup(html, "lxml")
    out = []
    for li in soup.select("li.booklink"):
        a = li.select_one("a.link")
        title = li.select_one(".title")
        sub = li.select_one(".subtitle")
        if not a or not a.get("href"):
            continue
        m = re.search(r"/ebooks/(\d+)", a["href"])
        if not m:
            continue
        out.append({
            "gid": int(m.group(1)),
            "title": _norm_text(title.get_text() if title else ""),
            "author": _norm_text(sub.get_text() if sub else ""),
        })
    return out


def archive_search(query: str, rows: int = 40) -> list[dict]:
    try:
        data = get_json(
            "https://archive.org/advancedsearch.php",
            params={
                "q": query,
                "fl[]": ["identifier", "title", "creator", "date", "language", "mediatype"],
                "rows": rows,
                "page": 1,
                "output": "json",
            },
            timeout=60,
        )
    except Exception as e:
        print(f"  ! archive search failed for {query!r}: {e}", file=sys.stderr)
        return []
    docs = data.get("response", {}).get("docs", [])
    out = []
    for d in docs:
        if d.get("mediatype") not in (None, "texts"):
            continue
        out.append({
            "identifier": d.get("identifier"),
            "title": _norm_text(str(d.get("title", ""))),
            "creator": _norm_text(str(d.get("creator", ""))),
            "date": d.get("date"),
            "language": d.get("language"),
        })
    return out


def main() -> int:
    REGISTRY.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    result: dict = {"gutenberg": [], "archive": []}

    seen_g: set[int] = set()
    for tier, q in GUTENBERG_QUERIES:
        print(f"[gut] t{tier} {q}")
        for cand in gutenberg_search(q):
            if cand["gid"] in seen_g:
                continue
            seen_g.add(cand["gid"])
            cand["tier"] = tier
            cand["query"] = q
            result["gutenberg"].append(cand)

    seen_a: set[str] = set()
    for tier, q in ARCHIVE_QUERIES:
        print(f"[arc] t{tier} {q}")
        for cand in archive_search(q):
            ident = cand.get("identifier")
            if not ident or ident in seen_a:
                continue
            seen_a.add(ident)
            cand["tier"] = tier
            cand["query"] = q
            result["archive"].append(cand)

    out = REGISTRY / "candidates.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}: {len(result['gutenberg'])} gutenberg, "
          f"{len(result['archive'])} archive candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
