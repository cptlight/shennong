#!/usr/bin/env python3
"""Track-02 supervised fine-tuning: teach the task shape, not the world.

Pre-training taught the register (the model has read 本草綱目). SFT teaches the **task**: given a preparation,
decide whether the claimed enrichment survives it; given a lead, name the candidate and what would kill it.

Two decisions that matter:

1. **Loss on the answer only.** The prompt is masked with -100. Otherwise the model spends its capacity
   learning to reproduce questions it will be given, which is the classic SFT mistake.
2. **The format is the demo's format.** Training examples are written as `Question: …\\nAnswer: …`, exactly
   what `/api/query` feeds the model, so what is trained is what a judge sees.

    python training/finetune.py --steps 300
    python training/finetune.py --eval-only          # baseline numbers on the SFT val split
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time

import torch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "model"))

DATA = ROOT / "artifacts" / "sft"


def load_model(ckpt: str):
    from tokenizers import Tokenizer

    from shennong_mini import ModelConfig, ShennongMini, load_checkpoint
    from shennong_moe import MoEConfig, ShennongMoE

    ck = load_checkpoint(ROOT / ckpt)
    cfg_d = ck.get("config") or {}
    if int(cfg_d.get("n_experts", 1)) > 1:
        cfg = MoEConfig.from_dict(cfg_d)
        model = ShennongMoE(cfg)
    else:
        cfg = ModelConfig.from_dict(cfg_d)
        model = ShennongMini(cfg)
    model.load_state_dict(ck["model"], strict=False)
    tok = Tokenizer.from_file(str(ROOT / "tokenizer/shennong-bpe/tokenizer.json"))
    return model, tok, ck


EOS_ID = 2          # <|eos|> — token_to_id("</s>") is None; the first run appended `or 0` = <|pad|>


def split_prompt(text: str) -> tuple[str, str]:
    """Split at the assistant turn. Everything before is masked out of the loss."""
    marker = "<|assistant|>"
    i = text.find(marker)
    if i < 0:
        return text, ""
    return text[: i + len(marker)], text[i + len(marker):].strip()


def encode_examples(tok, rows, seq_len: int):
    out = []
    for r in rows:
        prompt, answer = split_prompt(r["text"])
        p_ids = tok.encode(prompt).ids
        a_ids = tok.encode(answer).ids + [EOS_ID]
        if not a_ids:
            continue
        ids = (p_ids + a_ids)[:seq_len]
        labels = [-100] * min(len(p_ids), len(ids)) + a_ids[: max(0, len(ids) - len(p_ids))]
        if len(labels) < len(ids):
            labels += [-100] * (len(ids) - len(labels))
        out.append((ids, labels, len(p_ids)))
    return out


def collate(batch, pad_id: int = 0):
    t = max(len(b[0]) for b in batch)
    ids = torch.full((len(batch), t), pad_id, dtype=torch.long)
    labels = torch.full((len(batch), t), -100, dtype=torch.long)
    for i, (x, y, _) in enumerate(batch):
        ids[i, : len(x)] = torch.tensor(x)
        labels[i, : len(y)] = torch.tensor(y)
    return ids, labels


@torch.no_grad()
def evaluate(model, examples, pad_id=0) -> float:
    model.eval()
    losses, n = 0.0, 0
    for i in range(0, len(examples), 8):
        batch = examples[i:i + 8]
        ids, labels = collate(batch, pad_id)
        # NEXT-Token prediction: inputs are ids[:-1], targets are labels[1:]. Without the shift the model
        # is asked to reproduce the token at the same position, which it can read off the input — it scored
        # 0.07 CE while being unable to generate anything. That bug is why this comment exists.
        logits, _ = model(ids[:, :-1], targets=labels[:, 1:])
        ce = torch.nn.functional.cross_entropy(
            logits.view(-1, logits.size(-1)), labels[:, 1:].reshape(-1),
            ignore_index=-100, reduction="sum")
        toks = int((labels[:, 1:] != -100).sum())
        if toks:
            losses += float(ce)
            n += toks
    return losses / max(n, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="training/runs/shennong-moe-r1/ckpt-best.pt")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--seq", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--eval-steps", type=int, default=50)
    ap.add_argument("--run-name", default="sft-r1")
    ap.add_argument("--eval-only", action="store_true")
    args = ap.parse_args()

    model, tok, ck = load_model(args.ckpt)
    train = [json.loads(l) for l in (DATA / "train.jsonl").open(encoding="utf-8") if l.strip()]
    val = [json.loads(l) for l in (DATA / "val.jsonl").open(encoding="utf-8") if l.strip()]
    tr = encode_examples(tok, train, args.seq)
    va = encode_examples(tok, val, args.seq)
    print(f"SFT: {len(tr)} train / {len(va)} val examples · base step {ck.get('step')}")

    base_val = evaluate(model, va)
    print(f"baseline answer-only val loss: {base_val:.4f} (ppl {math.exp(min(base_val, 20)):.1f})")
    if args.eval_only:
        return 0

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.01)
    rng = random.Random(1337)
    run = ROOT / "training/runs" / args.run_name
    run.mkdir(parents=True, exist_ok=True)
    best = base_val
    t0 = time.time()
    curve = []
    model.train()
    for step in range(1, args.steps + 1):
        batch = [tr[rng.randrange(len(tr))] for _ in range(args.batch)]
        ids, labels = collate(batch)
        logits, loss = model(ids[:, :-1], targets=labels[:, 1:])
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 10 == 0 or step == 1:
            print(f"  step {step:>4} train(seq) {float(loss):.4f} · {step/(time.time()-t0):.2f} it/s", flush=True)
        if step % args.eval_steps == 0 or step == args.steps:
            v = evaluate(model, va)
            curve.append({"step": step, "val_answer_loss": round(v, 4)})
            print(f"  step {step:>4} VAL answer-only {v:.4f} (base {base_val:.4f})", flush=True)
            if v < best:
                best = v
                torch.save({"model": model.state_dict(), "config": ck["config"], "step": step,
                            "sft": {"base_val": base_val, "val": v, "data": str(DATA)}},
                           run / "ckpt-best.pt")
        model.train()

    out = {
        "run": args.run_name, "base_checkpoint": args.ckpt, "base_step": ck.get("step"),
        "examples_train": len(tr), "examples_val": len(va),
        "base_val_answer_loss": round(base_val, 4),
        "best_val_answer_loss": round(best, 4),
        "improvement_nats": round(base_val - best, 4),
        "steps": args.steps, "lr": args.lr, "batch": args.batch,
        "curve": curve, "wall_s": round(time.time() - t0, 1),
        "note": ("answer-only loss: the prompt tokens are masked with -100, so this measures the model's "
                 "ability to produce the domain answer, not to reproduce the question"),
    }
    (run / "metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nbase {base_val:.4f} -> best {best:.4f} ({base_val-best:+.4f} nats)")
    print(f"wrote {run/'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
