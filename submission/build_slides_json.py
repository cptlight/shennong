#!/usr/bin/env python3
"""
Generate `submission/slides.json` from `submission/SLIDES.md`.

The markdown is the primary artefact; this file exists so a future PPTX export has structured input.
Generating it instead of hand-maintaining it means the deck and the JSON cannot drift — and the script
also *enforces the 10-slide hard limit*, which is the one rule EthnoHack will actually check.

Run: python submission/build_slides_json.py
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "SLIDES.md")
OUT = os.path.join(HERE, "slides.json")
MAX_SLIDES = 10


def parse(md: str):
    slides = []
    # "## Slide 7 — [[PENDING: candidates.count]] drug candidates — one worked end-to-end"
    chunks = re.split(r"^## Slide (\d+)\s*[—-]\s*(.+)$", md, flags=re.MULTILINE)
    # chunks: [preamble, num, title, body, num, title, body, ...]
    for i in range(1, len(chunks), 3):
        num = int(chunks[i])
        title = chunks[i + 1].strip()
        body = chunks[i + 2]

        # stop at the deck-constraints section if present
        body = re.split(r"^## Deck constraints", body, flags=re.MULTILINE)[0]

        # "**Title:** ..." inside the body is the on-slide headline
        headline = title
        m = re.search(r"^\*\*Title:\*\*\s*(.+)$", body, flags=re.MULTILINE)
        if m:
            headline = m.group(1).strip()

        # Bullets wrap onto continuation lines in the markdown; a naive line-grep truncates them mid-sentence
        # (and then a placeholder on a continuation line silently escapes validation). Join properly:
        #   "- text" starts a bullet; any following indented, non-bullet line is a continuation;
        #   an indented "- " is a sub-bullet and is folded into its parent with a separator.
        bullets, cur, sub_started = [], None, False
        for raw in body.splitlines():
            if not raw.strip():
                continue
            stripped = raw.lstrip()
            if stripped.startswith("- ") and not raw.startswith("  - "):
                if cur is not None:
                    bullets.append(cur)
                cur, sub_started = stripped[2:].strip(), False
            elif stripped.startswith("- ") and raw.startswith("  - ") and cur is not None:
                cur += "  · " + stripped[2:].strip()
                sub_started = True
            elif cur is not None and raw.startswith(" "):
                cur += " " + stripped.strip()
            elif cur is not None and not raw.startswith(("**", "#", "|", ">")):
                cur += " " + stripped.strip()
        if cur is not None:
            bullets.append(cur)
        bullets = [re.sub(r"\s+", " ", b).strip() for b in bullets if b.strip()]

        visual = ""
        m = re.search(r"^\*\*Visual:\*\*\s*(.+?)(?:\n\n|\Z)", body, flags=re.MULTILINE | re.DOTALL)
        if m:
            visual = re.sub(r"\s+", " ", m.group(1)).strip()

        note = ""
        m = re.search(r"^\*\*Speaker note:\*\*\s*(.+?)(?:\n\n|\Z)", body, flags=re.MULTILINE | re.DOTALL)
        if m:
            note = re.sub(r"\s+", " ", m.group(1)).strip()

        slides.append(dict(n=num, title=headline, bullets=bullets[:5], visual=visual, speaker_note=note))

    slides.sort(key=lambda s: s["n"])
    return slides


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Generate slides.json from SLIDES.md and validate the deck")
    ap.add_argument("--final", action="store_true",
                    help="ship mode: [[PENDING: ...]] placeholders become errors instead of warnings")
    args = ap.parse_args(argv)

    with open(SRC, "r", encoding="utf-8") as f:
        md = f.read()
    slides = parse(md)

    # ---- hard-limit check: EthnoHack allows at most 10 slides ----
    errs, pending = [], []
    if len(slides) != MAX_SLIDES:
        errs.append(f"expected exactly {MAX_SLIDES} slides, found {len(slides)}")
    for s in slides:
        if not 3 <= len(s["bullets"]) <= 5:
            errs.append(f"slide {s['n']}: {len(s['bullets'])} bullets (want 3–5)")
        if not s["visual"]:
            errs.append(f"slide {s['n']}: no visual suggestion")
        if not s["speaker_note"]:
            errs.append(f"slide {s['n']}: no speaker note")
        if "PENDING" in json.dumps(s):
            msg = f"slide {s['n']}: still contains a [[PENDING: …]] placeholder"
            if args.final:
                errs.append(msg)
            else:
                pending.append(msg)

    numbered = [s["n"] for s in slides]
    if numbered != list(range(1, MAX_SLIDES + 1)):
        errs.append(f"slide numbering is not 1..{MAX_SLIDES}: {numbered}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(dict(
            deck="SHENNONG 神农", event="EthnoHack 2026",
            track="01 — Traditional Knowledge Mining",
            slide_count=len(slides),
            hard_limit=MAX_SLIDES,
            source="submission/SLIDES.md",
            note="Generated by build_slides_json.py from SLIDES.md. Do not edit by hand.",
            slides=slides), f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {OUT} — {len(slides)} slides")

    if pending:
        print("\n  still awaiting real numbers (allowed while drafting, blocks --final):")
        for p in pending:
            print(f"    · {p}")
    if errs:
        print("\nBLOCKING:", file=sys.stderr)
        for e in errs:
            print(f"  ✗ {e}", file=sys.stderr)
        return 1
    print("  ✓ exactly 10 slides · 3–5 bullets each · visual + speaker note on every slide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
