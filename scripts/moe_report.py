#!/usr/bin/env python3
"""Does the sparse MoE actually buy anything here? Measure, don't assert.

Produces `artifacts/moe_diagnostics.json` with three things:

1. **Dense vs MoE at matched token budget** — params (total + active), tokens seen, val loss, bits/byte,
   wall clock, tokens/s. The comparison is only meaningful at matched tokens, so it reads both runs'
   `metrics.json` and states the token counts next to the deltas.
2. **Expert↔language routing** — for Classical Chinese, Sanskrit, Latin and English samples drawn from
   the real corpus, which experts receive the tokens, and the Jensen–Shannon distance between those
   routing distributions. If the JS distance is large, the router independently rediscovered the
   script/tradition structure; if it is near zero, it did not, and we say so.
3. **Load balance** — per-expert usage share. A dead expert (share ≈ 0) means routing collapsed.

Usage:
    python scripts/moe_report.py --moe training/runs/shennong-moe-r1/ckpt-best.pt
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from shennong_moe import MoEConfig, ShennongMoE, expert_language_report  # noqa: E402
from shennong_mini import load_checkpoint  # noqa: E402


def load_metrics(run_dir: Path) -> dict | None:
    p = run_dir / "metrics.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def summarise(run_dir: Path) -> dict | None:
    m = load_metrics(run_dir)
    if not m:
        return None
    return {
        "run_id": m.get("run_id"),
        "model_family": m.get("model_family", "dense"),
        "params": m.get("params"),
        "active_params": m.get("active_params"),
        "tokens_seen": m.get("tokens_seen"),
        "steps": m.get("steps_completed"),
        "final_train_loss": m.get("final_train_loss"),
        "final_val_loss": m.get("final_val_loss"),
        "val_ppl": m.get("val_ppl"),
        "bits_per_byte": m.get("bits_per_byte"),
        "wall_clock_s": m.get("wall_clock_s"),
        "tokens_per_s": m.get("tokens_per_s"),
        "completed": m.get("completed"),
    }


def sample_texts(n_per_lang: int = 10) -> dict[str, list[str]]:
    """Pull held-out-ish samples per language straight from the processed corpus."""
    out: dict[str, list[str]] = {}
    path = ROOT / "corpus" / "processed" / "corpus.jsonl"
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            lang, text = rec.get("lang"), rec.get("text") or ""
            if lang and len(text) > 400:
                bucket = out.setdefault(lang, [])
                if len(bucket) < n_per_lang:
                    bucket.append(text[:2000])
            if all(len(v) >= n_per_lang for v in out.values()) and len(out) >= 4:
                break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--moe", default="training/runs/shennong-moe-r1/ckpt-best.pt")
    ap.add_argument("--dense", default="training/runs/shennong-mini-r1/metrics.json")
    ap.add_argument("--out", default="artifacts/moe_diagnostics.json")
    args = ap.parse_args()

    from tokenizers import Tokenizer

    ck_path = ROOT / args.moe
    if not ck_path.exists():
        raise SystemExit(f"no MoE checkpoint at {ck_path} — train it first")
    ck = load_checkpoint(ck_path)
    cfg = MoEConfig.from_dict(ck["config"])
    model = ShennongMoE(cfg)
    missing, unexpected = model.load_state_dict(ck["model"], strict=False)
    if missing or unexpected:
        print(f"note: load_state_dict missing={missing[:3]} unexpected={unexpected[:3]}")
    n = model.num_parameters()

    tok = Tokenizer.from_file(str(ROOT / "tokenizer/shennong-bpe/tokenizer.json"))

    samples = sample_texts()
    diag = expert_language_report(model, tok, samples)
    usage = diag["usage_share"]
    shares = {lang: v for lang, v in usage.items()}
    dead = [i for i in range(cfg.n_experts)
            if max((s[i] for s in shares.values()), default=0.0) < 0.02]

    moe_metrics = summarise(ck_path.parent)
    dense_metrics = None
    dp = ROOT / args.dense
    if dp.exists():
        dense_dir = dp.parent if dp.name == "metrics.json" else dp
        dense_metrics = summarise(dense_dir)

    out = {
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model": {
            "checkpoint": str(ck_path.relative_to(ROOT)),
            "step": ck.get("step"),
            "n_experts": cfg.n_experts,
            "top_k": cfg.top_k,
            "params_total": n,
            "params_active_per_token": cfg.n_params_active,
            "params_counted": sum(p.numel() for p in model.parameters()),
        },
        "comparison": {
            "note": "Only compare at matched tokens seen; the token counts are printed beside each "
                    "delta. This corpus snapshot is larger than the dense run's, so epochs differ.",
            "moe": moe_metrics,
            "dense": dense_metrics,
            "delta": None if not (moe_metrics and dense_metrics) else {
                "params_ratio": round((moe_metrics["params"] or 0) / max(1, dense_metrics["params"]), 3),
                "active_params_ratio": round((moe_metrics["active_params"] or moe_metrics["params"] or 0)
                                             / max(1, dense_metrics["params"]), 3),
                "tokens_seen_ratio": round((moe_metrics["tokens_seen"] or 0)
                                           / max(1, dense_metrics["tokens_seen"] or 1), 3),
                "val_loss_delta": None if not (moe_metrics["final_val_loss"] and dense_metrics["final_val_loss"])
                                  else round(moe_metrics["final_val_loss"] - dense_metrics["final_val_loss"], 4),
                "tokens_per_s_ratio": None if not (moe_metrics["tokens_per_s"] and dense_metrics["tokens_per_s"])
                                      else round(moe_metrics["tokens_per_s"] / dense_metrics["tokens_per_s"], 3),
            },
        },
        "routing": diag,
        "load_balance": {
            "dead_experts": dead,
            "mean_usage_share": [round(sum(s[i] for s in shares.values()) / max(1, len(shares)), 4)
                                 for i in range(cfg.n_experts)] if shares else [],
            "verdict": ("balanced" if not dead else f"collapsed: experts {dead} receive < 2% of tokens"),
        },
        "honest_reading": (
            "MoE buys capacity at equal per-token FFN compute, not at equal wall-clock on a CPU. "
            "Whether it wins here is read off val_loss_delta at a comparable tokens_seen — and if the "
            "routing JS distances are near zero, the experts are not specialising by language at all."
        ),
    }
    outp = ROOT / args.out
    outp.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out["comparison"]["delta"], indent=2))
    print(json.dumps(out["load_balance"], indent=2))
    print("routing JS distances:", json.dumps(diag["pairwise_js_distance"], indent=2))
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
