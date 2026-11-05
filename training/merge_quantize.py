"""Merge a LoRA adapter into base weights, then produce the shipping GGUF (quantised).

This is the merge + quantise stage of the flagship path:

    base checkpoint / HF dir  +  lora_adapter.pt  ->  merged HF dir  ->  GGUF f16
                                                                     ->  GGUF Q4_K_M

LoRA adapter format produced by `training/sft_lora.py`:
    {"lora": {"<native param name>": {"A": Tensor[r, d_in], "B": Tensor[d_out, r]}, ...},
     "rank": r, "alpha": a, "base_config": {...}}
Merge rule (Hu et al. 2021, arXiv:2106.09685):  W' = W + (alpha / rank) * B @ A.

Quantisation is delegated to llama.cpp's `llama-quantize` binary. **If that binary is not
built, this script does not pretend a quantised file exists**: it writes the f16 GGUF (if asked),
prints the exact quantise command and exits non-zero for that stage. Never claim a Q4 file you
did not produce.

Usage
-----
    # merge only
    python training/merge_quantize.py --base training/runs/shennong-0.5b-cpt/ckpt-best.pt \
        --lora training/runs/shennong-0.5b-lora/lora_adapter.pt \
        --out artifacts/shennong-0.5b-hf --tokenizer artifacts/qwen2.5-0.5b-base

    # merge + f16 GGUF + Q4_K_M
    python training/merge_quantize.py ... --gguf-out artifacts/shennong-0.5b-f16.gguf \
        --quantize Q4_K_M --quantized-out artifacts/shennong-0.5b-q4_k_m.gguf
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "model" / "export"))

from shennong_mini import ModelConfig, ShennongMini  # noqa: E402


# ---------------------------------------------------------------------------------------
# LoRA merge
# ---------------------------------------------------------------------------------------
def apply_lora(model: ShennongMini, adapter: dict, verbose: bool = True) -> dict:
    lora = adapter.get("lora") or adapter.get("state_dict") or {}
    rank = int(adapter.get("rank", 0))
    alpha = float(adapter.get("alpha", rank))
    scale = alpha / max(rank, 1)
    params = dict(model.named_parameters())
    merged, skipped = [], []
    with torch.no_grad():
        for name, entry in lora.items():
            key = name[:-7] if name.endswith(".weight") else name  # tolerate "...weight" keys
            base_key = key if key in params else (key + ".weight" if key + ".weight" in params else None)
            if base_key is None:
                skipped.append(name)
                continue
            A = entry["A"].to(torch.float32)
            B = entry["B"].to(torch.float32)
            delta = (B @ A) * scale
            if delta.shape != params[base_key].shape:
                raise RuntimeError(f"{name}: delta {tuple(delta.shape)} != weight "
                                   f"{tuple(params[base_key].shape)}")
            params[base_key].add_(delta.to(params[base_key].dtype))
            merged.append(base_key)
    if verbose:
        print(f"merged {len(merged)} LoRA matrices (rank={rank}, alpha={alpha}, scale={scale:.4f}); "
              f"skipped {len(skipped)}: {skipped[:5]}")
    if not merged:
        raise SystemExit("no LoRA matrices matched the base model — wrong adapter or base?")
    return {"merged": merged, "rank": rank, "alpha": alpha, "scale": scale, "skipped": skipped}


def load_base(base: Path) -> ShennongMini:
    """Load a base model from a training checkpoint or from a HF-format directory."""
    if base.is_dir():
        from to_hf import load_hf_model

        return load_hf_model(base)
    ck = torch.load(base, map_location="cpu")
    cfg = ModelConfig.from_dict(ck["config"])
    model = ShennongMini(cfg)
    model.load_state_dict(ck["model"], strict=False)
    return model


# ---------------------------------------------------------------------------------------
# Quantisation
# ---------------------------------------------------------------------------------------
def find_quantize_binary(explicit: str = "") -> Path | None:
    candidates = [
        Path(explicit) if explicit else None,
        ROOT / ".tmp" / "llama.cpp" / "build" / "bin" / "llama-quantize",
        ROOT / ".tmp" / "llama.cpp" / "build" / "bin" / "release" / "llama-quantize",
        Path(shutil.which("llama-quantize") or ""),
    ]
    for c in candidates:
        if c and Path(c).exists() and Path(c).is_file():
            return Path(c)
    return None


def quantize(f16_gguf: Path, out: Path, qtype: str, quantize_bin: str = "") -> bool:
    """Run llama-quantize. Returns True only if the output file really exists afterwards."""
    bin_path = find_quantize_binary(quantize_bin)
    if bin_path is None:
        print("\nNo `llama-quantize` binary found — NO quantised file was produced.", file=sys.stderr)
        print("Build it (a few minutes on this CPU):", file=sys.stderr)
        print("  cmake -B .tmp/llama.cpp/build -DCMAKE_BUILD_TYPE=Release .tmp/llama.cpp",
              file=sys.stderr)
        print("  cmake --build .tmp/llama.cpp/build --config Release -j4 --target llama-quantize",
              file=sys.stderr)
        print(f"Then: {bin_path or 'llama-quantize'} {f16_gguf} {out} {qtype}", file=sys.stderr)
        return False
    cmd = [str(bin_path), str(f16_gguf), str(out), qtype]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    exists = out.exists()
    if exists:
        print(f"quantised: {out}  {out.stat().st_size:,} bytes")
    return exists


# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="checkpoint .pt or HF dir of the base model")
    ap.add_argument("--lora", default="", help="lora_adapter.pt (omit for merge-less conversion)")
    ap.add_argument("--out", required=True, help="output HF-format directory")
    ap.add_argument("--tokenizer", default="", help="tokenizer dir to copy into --out")
    ap.add_argument("--gguf-out", default="", help="also write an f16 GGUF here")
    ap.add_argument("--quantize", default="", choices=["", "Q8_0", "Q5_K_M", "Q4_K_M", "Q4_0"],
                    help="quantisation type (needs llama-quantize)")
    ap.add_argument("--quantized-out", default="", help="output path for the quantised GGUF")
    args = ap.parse_args()

    from to_hf import write_hf
    from to_gguf import convert, sha256_file, verify_gguf

    model = load_base(Path(args.base))
    cfg = model.cfg
    print(f"base: {args.base}  {model.num_parameters():,} params")

    merge_info = None
    if args.lora:
        adapter = torch.load(args.lora, map_location="cpu")
        merge_info = apply_lora(model, adapter)

    out = Path(args.out)
    info = write_hf(model, out, args.tokenizer or None)
    print(f"wrote merged HF dir {out}  ({info['bytes']:,} bytes, {info['num_tensors']} tensors)")

    report = {"base": str(args.base), "lora": args.lora or None, "merge": merge_info,
              "hf_dir": str(out), "hf_bytes": info["bytes"], "params": model.num_parameters()}

    if args.gguf_out:
        gg = Path(args.gguf_out)
        gg.parent.mkdir(parents=True, exist_ok=True)
        conv = convert(out, gg, outtype="f16", name=cfg.__dict__.get("name", "shennong"))
        ver = verify_gguf(gg, expected_params=cfg.n_params_estimate, expected_vocab=cfg.vocab_size,
                          hf_dir=out)
        Path(str(gg) + ".sha256").write_text(f"{conv['sha256']}  {gg.name}\n", encoding="utf-8")
        print(f"f16 GGUF: {gg}  {conv['bytes']:,} bytes  sha256={conv['sha256']}")
        print(f"verify ok={ver['ok']}  values_bit_exact={ver['checks'].get('values_bit_exact')}")
        report.update({"gguf_f16": str(gg), "gguf_f16_bytes": conv["bytes"],
                       "gguf_f16_sha256": conv["sha256"], "verify": ver["checks"]})

    exit_code = 0
    if args.quantize:
        if not args.gguf_out:
            print("--quantize needs --gguf-out (quantisation runs on the f16 GGUF)", file=sys.stderr)
            return 2
        qout = Path(args.quantized_out or str(args.gguf_out).replace("f16", args.quantize.lower()))
        ok = quantize(Path(args.gguf_out), qout, args.quantize)
        report["quantized"] = {"path": str(qout), "type": args.quantize, "produced": ok}
        if ok:
            report["quantized"]["bytes"] = qout.stat().st_size
            report["quantized"]["sha256"] = sha256_file(qout)
            Path(str(qout) + ".sha256").write_text(
                f"{report['quantized']['sha256']}  {qout.name}\n", encoding="utf-8")
        else:
            exit_code = 3

    (Path(args.out) / "merge_report.json").write_text(json.dumps(report, indent=2) + "\n",
                                                      encoding="utf-8")
    print("wrote", Path(args.out) / "merge_report.json")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
