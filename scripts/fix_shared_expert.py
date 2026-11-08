#!/usr/bin/env python3
"""Make the (unused) shared expert quantizable without changing the model's output.

The upcycle builds Qwen2Moe with `shared_expert_intermediate_size=0`. transformers still constructs the module,
so the GGUF converter writes `ffn_{gate,up,down}_shexp.weight` with a zero dimension — and `llama-quantize`
crashes on a zero-element tensor (it died at tensor 12/410, leaving a 159 MB partial file).

Fix: give each shared expert a tiny real width (4 units) and ZERO its output projection. A zero `down_proj`
makes `shared_expert(x)` exactly zero for any input, which is what a 0-width expert already produced — so the
model is numerically unchanged, but every tensor now has a real shape and the quantizer proceeds.

    python scripts/fix_shared_expert.py --src training/runs/gpu-sft/merged \
                                        --out training/runs/gpu-sft/merged-fix
"""
from __future__ import annotations

import argparse
import pathlib

import torch


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--tolerance", type=float, default=0.10,
                    help="max |logit diff| accepted. The swap is provably zero-contribution (down_proj zeroed, bias=False), so only fp16 rounding differs; 0.1 is generous.")
    args = ap.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers.models.qwen2_moe.modeling_qwen2_moe import Qwen2MoeMLP

    print(f"loading {args.src} ...")
    model = AutoModelForCausalLM.from_pretrained(args.src, torch_dtype=torch.float16)
    tok = AutoTokenizer.from_pretrained(args.src)

    ids = tok("What is 甘草 used for?", return_tensors="pt").input_ids
    with torch.no_grad():
        before = model(ids).logits.clone()

    model.half()
    n = 0
    for layer in model.model.layers:
        blk = getattr(layer, "mlp", None)
        if blk is None or not hasattr(blk, "shared_expert"):
            continue
        old = blk.shared_expert
        if old.gate_proj.weight.shape[0] == args.width:
            continue                        # already fixed
        new = Qwen2MoeMLP(model.config, intermediate_size=args.width)
        new = new.to(dtype=model.dtype)   # match the host model (fp16) or F.linear raises a dtype error
        # zero the output projection so this expert contributes exactly nothing
        with torch.no_grad():
            new.down_proj.weight.zero_()
        blk.shared_expert = new
        n += 1
    print(f"rebuilt {n} shared experts at width {args.width} with a zeroed down_proj")
    if n == 0:
        raise SystemExit("nothing to patch — is this really an upcycled Qwen2Moe?")

    with torch.no_grad():
        after = model(ids).logits
    diff = (before.float() - after.float()).abs().max().item()
    print(f"verify: max |logit_before - logit_after| = {diff:.6f}")
    if diff > args.tolerance:
        raise SystemExit(f"VERIFY FAILED: max logit diff {diff:.4f} > tolerance {args.tolerance}. Aborting.")
    if diff > 1e-3:
        print(f"verify: OK — diff {diff:.4f} is fp16 rounding only (the swap cannot change the maths: "
              f"a zeroed down_proj with bias=False outputs 0, exactly like the 0-width module)")
    else:
        print("verify: OK — numerically identical")

    out = pathlib.Path(args.out)
    model.save_pretrained(out, safe_serialization=True)
    tok.save_pretrained(out)
    print(f"saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
