"""MediaWiki client for Wikisource (zh / sa / en) used to harvest classical Asian texts.

Why Wikisource: the underlying classical works are PD-old (author died >100 years ago); the
Wiki* community releases the transcription under CC BY-SA 4.0 (zh/sa) and we attribute the
project in ``corpus/DATA_CARD.md``. That is an explicit, verifiable licence -- not a guess.

Large works are split into subpages (e.g. ``本草綱目/草之一``), sometimes two levels deep
(``अष्टाङ्गहृदयम्/शारीरस्थानम्/अध्यायः १``), so pages are enumerated recursively.
"""

from __future__ import annotations

import json
import re
import sys
import time

from . import _net

SITE = {
    "zh": "https://zh.wikisource.org/w/api.php",
    "sa": "https://sa.wikisource.org/w/api.php",
    "en": "https://en.wikisource.org/w/api.php",
}

# TextExtracts (explaintext) leaves section headings as "== ... =="; drop the markers but
# keep the heading text, which carries real structure (卷/篇/chapter names).
_HEADING = re.compile(r"^\s*=+\s*(.*?)\s*=+\s*$", re.M)
_SUBST_REF = re.compile(r"\[(\d+)\]")
_WS = re.compile(r"[ \t\u3000]+")
_BLANKLINES = re.compile(r"\n{3,}")


class WikiClient:
    def __init__(self, lang: str = "zh"):
        if lang not in SITE:
            raise ValueError(f"unsupported wikisource language {lang!r}")
        self.lang = lang
        self.api = SITE[lang]

    # -- low level -------------------------------------------------------
    def _get(self, params: dict) -> dict:
        p = {"format": "json", "formatversion": "1"}
        p.update(params)
        return _net.get_json(self.api, params=p, timeout=60, retries=5)

    # -- structure -------------------------------------------------------
    def resolve_title(self, title: str) -> str:
        """Follow redirects and normalisation to the canonical page title."""
        d = self._get({"action": "query", "titles": title, "redirects": 1})
        pages = d.get("query", {}).get("pages", [])
        if isinstance(pages, dict):  # formatversion 1 fallback
            pages = list(pages.values())
        for p in pages:
            return p.get("title", title)
        return title

    def page_info(self, title: str) -> dict:
        d = self._get({"action": "query", "titles": title, "prop": "info",
                       "redirects": 1})
        pages = d.get("query", {}).get("pages", [])
        if isinstance(pages, dict):
            pages = list(pages.values())
        return pages[0] if pages else {}

    def list_subpages(self, prefix: str, max_pages: int = 900) -> list[str]:
        """All pages whose title begins with ``prefix + '/'`` (non-recursive)."""
        out: list[str] = []
        cont = None
        while True:
            params = {
                "action": "query", "list": "allpages", "apprefix": prefix + "/",
                "aplimit": 500, "apnamespace": 0,
            }
            if cont:
                params["apcontinue"] = cont
            d = self._get(params)
            out += [p["title"] for p in d.get("query", {}).get("allpages", [])]
            cont = d.get("continue", {}).get("apcontinue")
            if not cont or len(out) >= max_pages:
                break
            time.sleep(0.3)
        return out[:max_pages]

    def walk(self, root: str, max_depth: int = 3, max_pages: int = 900) -> list[str]:
        """Recursively enumerate a work: root page first, then all descendant subpages."""
        root = self.resolve_title(root)
        seen = [root]
        frontier = [root]
        for _depth in range(max_depth):
            nxt: list[str] = []
            for pref in frontier:
                for sub in self.list_subpages(pref):
                    if sub not in seen:
                        seen.append(sub)
                        nxt.append(sub)
            if not nxt:
                break
            frontier = nxt
            if len(seen) >= max_pages:
                break
        return seen

    # -- text ------------------------------------------------------------
    def extract(self, title: str) -> str:
        """Plain-text extract for one page (full text, no intro-only truncation)."""
        d = self._get({
            "action": "query", "prop": "extracts", "explaintext": 1,
            "titles": title, "redirects": 1, "exlimit": 1,
        })
        pages = d.get("query", {}).get("pages", [])
        if isinstance(pages, dict):
            pages = list(pages.values())
        if not pages or pages[0].get("missing"):
            return ""
        return pages[0].get("extract", "") or ""

    def harvest(self, root: str, log=print) -> tuple[str, dict]:
        """Fetch a whole work. Returns (concatenated_text, stats)."""
        pages = self.walk(root)
        chunks: list[str] = []
        empty: list[str] = []
        n_chars = 0
        for i, title in enumerate(pages, 1):
            try:
                raw = self.extract(title)
            except Exception as e:  # a single bad page must not kill the work
                log(f"  ! {title}: {e}")
                empty.append(title)
                continue
            txt = normalise_extract(raw)
            if txt:
                chunks.append(txt)
                n_chars += len(txt)
            else:
                empty.append(title)
            if i % 25 == 0:
                log(f"  {i}/{len(pages)} pages, {n_chars:,} chars")
        stats = {
            "pages_listed": len(pages),
            "pages_with_text": len(pages) - len(empty),
            "pages_empty": empty,
            "chars": n_chars,
        }
        return "\n\n".join(chunks), stats


def normalise_extract(text: str) -> str:
    """Turn a TextExtracts plaintext blob into clean training text.

    Keeps the classical orthography unchanged (traditional characters are signal, not noise).
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HEADING.sub(lambda m: m.group(1), text)
    text = _SUBST_REF.sub("", text)
    text = text.replace("\u00a0", " ")
    text = _WS.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANKLINES.sub("\n\n", text)
    return text.strip()


def harvest_to_meta(entry: dict, dest_dir, log=print) -> dict:
    """Fetch one manifest entry into ``dest_dir/text.raw`` and write ``meta.json``."""
    from pathlib import Path

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    client = WikiClient(entry["ws_lang"])
    log(f"[{entry['id']}] {entry['title']} ({entry['ws_lang']})")
    text, stats = client.harvest(entry["ws_page"], log=log)
    raw = dest_dir / "text.raw"
    raw.write_text(text + "\n", encoding="utf-8", newline="\n")
    meta = dict(entry)
    meta.pop("ws_page", None)
    meta.update({
        "fetcher": "wikisource",
        "fetch_stats": {
            "pages_listed": stats["pages_listed"],
            "pages_with_text": stats["pages_with_text"],
            "pages_empty": len(stats["pages_empty"]),
        },
        "raw_file": "text.raw",
        "raw_bytes": raw.stat().st_size,
        "raw_sha256": _net.sha256_file(raw),
        "raw_chars": len(text),
    })
    (dest_dir / "meta.json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"  -> {stats['pages_with_text']}/{stats['pages_listed']} pages, {len(text):,} chars")
    return meta
