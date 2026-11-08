#!/usr/bin/env python3
"""Retrain the upcycled MoE so its experts actually specialise.

Why the first MoE underperformed (-11.7 pts vs the dense 1.5B on 60 held-out questions): all four experts were
trained on the same mixed dataset. A learned top-2 router with no supervision has no reason to differentiate
them, so gradient descent gave every expert the same distribution — four copies of one expert, 4x the
parameters, none of the specialisation.

The fix is router supervision: add a cross-entropy term that teaches the router to predict the DOMAIN of each
sequence, so Track-1 tokens (classical texts, plant names across eras) flow to their own experts and Track-2
tokens (compounds, targets, pharmacology) to theirs. Experts then specialise because they only receive their
own domain's gradients.

Domains (4 experts, split from the 12 data kinds so each expert gets a coherent body of knowledge):
    0 classical   classical_use + formula          ~23.6k   classical Chinese therapeutics
    1 ethnobotany use                             ~29.9k   recorded uses across traditions
    2 natprod     target + pharmacology + compound + candidate + viability   ~22.6k
    3 identity    name_mapping + property + relation + incompatibility      ~12.0k

    python notebooks/train_moe_domains.py --out training/runs/moe-domains --max-steps 1800
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import torch
import torch.nn.functional as F

ROOT = pathlib.Path(__file__).resolve().parent.parent

DOMAINS = {
    0: ("classical", {"classical_use", "formula"}),
    1: ("ethnobotany", {"use"}),
    2: ("natprod", {"target", "pharmacology", "compound", "candidate", "viability"}),
    3: ("identity", {"name_mapping", "property", "relation", "incompatibility"}),
}
KIND_TO_DOMAIN = {k: d for d, (_, kinds) in DOMAINS.items() for k in kinds}


def preflight() -> None:
    if not torch.cuda.is_available():
        raise SystemExit(
            "No CUDA device. Runtime -> Change runtime type -> T4 GPU, then re-run.\n"
            "Training on CPU would take ~30 h; this script refuses."
        )
    print(f"GPU: {torch.cuda.get_device_name(0)} | {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")


def load_examples(path: pathlib.Path) -> list[dict]:
    out = []
    for line in path.open(encoding="utf-8"):
        r = json.loads(line)
        d = KIND_TO_DOMAIN.get(r.get("kind", ""))
        if d is not None and r.get("text"):
            out.append({"text": r["text"], "domain": d})
    return out


class Tokenised(torch.utils.data.Dataset):
    def __init__(self, rows, tok, max_len=384):
        self.rows, self.tok, self.max_len = rows, tok, max_len

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        ids = self.tok(r["text"], truncation=True, max_length=self.max_len, padding=False)["input_ids"]
        # mask the prompt: only the assistant reply contributes to the LM loss
        prompt_ids = self.tok(r["text"].split("<|assistant|>")[0] + "<|assistant|>",
                              truncation=True, max_length=self.max_len)["input_ids"]
        labels = list(ids)
        for j in range(min(len(prompt_ids), len(labels))):
            labels[j] = -100
        if not any(l != -100 for l in labels):
            labels[-1] = ids[-1]
        return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels, "domain": r["domain"]}


def collate(batch, pad_id):
    n = max(len(b["input_ids"]) for b in batch)
    def pad(v, val): return [x + [val] * (n - len(x)) for x in v]
    return {
        "input_ids": torch.tensor(pad([b["input_ids"] for b in batch], pad_id)),
        "attention_mask": torch.tensor(pad([b["attention_mask"] for b in batch], 0)),
        "labels": torch.tensor(pad([b["labels"] for b in batch], -100)),
        "domain": torch.tensor([b["domain"] for b in batch]),
    }


class DomainTrainer:
    """LM loss + router-domain cross entropy, so the router actually learns which expert owns what."""

    def __init__(self, model, tok, lam=0.1):
        self.model, self.tok, self.lam = model, tok, lam

    def step(self, batch):
        domain = batch.pop("domain")
        out = self.model(**batch, output_router_logits=True)
        lm = out.loss
        router = getattr(out, "router_logits", None)
        if not router:
            return lm
        bsz = domain.size(0)
        ce = 0.0
        for r in router:
            if r is None or r.dim() != 2:
                continue
            per_seq = r.view(bsz, -1, r.size(-1)).mean(dim=1)      # (B, n_experts)
            ce = ce + F.cross_entropy(per_seq, domain)
        ce = ce / max(1, len(router))
        return lm + self.lam * ce


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="artifacts/upcycled-moe")
    ap.add_argument("--out", default="training/runs/moe-domains")
    ap.add_argument("--max-steps", type=int, default=1800)
    ap.add_argument("--lam", type=float, default=0.1, help="weight of the router domain loss")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--resume", default=None)
    args = ap.parse_args()

    preflight()
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

    train = load_examples(ROOT / "artifacts/sft/train.jsonl")
    val = load_examples(ROOT / "artifacts/sft/val.jsonl")
    counts = {DOMAINS[d][0]: sum(1 for r in train if r["domain"] == d) for d in DOMAINS}
    print(f"train {len(train)} / val {len(val)} | per domain: {counts}")
    if any(v == 0 for v in counts.values()):
        raise SystemExit(f"a domain has no examples: {counts}")

    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float16)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    cfg = LoraConfig(r=64, lora_alpha=128, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                     "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, cfg)
    model.print_trainable_parameters()
    model.train()

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.01)
    sched = get_cosine_schedule_with_warmup(opt, 10, args.max_steps)

    ds = Tokenised(train, tok)
    dl = torch.utils.data.DataLoader(ds, batch_size=4, shuffle=True, num_workers=0,
                                     collate_fn=lambda b: collate(b, tok.pad_token_id or tok.eos_token_id))
    trainer = DomainTrainer(model, tok, lam=args.lam)

    step, running = 0, 0.0
    while step < args.max_steps:
        for batch in dl:
            batch = {k: v.to("cuda") for k, v in batch.items()}
            with torch.autocast("cuda", dtype=torch.float16):
                loss = trainer.step(batch)
            (loss / 4).backward()
            if (step + 1) % 4 == 0:
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            running += loss.item()
            step += 1
            if step % 25 == 0:
                print(f"step {step}/{args.max_steps} loss {running/25:.4f} lr {sched.get_last_lr()[0]:.2e}",
                      flush=True)
                running = 0.0
            if step % 500 == 0:
                p = pathlib.Path(args.out) / f"ckpt-{step}"
                p.mkdir(parents=True, exist_ok=True)
                model.save_pretrained(p)
                tok.save_pretrained(p)
                print(f"  saved {p}", flush=True)
            if step >= args.max_steps:
                break

    merged = pathlib.Path(args.out) / "merged"
    merged.mkdir(parents=True, exist_ok=True)
    model.merge_and_unload().save_pretrained(merged, safe_serialization=True)
    tok.save_pretrained(merged)
    print(f"saved model -> {merged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
