#!/usr/bin/env python3
"""Free-GPU training: fine-tune Qwen2.5-0.5B (Apache-2.0) into a sub-1 GB Track-02 specialist.

Run this in one cell on a free GPU (Colab T4 or Kaggle), or on CPU as a fallback. It is the same job our
19 M model was too small to do: take a *capable* base, teach it our domain corpus and our task shape, and
quantize it so it still runs on a laptop.

The honest reason for the base choice is in docs/USE.md and docs/COMPUTE.md: the corpus is ~29.8 M tokens,
so a from-scratch 0.5B would be ~16x data-starved. Fine-tuning a pretrained 0.5B with LoRA on that corpus is
the right size of change, and Qwen2.5-0.5B is Apache-2.0 (no licence contamination).

    # in Colab / Kaggle, one cell:
    !git clone https://github.com/cptlight/shennong && cd shennong
    !pip install -q transformers peft accelerate datasets huggingface_hub
    !python notebooks/train_gpu.py --epochs 3 --max_steps -1
"""
from __future__ import annotations

import argparse
import json
import pathlib

import torch

REPO = pathlib.Path(__file__).resolve().parent.parent
SFT = REPO / "artifacts" / "sft"
BASE_MODEL = "Qwen/Qwen2.5-0.5B"
ASSISTANT = "<|assistant|>"


def load_examples(split: str) -> list[dict]:
    rows = []
    for line in (SFT / f"{split}.jsonl").open(encoding="utf-8"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def tokenize_pair(tok, text: str, max_len: int = 1024):
    """Prompt masked, response kept — the response-only objective that made the 19 M model learn task shape."""
    i = text.find(ASSISTANT)
    if i < 0:
        return None
    prompt = text[: i + len(ASSISTANT)]
    response = text[i + len(ASSISTANT):].strip()
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    r_ids = tok(response, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
    input_ids = (p_ids + r_ids)[:max_len]
    labels = [-100] * min(len(p_ids), len(input_ids)) + r_ids[: max(0, len(input_ids) - len(p_ids))]
    labels += [-100] * (len(input_ids) - len(labels))
    return {"input_ids": input_ids, "labels": labels}


def collate(batch, pad_id: int):
    t = max(len(b["input_ids"]) for b in batch)
    ids = torch.full((len(batch), t), pad_id, dtype=torch.long)
    labels = torch.full((len(batch), t), -100, dtype=torch.long)
    for i, b in enumerate(batch):
        ids[i, : len(b["input_ids"])] = torch.tensor(b["input_ids"])
        labels[i, : len(b["labels"])] = torch.tensor(b["labels"])
    return {"input_ids": ids, "labels": labels, "attention_mask": (ids != pad_id).long()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--max-steps", type=int, default=-1, help="-1 = full epochs")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--out", default=str(REPO / "training/runs/gpu-sft"))
    args = ap.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer

    print(f"device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # Load fp32 and let the Trainer's fp16=True do mixed precision (fp32 master weights, fp16 autocast).
    # Loading fp16 directly made the GradScaler fail with "Attempting to unscale FP16 gradients" — there
    # were no fp32 master weights to unscale.
    # Force fp32: Qwen2.5-0.5B's config.json declares bfloat16, and from_pretrained honours it, which makes
    # the Trainer's fp16 GradScaler die with "not implemented for 'BFloat16'". fp32 master weights + fp16
    # autocast is the recipe that works on a T4.
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float32,
        device_map="auto" if torch.cuda.is_available() else None)

    # FULL fine-tuning, not LoRA. peft's LoRA path now requires torchao>=0.16 and Colab ships 0.10, which
    # is exactly the ImportError that killed the first run. At 494M params full FT needs ~5-6 GB on a T4,
    # fits comfortably, and is strictly better than LoRA at this size.
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"trainable (full FT): {trainable:,} params")

    train = [t for t in (tokenize_pair(tok, r["text"]) for r in load_examples("train")) if t]
    val = [t for t in (tokenize_pair(tok, r["text"]) for r in load_examples("val")) if t]
    print(f"examples: {len(train)} train / {len(val)} val")

    # a tiny Dataset-compatible wrapper so the Trainer stays in one file
    import torch.utils.data as tud
    class DS(tud.Dataset):
        def __init__(self, items):
            self.items = items
        def __len__(self):
            return len(self.items)
        def __getitem__(self, i):
            return self.items[i]

    ta = TrainingArguments(
        output_dir=args.out, per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=4, num_train_epochs=args.epochs, max_steps=args.max_steps,
        learning_rate=args.lr, lr_scheduler_type="cosine", warmup_steps=10,
        logging_steps=20, save_strategy="epoch", eval_strategy="epoch",
        bf16=False, fp16=torch.cuda.is_available(), report_to=[],
        seed=1337, save_total_limit=2,
    )
    trainer = Trainer(model=model, args=ta, train_dataset=DS(train), eval_dataset=DS(val),
                      data_collator=lambda b: collate(b, tok.pad_token_id))
    trainer.train()

    # save full fp16 weights for quantization
    out_model = pathlib.Path(args.out) / "merged"
    model.save_pretrained(out_model, safe_serialization=True)
    tok.save_pretrained(out_model)
    print(f"saved model -> {out_model}")
    print(f"params: {sum(p.numel() for p in model.parameters()):,}")
    print("NEXT: quantize to GGUF Q4_K_M (~380 MB) — see scripts/export_to_gguf.py on the target machine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
