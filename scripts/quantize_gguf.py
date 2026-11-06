#!/usr/bin/env python3
"""Convert a HF fine-tuned Qwen2.5-0.5B into a Q4_K_M GGUF, reproducibly.

The path that produced the released `shennong-0.5b-sft-Q4_K_M.gguf`:

    1. HF model dir  (tomscot/shennong-0.5b-sft, or training/runs/gpu-sft/merged)
    2. llama.cpp convert_hf_to_gguf.py --outtype f16
    3. llama-cpp-python llama_model_quantize, ftype Q4_K_M

Two gotchas found while doing it, both recorded so they are not re-learned:

  * llama.cpp's Qwen2 converter calls the sentencepiece path first and imports `sentencepiece` before
    checking for tokenizer.model — so a BPE Qwen2 model still needs sentencepiece installed, or the
    converter must be patched to check the file first. The patch (reorder the file check before the import)
    is in the release notes; the model itself is BPE (tokenizer.json) and never uses sentencepiece.
  * Qwen2.5-0.5B has d_model=896, which is not divisible by 256, so Q4_K falls back to q5_0/q6_K/q8_0 for
    144 of 290 tensors. The result is ~6.35 BPW and ~380 MB, not the ~4.5 BPW a clean Q4 would give. That
    is fine and correct; do not fight it.

    python scripts/quantize_gguf.py --hf-dir training/runs/gpu-sft/hf
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LLAMACPP = pathlib.Path("/tmp/llamacpp")  # clone it once: git clone --depth 1 https://github.com/ggml-org/llama.cpp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf-dir", default="training/runs/gpu-sft/hf")
    ap.add_argument("--out", default="artifacts/shennong-0.5b-sft-Q4_K_M.gguf")
    args = ap.parse_args()

    hf = ROOT / args.hf_dir
    f16 = hf.with_suffix(".f16.gguf")
    if not f16.exists():
        if not LLAMACPP.exists():
            subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp",
                            str(LLAMACPP)], check=True)
        subprocess.run([sys.executable, str(LLAMACPP / "convert_hf_to_gguf.py"), str(hf),
                        "--outfile", str(f16), "--outtype", "f16"], check=True)

    import llama_cpp.llama_cpp as lc
    params = lc.llama_model_quantize_default_params()
    params.ftype = lc.LLAMA_FTYPE_MOSTLY_Q4_K_M
    params.nthread = 4
    rc = lc.llama_model_quantize(str(f16).encode(), str(ROOT / args.out).encode(), params)
    print(f"quantize rc={rc} -> {ROOT / args.out}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
