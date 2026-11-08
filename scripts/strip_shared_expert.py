#!/usr/bin/env python3
"""Remove the zero-size shared-expert modules from an upcycled Qwen2Moe model.

Why: transformers always constructs `Qwen2MoeSparseMoeBlock.shared_expert` with
`intermediate_size=config.shared_expert_intermediate_size`. With that set to 0 (our upcycle uses no shared
expert), the modules exist with 0 hidden units, so
`convert_hf_to_gguf.py` writes `ffn_*_shexp.weight` tensors of shape [0, 896] — and `llama-quantize`
segfaults/crashes on a zero-element tensor (it died at tensor 12 of 410).

Dropping the modules is numerically a no-op: a 0-wide MLP outputs zeros, so skipping it changes nothing.
Verified by comparing logits before and after.

    python scripts/strip_shared_expert.py --src training/runs/gpu-sft/merged \
                                          --out training/runs/gpu-sft/merged-clean
"""
from __future__ import annotations

import argparse
import pathlib
import types

import torch


def patch_block(blk):
    """Forward without the (zero-width) shared expert."""

    def forward(self, hidden_states):
        residuals = hidden_states
        orig_shape = hidden_states.shape
        router_logits = self.gate(hidden_states)
        final_hidden_states = self.experts(hidden_states, router_logits)
        return final_hidden_states.view(orig_shape), router_logits

    blk.forward = types.MethodType(forward, blk)
    for attr in ("shared_expert", "shared_expert_gate"):
        if hasattr(blk, attr):
            delattr(blk, attr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", action="store_true", default=True)
    args = ap.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"loading {args.src} ...")
    model = AutoModelForCausalLM.from_pretrained(args.src, torch_dtype=torch.float32)
    tok = AutoTokenizer.from_pretrained(args.src)

    n_patched = 0
    before = None
    if args.verify:
        ids = tok("What is 甘草 used for?", return_tensors="pt").input_ids
        with torch.no_grad():
            before = model(ids).logits.clone()

    for layer in model.model.layers:
        blk = getattr(layer, "mlp", None)
        if blk is not None and hasattr(blk, "shared_expert"):
            patch_block(blk)
            n_patched += 1
    print(f"patched {n_patched} MoE blocks (shared expert removed)")

    if args.verify and before is not None:
        with torch.no_grad():
            after = model(ids).logits
        diff = (before - after).abs().max().item()
        print(f"verify: max |logit_before - logit_after| = {diff:.6f}")
        if diff > 1e-3:
            raise SystemExit("VERIFY FAILED: removing the shared expert changed the output — aborting.")
        print("verify: OK — numerically identical, safe to convert")

    out = pathlib.Path(args.out)
    model.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    print(f"saved -> {out}")
    print("NEXT: convert_hf_to_gguf.py on this dir — it will emit no zero-size tensors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
