"""Evaluate a trained SHENNONG checkpoint and produce the numbers the model card may quote.

Everything here is measured, nothing is estimated:
  * held-out cross-entropy, perplexity and **bits-per-byte**, computed **per language**
    (bpb is the honest cross-script metric; perplexity is not comparable across tokenizers);
  * a **memorisation check** — 5 continuations from verbatim 40-token *training* prefixes,
    reporting how much of the true continuation is copied vs. produced;
  * 10 raw generations (5 English, 5 Classical Chinese) for `artifacts/samples.md`;
  * **inference throughput** for a 128-token generation (the product number: this is meant to
    run on a laptop CPU).

The validation split is reproduced exactly as `train_pretrain.py` built it: corpus documents
shuffled with `random.Random(0)`, first 2% held out. --per-lang caps how many held-out docs per
language are scored (CPU budget); the cap is reported.

Usage
-----
    python training/eval_model.py --run training/runs/shennong-mini-<ts> \
        --tokenizer tokenizer/shennong-bpe/tokenizer.json \
        --corpus corpus/processed/corpus.jsonl --out-dir artifacts
"""

from __future__ import annotations

import argparse
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

from shennong_mini import ModelConfig, ShennongMini, load_checkpoint  # noqa: E402

EN_PROMPTS = [
    "The processing of Aconitum in classical Chinese pharmacy is intended to",
    "Glycyrrhiza uralensis is described in the Bencao Gangmu as",
    "A falsifiable hypothesis connecting 炮制 (processing) to modern extraction chemistry:",
    "Salvia miltiorrhiza contains tanshinones, which",
    "The eighteen antagonisms (十八反) matter to pharmacology because",
]
ZH_PROMPTS = [
    "甘草味甘，性平，歸",
    "凡藥炮製之法，",
    "神農本草經曰：上品",
    "凡藥有十八反，其間",
    "傷寒論太陽病，脈浮",
]

LN2 = math.log(2.0)


# ---------------------------------------------------------------------------------------
# Data / split
# ---------------------------------------------------------------------------------------
def load_docs(corpus: Path) -> list[dict]:
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
                docs.append(rec)
    return docs


def reproduce_split(docs: list[dict], val_frac: float = 0.02, seed: int = 0):
    """Exactly the split in train_pretrain.build_token_file (Random(0).shuffle, first 2%).

    Returns (val_docs, train_indices) so callers can sample true training documents without
    comparing dicts (24k x dict-equality is both slow and ambiguous).
    """
    rng = random.Random(seed)
    order = list(range(len(docs)))
    rng.shuffle(order)
    n_val = max(1, int(len(docs) * val_frac))
    return [docs[i] for i in order[:n_val]], order[n_val:]


# ---------------------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------------------
@torch.no_grad()
def eval_language(model: ShennongMini, tok, docs: list[dict], lang: str, seq_len: int,
                  max_docs: int, batch: int = 4) -> dict:
    """Token-level CE on whole held-out chunks (concatenated with <|eos|>), then ppl + bpb."""
    eos = tok.token_to_id("<|eos|>")
    selected = [d for d in docs if d.get("lang") == lang][:max_docs]
    if not selected:
        return {}
    ids_list = []
    for d in selected:
        ids = tok.encode(d["text"]).ids
        ids.append(eos if eos is not None else 0)
        ids_list.append(ids)
    n_bytes = sum(len(d["text"].encode("utf-8")) for d in selected)

    total_nats, total_tokens = 0.0, 0
    model.eval()
    for i in range(0, len(ids_list), batch):
        chunk = ids_list[i:i + batch]
        # pad to the longest item in the batch; ignore_index skips the pad positions
        maxlen = min(seq_len, max(len(c) for c in chunk))
        x = torch.full((len(chunk), maxlen), 0, dtype=torch.long)
        y = torch.full((len(chunk), maxlen), -100, dtype=torch.long)
        for j, c in enumerate(chunk):
            c = c[:maxlen]
            x[j, :len(c)] = torch.tensor(c, dtype=torch.long)
            y[j, :len(c) - 1] = torch.tensor(c[1:], dtype=torch.long)
        logits, _ = model(x)
        # manual CE so we can count non-ignored targets exactly
        loss = torch.nn.functional.cross_entropy(
            logits.view(-1, logits.size(-1)).float(), y.reshape(-1), ignore_index=-100,
            reduction="sum")
        total_nats += float(loss)
        total_tokens += int((y != -100).sum())
    model.train()
    mean_nats = total_nats / max(total_tokens, 1)
    return {
        "lang": lang,
        "docs": len(selected),
        "tokens": total_tokens,
        "utf8_bytes": n_bytes,
        "mean_nats_per_token": round(mean_nats, 4),
        "perplexity": round(math.exp(mean_nats), 2) if mean_nats < 20 else None,
        "bits_per_byte": round(total_nats / (LN2 * max(n_bytes, 1)), 4),
        "bits_per_token": round(mean_nats / LN2, 4),
    }


@torch.no_grad()
def memorisation_check(model: ShennongMini, tok, train_docs: list[dict], seq_len: int,
                       n: int = 5, prefix_tokens: int = 40, gen_tokens: int = 60) -> list[dict]:
    """Start from a verbatim 40-token *training* prefix; how much is regurgitated?"""
    rng = random.Random(7)
    picks = rng.sample(range(len(train_docs)), min(n, len(train_docs)))
    rows = []
    for idx in picks:
        ids = tok.encode(train_docs[idx]["text"]).ids
        if len(ids) < prefix_tokens + 10:
            continue
        prefix = ids[:prefix_tokens]
        truth = ids[prefix_tokens:prefix_tokens + gen_tokens]
        x = torch.tensor([prefix], dtype=torch.long)
        out = model.generate(x, max_new_tokens=gen_tokens, temperature=0.7, top_k=40, top_p=0.9,
                             repetition_penalty=1.0, seed=idx)
        gen = out[0, len(prefix):].tolist()
        # longest common substring between generated and true continuations (in tokens)
        def lcs(a, b):
            best = 0
            prev = [0] * (len(b) + 1)
            for i in range(1, len(a) + 1):
                cur = [0] * (len(b) + 1)
                for j in range(1, len(b) + 1):
                    if a[i - 1] == b[j - 1]:
                        cur[j] = prev[j - 1] + 1
                        best = max(best, cur[j])
                prev = cur
            return best

        rows.append({
            "train_doc_index": idx,
            "prefix_tokens": prefix_tokens,
            "gen_tokens": len(gen),
            "longest_common_substring_tokens": lcs(gen, truth),
            "prefix": tok.decode(prefix),
            "generated": tok.decode(gen),
            "true_continuation": tok.decode(truth),
        })
    return rows


@torch.no_grad()
def timed_generation(model: ShennongMini, tok, prompt: str, n_tokens: int = 128,
                     seed: int = 0) -> dict:
    ids = tok.encode(prompt).ids
    x = torch.tensor([ids], dtype=torch.long)
    model.eval()
    t0 = time.time()
    out = model.generate(x, max_new_tokens=n_tokens, temperature=0.8, top_k=50, top_p=0.95, seed=seed)
    dt = time.time() - t0
    n_new = out.shape[1] - len(ids)
    return {
        "prompt": prompt,
        "new_tokens": n_new,
        "seconds": round(dt, 2),
        "tokens_per_s": round(n_new / dt, 1) if dt > 0 else None,
        "text": tok.decode(out[0, len(ids):].tolist()),
    }


# ---------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="training/runs/<run_id>")
    ap.add_argument("--ckpt", default="ckpt-best.pt", help="checkpoint file name inside the run dir")
    ap.add_argument("--tokenizer", default="tokenizer/shennong-bpe/tokenizer.json")
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--out-dir", default="artifacts")
    ap.add_argument("--per-lang", type=int, default=40, help="held-out docs scored per language")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--no-samples", action="store_true", help="skip generation (fast metrics only)")
    args = ap.parse_args()

    from tokenizers import Tokenizer

    torch.set_num_threads(args.threads)
    run_dir = Path(args.run)
    ckpt_path = run_dir / args.ckpt
    if not ckpt_path.exists():
        ckpt_path = run_dir / "ckpt.pt"
    ck = load_checkpoint(ckpt_path)
    cfg = ModelConfig.from_dict(ck["config"])
    model = ShennongMini(cfg)
    model.load_state_dict(ck["model"], strict=False)
    model.eval()
    tok = Tokenizer.from_file(args.tokenizer)
    if tok.get_vocab_size() != cfg.vocab_size:
        raise SystemExit(f"tokenizer vocab {tok.get_vocab_size()} != model vocab {cfg.vocab_size}")

    docs = load_docs(Path(args.corpus))
    val_docs, train_idx = reproduce_split(docs)
    print(f"corpus docs={len(docs):,}  held-out docs={len(val_docs):,} (~2%)")

    # --- per-language held-out metrics --------------------------------------------
    langs = sorted({d.get("lang", "?") for d in val_docs})
    per_lang = {}
    for lang in langs:
        m = eval_language(model, tok, val_docs, lang, cfg.seq_len, args.per_lang)
        if m:
            per_lang[lang] = m
            print(f"  {lang:8s} docs={m['docs']:3d} tok={m['tokens']:6d} "
                  f"CE={m['mean_nats_per_token']:.4f} ppl={m['perplexity']} "
                  f"bpb={m['bits_per_byte']:.4f}")
    if not per_lang:
        raise SystemExit("no held-out docs matched any language")

    tot_nats = sum(m["mean_nats_per_token"] * m["tokens"] for m in per_lang.values())
    tot_tok = sum(m["tokens"] for m in per_lang.values())
    tot_bytes = sum(m["utf8_bytes"] for m in per_lang.values())
    pooled = {
        "tokens": tot_tok,
        "utf8_bytes": tot_bytes,
        "mean_nats_per_token": round(tot_nats / max(tot_tok, 1), 4),
        "perplexity": round(math.exp(tot_nats / max(tot_tok, 1)), 2) if tot_nats / max(tot_tok, 1) < 20 else None,
        "bits_per_byte": round(tot_nats / (LN2 * max(tot_bytes, 1)), 4),
    }
    print(f"  POOLED   tok={pooled['tokens']} CE={pooled['mean_nats_per_token']:.4f} "
          f"ppl={pooled['perplexity']} bpb={pooled['bits_per_byte']:.4f}")

    # --- memorisation -------------------------------------------------------------
    train_docs = [docs[i] for i in train_idx]
    memor = memorisation_check(model, tok, train_docs, cfg.seq_len) if not args.no_samples else []
    if memor:
        mean_lcs = sum(r["longest_common_substring_tokens"] for r in memor) / len(memor)
        print(f"memorisation: mean longest verbatim run = {mean_lcs:.1f} tokens "
              f"(of {memor[0]['gen_tokens']} generated)")

    # --- samples + throughput -----------------------------------------------------
    samples, speed = [], None
    if not args.no_samples:
        for p in EN_PROMPTS:
            samples.append({"lang": "en", **timed_generation(model, tok, p)})
        for p in ZH_PROMPTS:
            samples.append({"lang": "zh-Hant", **timed_generation(model, tok, p)})
        speed = timed_generation(model, tok, EN_PROMPTS[0], n_tokens=128, seed=1)
        print(f"inference: {speed['new_tokens']} tokens in {speed['seconds']}s "
              f"= {speed['tokens_per_s']} tok/s (single-stream, {args.threads} threads)")

    result = {
        "run": run_dir.name,
        "checkpoint": str(ckpt_path),
        "params": model.num_parameters(),
        "config": cfg.to_dict(),
        "val_docs_total": len(val_docs),
        "per_lang_doc_cap": args.per_lang,
        "per_language": per_lang,
        "pooled": pooled,
        "memorisation": {
            "method": "generate 60 tokens from a verbatim 40-token training prefix "
                      "(temperature 0.7, top-k 40, top-p 0.9); longest common token run vs the "
                      "true continuation",
            "mean_longest_verbatim_run_tokens": (round(sum(r["longest_common_substring_tokens"]
                                                           for r in memor) / len(memor), 2)
                                                 if memor else None),
            "samples": memor,
        },
        "inference": speed,
        "samples": samples,
        "seed": 1337,
        "torch_version": torch.__version__,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "eval.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")

    # --- artifacts/samples.md -----------------------------------------------------
    md = ["# SHENNONG-mini — raw generated samples", "",
          f"Run: `{run_dir.name}` · checkpoint `{args.ckpt}` · "
          f"{model.num_parameters():,} parameters · CPU only", "",
          "These are **raw, unedited** continuations from the from-scratch model, greedily/"
          "stochastically sampled (temperature 0.8, top-k 50, top-p 0.95). A ~9 M-parameter "
          "model trained for a few hours on CPU is expected to be fluent-ish at short-range "
          "character statistics and unreliable at facts; the point of publishing them verbatim "
          "is that nothing here is cherry-picked or post-edited.", ""]
    if speed:
        md += [f"**Inference throughput:** {speed['tokens_per_s']} tokens/s for a 128-token "
               f"generation on this machine (single stream, CPU, {args.threads} threads).", ""]
    md += ["## English prompts", "", "| # | prompt | continuation |", "|---|---|---|"]
    en = [s for s in samples if s["lang"] == "en"]
    for i, s in enumerate(en, 1):
        md.append(f"| {i} | `{s['prompt']}` | {s['text'].strip()[:600].replace('|', '/')} |")
    md += ["", "## Classical Chinese (中文) prompts", "", "| # | prompt | continuation |", "|---|---|---|"]
    zh = [s for s in samples if s["lang"] == "zh-Hant"]
    for i, s in enumerate(zh, 1):
        md.append(f"| {i} | `{s['prompt']}` | {s['text'].strip()[:600].replace('|', '/')} |")
    if memor:
        md += ["", "## Memorisation check (verbatim training prefixes)", "",
               "Continuations from a verbatim 40-token prefix of **training** text. "
               "`LCS` is the longest verbatim run of tokens shared with the true continuation.", "",
               "| prefix | LCS (tokens) | generated |", "|---|---|---|"]
        for r in memor:
            md.append(f"| `{r['prefix'][:60]}` | {r['longest_common_substring_tokens']} / "
                      f"{r['gen_tokens']} | {r['generated'][:400].replace('|', '/')} |")
    (out_dir / "samples.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out_dir / 'samples.md'} and {run_dir / 'eval.json'}")

    # --- add the contract metric to metrics.json ----------------------------------
    mp = run_dir / "metrics.json"
    if mp.exists():
        m = json.loads(mp.read_text())
        m["bits_per_byte"] = pooled["bits_per_byte"]
        m["val_bpb_by_language"] = {k: v["bits_per_byte"] for k, v in per_lang.items()}
        m["val_ppl_by_language"] = {k: v["perplexity"] for k, v in per_lang.items()}
        m["inference_tokens_per_s"] = speed["tokens_per_s"] if speed else None
        mp.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"updated {mp} with bits_per_byte / per-language metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
