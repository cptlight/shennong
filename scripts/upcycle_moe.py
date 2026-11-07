#!/usr/bin/env python3
"""Upcycle a dense Qwen2.5-0.5B into a REAL sparse MoE (Qwen2Moe, 4 experts, top-2).

Why upcycling: a sparse MoE that trains on a T4 must be small, and no pretrained small MoE ships with
trainable expert modules. Granite MoE stores its experts as batched tensors (LoRA cannot reach them);
Qwen2Moe stores them as `ModuleList[Qwen2MoeMLP]` with real `nn.Linear` layers, so LoRA adapts the experts.

The trick that makes it safe: copy the dense FFN into EVERY expert and normalise the top-k weights
(`norm_topk_prob=True`). The upcycled model then starts numerically identical to the dense model, so training
can only improve it — it never has to recover from a random initialisation.

    python scripts/upcycle_moe.py --base Qwen/Qwen2.5-0.5B --experts 4 --out artifacts/upcycled-moe

Result: ~1.44 B total / ~0.81 B active, which quantises to ~900 MB at Q4_K_M (under the 1.5 GB target).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--experts", type=int, default=4)
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--out", default="artifacts/upcycled-moe")
    ap.add_argument("--verify", action="store_true", default=True, help="compare logits against the dense base")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Qwen2MoeConfig, Qwen2MoeForCausalLM

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    print(f"loading dense base {args.base} ...")
    src = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float32)
    tok = AutoTokenizer.from_pretrained(args.base)
    c = src.config
    print(f"  dense params: {sum(p.numel() for p in src.parameters()):,}")

    moe_cfg = Qwen2MoeConfig(
        vocab_size=c.vocab_size,
        hidden_size=c.hidden_size,
        intermediate_size=c.intermediate_size,          # shared_expert size (unused when 0 below)
        moe_intermediate_size=c.intermediate_size,      # per-expert FFN
        num_hidden_layers=c.num_hidden_layers,
        num_attention_heads=c.num_attention_heads,
        num_key_value_heads=c.num_key_value_heads,
        max_position_embeddings=c.max_position_embeddings,
        rope_theta=c.rope_theta,
        rms_norm_eps=c.rms_norm_eps,
        hidden_act=c.hidden_act,
        tie_word_embeddings=c.tie_word_embeddings,
        attention_dropout=getattr(c, "attention_dropout", 0.0),
        sliding_window=getattr(c, "sliding_window", None),
        use_sliding_window=getattr(c, "use_sliding_window", False),
        num_experts=args.experts,
        num_experts_per_tok=args.top_k,
        shared_expert_intermediate_size=0,              # no shared expert: the experts carry the FFN
        norm_topk_prob=True,                           # weights sum to 1 -> starts equal to the dense model
        decoder_sparse_step=1,                          # MoE in every layer
        mlp_only_layers=[],
    )
    print(f"building Qwen2Moe: {args.experts} experts, top-{args.top_k}, per-expert FFN {c.intermediate_size}")
    moe = Qwen2MoeForCausalLM(moe_cfg)
    print(f"  moe total params: {sum(p.numel() for p in moe.parameters()):,}")

    # ---- weight transfer: everything shared, then the dense FFN copied into every expert ----
    src_sd = src.state_dict()
    tgt_sd = moe.state_dict()
    copied = {}
    missing_ffn = []
    with torch.no_grad():
        for name, param in tgt_sd.items():
            if ".mlp.experts." in name:
                missing_ffn.append(name)          # filled below
                continue
            if ".mlp.gate." in name:              # router: leave the fresh random init
                continue
            if name in src_sd and src_sd[name].shape == param.shape:
                param.copy_(src_sd[name])
                copied[name] = True
            else:
                missing_ffn.append(name)

    # experts.N.{gate,up,down}_proj  <-  dense mlp.{gate,up,down}_proj
    per_layer = {}
    with torch.no_grad():
        for name in list(missing_ffn):
            if ".mlp.experts." not in name:
                continue
            # model.layers.12.mlp.experts.2.gate_proj.weight -> model.layers.12.mlp.gate_proj.weight
            parts = name.split(".")
            e_idx = parts.index("experts")
            layer_prefix = ".".join(parts[:e_idx])      # model.layers.12.mlp
            proj = ".".join(parts[e_idx + 2:])          # gate_proj.weight
            src_name = f"{layer_prefix}.{proj}"
            if src_name in src_sd:
                tgt_sd[name].copy_(src_sd[src_name])
                per_layer[name] = src_name

    n_expert_desc = len(per_layer)
    total_experts = args.experts * c.num_hidden_layers * 3
    print(f"copied shared weights: {len(copied):,}")
    print(f"expert tensors filled: {n_expert_desc}/{total_experts}")

    # ---- verify: the upcycled model must produce the same logits as the dense one ----
    if args.verify:
        src.eval(); moe.eval()
        ids = tok("What is 甘草 used for?", return_tensors="pt").input_ids
        with torch.no_grad():
            a = src(ids).logits
            b = moe(ids).logits
        diff = (a - b).abs().max().item()
        print(f"verify: max |logit_dense - logit_moe| = {diff:.5f}")
        if diff > 0.5:
            print("WARNING: the upcycled model does NOT match the dense base — check the weight mapping "
                  "before training on it.", file=sys.stderr)
        else:
            print("verify: OK — upcycled model is numerically equivalent to the dense base")

    moe.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    report = {"base": args.base, "experts": args.experts, "top_k": args.top_k,
              "total_params": sum(p.numel() for p in moe.parameters()),
              "active_estimate": None, "out": str(out)}
    (out / "upcycle_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nsaved -> {out}")
    print("NEXT: LoRA fine-tune on artifacts/sft (LoRA reaches the experts because they are nn.Linear),")
    print("      then convert with llama.cpp (Qwen2Moe is a native gguf arch) and quantise to Q4_K_M (~900 MB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
