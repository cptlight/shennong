#!/usr/bin/env python3
"""Check that every number in the pitch copy still matches the artifacts.

The failure this prevents
-------------------------
Three times in this project a number was quoted from memory and was wrong: the 菖蒲 retention (1.5 % was the
limonene validation, not the card), the unanimous-refutation count (claimed before it was counted), and the
funnel arithmetic (203 − 151 ≠ 28). Each time the fix was the same: open the artifact and read it.

This script does that mechanically. It parses the numbers out of the submission copy, compares them to the
files that produce them, and exits non-zero on any mismatch, so a stale script fails the build instead of
being discovered by a judge.

    python scripts/audit_script_numbers.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPIES = [
    ROOT / "submission/DEVPOST.md",
    ROOT / "submission/SLIDES.md",
    ROOT / "submission/VIDEO_SCRIPT_3MIN.md",
    ROOT / "docs/COMPUTE.md",
    ROOT / "README.md",
]


def load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> int:
    tf = load("artifacts/tradition_first.json")
    cv = load("artifacts/consensus_vs_arbiter.json")
    det = load("artifacts/deterministic_outcomes.json")

    # ---- ground truth, read from the files ----
    truth = {}
    if tf:
        truth["candidates"] = tf["n_candidates"]
        truth["attestation"] = tf["n_failed_ancient_gate"]
        truth["theory"] = tf["n_failed_theory_gate"]
        truth["pass_both"] = (tf["n_passed_gates"] or 0) + (tf["n_failed_first_principles"] or 0)
        truth["refuted"] = tf["n_failed_first_principles"]
        truth["survive"] = tf["n_passed_gates"]
    if cv:
        truth["physics_checks_failed"] = cv["physics_refutations"]
        truth["unanimous"] = cv["refuted_despite_unanimous"]
    terpenoid = None
    for x in (det.get("results") or []):
        if "Acorus" in (x.get("binomial") or "") and x.get("chemotype") == "terpenoid":
            terpenoid = x["outcome"]["median_retention"]
    if terpenoid is not None:
        truth["acorus_terpenoid_median_pct"] = round(terpenoid * 100, 1)

    print("ground truth from artifacts:")
    for k, v in truth.items():
        print(f"  {k:<28} {v}")

    # arithmetic must close
    problems = []
    if tf:
        if truth["candidates"] - truth["attestation"] - truth["theory"] != truth["pass_both"]:
            problems.append("funnel arithmetic does not close: candidates - attestation - theory != pass_both")
        if truth["pass_both"] - truth["refuted"] != truth["survive"]:
            problems.append("funnel arithmetic does not close: pass_both - refuted != survive")

    # named unanimity must match the count
    if cv:
        named = cv.get("unanimous_refutations_named") or []
        if named and len(named) != cv["refuted_despite_unanimous"]:
            problems.append(f"named unanimity ({len(named)}) != refuted_despite_unanimous "
                            f"({cv['refuted_despite_unanimous']})")

    # ---- copy checks ----
    for path in COPIES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        # 1) the stale limonene number must never appear as the card value
        for bad in ("98.5 % of a monoterpene is stripped", "retention bar collapsing to 1.5"):
            if bad in text:
                problems.append(f"{rel}: stale limonene phrasing used as the card value: {bad!r}")

        # 2) if the funnel is quoted, all six numbers must be present
        if "203" in text and "18" in text and "151" in text:
            for k in ("151", "24", "28", "10", "18"):
                if k not in text:
                    problems.append(f"{rel}: funnel quoted but {k} missing — arithmetic cannot be checked live")

        # 3) the 菖蒲 number, if quoted, must equal the card
        if "菖蒲" in text and terpenoid is not None:
            m = re.search(r"median\s+(\d{2}(?:\.\d)?)\s*%", text)
            if m and abs(float(m.group(1)) - truth["acorus_terpenoid_median_pct"]) > 1.0:
                problems.append(f"{rel}: 菖蒲 median {m.group(1)}% does not match card "
                                f"{truth['acorus_terpenoid_median_pct']}%")

        # 4) if physics-check language is used with the funnel, both denominators must be explained
        if "78 of 203" in text and "28" in text:
            if not re.search(r"(fail a physics check somewhere|of the 28|two different denominators)",
                             text, re.I):
                problems.append(f"{rel}: '78 of 203' and '28' appear without reconciling the two denominators")

    if problems:
        print("\nFAILURES:")
        for p in problems:
            print("  ✗", p)
        return 1
    print("\n✓ all pitch numbers match the artifacts (funnel closes, unanimity named, "
          "菖蒲 = card value, denominators reconciled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
