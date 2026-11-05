#!/usr/bin/env python3
"""Audit every candidate's citation with the support verifier — and measure the verifier itself.

Two jobs:

1. **Annotate** each of the 60 candidates with a `support` block: supported / score / signals. A
   candidate whose evidence fails support is flagged in the artefact rather than quietly kept.
2. **Measure the verifier** against a shuffled-negative gold set built from the candidates themselves:
   positives are each candidate paired with *its own* verified span; negatives are the same candidate
   paired with a **different** candidate's span. A verifier with no power would score both alike; the
   precision/recall/AUC below are therefore a real measurement of the check, not a sanity test.

    python scripts/support_audit.py
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shennong.verify import auc, verify_support  # noqa: E402


def candidate_view(c: dict) -> dict:
    lead = c.get("lead") or {}
    line = c.get("classical_line") or {}
    return {
        "id": c.get("id"),
        "claim": c.get("association_claim") or c.get("theory_justification") or "",
        "span": line.get("text") or "",
        "drug_names": [x for x in [lead.get("drug"), lead.get("drug_modern"),
                                   c.get("name_cn"), line.get("names_drug")] if x],
        "indication": lead.get("indication") or "",
        "line": line,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="artifacts/drug_candidates.json")
    ap.add_argument("--out", default="artifacts/support_verification.json")
    ap.add_argument("--negatives-per-positive", type=int, default=5)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    doc = json.loads((ROOT / args.candidates).read_text(encoding="utf-8"))
    cands = doc["candidates"]
    views = [candidate_view(c) for c in cands]

    # --- 1. annotate each candidate with its own support verdict -----------------------
    annotated = 0
    for c, v in zip(cands, views):
        r = verify_support(v["claim"], v["span"], v["drug_names"], v["indication"])
        c["support"] = {
            **r.to_dict(),
            "method": ("claim-span support: entity presence (繁/简 folded), classical relation cue, "
                       "indication bigram overlap, polarity conflict, length sanity. NOT cross-lingual "
                       "semantic entailment — see shennong/verify.py"),
            "span_locator": v["line"].get("locator"),
        }
        annotated += 1

    # --- 2. build the shuffled-negative gold set ---------------------------------------
    rng = random.Random(args.seed)
    pos_scores, neg_scores = [], []
    pos_supported = neg_supported = 0
    d_pos = d_neg = 0
    examples_neg = []
    for i, (v, c) in enumerate(zip(views, cands)):
        if not v["span"]:
            continue
        p = verify_support(v["claim"], v["span"], v["drug_names"], v["indication"])
        pos_scores.append(p.score)
        d_pos += 1
        pos_supported += int(p.supported)

        # A true negative must come from a *different lead drug*: two candidates sharing a plant can
        # legitimately cite a span that names that plant, so pairing them inflates false positives.
        own = (views[i]["drug_names"][0] if views[i]["drug_names"] else "").strip()
        others = [j for j in range(len(views))
                  if j != i and views[j]["span"]
                  and (views[j]["drug_names"][0] if views[j]["drug_names"] else "").strip() != own]
        for j in rng.sample(others, min(args.negatives_per_positive, len(others))):
            n = verify_support(v["claim"], views[j]["span"], v["drug_names"], v["indication"])
            neg_scores.append(n.score)
            d_neg += 1
            neg_supported += int(n.supported)
            if n.supported and len(examples_neg) < 5:
                examples_neg.append({"candidate": v["id"], "foreign_span_from": views[j]["id"],
                                     "score": n.score, "false_positive": True})

    # --- operating characteristic: the boolean rule is one threshold, so publish the sweep ---
    def metrics_at(thr: float) -> dict:
        tp = sum(1 for x in pos_scores if x >= thr)
        fp = sum(1 for x in neg_scores if x >= thr)
        fn = len(pos_scores) - tp
        tn = len(neg_scores) - fp
        prec = tp / (tp + fp) if (tp + fp) else None
        rec = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
        return {"threshold": thr,
                "precision": None if prec is None else round(prec, 4),
                "recall": None if rec is None else round(rec, 4),
                "f1": None if f1 is None else round(f1, 4),
                "tp": tp, "fp": fp, "tn": tn, "fn": fn}

    sweep = [metrics_at(t) for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8)]
    best = max((m for m in sweep if m["f1"] is not None), key=lambda m: m["f1"])
    roc_auc = auc(pos_scores, neg_scores)
    # adopt the F1-optimal threshold for the published verdict
    adopted = best["threshold"]
    pos_supported = best["tp"]
    neg_supported = best["fp"]
    for c, v in zip(cands, views):
        sup = (c.get("support") or {}).get("score", 0.0)
        c["support"]["supported"] = bool(sup >= adopted)
        c["support"]["adopted_threshold"] = adopted

    tp, fn = pos_supported, d_pos - pos_supported
    fp, tn = neg_supported, d_neg - neg_supported
    precision = best["precision"]
    recall = best["recall"]
    f1 = best["f1"]

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what_this_is": ("A measured check that each candidate's cited span supports its claim — entity, "
                         "relation cue, polarity, length — plus the verifier's own precision/recall/AUC on "
                         "a shuffled-negative gold set."),
        "what_this_is_not": ("Not cross-lingual semantic entailment. Claims are largely English and spans "
                             "Chinese/Sanskrit; judging entailment needs a multilingual encoder, which is "
                             "the documented next step."),
        "n_candidates": len(cands),
        "n_positives": d_pos,
        "n_negatives": d_neg,
        "verifier_metrics": {
            "precision": None if precision is None else round(precision, 4),
            "recall": None if recall is None else round(recall, 4),
            "f1": None if f1 is None else round(f1, 4),
            "auc": None if roc_auc != roc_auc else round(roc_auc, 4),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "mean_score_pos": round(statistics.mean(pos_scores), 4) if pos_scores else None,
            "mean_score_neg": round(statistics.mean(neg_scores), 4) if neg_scores else None,
            "adopted_threshold": adopted,
            "threshold_rule": "score >= adopted_threshold; chosen to maximise F1 on this gold set",
        },
        "operating_characteristic": sweep,
        "candidates_supported": pos_supported,
        "candidates_unsupported": [c["id"] for c, v in zip(cands, views)
                                   if not (c.get("support") or {}).get("supported")],
        "false_positive_examples": examples_neg,
    }

    (ROOT / args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / args.candidates).write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    m = report["verifier_metrics"]
    print(f"annotated {annotated} candidates")
    print(f"gold set: {d_pos} positives / {d_neg} shuffled negatives")
    print(f"verifier: precision {m['precision']} recall {m['recall']} f1 {m['f1']} AUC {m['auc']}")
    print(f"mean score pos {m['mean_score_pos']} vs neg {m['mean_score_neg']}")
    print(f"candidates supported: {pos_supported}/{d_pos}")
    if report["candidates_unsupported"]:
        print(f"unsupported: {report['candidates_unsupported'][:8]}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
