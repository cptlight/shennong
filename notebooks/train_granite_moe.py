#!/usr/bin/env python3
"""Fine-tune a REAL sparse MoE — ibm-granite/granite-3.0-1b-a400m — on the SHENNONG corpus.

This is a genuine mixture-of-experts: GraniteMoeForCausalLM has 32 experts per layer with a top-8 router
INSIDE the network. Every training example flows through the whole model — the router learns which experts to
fire for TCM/Ayurvedic/pharmacology questions — so all of our data is taught to the model, not split per
expert the way the LoRA-adapter version did.

    python notebooks/train_granite_moe.py --epochs 1 --sample 40000     # ~1.2 h on a T4
    python notebooks/train_granite_moe.py --epochs 1                    # full 88k, ~2.5 h

Output: training/runs/granite-moe/merged (fp16 safetensors) -> convert to GGUF Q4_K_M (~822 MB).
"""
from __future__ import annotations

import argparse
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
SFT = REPO / "artifacts" / "sft"
BASE_MODEL = "ibm-granite/granite-3.0-1b-a400m-instruct"
MAX_LEN = 384

# GraniteMoe names its FFN projections gate_up_proj / down_proj (NOT gate_proj + up_proj like Llama/Qwen)
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_up_proj", "down_proj"]


def load_examples(split: str) -> list[dict]:
    p = SFT / f"{split}.jsonl"
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def tokenize_pair(tok, text: str) -> dict | None:
    """Train on the answer only; the prompt tokens are masked with -100."""
    marker = "<|assistant|>"
    if marker not in text:
        return None
    prompt_part = text.split(marker, 1)[0] + marker
    ids = tok(text, truncation=True, max_length=MAX_LEN)["input_ids"]
    pids = tok(prompt_part, truncation=True, max_length=MAX_LEN)["input_ids"]
    labels = list(ids)
    for i in range(min(len(pids), len(labels))):
        labels[i] = -100
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE_MODEL)
    ap.add_argument("--r", type=int, default=32)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--sample", type=int, default=0, help="cap training rows (0 = all)")
    ap.add_argument("--full-finetune", action="store_true",
                    help="train ALL weights (the experts are batched Parameters, so LoRA cannot reach them). "
                         "Uses Adafactor + gradient checkpointing to fit a T4.")
    ap.add_argument("--out", default=str(REPO / "training/runs/granite-moe"))
    args = ap.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    # ---- PREFLIGHT: fail in 5 seconds, not 40 minutes ----
    print(f"device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    if not torch.cuda.is_available():
        raise SystemExit("PREFLIGHT FAIL: torch cannot see a GPU. Runtime -> Change runtime type -> T4 GPU. "
                         "No pip command fixes this.")
    print(f"torch {torch.__version__} | cuda {torch.version.cuda}")
    try:
        from transformers import GraniteMoeForCausalLM  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"PREFLIGHT FAIL: no GraniteMoeForCausalLM "
                         f"(transformers {__import__('transformers').__version__}). "
                         f"pip install \"transformers==4.46.3\". {exc}")
    train_rows_probe = SFT / "train.jsonl"
    if not train_rows_probe.exists():
        raise SystemExit(f"PREFLIGHT FAIL: missing {train_rows_probe} — clone the repo properly.")
    print(f"base: {args.base}")

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # fp16 weights produce fp16 gradients, and the GradScaler then dies with
    # "Attempting to unscale FP16 gradients". Full fine-tune therefore keeps fp32 master weights and lets
    # autocast handle fp16 compute; LoRA can stay fp16 because only the adapters get gradients.
    load_dtype = torch.float32 if args.full_finetune else (
        torch.float16 if torch.cuda.is_available() else torch.float32)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=load_dtype,
        device_map="auto" if torch.cuda.is_available() else None)
    print(f"loaded in {str(load_dtype).replace('torch.','')}")
    print(f"params: {sum(p.numel() for p in model.parameters()):,}")

    if args.full_finetune:
        # GraniteMoeExperts.down_proj / gate_up_proj are batched Parameters, not nn.Linear — PEFT cannot
        # attach LoRA to them, so attention-only LoRA leaves the experts frozen. Full FT trains the real MoE.
        for p_ in model.parameters():
            p_.requires_grad_(True)
        model.gradient_checkpointing_enable()
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"FULL FINE-TUNE — trainable: {trainable:,} (experts included)")
        optim_name = "adafactor"      # factorised states: the only optimiser that fits a T4 at 1.33 B
    else:
        lora = LoraConfig(r=args.r, lora_alpha=args.r * 2, lora_dropout=0.05,
                          target_modules=TARGET_MODULES, task_type="CAUSAL_LM")
        model = get_peft_model(model, lora)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"LoRA trainable: {trainable:,}")
        if trainable == 0:
            raise SystemExit(f"PREFLIGHT FAIL: LoRA attached to 0 params. target_modules={TARGET_MODULES} "
                             f"matched nothing in this build.")
        matched = sorted({n.rsplit(".", 1)[0].split(".")[-1] for n, _ in model.named_modules()
                          if any(n.endswith(t) for t in TARGET_MODULES)})
        print(f"LoRA target modules matched: {matched[:8]}")
        optim_name = "adamw_torch"

    batch = args.batch
    accum = 4
    if args.full_finetune and args.batch == 4:
        batch, accum = 1, 16     # fp32 weights+grads need the headroom; keep the effective batch at 16
        print(f"full fine-tune: batch {batch} x accum {accum} (effective {batch*accum})")

    train_rows = load_examples("train")
    val_rows = load_examples("val")
    if args.sample and len(train_rows) > args.sample:
        import random
        random.Random(1337).shuffle(train_rows)
        train_rows = train_rows[: args.sample]
    train = [t for t in (tokenize_pair(tok, r["text"]) for r in train_rows) if t]
    val = [t for t in (tokenize_pair(tok, r["text"]) for r in val_rows) if t]
    print(f"examples: {len(train):,} train / {len(val):,} val")

    import torch.utils.data as tud

    class DS(tud.Dataset):
        def __init__(self, items): self.items = items
        def __len__(self): return len(self.items)
        def __getitem__(self, i): return self.items[i]

    ta = TrainingArguments(
        output_dir=args.out, per_device_train_batch_size=batch,
        gradient_accumulation_steps=accum, num_train_epochs=args.epochs, max_steps=args.max_steps,
        learning_rate=args.lr, lr_scheduler_type="cosine", warmup_steps=10,
        logging_steps=20, save_strategy="epoch", eval_strategy="epoch",
        bf16=False, fp16=torch.cuda.is_available(), report_to=[], seed=1337, save_total_limit=1,
        optim=optim_name,
    )
    trainer = Trainer(model=model, args=ta, train_dataset=DS(train), eval_dataset=DS(val),
                      data_collator=lambda b: collate(b, tok.pad_token_id))
    trainer.train()

    merged = trainer.model.merge_and_unload() if not args.full_finetune else trainer.model
    out_model = pathlib.Path(args.out) / "merged"
    merged.save_pretrained(out_model, safe_serialization=True)
    tok.save_pretrained(out_model)
    print(f"saved -> {out_model}")
    print(f"params: {sum(p.numel() for p in merged.parameters()):,}")
    print("\nNEXT — convert to GGUF (llama.cpp supports GRANITE_MOE natively):")
    print(f"  python llama.cpp/convert_hf_to_gguf.py {out_model} --outfile granite-moe-f16.gguf --outtype f16")
    print("  python llama.cpp/llama-quantize granite-moe-f16.gguf granite-moe-Q4_K_M.gguf Q4_K_M")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
