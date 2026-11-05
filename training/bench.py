"""Step 0 for SHENNONG: measure CPU throughput *before* choosing the training config.

Everything downstream (token budget, wall-clock, whether bf16 autocast is worth it,
how many threads to use) is decided from this measurement, not from assumptions.

Run:
    .venv/bin/python training/bench.py
Writes:
    training/runs/bench.json
"""

from __future__ import annotations

import json
import os
import platform
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from shennong_mini import ShennongMini, ModelConfig  # noqa: E402

OUT = ROOT / "training" / "runs" / "bench.json"


def matmul_gflops(n: int = 2048, iters: int = 5) -> float:
    a = torch.randn(n, n)
    b = torch.randn(n, n)
    for _ in range(1):
        a @ b
    t0 = time.perf_counter()
    for _ in range(iters):
        a @ b
    dt = (time.perf_counter() - t0) / iters
    return (2 * n**3) / dt / 1e9


def bench_config(cfg: ModelConfig, batch: int, dtype: str, timed: int = 5, warmup: int = 2) -> dict:
    """Time forward+backward+optimizer step at a fixed seq length."""
    torch.manual_seed(0)
    model = ShennongMini(cfg)
    model.train()
    n_params = model.num_parameters()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    x = torch.randint(0, cfg.vocab_size, (batch, cfg.seq_len))
    y = torch.randint(0, cfg.vocab_size, (batch, cfg.seq_len))
    tokens_per_step = batch * cfg.seq_len

    def one_step() -> None:
        opt.zero_grad(set_to_none=True)
        if dtype == "bf16":
            with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
                _, loss = model(x, targets=y)
        else:
            _, loss = model(x, targets=y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    for _ in range(warmup):
        one_step()
    t0 = time.perf_counter()
    for _ in range(timed):
        one_step()
    dt = (time.perf_counter() - t0) / timed
    tokens_per_s = tokens_per_step / dt
    # 6*N*tokens is the standard fwd+bwd FLOPs estimate; attention FLOPs at seq<=512 are ~2% .
    achieved_gflops = 6 * n_params * tokens_per_s / 1e9
    return {
        "config": asdict(cfg),
        "params": n_params,
        "params_non_embedding": model.num_parameters(non_embedding=True),
        "batch": batch,
        "seq_len": cfg.seq_len,
        "dtype": dtype,
        "ms_per_step": round(dt * 1000, 2),
        "tokens_per_s": round(tokens_per_s, 1),
        "achieved_model_gflops": round(achieved_gflops, 2),
        "projected_tokens_in_3h": int(tokens_per_s * 3 * 3600),
    }


def main() -> None:
    torch.set_grad_enabled(True)
    print(f"host: {platform.platform()}  cpu: {platform.processor()}")
    print(f"torch {torch.__version__}  threads={torch.get_num_threads()}  "
          f"interop={torch.get_num_interop_threads()}")

    results: dict = {
        "env": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count_logical": os.cpu_count(),
            "torch": torch.__version__,
            "torch_threads": torch.get_num_threads(),
            "torch_interop_threads": torch.get_num_interop_threads(),
            "python": sys.version.split()[0],
            "cpu_only": True,
        },
        "matmul_gflops": {},
        "thread_sweep": [],
        "dtype_sweep": [],
        "configs": [],
    }

    for n in (1024, 2048):
        g = matmul_gflops(n)
        results["matmul_gflops"][f"{n}x{n}"] = round(g, 2)
        print(f"matmul {n}x{n}: {g:.1f} GFLOPS")

    # ---- thread sweep on a mid-size config -------------------------------------------
    sweep_cfg = ModelConfig(vocab_size=16384, d_model=384, n_layer=8, n_head=6,
                            n_kv_head=2, d_ff=1024, seq_len=512)
    for n_threads in (1, 2, 4, 8):
        torch.set_num_threads(n_threads)
        r = bench_config(sweep_cfg, batch=8, dtype="fp32", timed=3)
        r["torch_threads"] = n_threads
        results["thread_sweep"].append(r)
        print(f"threads={n_threads}: {r['ms_per_step']:.0f} ms/step  "
              f"{r['tokens_per_s']:.0f} tok/s  {r['achieved_model_gflops']:.1f} GFLOPS")

    # Pick the fastest thread setting for the remaining measurements.
    best_threads = max(results["thread_sweep"], key=lambda r: r["tokens_per_s"])["torch_threads"]
    torch.set_num_threads(best_threads)
    results["chosen_threads"] = best_threads
    print(f"-> using {best_threads} threads")

    # ---- dtype sweep (bf16 autocast is emulated on Haswell; measure, don't assume) ----
    for dtype in ("fp32", "bf16"):
        r = bench_config(sweep_cfg, batch=8, dtype=dtype, timed=3)
        results["dtype_sweep"].append(r)
        print(f"dtype={dtype}: {r['ms_per_step']:.0f} ms/step  {r['tokens_per_s']:.0f} tok/s")
    best_dtype = max(results["dtype_sweep"], key=lambda r: r["tokens_per_s"])["dtype"]
    results["chosen_dtype"] = best_dtype
    print(f"-> using dtype={best_dtype}")

    # ---- candidate architectures -----------------------------------------------------
    candidates = [
        ("A_10M",  ModelConfig(vocab_size=16384, d_model=256, n_layer=6, n_head=4,
                               n_kv_head=2, d_ff=768, seq_len=512), 16),
        ("B_15M",  ModelConfig(vocab_size=16384, d_model=320, n_layer=8, n_head=5,
                               n_kv_head=1, d_ff=896, seq_len=512), 16),
        ("C_19M",  ModelConfig(vocab_size=16384, d_model=384, n_layer=8, n_head=6,
                               n_kv_head=2, d_ff=1024, seq_len=512), 12),
        ("D_14M",  ModelConfig(vocab_size=16384, d_model=384, n_layer=6, n_head=6,
                               n_kv_head=2, d_ff=1024, seq_len=512), 16),
        ("E_34M",  ModelConfig(vocab_size=16384, d_model=512, n_layer=8, n_head=8,
                               n_kv_head=2, d_ff=1408, seq_len=512), 8),
    ]
    for name, cfg, batch in candidates:
        r = bench_config(cfg, batch=batch, dtype=best_dtype, timed=3)
        r["name"] = name
        r["effective_batch_tokens"] = batch * cfg.seq_len
        results["configs"].append(r)
        print(f"{name}: params={r['params']/1e6:.1f}M  {r['ms_per_step']:.0f} ms/step  "
              f"{r['tokens_per_s']:.0f} tok/s  proj(3h)={r['projected_tokens_in_3h']/1e6:.1f}M tok")

    results["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
