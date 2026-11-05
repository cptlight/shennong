"""Step 0 for SHENNONG: measure CPU throughput *before* choosing the training config.

Everything downstream (token budget, wall-clock, whether bf16 autocast is worth it,
how many threads to use) is decided from this measurement, not from assumptions.

Run:  .venv/bin/python -u training/bench.py
Writes: training/runs/bench.json   (incrementally, so a partial run is still useful)
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

from shennong_mini import ModelConfig, ShennongMini  # noqa: E402

OUT = ROOT / "training" / "runs" / "bench.json"
RESULTS: dict = {}


def flush() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)


def say(msg: str) -> None:
    print(msg, flush=True)


def matmul_gflops(n: int, iters: int = 4) -> float:
    a, b = torch.randn(n, n), torch.randn(n, n)
    a @ b
    t0 = time.perf_counter()
    for _ in range(iters):
        a @ b
    dt = (time.perf_counter() - t0) / iters
    return (2 * n**3) / dt / 1e9


def timed_step(cfg: ModelConfig, batch: int, dtype: str, timed: int = 2, warmup: int = 1,
               opt: bool = True) -> dict:
    torch.manual_seed(0)
    model = ShennongMini(cfg)
    model.train()
    n_params = model.num_parameters()
    optim = torch.optim.AdamW(model.parameters(), lr=1e-4) if opt else None
    x = torch.randint(0, cfg.vocab_size, (batch, cfg.seq_len))
    y = torch.randint(0, cfg.vocab_size, (batch, cfg.seq_len))
    tokens_per_step = batch * cfg.seq_len

    def one() -> None:
        if optim is not None:
            optim.zero_grad(set_to_none=True)
        if dtype == "bf16":
            ctx = torch.autocast(device_type="cpu", dtype=torch.bfloat16)
        else:
            ctx = torch.autocast(device_type="cpu", enabled=False)
        with ctx:
            _, loss = model(x, targets=y)
        loss.backward()
        if optim is not None:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()

    for _ in range(warmup):
        one()
    t0 = time.perf_counter()
    for _ in range(timed):
        one()
    dt = (time.perf_counter() - t0) / timed
    tps = tokens_per_step / dt
    return {
        "config": asdict(cfg), "params": n_params,
        "params_non_embedding": model.num_parameters(non_embedding=True),
        "batch": batch, "seq_len": cfg.seq_len, "dtype": dtype, "optimizer": opt,
        "ms_per_step": round(dt * 1000, 1), "tokens_per_s": round(tps, 1),
        "achieved_model_gflops": round(6 * n_params * tps / 1e9, 1),
        "projected_tokens_in_3h": int(tps * 3 * 3600),
        "tokens_per_step": tokens_per_step,
    }


def main() -> None:
    say(f"host={platform.platform()}  torch={torch.__version__}  "
        f"threads={torch.get_num_threads()}  interop={torch.get_num_interop_threads()}")
    conf = torch.__config__.show()
    say(conf)
    RESULTS["torch_config"] = conf
    RESULTS["env"] = {
        "platform": platform.platform(), "machine": platform.machine(),
        "cpu_count_logical": os.cpu_count(), "torch": torch.__version__,
        "torch_threads": torch.get_num_threads(), "python": sys.version.split()[0],
        "cpu_only": True,
    }
    flush()

    # ---- 1. raw matmul throughput ------------------------------------------------
    RESULTS["matmul_gflops"] = {}
    for n in (1024, 2048, 4096):
        g = matmul_gflops(n)
        RESULTS["matmul_gflops"][str(n)] = round(g, 1)
        say(f"matmul {n}x{n}: {g:.1f} GFLOPS")
        flush()

    # ---- 2. thread sweep (does threading help at all?) ---------------------------
    sweep = ModelConfig(vocab_size=16384, d_model=384, n_layer=8, n_head=6,
                        n_kv_head=2, d_ff=1024, seq_len=512)
    RESULTS["thread_sweep"] = []
    for n_threads in (1, 4, 8):
        torch.set_num_threads(n_threads)
        r = timed_step(sweep, batch=8, dtype="fp32")
        r["torch_threads"] = n_threads
        RESULTS["thread_sweep"].append(r)
        say(f"threads={n_threads}: {r['ms_per_step']:.0f} ms/step  {r['tokens_per_s']:.0f} tok/s  "
            f"{r['achieved_model_gflops']:.1f} GFLOPS")
        flush()
    best_threads = max(RESULTS["thread_sweep"], key=lambda r: r["tokens_per_s"])["torch_threads"]
    torch.set_num_threads(best_threads)
    RESULTS["chosen_threads"] = best_threads
    say(f"-> threads={best_threads}")

    # ---- 3. dtype sweep (bf16 is emulated on Haswell: measure, don't assume) -----
    RESULTS["dtype_sweep"] = []
    for dtype in ("fp32", "bf16"):
        r = timed_step(sweep, batch=8, dtype=dtype)
        RESULTS["dtype_sweep"].append(r)
        say(f"dtype={dtype}: {r['ms_per_step']:.0f} ms/step  {r['tokens_per_s']:.0f} tok/s")
        flush()
    best_dtype = max(RESULTS["dtype_sweep"], key=lambda r: r["tokens_per_s"])["dtype"]
    RESULTS["chosen_dtype"] = best_dtype
    say(f"-> dtype={best_dtype}")

    # ---- 4. batch sweep on one config (bigger batch = better BLAS efficiency?) ---
    RESULTS["batch_sweep"] = []
    for batch in (4, 16, 32):
        r = timed_step(sweep, batch=batch, dtype=best_dtype)
        RESULTS["batch_sweep"].append(r)
        say(f"batch={batch}: {r['ms_per_step']:.0f} ms/step  {r['tokens_per_s']:.0f} tok/s")
        flush()

    # ---- 5. candidate architectures for the multilingual model -------------------
    cands = [
        ("M_17M_v24k", ModelConfig(vocab_size=24576, d_model=320, n_layer=8, n_head=5,
                                   n_kv_head=1, d_ff=896, seq_len=512), 16),
        ("M_22M_v32k", ModelConfig(vocab_size=32000, d_model=384, n_layer=6, n_head=6,
                                   n_kv_head=2, d_ff=1024, seq_len=512), 16),
        ("M_25M_v32k", ModelConfig(vocab_size=32000, d_model=384, n_layer=8, n_head=6,
                                   n_kv_head=2, d_ff=1024, seq_len=512), 12),
    ]
    RESULTS["configs"] = []
    for name, cfg, batch in cands:
        r = timed_step(cfg, batch=batch, dtype=best_dtype)
        r["name"] = name
        r["effective_batch_tokens"] = batch * cfg.seq_len
        RESULTS["configs"].append(r)
        say(f"{name}: params={r['params']/1e6:.1f}M  {r['ms_per_step']:.0f} ms/step  "
            f"{r['tokens_per_s']:.0f} tok/s  proj(3h)={r['projected_tokens_in_3h']/1e6:.1f}M tok")
        flush()

    RESULTS["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1)
    flush()
    say(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
