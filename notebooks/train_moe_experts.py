#!/usr/bin/env python3
"""Train the MoE-of-LoRAs: one LoRA adapter per domain on the SAME base model.

Unlike notebooks/train_gpu.py (which merges the adapter into a single dense model), this keeps each domain as
a separate adapter that is swapped at inference. That is what makes it a mixture of *experts* rather than one
model that saw everything.

    python notebooks/train_moe_experts.py --domains t2_natprod safety     # quick pair
    python notebooks/train_moe_experts.py --domains t1_classical t2_natprod safety --epochs 2
    python notebooks/train_moe_experts.py --domain t1_classical --sample 20000 --epochs 1   # if short on time

Output: training/runs/moe/<domain>/adapter (PEFT), then convert to GGUF with llama.cpp:

    python llama.cpp/convert_lora_to_gguf.py training/runs/moe/<domain>/adapter \\
        --outfile training/runs/moe/<domain>/<domain>.gguf --outtype q8_0
"""
from __future__ import annotations

import argparse
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DOMAINS_DIR = REPO / "artifacts" / "sft" / "domains"
BASE_MODEL = "Qwen/Qwen2.5-1.5B"
OUT_ROOT = REPO / "training" / "runs" / "moe"
MAX_LEN = 384


def load_examples(domain: str, split: str) -> list[dict]:
    p = DOMAINS_DIR / f"{domain}.jsonl"
    rows = []
    for line in p.open(encoding="utf-8"):
        if not line.strip():
            continue
        ex = json.loads(line)
        if ex.get("split") == split:
            rows.append(ex)
    return rows


def tokenize_pair(tok, text: str) -> dict | None:
    marker = "<|assistant|>"
    if marker not in text:
        return None
    prompt_part = text.split(marker, 1)[0] + marker
    ids = tok(text, truncation=True, max_length=MAX_LEN)["input_ids"]
    pids = tok(prompt_part, truncation=True, max_length=MAX_LEN)["input_ids"]
    labels = list(ids)
    for i in range(min(len(pids), len(labels))):
        labels[i] = -100          # only train on the answer
    return {"input_ids": ids, "labels": labels}


def collate(batch, pad_id):
    import torch
    t = max(len(b["input_ids"]) for b in batch)
    ids = torch.full((len(batch), t), pad_id, dtype=torch.long)
    labels = torch.full((len(batch), t), -100, dtype=torch.long)
    for i, b in enumerate(batch):
        ids[i, : len(b["input_ids"])] = torch.tensor(b["input_ids"])
        labels[i, : len(b["labels"])] = torch.tensor(b["labels"])
    return {"input_ids": ids, "labels": labels, "attention_mask": (ids != pad_id).long()}


def train_one(domain: str, args, tok, model_factory):
    import torch
    train_rows = load_examples(domain, "train")
    val_rows = load_examples(domain, "val")
    if args.sample and len(train_rows) > args.sample:
        import random
        random.Random(1337).shuffle(train_rows)
        train_rows = train_rows[: args.sample]
    train = [t for t in (tokenize_pair(tok, r["text"]) for r in train_rows) if t]
    val = [t for t in (tokenize_pair(tok, r["text"]) for r in val_rows) if t]
    print(f"\n=== {domain}: {len(train):,} train / {len(val):,} val ===", flush=True)

    from peft import LoraConfig, get_peft_model
    from transformers import Trainer, TrainingArguments
    import torch.utils.data as tud

    model = model_factory()
    lora = LoraConfig(r=args.r, lora_alpha=args.r * 2, lora_dropout=0.05,
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"],
                      task_type="CAUSAL_LM")
    model = get_peft_model(model, lora)
    print(f"trainable: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    class DS(tud.Dataset):
        def __init__(self, items): self.items = items
        def __len__(self): return len(self.items)
        def __getitem__(self, i): return self.items[i]

    out = OUT_ROOT / domain
    ta = TrainingArguments(
        output_dir=str(out), per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=4, num_train_epochs=args.epochs, max_steps=args.max_steps,
        learning_rate=args.lr, lr_scheduler_type="cosine", warmup_steps=10,
        logging_steps=20, save_strategy="epoch", eval_strategy="epoch",
        bf16=False, fp16=True, report_to=[], seed=1337, save_total_limit=2,
    )
    trainer = Trainer(model=model, args=ta, train_dataset=DS(train), eval_dataset=DS(val),
                      data_collator=lambda b: collate(b, tok.pad_token_id))
    trainer.train()

    # keep the ADAPTER (not merged): this is the expert
    adapter_dir = out / "adapter"
    trainer.model.save_pretrained(adapter_dir, safe_serialization=True)
    tok.save_pretrained(adapter_dir)
    print(f"saved adapter -> {adapter_dir}")
    del model, trainer
    torch.cuda.empty_cache()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", default=["t1_classical", "t2_natprod", "safety"])
    ap.add_argument("--r", type=int, default=32)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--sample", type=int, default=0, help="cap the training rows per domain (0 = all)")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"base: {BASE_MODEL}")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def model_factory():
        from transformers import AutoModelForCausalLM as M
        return M.from_pretrained(BASE_MODEL, torch_dtype=torch.float16, device_map="auto")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for d in args.domains:
        train_one(d, args, tok, model_factory)

    print("\n=== next: convert each adapter to GGUF (llama.cpp) ===")
    for d in args.domains:
        print(f"  python convert_lora_to_gguf.py training/runs/moe/{d}/adapter "
              f"--outfile artifacts/adapters/{d}.gguf --outtype q8_0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
