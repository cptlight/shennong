#!/usr/bin/env python3
"""Run the multi-domain expert panel over the cross-sections.

Each candidate (drug, 炮制, chemotype) is evaluated independently by five experts grounded in five
different tables, then fused: the number of **distinct supporting domains** is what separates a
cross-domain interpolation from a single-source assertion.

    python scripts/run_experts.py
"""
from __future__ import annotations

import argparse, json, sys, time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shennong.experts import EXPERTS, World, fuse  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cross-sections", default="artifacts/cross_sections.json")
    ap.add_argument("--out-json", default="artifacts/expert_consensus.json")
    ap.add_argument("--out-md", default="artifacts/EXPERT_CONSENSUS.md")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    w = World.load()
    src = json.loads((ROOT / args.cross_sections).read_text(encoding="utf-8"))
    items = src.get("top") or src.get("cross_sections") or []
    # use the full set if present
    full = json.loads((ROOT / args.cross_sections).read_text(encoding="utf-8"))
    items = full.get("all") or items
    print(f"{len(items)} candidate cross-sections · {len(EXPERTS)} experts")

    results = []
    for it in items:
        claim = (f"{it.get('process')} of {it.get('drug_surface')} "
                 f"({it.get('binomial')}) should measurably enrich its {it.get('chemotype')} content")
        proposals = [fn(w, it) for fn in EXPERTS.values()]
        c = fuse(claim, proposals)
        results.append({"item": it, "consensus": c.to_dict()})

    results.sort(key=lambda r: (r["consensus"]["agreement"], r["consensus"]["consensus_score"],
                                r["item"].get("sharpness", 0)),
                 reverse=True)
    agree = Counter(r["consensus"]["agreement"] for r in results)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": ("multi-domain expert panel: five experts, each grounded in a different table, "
                 "scoring the same claim; the fusion counts INDEPENDENT supporting domains"),
        "n_candidates": len(results),
        "agreement_distribution": dict(sorted(agree.items(), reverse=True)),
        "top": [r for r in results[: args.top]],
    }
    (ROOT / args.out_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Multi-domain expert consensus", "", payload["generated_at"], "",
         "Five experts, five different data tables, no shared evidence. A claim supported by several",
         "**independent domains** is an interpolation; a claim supported by one is an assertion. The",
         "fusion reports which domains disagree rather than averaging the disagreement away.", "",
         "| Claim | Domains agreeing | Consensus | Verdict |", "|---|---|---|---|"]
    for r in results[:20]:
        it, c = r["item"], r["consensus"]
        L.append(f"| {it.get('drug_surface')} + {it.get('process')} → {it.get('chemotype')} | "
                 f"**{c['agreement']}/5** | {c['consensus_score']} | {c['verdict']} |")

    L += ["", "## Distribution of independent support", "", "| Domains agreeing | Candidates |", "|---|---|"]
    for k in sorted(agree, reverse=True):
        L.append(f"| {k} | {agree[k]} |")

    L += ["", "## The strongest cross-domain interpolations", ""]
    for r in results[:6]:
        it, c = r["item"], r["consensus"]
        L += [f"### {it.get('drug_surface')} + {it.get('process')} → {it.get('chemotype')}", "",
              f"**{c['verdict']}** (consensus {c['consensus_score']}, {c['agreement']}/5 domains)", "",
              "| Domain | Score | What it says |", "|---|---|---|"]
        for d in c["domains"]:
            L.append(f"| {d['domain']} | {d['score']} | {d['rationale'][:110]} |")
        if c["disagreements"]:
            L += ["", "**Disagreement:** " + "; ".join(c["disagreements"])[:300]]
        L.append("")
    (ROOT / args.out_md).write_text("\n".join(L), encoding="utf-8")

    print("agreement distribution:", dict(sorted(agree.items(), reverse=True)))
    print(f"wrote {args.out_json} and {args.out_md}")
    for r in results[:6]:
        it, c = r["item"], r["consensus"]
        print(f"  {c['agreement']}/5  {it.get('drug_surface')}+{it.get('process')} -> "
              f"{it.get('chemotype'):<12} consensus {c['consensus_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
