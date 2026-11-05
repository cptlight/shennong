#!/usr/bin/env python3
"""
Stage / apply / revert the "results pending" fallback for the theory-predictivity surfaces.

WHY THIS EXISTS
---------------
`eval/report.json` is the last blocker. If the real-corpus report does not land, we still must not ship a
public page containing either (a) a fixture number presented as a result, or (b) a raw `[[PENDING: …]]`
token. This script swaps the three numeric surfaces — slide 8, the Devpost theory paragraph, and video
segment 9 — for an explicit *"pre-registered analysis running — results pending"* statement.

It is deliberately reversible and dry-runnable. It is NOT applied by default.

    python submission/apply_pending_variant.py --dry-run     # show what would change
    python submission/apply_pending_variant.py --apply       # swap in the pending variant
    python submission/apply_pending_variant.py --revert      # restore the numeric placeholders
    python submission/apply_pending_variant.py --status      # which variant is currently in place

After `--apply`, run `python submission/build_slides_json.py` to regenerate slides.json.

SAFETY: every replacement is anchored on an exact string that currently exists in the file. If an anchor is
missing (because sync_numbers.py has already filled the real numbers), the script refuses to do anything —
it will not silently rewrite text it does not recognise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = "PENDING-VARIANT"

# (file, label, numeric_text, pending_text)
# The numeric text is the *current* placeholder-bearing block; the pending text replaces it wholesale.
SURFACES = [
    (
        "submission/SLIDES.md",
        "slide 8",
        """- **Pre-registered.** Thresholds and the permutation construction were written into `docs/EVALUATION.md` *before*
  the numbers existed, so the test cannot be tuned into a positive. Each test: effect size, n, p, permutation null
  (theory vectors shuffled across drugs):
  - **四氣 (nature)** → compound polarity / thermolability · AUC **[[PENDING: theory.tcm_nature]]**
  - **歸經 (channel tropism)** → target organ or receptor family · AUC **[[PENDING: theory.tcm_channel]]**
  - **五味 (flavours)** → receptor class · AUC **[[PENDING: theory.tcm_flavor]]**
  - **vīrya (Ayurvedic hot/cold)** → logP / thermolability · ρ **[[PENDING: theory.ayurveda_virya]]**
  - **ṣaḍrasa (six tastes)** → pharmacological action class · AUC **[[PENDING: theory.ayurveda_rasa]]**
- **[[PENDING: eval.theory_positive_count]] of [[PENDING: eval.theory_n_tests]]** tests beat the null at
  p < 0.05. [[PENDING: eval.theory_summary_sentence]]""",
        """- **Pre-registered.** The thresholds, the permutation construction and the withdrawal criteria were written into
  `docs/EVALUATION.md` *before* the numbers existed, so the test cannot be tuned into a positive. Five tests are
  specified: 四氣 → polarity/thermolability · 歸經 → target organ · 五味 → action class · vīrya → logP ·
  ṣaḍrasa → action class.
- **Pre-registered analysis running — results pending.** The five test definitions, the effect-size thresholds
  (AUC ≥ 0.60 or |ρ| ≥ 0.15, permutation p < 0.05) and the null construction are published; the real-corpus
  numbers are not yet in this deck. We would rather show this line than a placeholder or a preliminary figure.""",
    ),
    (
        "submission/DEVPOST.md",
        "theory paragraph",
        """This is the only claim here that can be **wrong in an interesting way**. If 歸經 predicts receptor family at a
useful AUC, we have validated a two-thousand-year-old system as a usable prior for drug discovery. If it lands at
0.51, we have published a real negative result about a framework a billion people use — also a finding, and one
nobody else in this competition will have. **And it is pre-registered:** the thresholds and the permutation
construction were written down in `docs/EVALUATION.md` before the numbers existed, so we cannot tune it into a
positive.""",
        """This is the only claim here that can be **wrong in an interesting way**. If 歸經 predicts receptor family at a
useful AUC, we have validated a two-thousand-year-old system as a usable prior for drug discovery. If it lands at
0.51, we have published a real negative result about a framework a billion people use — also a finding, and one
nobody else in this competition will have.

**And it is pre-registered:** the thresholds, the effect sizes and the permutation construction were written into
`docs/EVALUATION.md` before the numbers existed, so the test cannot be tuned into a positive — including a
withdrawal threshold for the null model, which we committed to honour either way. **The real-corpus analysis is
running as we submit; the numbers are not in this page yet.** We state that plainly rather than quoting a
preliminary figure."""),
    (
        "submission/VIDEO_SCRIPT.md",
        "segment 9",
        """**Artefact:** Workbench Methodology → theory-predictivity cards; `eval/report.json`; `docs/EVALUATION.md`.
Numbers read on camera from `eval/report.json` — the same file a judge can open.""",
        """**Artefact:** Workbench Methodology → theory-predictivity cards; `eval/report.json`; `docs/EVALUATION.md`.
**If the real-corpus report has not landed at record time, speak this instead of reading numbers:**
> "The five tests are pre-registered — the thresholds and the permutation construction are in the repository,
> written before the numbers existed. The real-corpus run is still going as we record this. What I can tell you
> is the design: AUC or rank correlation, a permutation null, n, and a withdrawal threshold we committed to
> before we saw a single result. When it finishes, the number goes in the repository next to the method — win
> or lose."
Numbers, when present, are read on camera from `eval/report.json` — the same file a judge can open."""),
]


def classify(text: str):
    marks = {lbl: MARKER in text or pending.split("\n")[0][:40] in text for _, lbl, _, pending in SURFACES}
    return marks


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stage/apply/revert the results-pending fallback")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--revert", action="store_true")
    g.add_argument("--status", action="store_true")
    args = ap.parse_args(argv)

    plan = []
    for rel, label, numeric, pending in SURFACES:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            print(f"  ✗ missing file: {rel}", file=sys.stderr)
            return 2
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if MARKER in text or pending.split("\n")[0] in text:
            state = "applied"
        elif numeric in text:
            state = "numeric"
        else:
            state = "unknown"
        plan.append((rel, label, path, text, numeric, pending, state))

    if args.status:
        print("  variant state per surface:")
        for rel, label, _, _, _, _, state in plan:
            print(f"    {rel:<34}{label:<18}{state}")
        return 0

    bad = [p for p in plan if p[6] == "unknown"]
    if bad and (args.apply or args.revert):
        print("  ✗ refusing: these surfaces match neither the numeric nor the pending variant:", file=sys.stderr)
        for rel, label, *_ in bad:
            print(f"      {rel} · {label}", file=sys.stderr)
        print("    (probably because sync_numbers.py already filled real values — in that case do NOT apply "
              "the fallback; the real numbers are better.)", file=sys.stderr)
        return 1

    changed = 0
    for rel, label, path, text, numeric, pending, state in plan:
        if args.apply:
            if state != "numeric":
                print(f"    = {rel} · {label}: already {state}, skipped")
                continue
            new = text.replace(numeric, pending, 1)
        elif args.revert:
            if state != "applied":
                print(f"    = {rel} · {label}: already {state}, skipped")
                continue
            new = text.replace(pending, numeric, 1)
        else:  # dry-run
            if state != ("numeric" if args.dry_run else "applied"):
                print(f"    = {rel} · {label}: {state}, nothing to do")
                continue
            new = text.replace(numeric, pending, 1) if numeric in text else text
        if new != text:
            if not args.dry_run:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
            print(f"    {'~' if args.dry_run else '✓'} {rel} · {label}: {state} → "
                  f"{'applied' if args.apply else 'numeric'}")
            changed += 1

    verb = "would change" if args.dry_run else "changed"
    print(f"\n  {changed} surface(s) {verb}")
    if args.apply and not args.dry_run:
        print("  next: python submission/build_slides_json.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
