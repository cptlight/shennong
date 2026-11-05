"""Turn a raw download into clean training text.

One function per source family, because the artefacts are genuinely different:

* ``gutenberg`` -- plain prose with a licence header/footer block to strip.
* ``archive``   -- OCR'd book scans: page numbers, running heads, hyphenated line breaks,
  "Digitized by Google" stamps and other librarial noise.
* ``wikisource``-- MediaWiki plaintext extracts: structural ``<篇名>`` markers, hard-wrapped
  CJK lines that must be re-joined (CJK has no inter-word spaces), occasional U+FFFD.

Historical orthography is *kept*: traditional characters, 19th-century English spellings and
Vedic transliteration are signal, not noise. We only remove noise that is clearly mechanical.

    python -m data.clean            # clean every fetched source
    python -m data.clean --report   # print a per-source quality report
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import _net

PROCESSED_TEXT = _net.PROCESSED / "text"

# --------------------------------------------------------------------------
# character-class detectors
# --------------------------------------------------------------------------
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_DEV = re.compile(r"[\u0900-\u097f]")
_ALPHA = re.compile(r"[A-Za-z\u00c0-\u024f]")
_CTRL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]")
_FFFD = "\ufffd"
_MULTISPACE = re.compile(r"[ \t\u00a0\u3000]{2,}")
_MANY_NL = re.compile(r"\n{3,}")


def ratio(pat: re.Pattern, text: str) -> float:
    if not text:
        return 0.0
    return len(pat.findall(text)) / max(1, len(text))


def cjk_ratio(t: str) -> float:
    return ratio(_CJK, t)


def devanagari_ratio(t: str) -> float:
    return ratio(_DEV, t)


def alpha_ratio(t: str) -> float:
    return ratio(_ALPHA, t)


def replacement_ratio(t: str) -> float:
    if not t:
        return 0.0
    return t.count(_FFFD) / len(t)


# --------------------------------------------------------------------------
# Gutenberg
# --------------------------------------------------------------------------
_PG_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
                       re.I | re.S)
_PG_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)


def strip_gutenberg(text: str) -> str:
    m = _PG_START.search(text)
    if m:
        text = text[m.end():]
    m = _PG_END.search(text)
    if m:
        text = text[:m.start()]
    return text


# --------------------------------------------------------------------------
# Internet Archive OCR
# --------------------------------------------------------------------------
# lines that are pure pagination / librarial noise
_IA_NOISE = re.compile(
    r"^\s*(?:"
    r"digiti[sz]ed by (?:google|microsoft|the internet archive)"
    r"|generated (?:on|by) .{0,60}"
    r"|original from .{0,60}"
    r"|harvard university|university of .{0,40}librar.{0,10}"
    r"|downloaded from .{0,80}"
    r"|[ivxlcdm]{1,7}\s*"          # roman page numbers
    r"|\d{1,4}\s*"                 # arabic page numbers
    r"|page \d+.*"
    r"|chapter [ivxlcdm]+.*"       # running heads
    r")\s*$",
    re.I,
)
_HYPHEN_BREAK = re.compile(r"(\w)[-\u2010\u2011]\n(\w)")


def _dedupe_running_heads(lines: list[str], min_repeat: int = 12, max_len: int = 70) -> list[str]:
    """Drop short lines that recur suspiciously often (book title / chapter running heads)."""
    from collections import Counter

    norm = [re.sub(r"\s+", " ", ln).strip().lower() for ln in lines]
    counts = Counter(ln for ln in norm if 3 <= len(ln) <= max_len)
    head = {ln for ln, c in counts.items() if c >= min_repeat}
    if not head:
        return lines
    out = []
    for ln, key in zip(lines, norm):
        # never delete a line that looks like real prose (lots of lowercase words)
        if key in head and len(key.split()) <= 8:
            continue
        out.append(ln)
    return out


def clean_archive(text: str, lang: str = "en") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    # de-hyphenate words broken across a line (English/Latin only)
    if lang in ("en", "la", "sa-Latn"):
        text = _HYPHEN_BREAK.sub(r"\1\2", text)
    lines = text.split("\n")
    kept = []
    for ln in lines:
        s = ln.strip()
        if not s:
            kept.append("")
            continue
        if _IA_NOISE.match(s):
            continue
        # OCR garbage: too few alphanumerics relative to symbols
        alnum = sum(c.isalnum() for c in s)
        if len(s) > 12 and alnum / len(s) < 0.45:
            continue
        if replacement_ratio(s) > 0.02:
            continue
        kept.append(s)
    kept = _dedupe_running_heads(kept)
    return "\n".join(kept)


# --------------------------------------------------------------------------
# Wikisource
# --------------------------------------------------------------------------
_WS_TAG_LINE = re.compile(r"^\s*<(目录|篇名|内容|正文|标题|书名|作者|朝代|年份)>\s*$")
_WS_TAG_INLINE = re.compile(r"<(篇名|目录|内容)>")
_WS_CONTENT_PREFIX = re.compile(r"^内容[：:]\s*")


def clean_wikisource(text: str, lang: str = "zh-Hant") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    text = _WS_TAG_INLINE.sub("", text)
    out_lines: list[str] = []
    for ln in text.split("\n"):
        s = ln.strip()
        if _WS_TAG_LINE.match(s):
            continue
        s = _WS_CONTENT_PREFIX.sub("", s)
        out_lines.append(s)
    if lang.startswith("zh"):
        return _reflow_cjk(out_lines)
    # Devanagari: verses are meaningful lines; just collapse runs of blanks
    return _MANY_NL.sub("\n\n", "\n".join(out_lines)).strip()


_CJK_PUNCT_END = "。！？；：」』）】…"
_FIELD_MARK = re.compile(r"^【[^】]{1,8}】")
# A line that is a drug/entry name: short, and carries no sentence punctuation at all.
_CJK_NAME_MAX = 18


def _is_cjk_heading(s: str) -> bool:
    """True for a classical entry-name line ("甘草") or a field marker ("【氣味】…")."""
    if _FIELD_MARK.match(s):
        return True
    if len(s) > _CJK_NAME_MAX:
        return False
    if re.search(r"[。！？；：，、]", s):
        return False
    return True


def _reflow_cjk(lines: list[str]) -> str:
    """Re-join hard-wrapped CJK prose while preserving entry structure.

    CJK text has no inter-word spaces, so a newline in the middle of a sentence is an
    artefact of the source transcription, not a boundary. But 本草 "entries" *are* delimited
    by a standalone drug-name line followed by 【釋名】【氣味】【主治】 field markers, and that
    structure is exactly what the property parser needs. So: re-join prose lines, keep
    heading and field lines as their own paragraphs.
    """
    paras: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            paras.append("".join(buf))
            buf.clear()

    for ln in lines:
        if not ln:
            flush()
            continue
        if _is_cjk_heading(ln):
            flush()
            paras.append(ln)
            continue
        buf.append(ln)
    flush()
    return "\n\n".join(p for p in paras if p.strip()).strip()


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def clean_text(raw: str, kind: str, lang: str) -> str:
    if kind == "gutenberg":
        raw = strip_gutenberg(raw)
        txt = clean_archive(raw, lang="en")  # same OCR-noise rules are harmless for PG
        txt = unicodedata.normalize("NFC", txt)
    elif kind == "archive":
        txt = clean_archive(raw, lang=lang)
        txt = unicodedata.normalize("NFC", txt)
    elif kind == "wikisource":
        txt = clean_wikisource(raw, lang=lang)
        txt = unicodedata.normalize("NFC", txt)
    else:
        raise ValueError(f"unknown source kind {kind!r}")
    txt = _CTRL.sub("", txt)
    txt = _MULTISPACE.sub(" ", txt)
    # normalise the whitespace-only edges of every line but keep structure
    lines = [ln.rstrip() for ln in txt.split("\n")]
    txt = "\n".join(lines)
    txt = _MANY_NL.sub("\n\n", txt)
    return txt.strip()


def quality(txt: str, lang: str) -> dict:
    n = len(txt)
    stats = {
        "chars": n,
        "cjk_ratio": round(cjk_ratio(txt), 4),
        "devanagari_ratio": round(devanagari_ratio(txt), 4),
        "alpha_ratio": round(alpha_ratio(txt), 4),
        "replacement_ratio": round(replacement_ratio(txt), 6),
        "lines": txt.count("\n") + 1 if txt else 0,
    }
    if lang.startswith("zh"):
        stats["script_ok"] = stats["cjk_ratio"] > 0.55
    elif lang == "sa":
        stats["script_ok"] = stats["devanagari_ratio"] > 0.45
    else:
        stats["script_ok"] = stats["alpha_ratio"] > 0.55
    stats["clean"] = bool(stats["script_ok"] and stats["replacement_ratio"] < 0.002
                          and n >= 2000)
    return stats


def clean_source(source_id: str, force: bool = False) -> dict | None:
    raw_dir = _net.RAW / source_id
    meta_path = raw_dir / "meta.json"
    raw_path = raw_dir / "text.raw"
    if not meta_path.exists() or not raw_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    kind = meta.get("fetcher", "wikisource")
    lang = meta.get("lang", "en")
    out = PROCESSED_TEXT / f"{source_id}.txt"
    PROCESSED_TEXT.mkdir(parents=True, exist_ok=True)
    if out.exists() and not force:
        txt = out.read_text(encoding="utf-8")
    else:
        raw = raw_path.read_text(encoding="utf-8", errors="replace")
        txt = clean_text(raw, kind, lang)
        out.write_text(txt + "\n", encoding="utf-8", newline="\n")
    stats = quality(txt, lang)
    meta["clean_stats"] = stats
    meta["clean_file"] = f"corpus/processed/text/{source_id}.txt"
    meta["clean_sha256"] = _net.sha256_file(out)
    meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"source_id": source_id, "lang": lang, **stats}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="print per-source quality table")
    ap.add_argument("--force", action="store_true", help="re-clean even if output exists")
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args(argv)

    ids = sorted(p.name for p in _net.RAW.iterdir()
                 if p.is_dir() and (p / "meta.json").exists())
    if args.only:
        ids = [i for i in ids if i in set(args.only)]
    rows = []
    for sid in ids:
        try:
            r = clean_source(sid, force=args.force)
            if r:
                rows.append(r)
                if not r["clean"]:
                    print(f"[WARN] {sid}: script_ok={r['script_ok']} "
                          f"repl={r['replacement_ratio']} chars={r['chars']:,}",
                          file=sys.stderr)
        except Exception as e:
            print(f"[FAIL] {sid}: {e!r}", file=sys.stderr)

    if args.report or True:
        print(f"\n{'source_id':<44}{'lang':<8}{'chars':>10}  script  repl   ok")
        for r in rows:
            print(f"{r['source_id']:<44}{r['lang']:<8}{r['chars']:>10,}  "
                  f"{str(r['script_ok']):<6}{r['replacement_ratio']:<7}{r['clean']}")
    ok = sum(1 for r in rows if r["clean"])
    print(f"\ncleaned {len(rows)} sources, {ok} pass quality gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
