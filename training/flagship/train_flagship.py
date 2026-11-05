#!/usr/bin/env python3
"""Train the SHENNONG-0.5B flagship on a *free* GPU (Colab / Kaggle / Lightning).

Why this exists
---------------
`shennong-mini` is trained from scratch on a CPU here, which is a real but tiny model. The flagship
needs a GPU. Any free tier works: the whole job is ~1–2 GPU-hours because the corpus is ~10 M tokens
and 0.5 B parameters is small.

Pipeline
--------
  1. Qwen2.5-0.5B (Apache-2.0)  --domain CPT-->  shennong-0.5b-cpt
  2. shennong-0.5b-cpt          --SFT-->        shennong-0.5b
  3. export HF format -> convert_hf_to_gguf.py -> llama-quantize Q4_K_M -> < 1 GB GGUF

Why Qwen2.5-0.5B as the base: it is Apache-2.0 (so derivatives are redistributable), it has a
multilingual tokenizer with real Classical-Chinese coverage, and it is small enough to fine-tune
full-precision on a 16 GB T4 without LoRA tricks.

    python training/flagship/train_flagship.py --stage cpt --epochs 3
    python training/flagship/train_flagship.py --stage sft
    bash  training/flagship/export_gguf.sh

Honesty contract: `metrics.json` for the flagship records what *actually* ran. If you only run CPT,
the model card must say "CPT only, SFT not run".
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------------------
# corpus -> token ids
# ---------------------------------------------------------------------------------------
def build_tokens(corpus: Path, tokenizer, out_dir: Path, max_tokens: int = 0) -> Path:
    import numpy as np

    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / "cpt_tokens.npy"
    meta_p = out_dir / "cpt_tokens.json"
    if cache.exists() and meta_p.exists():
        m = json.loads(meta_p.read_text())
        log(f"using cached tokens: {m['tokens']:,}")
        return cache

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
            if rec.get("text"):
                docs.append(rec["text"])

    eos = tokenizer.eos_token_id
    ids: list[int] = []
    t0 = time.time()
    for i in range(0, len(docs), 256):
        for enc in tokenizer(docs[i:i + 256], add_special_tokens=False)["input_ids"]:
            ids.extend(enc)
            ids.append(eos)
        if max_tokens and len(ids) >= max_tokens:
            break
    arr = np.asarray(ids, dtype=np.uint32)
    np.save(cache, arr)
    meta_p.write_text(json.dumps({"tokens": int(arr.size), "docs": len(docs),
                                  "chars": sum(len(d) for d in docs),
                                  "seconds": round(time.time() - t0, 1)}, indent=2))
    log(f"tokenised {arr.size:,} tokens from {len(docs):,} chunks in {time.time() - t0:.0f}s")
    return cache


def get_batch(arr, batch: int, seq: int, rng):
    import torch

    ix = rng.integers(0, arr.size - seq - 1, size=batch)
    x = torch.stack([torch.from_numpy(arr[i:i + seq].astype("int64")) for i in ix])
    y = torch.stack([torch.from_numpy(arr[i + 1:i + 1 + seq].astype("int64")) for i in ix])
    return x, y


# ---------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--corpus", default=str(ROOT / "corpus/processed/corpus.jsonl"))
    ap.add_argument("--sft-data", default=str(ROOT / "training/data/sft_instructions.jsonl"))
    ap.add_argument("--out-dir", default=str(ROOT / "artifacts/shennong-0.5b"))
    ap.add_argument("--stage", choices=["cpt", "sft", "both"], default="cpt")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--warmup-frac", type=float, default=0.03)
    ap.add_argument("--max-tokens", type=int, default=0, help="cap tokenised corpus (0 = all)")
    ap.add_argument("--eval-frac", type=float, default=0.01)
    ap.add_argument("--log-every", type=int, default=20)
    ap.add_argument("--save-every", type=int, default=300)
    ap.add_argument("--max-steps", type=int, default=0, help="stop after N steps (smoke test)")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    if not torch.cuda.is_available():
        log("WARNING: no CUDA GPU detected — this will be very slow. Use a Colab/Kaggle GPU runtime.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    log(f"device={device} threads={torch.get_num_threads()}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "flagship_metrics.json"
    metrics: dict = {
        "base": args.base,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "args": vars(args),
        "stages": {},
    }

    tok = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=dtype, attn_implementation="sdpa", trust_remote_code=True
    ).to(device)
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        try:
            model.config.use_cache = False
        except Exception:  # noqa: BLE001
            pass
    n_params = sum(p.numel() for p in model.parameters())
    log(f"loaded {args.base}: {n_params / 1e6:.1f}M params, dtype={dtype}")
    metrics["params"] = n_params

    train_arr = val_arr = None
    if args.stage in ("cpt", "both"):
        arr_path = build_tokens(Path(args.corpus), tok, out_dir / "data", args.max_tokens)
        arr = np.load(arr_path, mmap_mode="r")
        n_val = max(args.seq * 2, int(len(arr) * args.eval_frac))
        train_arr, val_arr = arr[:-n_val], arr[-n_val:]
        log(f"CPT tokens: train={len(train_arr):,} val={len(val_arr):,}")

        tokens_per_step = args.batch * args.accum * args.seq
        total_tokens = int(len(train_arr) * args.epochs)
        steps = max(1, total_tokens // tokens_per_step)
        if args.max_steps:
            steps = min(steps, args.max_steps)
        warmup = max(10, int(steps * args.warmup_frac))
        log(f"CPT: {steps} steps × {tokens_per_step:,} tok = {steps * tokens_per_step / 1e6:.2f}M tokens")

        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.01)
        sched = None
        if device == "cuda":
            from torch.amp import GradScaler
            scaler = GradScaler("cuda")
        else:
            scaler = None
        scaler_obj = scaler

        rng = np.random.default_rng(args.seed)
        model.train()
        curve = []
        t0 = time.time()
        seen = 0
        for step in range(steps):
            lr = args.lr * (step + 1) / warmup if step < warmup else \
                args.lr * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (step - warmup) / max(1, steps - warmup))))
            for g in opt.param_groups:
                g["lr"] = lr
            opt.zero_grad(set_to_none=True)
            tot = 0.0
            for _ in range(args.accum):
                x, y = get_batch(train_arr, args.batch, args.seq, rng)
                x, y = x.to(device), y.to(device)
                if scaler_obj is not None:
                    from torch.amp import autocast
                    with autocast("cuda", dtype=torch.float16):
                        loss = model(input_ids=x, labels=y).loss
                    scaler_obj.scale(loss / args.accum).backward()
                else:
                    loss = model(input_ids=x, labels=y).loss
                    (loss / args.accum).backward()
                tot += float(loss)
            if scaler_obj is not None:
                scaler_obj.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler_obj.step(opt)
                scaler_obj.update()
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
            seen += tokens_per_step

            if step % args.log_every == 0 or step == steps - 1:
                entry = {"step": step, "loss": round(tot / args.accum, 4), "lr": lr,
                         "tokens_seen": seen}
                curve.append(entry)
                log(f"cpt step {step}/{steps} loss {entry['loss']:.4f} "
                    f"({seen / max(1e-9, time.time() - t0):,.0f} tok/s)")
                metrics["stages"]["cpt"] = {"steps": step + 1, "tokens_seen": seen,
                                            "last_loss": entry["loss"], "loss_curve": curve,
                                            "wall_clock_s": round(time.time() - t0, 1)}
                metrics_path.write_text(json.dumps(metrics, indent=2))

            if (step + 1) % args.save_every == 0:
                ck = out_dir / "checkpoint-cpt"
                model.save_pretrained(ck)
                tok.save_pretrained(ck)
                log(f"checkpoint -> {ck}")
        metrics["stages"]["cpt"]["wall_clock_s"] = round(time.time() - t0, 1)
        metrics_path.write_text(json.dumps(metrics, indent=2))

    if args.stage in ("sft", "both"):
        sft_path = Path(args.sft_data)
        if not sft_path.exists():
            log(f"SFT data missing: {sft_path} — skipping SFT (record this in the model card)")
            metrics["stages"]["sft"] = {"status": "skipped", "reason": f"{sft_path} not found"}
        else:
            rows = [json.loads(l) for l in sft_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            log(f"SFT: {len(rows)} examples")
            texts = []
            for r in rows:
                msgs = []
                if r.get("system"):
                    msgs.append({"role": "system", "content": r["system"]})
                user = r.get("instruction", "") + ("\n\n" + r["input"] if r.get("input") else "")
                msgs.append({"role": "user", "content": user})
                msgs.append({"role": "assistant", "content": r.get("output", "")})
                texts.append(tok.apply_chat_template(msgs, tokenize=False))
            enc = [tok(t, truncation=True, max_length=args.seq, padding="max_length",
                       return_tensors="pt") for t in texts]
            from torch.utils.data import DataLoader, TensorDataset
            ds = TensorDataset(torch.stack([e["input_ids"][0] for e in enc]),
                              torch.stack([e["attention_mask"][0] for e in enc]))
            dl = DataLoader(ds, batch_size=2, shuffle=True)
            opt = torch.optim.AdamW(model.parameters(), lr=args.lr / 2, betas=(0.9, 0.95), weight_decay=0.01)
            model.train()
            t0 = time.time()
            steps = 0
            for epoch in range(2):
                for x, mask in dl:
                    x, mask = x.to(device), mask.to(device)
                    y = x.clone()
                    y[mask == 0] = -100
                    opt.zero_grad(set_to_none=True)
                    if device == "cuda":
                        from torch.amp import autocast
                        with autocast("cuda", dtype=torch.float16):
                            loss = model(input_ids=x, attention_mask=mask, labels=y).loss
                    else:
                        loss = model(input_ids=x, attention_mask=mask, labels=y).loss
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    opt.step()
                    steps += 1
                    if steps % 10 == 0:
                        log(f"sft step {steps} loss {float(loss):.4f}")
                        metrics["stages"]["sft"] = {"status": "ran", "steps": steps,
                                                    "last_loss": float(loss),
                                                    "wall_clock_s": round(time.time() - t0, 1)}
                        metrics_path.write_text(json.dumps(metrics, indent=2))
            metrics["stages"]["sft"] = {**metrics["stages"].get("sft", {}), "status": "ran",
                                        "wall_clock_s": round(time.time() - t0, 1)}

    final = out_dir / "final"
    model.save_pretrained(final)
    tok.save_pretrained(final)
    model.eval()
    # a couple of samples so the model card has real generations
    samples = []
    for prompt in ["附子必須先炮製，因為", "甘草與甘遂同用，屬於", "Which classical processing step reduces aconitine toxicity, and why?"]:
        ids = tok(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=80, do_sample=True, temperature=0.8, top_p=0.95)
        text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        samples.append({"prompt": prompt, "completion": text.strip()})
        log(f"sample: {prompt!r} -> {text.strip()[:120]!r}")
    metrics["samples"] = samples
    metrics["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    metrics_path.write_text(json.dumps(metrics, indent=2))
    log(f"done -> {final}")
    log("next: bash training/flagship/export_gguf.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
