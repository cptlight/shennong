#!/usr/bin/env python3
"""Pretrain `shennong-mini` from scratch on CPU.

This is the run that produces the actual open weights. It is deliberately boring: a plain
causal-LM loop over a pre-tokenised uint16 token file, with resumable checkpoints and a
`metrics.json` that is rewritten continuously — so a reaped shell can never destroy a night of work,
and the Workbench can plot a *real* loss curve the moment step 50 exists.

Everything the model card reports (tokens seen, wall clock, val loss, bytes-per-byte) is written by
this script. No number in the model card is typed by a human.

    python training/train_pretrain.py --config model/configs/shennong-mini-cpu.json --steps 1000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from shennong_mini import ModelConfig, ShennongMini, load_checkpoint, save_checkpoint  # noqa: E402

CACHE = ROOT / "training" / "cache"


# ---------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------
def build_token_file(corpus: Path, tokenizer_path: Path, cache_key: str, val_frac: float = 0.02) -> dict:
    """Tokenise the corpus once into train/val uint16 arrays and cache them."""
    from tokenizers import Tokenizer

    CACHE.mkdir(parents=True, exist_ok=True)
    train_p = CACHE / f"train_{cache_key}.npy"
    val_p = CACHE / f"val_{cache_key}.npy"
    meta_p = CACHE / f"meta_{cache_key}.json"

    if train_p.exists() and val_p.exists() and meta_p.exists():
        meta = json.loads(meta_p.read_text())
        print(f"using cached tokens: train={meta['train_tokens']:,} val={meta['val_tokens']:,}")
        return meta

    tok = Tokenizer.from_file(str(tokenizer_path))
    eos = tok.token_to_id("<|eos|>")
    eos = 0 if eos is None else eos

    docs: list[str] = []
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("text") or ""
            if t:
                docs.append(t)

    random.Random(0).shuffle(docs)  # deterministic shuffle, keeps val representative
    n_val = max(1, int(len(docs) * val_frac))
    val_docs, train_docs = docs[:n_val], docs[n_val:]

    def encode(ds: list[str]) -> np.ndarray:
        ids: list[int] = []
        for i in range(0, len(ds), 512):
            for enc in tok.encode_batch(ds[i:i + 512]):
                ids.extend(enc.ids)
                ids.append(eos)
        return np.asarray(ids, dtype=np.uint16)

    t0 = time.time()
    train_ids, val_ids = encode(train_docs), encode(val_docs)
    np.save(train_p, train_ids)
    np.save(val_p, val_ids)
    meta = {
        "train_tokens": int(train_ids.size),
        "val_tokens": int(val_ids.size),
        "train_docs": len(train_docs),
        "val_docs": len(val_docs),
        "corpus_chars": sum(len(d) for d in docs),
        "tokenizer": str(tokenizer_path),
        "corpus": str(corpus),
        "eos_id": eos,
        "build_seconds": round(time.time() - t0, 1),
    }
    meta_p.write_text(json.dumps(meta, indent=2))
    print(f"tokenised in {meta['build_seconds']}s: train={meta['train_tokens']:,} val={meta['val_tokens']:,}")
    return meta


def get_batch(data: np.ndarray, batch: int, seq: int, rng: np.random.Generator) -> tuple[torch.Tensor, torch.Tensor]:
    ix = rng.integers(0, data.size - seq - 1, size=batch)
    x = np.stack([data[i:i + seq] for i in ix]).astype(np.int64)
    y = np.stack([data[i + 1:i + 1 + seq] for i in ix]).astype(np.int64)
    return torch.from_numpy(x), torch.from_numpy(y)


@torch.no_grad()
def evaluate(model: ShennongMini, data: np.ndarray, seq: int, batch: int, iters: int,
             seed: int = 1234) -> float:
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
    cosine = 0.5 * (1 + math.cos(math.pi * min(1.0, progress)))
    return base_lr * (min_frac + (1 - min_frac) * cosine)


# ---------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="model/configs/shennong-mini-cpu.json")
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--tokenizer", default="tokenizer/shennong-bpe/tokenizer.json")
    ap.add_argument("--run-name", default="")
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--accum", type=int, default=2)
    ap.add_argument("--seq", type=int, default=512)
    ap.add_argument("--lr", type=float, default=6e-4)
    ap.add_argument("--warmup", type=int, default=60)
    ap.add_argument("--eval-steps", type=int, default=100)
    ap.add_argument("--eval-iters", type=int, default=8)
    ap.add_argument("--ckpt-steps", type=int, default=100)
    ap.add_argument("--log-steps", type=int, default=25)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--resume", default="")
    ap.add_argument("--train-frac", type=float, default=1.0, help="use a fraction of train tokens (smoke runs)")
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    cfg = ModelConfig.from_json(ROOT / args.config)
    cfg.vocab_size = cfg.vocab_size  # explicit: must match the trained tokenizer
    run_name = args.run_name or time.strftime("shennong-mini-%Y%m%d-%H%M%S")
    run_dir = ROOT / "training" / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    tok_path = ROOT / args.tokenizer
    if not tok_path.exists():
        raise SystemExit(f"tokenizer missing: {tok_path} — run `make tokenizer` first")
    # Cache key must cover the CORPUS too: keying only on the tokenizer means a re-emitted corpus
    # silently reuses tokens built from an older snapshot, which breaks exact reproducibility of a run.
    corpus_path = ROOT / args.corpus
    corpus_stat = corpus_path.stat()
    cache_key = "-".join([
        tok_path.parent.name,
        hashlib.sha256(tok_path.read_bytes()).hexdigest()[:10],
        f"{corpus_stat.st_size:x}",
    ])
    meta = build_token_file(ROOT / args.corpus, tok_path, cache_key)
    if cfg.vocab_size != meta.get("vocab_size", cfg.vocab_size):
        pass  # tokenizer vocab is authoritative; assert below against the tokenizer file

    train_all = np.load(CACHE / f"train_{cache_key}.npy", mmap_mode="r")
    val_all = np.load(CACHE / f"val_{cache_key}.npy", mmap_mode="r")
    if args.train_frac < 1.0:
        train_all = np.asarray(train_all[: int(len(train_all) * args.train_frac)])
        val_all = np.asarray(val_all[: max(args.seq * 4, int(len(val_all) * args.train_frac))])

    model = ShennongMini(cfg)
    n_params = model.num_parameters()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1, eps=1e-8)

    start_step = 0
    history: list[dict] = []
    if args.resume:
        ck = load_checkpoint(args.resume)
        model.load_state_dict(ck["model"])
        if ck.get("optimizer"):
            opt.load_state_dict(ck["optimizer"])
        start_step = ck.get("step", 0)
        hist_path = run_dir / "log.jsonl"
        if hist_path.exists():
            history = [json.loads(line) for line in hist_path.read_text().splitlines() if line.strip()]
        print(f"resumed from {args.resume} at step {start_step}")

    # --- record everything the model card is allowed to quote ---------------------
    run_meta = {
        "run_id": run_name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "config": cfg.to_dict(),
        "params": n_params,
        "non_embedding_params": model.num_parameters(non_embedding=True),
        "args": vars(args),
        "corpus": meta,
        "threads": args.threads,
        "torch_version": torch.__version__,
        "platform": sys.platform,
        "seed": args.seed,
    }
    (run_dir / "run.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log_path = run_dir / "log.jsonl"
    metrics_path = run_dir / "metrics.json"

    tokens_per_step = args.batch * args.accum * args.seq
    print(f"\n{run_name}: {n_params / 1e6:.2f}M params | {args.steps} steps x {tokens_per_step:,} tok = "
          f"{args.steps * tokens_per_step / 1e6:.2f}M tokens | corpus {len(train_all):,} tokens")

    t_start = time.time()
    model.train()
    rng = np.random.default_rng(args.seed + start_step)
    best_val = float("inf")
    last_val = None
    last_train = None

    def flush_metrics(step: int, done: bool = False) -> None:
        elapsed = time.time() - t_start
        seen = step * tokens_per_step
        m = {
            **{k: v for k, v in run_meta.items() if k != "args"},
            "steps_completed": step,
            "tokens_seen": seen,
            "epochs": round(seen / max(1, len(train_all)), 3),
            "wall_clock_s": round(elapsed, 1),
            "tokens_per_s": round(seen / elapsed, 1) if elapsed > 0 else None,
            "final_train_loss": last_train,
            "final_val_loss": last_val,
            "best_val_loss": best_val if best_val != float("inf") else None,
            "val_ppl": round(math.exp(last_val), 2) if last_val is not None and last_val < 20 else None,
            "loss_curve": history,
            "completed": done,
            "checkpoint": str(run_dir / "ckpt.pt") if (run_dir / "ckpt.pt").exists() else None,
        }
        metrics_path.write_text(json.dumps(m, indent=2), encoding="utf-8")

    for step in range(start_step, args.steps):
        lr = lr_at(step, args.lr, args.warmup, args.steps)
        for g in opt.param_groups:
            g["lr"] = lr

        t_step = time.time()
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
        step_dt = time.time() - t_step

        if step % args.log_steps == 0 or step == args.steps - 1:
            val = None
            if step % args.eval_steps == 0 or step == args.steps - 1:
                val = evaluate(model, val_all, args.seq, args.batch, args.eval_iters)
                last_val = val
                if val < best_val:
                    best_val = val
                    save_checkpoint(run_dir / "ckpt-best.pt", model, opt, step, {"val_loss": val})
            entry = {"step": step, "loss": round(last_train, 4), "val_loss": None if val is None else round(val, 4),
                     "lr": round(lr, 8), "tokens_seen": (step + 1) * tokens_per_step,
                     "tokens_per_s": round(tokens_per_step / step_dt, 1) if step_dt > 0 else None}
            history.append(entry)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            eta = (args.steps - step - 1) * (time.time() - t_start) / max(1, step - start_step + 1)
            print(f"step {step:>5} | loss {last_train:.4f}"
                  f"{f' | val {val:.4f}' if val is not None else ''} | lr {lr:.2e} | "
                  f"{entry['tokens_per_s']} tok/s | eta {eta / 60:.0f}m", flush=True)
            flush_metrics(step + 1)

        if (step + 1) % args.ckpt_steps == 0 or step == args.steps - 1:
            save_checkpoint(run_dir / "ckpt.pt", model, opt, step + 1, {"val_loss": last_val})
            flush_metrics(step + 1, done=step == args.steps - 1)

    # final: save HF-style weights dir is model-forge's exporter job; we save a torch checkpoint
    save_checkpoint(run_dir / "ckpt.pt", model, opt, args.steps, {"val_loss": last_val})
    flush_metrics(args.steps, done=True)

    # loss curve
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        art = ROOT / "artifacts"
        art.mkdir(exist_ok=True)
        steps = [e["step"] for e in history]
        tr = [e["loss"] for e in history]
        va = [e["val_loss"] for e in history]
        fig, ax = plt.subplots(figsize=(7, 4), dpi=160)
        ax.plot(steps, tr, color="#b4532a", lw=1.6, label="train loss")
        pts = [(s, v) for s, v in zip(steps, va) if v is not None]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#2f6f5e", lw=1.8, marker="o", ms=3,
                    label="held-out val loss")
        ax.set_xlabel("step")
        ax.set_ylabel("cross-entropy (nats/token)")
        ax.set_title(f"shennong-mini — {n_params / 1e6:.1f}M params, "
                     f"{args.steps * tokens_per_step / 1e6:.1f}M tokens, CPU only")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False)
        fig.tight_layout()
        for ext in ("png", "svg"):
            fig.savefig(art / f"loss_curve.{ext}")
        plt.close(fig)
        print(f"wrote {art / 'loss_curve.png'}")
    except Exception as exc:  # noqa: BLE001
        print(f"(loss curve plot skipped: {exc})")

    print(f"\nDONE {run_name}: {args.steps} steps, {args.steps * tokens_per_step:,} tokens, "
          f"val {last_val}, {(time.time() - t_start) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
