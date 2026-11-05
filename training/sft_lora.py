"""LoRA supervised fine-tuning for the SHENNONG family (flagship path, and small-scale on mini).

HONEST FRAMING — read this before quoting any result
----------------------------------------------------
`training/data/` contains a *hand-written* set of ~60 instruction/response pairs covering the
five task shapes SHENNONG needs (entity extraction, preparation→process translation, hypothesis
critique, falsification design, and "propose a drug candidate"). Sixty examples demonstrate a
**task shape**, not a capability. On a 494 M flagship they are a legitimate SFT *seed*; on the
8.7 M `shennong-mini` they cannot teach skills — the point of running this stage there is to
prove the pipeline is executable end to end (adapter saved, mergeable, GGUF-able).

Method: LoRA (Hu et al. 2021, arXiv:2106.09685) with rank r and alpha=a, applied to all
attention + MLP projections; base weights are frozen. Loss is computed on assistant tokens only
(everything before `<|assistant|>` is masked with -100).

Usage
-----
    python training/sft_lora.py \
        --base training/runs/shennong-mini-r1/ckpt-best.pt \
        --config model/configs/shennong-mini-cpu.json \
        --tokenizer tokenizer/shennong-bpe \
        --data training/data/instruction_drug_candidate.jsonl training/data/instruction_core.jsonl \
        --out training/runs/shennong-mini-lora --steps 200 --lr 2e-4 --rank 8
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "model" / "export"))

from shennong_mini import ModelConfig, ShennongMini, load_checkpoint  # noqa: E402

DEFAULT_SYSTEM = (
    "You are a careful research assistant for computational ethnopharmacology. You read "
    "classical Asian medical texts (Chinese, Sanskrit, Arabic/Persian, Latin) and reason about "
    "them using modern biology and chemistry. You never give dosing, diagnosis or treatment "
    "advice, and you separate what the text says from what modern evidence shows."
)

TARGET_SUFFIXES = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


# ---------------------------------------------------------------------------------------
# LoRA
# ---------------------------------------------------------------------------------------
class LoRALinear(nn.Module):
    def __init__(self, base: nn.Linear, rank: int = 8, alpha: float = 16.0) -> None:
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.A = nn.Parameter(torch.empty(rank, base.in_features))
        self.B = nn.Parameter(torch.zeros(base.out_features, rank))
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))
        self.rank = rank
        self.scaling = alpha / rank

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x) + (x @ self.A.t() @ self.B.t()) * self.scaling


def inject_lora(model: ShennongMini, rank: int, alpha: float) -> int:
    """Replace target Linear modules by LoRALinear; returns the number replaced."""
    n = 0
    for name, module in list(model.named_modules()):
        for child_name, child in list(module.named_children()):
            if isinstance(child, nn.Linear) and child_name in TARGET_SUFFIXES:
                setattr(module, child_name, LoRALinear(child, rank, alpha))
                n += 1
    return n


def lora_state_dict(model: ShennongMini) -> dict[str, dict[str, torch.Tensor]]:
    out = {}
    for name, module in model.named_modules():
        if isinstance(module, LoRALinear):
            out[name] = {"A": module.A.detach().cpu(), "B": module.B.detach().cpu()}
    return out


# ---------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------
def format_example(ex: dict, tok, max_len: int) -> tuple[list[int], list[int]]:
    system = ex.get("system") or DEFAULT_SYSTEM
    turns = ex.get("messages") or []
    prefix = f"<|system|>\n{system}<|eos|>\n"
    parts = [(prefix, False)]
    for i, turn in enumerate(turns):
        role = turn["role"]
        content = turn["content"].strip()
        if role == "assistant":
            parts.append((f"<|assistant|>\n{content}<|eos|>\n", True))
        elif role == "user":
            parts.append((f"<|user|>\n{content}<|eos|>\n", False))
        else:
            parts.append((f"<|system|>\n{content}<|eos|>\n", False))
    ids, labels = [], []
    for text, is_target in parts:
        t = tok.encode(text).ids
        ids.extend(t)
        labels.extend(t if is_target else [-100] * len(t))
    if len(ids) > max_len:
        ids, labels = ids[:max_len], labels[:max_len]
        # keep at least one supervised token
        if all(l == -100 for l in labels):
            labels[-1] = ids[-1]
    return ids, labels


def load_dataset(paths: list[Path], tok, max_len: int, seed: int) -> list[tuple[list[int], list[int]]]:
    rows = []
    for p in paths:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(format_example(json.loads(line), tok, max_len))
    rng = random.Random(seed)
    rng.shuffle(rows)
    return rows


def collate(batch, pad_id: int, device="cpu"):
    maxlen = max(len(x) for x, _ in batch)
    x = torch.full((len(batch), maxlen), pad_id, dtype=torch.long)
    y = torch.full((len(batch), maxlen), -100, dtype=torch.long)
    for i, (ids, labels) in enumerate(batch):
        x[i, :len(ids)] = torch.tensor(ids, dtype=torch.long)
        y[i, :len(labels)] = torch.tensor(labels, dtype=torch.long)
    return x, y


# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="checkpoint .pt or HF dir to adapt")
    ap.add_argument("--config", default="", help="config json (only needed for bare state dicts)")
    ap.add_argument("--tokenizer", default="tokenizer/shennong-bpe")
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True, help="output run directory")
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--max-seq", type=int, default=512)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--alpha", type=float, default=16.0)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    from tokenizers import Tokenizer

    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    tok = Tokenizer.from_file(str(Path(args.tokenizer) / "tokenizer.json"))
    pad_id = tok.token_to_id("<|pad|>") or 0

    base = Path(args.base)
    if base.is_dir():
        from to_hf import load_hf_model

        model = load_hf_model(base)
    else:
        ck = load_checkpoint(base)
        cfg = ModelConfig.from_dict(ck["config"])
        model = ShennongMini(cfg)
        model.load_state_dict(ck["model"], strict=False)
    cfg = model.cfg
    if cfg.vocab_size != tok.get_vocab_size():
        raise SystemExit(f"tokenizer vocab {tok.get_vocab_size()} != model vocab {cfg.vocab_size}")

    n_left = inject_lora(model, args.rank, args.alpha)
    if n_left == 0:
        raise SystemExit("no target Linear modules found — model layout changed?")
    # LoRA trains *only* the adapters: freeze embeddings, norms and anything else left over.
    for name, p in model.named_parameters():
        if not (name.endswith(".A") or name.endswith(".B")):
            p.requires_grad_(False)
    trainable = [p for p in model.parameters() if p.requires_grad]
    n_trainable = sum(p.numel() for p in trainable)
    print(f"injected LoRA into {n_left} projections: rank={args.rank} alpha={args.alpha} "
          f"trainable={n_trainable:,} / total={model.num_parameters():,}")

    rows = load_dataset([Path(p) for p in args.data], tok, args.max_seq, args.seed)
    print(f"loaded {len(rows)} instruction examples from {len(args.data)} file(s)")
    if not rows:
        raise SystemExit("no training rows")

    opt = torch.optim.AdamW(trainable, lr=args.lr, betas=(0.9, 0.95), weight_decay=0.0)
    run_dir = Path(args.out)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "log.jsonl"

    def lr_at(step: int) -> float:
        if step < args.warmup:
            return args.lr * (step + 1) / max(1, args.warmup)
        p = (step - args.warmup) / max(1, args.steps - args.warmup)
        return args.lr * (0.05 + 0.95 * 0.5 * (1 + math.cos(math.pi * min(1.0, p))))

    model.train()
    rng = random.Random(args.seed)
    t0 = time.time()
    losses = []
    for step in range(args.steps):
        lr = lr_at(step)
        for g in opt.param_groups:
            g["lr"] = lr
        batch = [rows[rng.randrange(len(rows))] for _ in range(args.batch)]
        x, y = collate(batch, pad_id)
        opt.zero_grad(set_to_none=True)
        logits, _ = model(x)
        loss = nn.functional.cross_entropy(logits.view(-1, logits.size(-1)).float(),
                                           y.reshape(-1), ignore_index=-100)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        opt.step()
        losses.append(float(loss))
        if step % 10 == 0 or step == args.steps - 1:
            entry = {"step": step, "loss": round(float(loss), 4), "lr": round(lr, 8),
                     "elapsed_s": round(time.time() - t0, 1)}
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
            print(f"step {step:>4} | loss {float(loss):.4f} | lr {lr:.2e} | "
                  f"{(time.time() - t0) / 60:.1f}m", flush=True)

    adapter = {"lora": lora_state_dict(model), "rank": args.rank, "alpha": args.alpha,
               "base_config": cfg.to_dict(),
               "data": [str(p) for p in args.data], "steps": args.steps, "seed": args.seed}
    torch.save(adapter, run_dir / "lora_adapter.pt")
    metrics = {
        "run_id": run_dir.name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base": str(args.base),
        "params_total": model.num_parameters(),
        "lora_trainable_params": n_trainable,
        "lora_projections": n_left,
        "rank": args.rank,
        "alpha": args.alpha,
        "examples": len(rows),
        "steps": args.steps,
        "wall_clock_s": round(time.time() - t0, 1),
        "final_train_loss": round(sum(losses[-10:]) / len(losses[-10:]), 4),
        "first_train_loss": round(losses[0], 4),
        "seed": args.seed,
        "torch_version": torch.__version__,
        "note": ("Hand-written instruction set of ~60 examples demonstrates the task shape; "
                 "this is not a capability claim. See training/data/README.md."),
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nsaved adapter -> {run_dir / 'lora_adapter.pt'}  "
          f"({(run_dir / 'lora_adapter.pt').stat().st_size:,} bytes)")
    print(f"final loss (last 10 mean) {metrics['final_train_loss']}  "
          f"({metrics['wall_clock_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
