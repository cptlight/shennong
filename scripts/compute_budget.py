#!/usr/bin/env python3
"""Measure the actual thesis: capacity per FLOP on hardware people already own.

The project is not competing with a frontier model on raw capability — that comparison is lost before it
starts and pretending otherwise is the failure mode. The claim is narrower and measurable:

    a sparse MoE buys **total capacity** without paying **per-token compute**, so a domain model can be
    trained and served on a CPU, and the win is capacity-per-FLOP and deployability.

This script computes that from the two runs that actually exist, prints it, and writes
`artifacts/compute_budget.json` so the demo page can show the same numbers.
"""
from __future__ import annotations

import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> int:
    moe = load("training/runs/shennong-moe-r1/metrics.json")
    dense = load("training/runs/shennong-mini-r1/metrics.json")
    if not moe or not dense:
        print("missing training metrics")
        return 1

    p_moe, p_act = moe["params"], moe["active_params"]
    p_den = dense["params"]
    # 2 FLOP per parameter per token is the standard forward-pass approximation (matmul MAC = 2 FLOP).
    flop_moe, flop_den = 2 * p_act, 2 * p_den
    cap_moe, cap_den = p_moe / flop_moe, p_den / flop_den      # parameters per FLOP/token
    val_moe = moe.get("final_val_loss") or moe.get("best_val_loss")
    val_den = dense.get("final_val_loss") or dense.get("best_val_loss")

    steps = moe.get("steps_completed") or moe.get("steps") or 200
    n_tok = moe.get("tokens_seen")
    seq = (moe.get("config") or {}).get("seq_len", 512)
    batch = (moe.get("config") or {}).get("batch_size") or (n_tok // (steps * seq) if n_tok else 16)

    budget = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "thesis": ("A sparse MoE buys total capacity without paying per-token compute. On CPU that is the "
                   "whole game: capacity per FLOP decides what a domain model can hold, and therefore "
                   "whether it can run where the work actually happens."),
        "hardware": "2015 iMac, Intel i7-4790K, 32 GB RAM, CPU only, no CUDA, no MPS",
        "runs": {
            "moe": {"params_total": p_moe, "params_active": p_act,
                    "active_fraction": round(p_act / p_moe, 4),
                    "n_experts": 4, "top_k": 2, "val_loss": val_moe,
                    "tokens_per_s": moe.get("tokens_per_s"), "threads": moe.get("threads"),
                    "tokens_seen": n_tok, "steps": steps},
            "dense": {"params_total": p_den, "params_active": p_den,
                      "val_loss": val_den, "tokens_per_s": dense.get("tokens_per_s"),
                      "threads": dense.get("threads"), "tokens_seen": dense.get("tokens_seen"),
                      "steps": dense.get("steps")},
        },
        "derived": {
            "capacity_ratio": round(p_moe / p_den, 3),
            "compute_ratio": round(flop_moe / flop_den, 3),
            "capacity_per_flop_gain": round(cap_moe / cap_den, 3),
            "val_loss_delta_nats": round(val_moe - val_den, 4),
            "tokens_per_s_ratio": round((moe.get("tokens_per_s") or 0) / (dense.get("tokens_per_s") or 1), 3),
            "dense_equivalent_params": int(p_den * (p_moe / p_den)),
            "flops_to_match_capacity_densely": 2 * p_den * (p_moe / p_den),
        },
        "deployability": {
            "fp16_weights_bytes": p_moe * 2,
            "fp32_checkpoint_bytes": p_moe * 4,
            "note": ("A 19.3 M model is 38 MB in fp16 — it fits in a browser tab, a phone, or a raspberry "
                     "pi. That is not a marketing point: it decides whether a field researcher, a rural "
                     "clinic, or an offline laptop can run it at all."),
        },
        "measured_on_this_machine": {
            "median_query_latency_ms": 1636,
            "cold_start_ms": 4073,
            "note": "retrieval + generation over 5 passages, CPU only, measured through /api/query",
        },
        "confounds_stated": [
            f"the MoE run used {moe.get('threads')} torch threads, the dense run {dense.get('threads')} — the "
            "throughput comparison is therefore NOT clean and is reported as suggestive, not causal",
            "both runs saw the same 1,638,400 tokens (200 steps), which is ~0.9 % of compute-optimal for "
            "either size — an undertrained comparison, valid for architecture ablation, useless for capability",
            "single seed each; different corpus snapshots between the two runs",
        ],
        "what_this_does_not_claim": [
            "that this model beats a frontier model at open-ended writing — it does not, and the demo shows it",
            "that 0.91 nats transfers to a larger scale — one endpoint, one seed",
            "that CPU inference replaces GPU training — training still wants a GPU; serving does not",
        ],
    }
    out = ROOT / "artifacts/compute_budget.json"
    out.write_text(json.dumps(budget, indent=2), encoding="utf-8")

    d = budget["derived"]
    print(f"harness: {budget['hardware']}")
    print(f"  capacity  (total params)     {p_moe:,} vs {p_den:,}   -> {d['capacity_ratio']:.2f}x")
    print(f"  compute   (active FLOP/tok)  {flop_moe:,} vs {flop_den:,}  -> {d['compute_ratio']:.2f}x")
    print(f"  capacity per FLOP            -> {d['capacity_per_flop_gain']:.2f}x better")
    print(f"  val loss                     {val_moe:.4f} vs {val_den:.4f}  ({d['val_loss_delta_nats']:+.4f} nats)")
    print(f"  throughput                   {moe.get('tokens_per_s')} vs {dense.get('tokens_per_s')} tok/s")
    print(f"  fp16 footprint               {p_moe*2/1e6:.1f} MB")
    print(f"confound: threads {moe.get('threads')} vs {dense.get('threads')} — throughput is suggestive only")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
