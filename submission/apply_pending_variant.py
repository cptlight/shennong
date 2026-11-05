#!/usr/bin/env python3
"""
Stage / apply / revert the "results pending" fallback for the theory-predictivity surfaces.

WHY THIS EXISTS
---------------
`eval/report.json` is the last blocker. If the real-corpus report does not land, we still must not ship a public
page containing either (a) a fixture number presented as a result, or (b) a raw `[[PENDING: …]]` token. This
script replaces the three numeric surfaces — slide 8, the Devpost theory paragraph, and video segment 9 — with
an explicit *"pre-registered analysis running — results pending"* statement.

DESIGN
------
Each surface is located by a **start marker** and an **end marker**, and the block between them is replaced.
The original blocks are saved to `submission/.pending_variant_backup.json` on first apply, so `--revert`
restores byte-for-byte rather than reconstructing anything. Idempotent; refuses to touch a file whose markers
no longer match (which is what happens once `sync_numbers.py` fills real values — and in that case the real
numbers are better than the fallback).

    python submission/apply_pending_variant.py --status
    python submission/apply_pending_variant.py --dry-run
    python submission/apply_pending_variant.py --apply
    python submission/apply_pending_variant.py --revert
    python submission/build_slides_json.py        # after --apply or --revert
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(ROOT, "submission", ".pending_variant_backup.json")

SURFACES = [
    dict(
        file="submission/SLIDES.md",
        label="slide 8",
        start="- **Pre-registered.** Thresholds and the permutation construction",
        end="[[PENDING: eval.theory_summary_sentence]]",
        replacement=(
            "- **Pre-registered.** The thresholds, the permutation construction and the withdrawal criteria were\n"
            "  written into `docs/EVALUATION.md` *before* the numbers existed, so the test cannot be tuned into a\n"
            "  positive. Five tests are specified: 四氣 → polarity/thermolability · 歸經 → target organ ·\n"
            "  五味 → action class · vīrya → logP · ṣaḍrasa → action class.\n"
            "- **Pre-registered analysis running — results pending.** The test definitions, the effect-size\n"
            "  thresholds (AUC ≥ 0.60 or |ρ| ≥ 0.15, permutation p < 0.05) and the null construction are published;\n"
            "  the real-corpus numbers are not yet in this deck. We would rather show this line than a placeholder\n"
            "  or a preliminary figure presented as a result."
        ),
    ),
    dict(
        file="submission/DEVPOST.md",
        label="theory paragraph",
        start="**And it is pre-registered:** the thresholds and the permutation",
        end="tune it into a\npositive.",
        replacement=(
            "**And it is pre-registered:** the thresholds, the effect sizes and the permutation construction were\n"
            "written into `docs/EVALUATION.md` before the numbers existed, so the test cannot be tuned into a\n"
            "positive — including a withdrawal threshold for the null model, which we committed to honour either\n"
            "way. **The real-corpus analysis is running as we submit; the numbers are not in this page yet.** We\n"
            "state that plainly rather than quoting a preliminary figure."
        ),
    ),
    dict(
        file="submission/VIDEO_SCRIPT.md",
        label="segment 9 (spoken fallback)",
        start="**Artefact:** Workbench Methodology → theory-predictivity cards",
        end="the same file a judge can open.",
        replacement=(
            "**Artefact:** Workbench Methodology → theory-predictivity cards; `eval/report.json`;\n"
            "`docs/EVALUATION.md`.\n\n"
            "**If the real-corpus report has not landed at record time, speak this instead of reading numbers:**\n"
            "> \"The five tests are pre-registered — the thresholds and the permutation construction are in the\n"
            "> repository, written before the numbers existed. The real-corpus run is still going as we record this.\n"
            "> What I can tell you is the design: AUC or rank correlation, a permutation null, n, and a withdrawal\n"
            "> threshold we committed to before we saw a single result. When it finishes, the number goes in the\n"
            "> repository next to the method — win or lose.\"\n\n"
            "Numbers, when present, are read on camera from `eval/report.json` — the same file a judge can open."
        ),
    ),
]


def _load_backup():
    try:
        with open(BACKUP, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_backup(data):
    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _find(text, start, end):
    """Return (begin, end_idx) of the block delimited by start..end inclusive, or None."""
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i)
    if j < 0:
        return None
    return i, j + len(end)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage/apply/revert the results-pending fallback")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--revert", action="store_true")
    g.add_argument("--status", action="store_true")
    args = ap.parse_args(argv)

    backup = _load_backup()
    rows = []
    for surf in SURFACES:
        path = os.path.join(ROOT, surf["file"])
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            print(f"  ✗ cannot read {surf['file']}: {exc}", file=sys.stderr)
            return 2
        if surf["replacement"] in text:
            state = "applied"
        elif _find(text, surf["start"], surf["end"]):
            state = "numeric"
        else:
            state = "unknown"
        rows.append((surf, path, text, state))

    if args.status:
        print("  variant state per surface:")
        for surf, _, _, state in rows:
            print(f"    {surf['file']:<34}{surf['label']:<30}{state}")
        return 0

    if (args.apply or args.revert) and any(r[3] == "unknown" for r in rows):
        print("  ✗ refusing: these surfaces match neither variant:", file=sys.stderr)
        for surf, _, _, state in rows:
            if state == "unknown":
                print(f"      {surf['file']} · {surf['label']}", file=sys.stderr)
        print("    Likely cause: sync_numbers.py already filled the real values. In that case do NOT apply "
              "the fallback — the real numbers are strictly better.", file=sys.stderr)
        return 1

    changed = 0
    for surf, path, text, state in rows:
        if args.apply:
            if state != "numeric":
                print(f"    = {surf['file']} · {surf['label']}: {state}, skipped")
                continue
            span = _find(text, surf["start"], surf["end"])
            original = text[span[0]:span[1]]
            backup.setdefault(surf["file"], {})[surf["label"]] = original
            new = text[:span[0]] + surf["replacement"] + text[span[1]:]
        elif args.revert:
            if state != "applied":
                print(f"    = {surf['file']} · {surf['label']}: {state}, skipped")
                continue
            original = (backup.get(surf["file"]) or {}).get(surf["label"])
            if not original:
                print(f"    ✗ no backup for {surf['file']} · {surf['label']} — cannot restore exactly",
                      file=sys.stderr)
                return 1
            new = text.replace(surf["replacement"], original, 1)
        else:  # dry-run
            if state != "numeric":
                print(f"    = {surf['file']} · {surf['label']}: {state}, nothing to do")
                continue
            new = text  # report intent only
        if args.dry_run:
            if state == "numeric":
                print(f"    ~ {surf['file']} · {surf['label']}: numeric → applied (dry run, not written)")
            continue
        if new != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            print(f"    ✓ {surf['file']} · {surf['label']}: {state} → "
                  f"{'numeric' if args.revert else 'applied'}")
            changed += 1

    if args.apply and not args.dry_run:
        _save_backup(backup)
    print(f"\n  {changed} surface(s) changed")
    if changed and not args.dry_run:
        print("  next: python submission/build_slides_json.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
