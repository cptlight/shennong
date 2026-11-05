"""Continued pretraining (CPT) of the `shennong-0.5b` flagship on the SHENNONG corpus.

This is the *domain adaptation* stage of the flagship path:

    Qwen2.5-0.5B (public, Apache-2.0, 494 M params)
        -> continued pretraining on the Asian medical/alchemical + biology corpus
        -> LoRA SFT (training/sft_lora.py)  -> merge + Q4_K_M GGUF (training/merge_quantize.py)

WHY THIS FILE IS A RECIPE AND NOT A RESULT
------------------------------------------
This machine is CPU-only (Intel i7-4790K, no CUDA/MPS). Loading the 0.5 B base weights is
possible (~1 GB download, ~3 GB RAM), but a single CPT epoch over the SHENNONG corpus at
seq 1024 is on the order of 10^2 GPU-hours or weeks of CPU time. It was therefore **not run
here**, and no `shennong-0.5b` numbers appear in the model card except as "not yet run".
The architecture path is real and the script is executable: it loads the base weights, builds
the token cache with exactly the same code as `train_pretrain.py`, and saves resumable
checkpoints in the same format, so an HGX/A100 run only needs `--base <local-dir>`.

NOTE ON ARCHITECTURE: Qwen2.5 uses a Llama-style decoder with q/k/v projection biases and
RoPE theta 1e6. `model/shennong_mini.py` supports both (`attention_bias`, `rope_theta`), and
`model/configs/shennong-0.5b.json` mirrors the Qwen2.5-0.5B dimensions, so the base weights
load without architecture surgery.

Usage
-----
    huggingface-cli download Qwen/Qwen2.5-0.5B --local-dir artifacts/qwen2.5-0.5b-base
    python training/cpt.py --base artifacts/qwen2.5-0.5b-base \
        --config model/configs/shennong-0.5b.json \
        --corpus corpus/processed/corpus.jsonl \
        --steps 4000 --batch 8 --accum 8 --seq 1024 --lr 5e-5 \
        --run-name shennong-0.5b-cpt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "model" / "export"))
sys.path.insert(0, str(ROOT / "training"))

from shennong_mini import ModelConfig, ShennongMini, load_checkpoint, save_checkpoint  # noqa: E402

CACHE = ROOT / "training" / "cache"


# ---------------------------------------------------------------------------------------
# Data (same format/behaviour as train_pretrain.build_token_file, different EOS lookup)
# ---------------------------------------------------------------------------------------
def find_eos(tok) -> int:
    for name in ("<|eos|>", "<|endoftext|>", "<|end_of_text|>", "</s>"):
        i = tok.token_to_id(name)
        if i is not None:
            return i
    return 0


def build_token_file(corpus: Path, tokenizer_path: Path, cache_key: str, val_frac: float,
                     seq_len: int) -> dict:
    from tokenizers import Tokenizer

    CACHE.mkdir(parents=True, exist_ok=True)
    train_p = CACHE / f"train_{cache_key}.npy"
    val_p = CACHE / f"val_{cache_key}.npy"
    meta_p = CACHE / f"meta_{cache_key}.json"
    if train_p.exists() and val_p.exists() and meta_p.exists():
        return json.loads(meta_p.read_text())

    tok = Tokenizer.from_file(str(tokenizer_path))
    eos = find_eos(tok)
    vocab = tok.get_vocab_size()
    dtype = np.uint16 if vocab <= 65535 else np.uint32
    docs = []
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("text"):
                docs.append(rec["text"])
    random.Random(0).shuffle(docs)
    n_val = max(1, int(len(docs) * val_frac))
    val_docs, train_docs = docs[:n_val], docs[n_val:]

    def encode(ds):
        ids: list[int] = []
        for i in range(0, len(ds), 512):
            for enc in tok.encode_batch(ds[i:i + 512]):
                ids.extend(enc.ids)
                ids.append(eos)
        return np.asarray(ids, dtype=dtype)

    t0 = time.time()
    train_ids, val_ids = encode(train_docs), encode(val_docs)
    np.save(train_p, train_ids)
    np.save(val_p, val_ids)
    meta = {"train_tokens": int(train_ids.size), "val_tokens": int(val_ids.size),
            "train_docs": len(train_docs), "val_docs": len(val_docs),
            "tokenizer": str(tokenizer_path), "eos_id": eos, "dtype": str(dtype),
            "seq_len_for_cache": seq_len, "build_seconds": round(time.time() - t0, 1)}
    meta_p.write_text(json.dumps(meta, indent=2))
    print(f"tokenised in {meta['build_seconds']}s: train={meta['train_tokens']:,} "
          f"val={meta['val_tokens']:,} (dtype={dtype})")
    return meta


def get_batch(data: np.ndarray, batch: int, seq: int, rng: np.random.Generator):
    ix = rng.integers(0, data.size - seq - 1, size=batch)
    x = np.stack([data[i:i + seq] for i in ix]).astype(np.int64)
    y = np.stack([data[i + 1:i + 1 + seq] for i in ix]).astype(np.int64)
    return torch.from_numpy(x), torch.from_numpy(y)


@torch.no_grad()
def evaluate(model, data, seq, batch, iters, seed=1234) -> float:
    model.eval()
    rng = np.random.default_rng(seed)
    losses = []
    for _ in range(iters):
        x, y = get_batch(data, batch, seq, rng)
        _, loss = model(x, y)
        losses.append(float(loss))
    model.train()
    return float(np.mean(losses))


def lr_at(step: int, base_lr: float, warmup: int, total: int, min_frac: float = 0.1) -> float:
    if step < warmup:
        return base_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return base_lr * (min_frac + (1 - min_frac) * 0.5 * (1 + math.cos(math.pi * min(1.0, progress))))


# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="HF dir of the base model (Qwen2.5-0.5B)")
    ap.add_argument("--config", default="model/configs/shennong-0.5b.json")
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--tokenizer", default="", help="defaults to <base>/tokenizer.json")
    ap.add_argument("--run-name", default="")
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--eval-steps", type=int, default=250)
    ap.add_argument("--eval-iters", type=int, default=8)
    ap.add_argument("--ckpt-steps", type=int, default=250)
    ap.add_argument("--log-steps", type=int, default=10)
    ap.add_argument("--val-frac", type=float, default=0.02)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--resume", default="")
    args = ap.parse_args()

    from to_hf import load_hf_model

    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    base = Path(args.base)
    if not (base / "model.safetensors").exists() and not list(base.glob("*.safetensors")):
        raise SystemExit(f"{base} does not look like an HF model directory (no *.safetensors)")

    tok_path = Path(args.tokenizer) if args.tokenizer else base / "tokenizer.json"
    if not tok_path.exists():
        raise SystemExit(f"tokenizer.json not found at {tok_path}")

    model = load_hf_model(base)
    cfg = model.cfg
    # The config file documents the intended flagship dims; verify the loaded weights match.
    want = ModelConfig.from_json(ROOT / args.config)
    dims = ("vocab_size", "d_model", "n_layer", "n_head", "n_kv_head", "d_ff")
    mismatch = {k: (getattr(cfg, k), getattr(want, k)) for k in dims
                if getattr(cfg, k) != getattr(want, k)}
    if mismatch:
        print(f"WARNING: loaded base dims differ from {args.config}: {mismatch}")
    print(f"base: {base}  {model.num_parameters():,} params  vocab={cfg.vocab_size}")

    run_name = args.run_name or time.strftime("shennong-0.5b-cpt-%Y%m%d-%H%M%S")
    run_dir = ROOT / "training" / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    cache_key = "cpt-" + hashlib.sha256(str(tok_path).encode()).hexdigest()[:10]
    meta = build_token_file(ROOT / args.corpus, tok_path, cache_key, args.val_frac, args.seq)
    dtype = np.uint16 if meta["dtype"] == "uint16" else np.uint32
    train_all = np.load(CACHE / f"train_{cache_key}.npy", mmap_mode="r")
    val_all = np.load(CACHE / f"val_{cache_key}.npy", mmap_mode="r")

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95),
                            weight_decay=0.1, eps=1e-8)
    start_step = 0
    history: list[dict] = []
    if args.resume:
        ck = load_checkpoint(args.resume)
        model.load_state_dict(ck["model"])
        if ck.get("optimizer"):
            opt.load_state_dict(ck["optimizer"])
        start_step = ck.get("step", 0)
        lp = run_dir / "log.jsonl"
        if lp.exists():
            history = [json.loads(line) for line in lp.read_text().splitlines() if line.strip()]
        print(f"resumed from {args.resume} at step {start_step}")

    tokens_per_step = args.batch * args.accum * args.seq
    run_meta = {"run_id": run_name, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "stage": "continued_pretraining", "base": str(base),
                "config": cfg.to_dict(), "params": model.num_parameters(),
                "non_embedding_params": model.num_parameters(non_embedding=True),
                "args": vars(args), "corpus": meta, "torch_version": torch.__version__,
                "seed": args.seed}
    (run_dir / "run.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    log_path = run_dir / "log.jsonl"
    metrics_path = run_dir / "metrics.json"
    print(f"\n{run_name}: {model.num_parameters() / 1e6:.1f}M params | "
          f"{args.steps} steps x {tokens_per_step:,} tok = "
          f"{args.steps * tokens_per_step / 1e6:.1f}M tokens")

    t_start = time.time()
    rng = np.random.default_rng(args.seed + start_step)
    best_val, last_val, last_train = float("inf"), None, None
    model.train()

    def flush_metrics(step: int, done: bool = False) -> None:
        elapsed = time.time() - t_start
        seen = step * tokens_per_step
        m = {**run_meta, "steps_completed": step, "tokens_seen": seen,
             "epochs": round(seen / max(1, train_all.size), 3),
             "wall_clock_s": round(elapsed, 1),
             "tokens_per_s": round(seen / elapsed, 1) if elapsed > 0 else None,
             "final_train_loss": last_train, "final_val_loss": last_val,
             "best_val_loss": best_val if best_val != float("inf") else None,
             "val_ppl": round(math.exp(last_val), 2) if last_val and last_val < 20 else None,
             "loss_curve": history, "completed": done,
             "checkpoint": str(run_dir / "ckpt.pt") if (run_dir / "ckpt.pt").exists() else None}
        metrics_path.write_text(json.dumps(m, indent=2), encoding="utf-8")

    for step in range(start_step, args.steps):
        lr = lr_at(step, args.lr, args.warmup, args.steps)
        for g in opt.param_groups:
            g["lr"] = lr
        opt.zero_grad(set_to_none=True)
        total_loss = 0.0
        for _ in range(args.accum):
            x, y = get_batch(train_all, args.batch, args.seq, rng)
            _, loss = model(x, y)
            (loss / args.accum).backward()
            total_loss += float(loss)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        last_train = total_loss / args.accum

        if step % args.log_steps == 0 or step == args.steps - 1:
            val = None
            if step % args.eval_steps == 0 or step == args.steps - 1:
                val = evaluate(model, val_all, args.seq, args.batch, args.eval_iters)
                last_val = val
                if val < best_val:
                    best_val = val
                    save_checkpoint(run_dir / "ckpt-best.pt", model, opt, step, {"val_loss": val})
            entry = {"step": step, "loss": round(last_train, 4),
                     "val_loss": None if val is None else round(val, 4),
                     "lr": round(lr, 8), "tokens_seen": (step + 1) * tokens_per_step}
            history.append(entry)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            eta = (args.steps - step - 1) * (time.time() - t_start) / max(1, step - start_step + 1)
            print(f"step {step:>5} | loss {last_train:.4f}"
                  f"{f' | val {val:.4f}' if val is not None else ''} | lr {lr:.2e} | "
                  f"eta {eta / 3600:.1f}h", flush=True)
            flush_metrics(step + 1)

        if (step + 1) % args.ckpt_steps == 0 or step == args.steps - 1:
            save_checkpoint(run_dir / "ckpt.pt", model, opt, step + 1, {"val_loss": last_val})
            flush_metrics(step + 1, done=step == args.steps - 1)

    save_checkpoint(run_dir / "ckpt.pt", model, opt, args.steps, {"val_loss": last_val})
    flush_metrics(args.steps, done=True)
    print(f"\nDONE {run_name}: {args.steps * tokens_per_step:,} tokens, val {last_val}, "
          f"{(time.time() - t_start) / 3600:.1f}h")
    print("Next: python training/sft_lora.py --base <this ckpt> --data training/data/*.jsonl ...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
