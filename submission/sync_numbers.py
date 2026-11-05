#!/usr/bin/env python3
"""
Fill `[[PENDING: name]]` placeholders from the repository's own artefacts.

The problem this solves: the deck, the Devpost page, the video script and the docs all quote numbers that are
still being produced. Hand-editing them guarantees drift. So the placeholders are *named*, and this script
resolves each name against the file that owns it.

    python submission/sync_numbers.py --dry-run     # what would change
    python submission/sync_numbers.py              # fill them
    python submission/sync_numbers.py --check      # exit 1 if anything is still unresolved

Resolution order per name:
  1. an explicit resolver below (a computed or derived value),
  2. `eval/report.json`,
  3. `training/runs/*/metrics.json`,
  4. `corpus/registry/sources.yaml`,
  5. `artifacts/drug_candidates.json` / `app/data/*.json`.

A name that cannot be resolved is left in place and reported — never guessed. Run
`submission/check_pending.py` as the final ship gate.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

TARGETS = [
    os.path.join("submission", "SLIDES.md"),
    os.path.join("submission", "DEVPOST.md"),
    os.path.join("submission", "VIDEO_SCRIPT.md"),
    os.path.join("docs", "EVALUATION.md"),
    os.path.join("docs", "NUMBERS.md"),
]
TOKEN = re.compile(r"\[\[PENDING:\s*([^\]]+?)\]\]")


# --------------------------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------------------------
def _json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_corpus_stats():
    """Corpus figures: `stats.json` (emitted training text) wins; the registry supplies licence counts."""
    emitted = _json(os.path.join(ROOT, "corpus", "processed", "stats.json")) or {}
    try:
        import serve  # app/serve.py
    except Exception:  # noqa: BLE001
        return None
    rows = serve.normalise_sources(serve.parse_sources_yaml(os.path.join(ROOT, "corpus", "registry", "sources.yaml")))
    if not rows:
        return None
    ok = [r for r in rows if r["status"] == "ok"]
    return dict(
        # emitted text is authoritative when the builder has published its stats
        sources_ok=emitted.get("sources_total") or len(ok),
        chars=emitted.get("chars_total") or sum(r["chars"] for r in ok if isinstance(r["chars"], int)),
        records=emitted.get("records"),
        languages=len((emitted.get("chars_by_lang") or {})) or len({r["lang"] for r in ok}),
        traditions=len((emitted.get("chars_by_tradition") or {})) or len({r["tradition"] for r in ok}),
        excluded=len(rows) - len(ok),
        licence_dom=sum(1 for r in ok if str(r["licence"]).lower().startswith("public domain")),
        licence_ccby=sum(1 for r in ok if "CC-BY" in str(r["licence"]).upper()),
    )


def load_eval():
    d = _json(os.path.join(ROOT, "eval", "report.json"))
    # A fixture-flagged report is preliminary by its own admission; never publish its numbers.
    if isinstance(d, dict) and d.get("fixture"):
        return None
    return d


def load_metrics():
    paths = sorted(glob.glob(os.path.join(ROOT, "training", "runs", "*", "metrics.json")),
                   key=os.path.getmtime, reverse=True)
    if not paths:
        return None
    m = _json(paths[0])
    # An unfinished run's final_* fields are the loss at initialisation, not a result.
    if isinstance(m, dict) and not m.get("completed"):
        # An unfinished run has no final losses and its tokens_seen is one step's worth — quoting either
        # would be a fabricated result. Only the architecture counts are safe from an incomplete run.
        for k in ("final_train_loss", "final_val_loss", "val_ppl", "bits_per_byte", "tokens_seen"):
            m.pop(k, None)
    return m


def load_candidates():
    for p in (os.path.join(ROOT, "artifacts", "drug_candidates.json"),
              os.path.join(ROOT, "app", "data", "drug_candidates.json")):
        d = _json(p)
        if isinstance(d, dict) and d.get("candidates") and not d.get("fixture"):
            return d
    return None


def load_hypotheses():
    for p in (os.path.join(ROOT, "app", "data", "hypotheses.json"),):
        d = _json(p)
        if isinstance(d, dict) and d.get("hypotheses") and not d.get("fixture"):
            return d
    return None


# --------------------------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------------------------
def n(x):
    """Format an integer, or propagate None — a missing number must never render as the string "None"."""
    if x is None:
        return None
    return f"{x:,}" if isinstance(x, int) else str(x)


def pct(x):
    if x is None:
        return None
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else str(x)


def f3(x):
    if x is None:
        return None
    return f"{x:.3f}" if isinstance(x, (int, float)) else str(x)


def verdict(metric, value, p, auc_thresh=0.60, rho_thresh=0.15, alpha=0.05):
    if not isinstance(value, (int, float)) or not isinstance(p, (int, float)):
        return None
    above = value >= auc_thresh if metric == "auc" else abs(value) >= rho_thresh
    if above and p < alpha:
        return "predicts above chance"
    if above:
        return "trend, not significant"
    return "no predictive signal"


def resolve():
    """name -> formatted value. Only values that genuinely exist on disk."""
    out: dict = {}
    corpus = load_corpus_stats()
    ev = load_eval()
    mx = load_metrics()
    cands = load_candidates()
    hyps = load_hypotheses()

    if corpus:
        out["corpus.sources_ok"] = n(corpus["sources_ok"])
        out["corpus.excluded"] = n(corpus["excluded"])
        out["corpus.chars"] = f"{corpus['chars']:,}"
        out["corpus.languages"] = n(corpus["languages"])
        out["corpus.traditions"] = n(corpus["traditions"])
        out["corpus.licence_dom"] = n(corpus["licence_dom"])
        out["corpus.licence_ccby"] = n(corpus["licence_ccby"])

    if mx:
        out["model.mini_params"] = n(mx.get("params"))
        out["model.steps"] = n(mx.get("steps_completed", mx.get("steps")))
        out["model.tokens"] = n(mx.get("tokens_seen"))
        out["model.final_train_loss"] = f3(mx.get("final_train_loss"))
        out["model.final_val_loss"] = f3(mx.get("final_val_loss"))
        out["model.val_ppl"] = f"{mx['val_ppl']:.1f}" if isinstance(mx.get("val_ppl"), (int, float)) else None
        out["model.bits_per_byte"] = f"{mx['bits_per_byte']:.2f}" if isinstance(mx.get("bits_per_byte"), (int, float)) else None

    if ev:
        dd = ev.get("drug_discovery") or {}
        tp = dd.get("theory_predictivity") or {}
        for key, entry in tp.items():
            if not isinstance(entry, dict):
                continue
            met = (entry.get("metric") or "").lower()
            val, p = entry.get("value"), entry.get("p")
            if isinstance(val, (int, float)):
                out[f"theory.{key}_value"] = f3(val)
                out[f"theory.{key}"] = f3(val)
            if isinstance(p, (int, float)):
                out[f"theory.{key}_p"] = f"{p:.3f}"
            nn = entry.get("n")
            if isinstance(nn, int):
                out[f"eval.n_{key}"] = n(nn)
            v = verdict(met, val, p)
            if v:
                out[f"theory.{key}_verdict"] = v
        for k in ("candidates", "mean_novelty", "lipinski_pass_rate"):
            if dd.get(k) is not None:
                target = {"candidates": "candidates.count", "mean_novelty": "eval.mean_candidate_novelty",
                          "lipinski_pass_rate": "eval.lipinski_pass_rate"}[k]
                out[target] = f3(dd[k]) if isinstance(dd[k], float) else n(dd[k])
        nc = ev.get("negative_controls") or {}
        qx = nc.get("quxiangbilei") or {}
        if isinstance(qx.get("rho"), (int, float)):
            out["eval.quxiangbilei_rho"] = f3(qx["rho"])
        if isinstance(qx.get("p"), (int, float)):
            out["eval.quxiangbilei_p"] = f"{qx['p']:.3f}"
        if isinstance(qx.get("n"), int):
            out["eval.quxiangbilei_n"] = n(qx["n"])
        nm = nc.get("null_model") or {}
        if isinstance(nm.get("score_drop"), (int, float)):
            out["eval.null_model_drop"] = f3(nm["score_drop"])
        for k in ("grounded_answer_rate", "citation_fidelity", "correct_refusal_rate",
                  "over_refusal_rate", "policy_screen_recall", "policy_screen_precision"):
            blk = ev.get("refusal_benchmark") or {}
            if blk.get(k) is not None:
                out[f"eval.{k}"] = pct(blk[k])
        abl = ev.get("ablations") or {}
        for k, v in abl.items():
            out[f"ablation.{k}"] = str(v)

    if cands:
        cs = cands["candidates"]
        out["candidates.count"] = n(len(cs))
        out["candidates.resolved"] = n(sum(1 for c in cs if c.get("smiles")))

    if hyps:
        out["hypotheses.count"] = n(len(hyps["hypotheses"]))

    # computed directly from the workbench assets
    static = os.path.join(ROOT, "app", "static")
    if os.path.isdir(static):
        total = sum(os.path.getsize(os.path.join(static, f)) for f in os.listdir(static))
        out["app.bytes"] = n(total // 1024)

    return {k: v for k, v in out.items() if v not in (None, "")}


# --------------------------------------------------------------------------------------------
# rewriting
# --------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Fill [[PENDING: name]] placeholders from repository artefacts")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if anything remains unresolved (read-only: implies --dry-run)")
    args = ap.parse_args(argv)
    if args.check:
        args.dry_run = True  # --check is a query, not a mutation

    values = resolve()
    filled_total, remaining_total = 0, 0
    unresolved: dict = {}

    for rel in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        stats = {"filled": 0, "left": 0}

        def sub(m):
            name = m.group(1).strip()
            if name in values:
                stats["filled"] += 1
                return values[name]
            stats["left"] += 1
            unresolved.setdefault(name, []).append(rel)
            return m.group(0)

        new = TOKEN.sub(sub, text)
        filled_total += stats["filled"]
        remaining_total += stats["left"]
        if new != text and not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
        if stats["filled"] or stats["left"]:
            print(f"  {rel:<34} filled {stats['filled']:>3} · left {stats['left']:>3}"
                  f"{'  (dry run)' if args.dry_run else ''}")

    print(f"\n  resolved values available: {len(values)}")
    if unresolved:
        print(f"  still owed: {len(unresolved)} distinct names across {len(set(sum(unresolved.values(), [])))} files")
        for name in sorted(unresolved):
            print(f"    · {name:<32} {', '.join(sorted(set(unresolved[name])))}")
    else:
        print("  nothing outstanding")

    if args.check and unresolved:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
