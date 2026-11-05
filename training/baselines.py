"""Compute trivial baselines for the held-out stream — the honesty test for the model.

A language model that cannot beat a **unigram token model** (no context at all) has learned
nothing beyond token frequency. This script computes, on the *exact* validation token stream
used by training (from the token cache):

  * uniform over the vocabulary:  log2(vocab) bits/token
  * add-one smoothed unigram:     -log2 p(token) from training-split frequencies
  * raw UTF-8 bytes:              8 bits/byte by definition (the "no model" baseline)

and converts all of them to **bits per byte** (the cross-tokenizer comparable metric), using the
UTF-8 byte count of the tokens actually scored.

Usage
-----
    python training/baselines.py --run training/runs/shennong-mini-r1
Writes:
    training/runs/<run>/baselines.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "training" / "cache"


def cache_key_for(run_meta: dict) -> str:
    tok_rel = (run_meta.get("args") or {}).get("tokenizer") or "tokenizer/shennong-bpe/tokenizer.json"
    tok_path = ROOT / tok_rel
    if not tok_path.exists():
        return ""
    return tok_path.parent.name + "-" + hashlib.sha256(tok_path.read_bytes()).hexdigest()[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="training/runs/shennong-mini-r1")
    ap.add_argument("--tokenizer", default="", help="defaults to the run's tokenizer")
    args = ap.parse_args()

    from tokenizers import Tokenizer

    run_dir = ROOT / args.run
    run_meta = {}
    if (run_dir / "run.json").exists():
        run_meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))

    tok_path = Path(args.tokenizer) if args.tokenizer else ROOT / (
        (run_meta.get("args") or {}).get("tokenizer") or "tokenizer/shennong-bpe/tokenizer.json")
    tok = Tokenizer.from_file(str(tok_path))
    vocab = tok.get_vocab_size()

    key = cache_key_for(run_meta)
    train_p = CACHE / f"train_{key}.npy"
    val_p = CACHE / f"val_{key}.npy"
    if not (train_p.exists() and val_p.exists()):
        raise SystemExit(f"token cache not found for key {key!r} ({train_p})")

    train = np.load(train_p, mmap_mode="r")
    val = np.load(val_p)
    val_ids = val.astype(np.int64)
    n_tok = int(val_ids.size)

    counts = np.bincount(np.asarray(train, dtype=np.int64), minlength=vocab).astype(np.float64)
    probs = (counts + 1.0) / (counts.sum() + vocab)      # add-one smoothing
    logp = -np.log2(probs)
    unigram_bits = float(logp[val_ids].sum())

    # bytes actually covered by the scored val token stream
    n_bytes = 0
    for start in range(0, n_tok - 1, 512):
        w = val_ids[start:start + 512].tolist()
        if len(w) < 2:
            break
        n_bytes += len(tok.decode(w).encode("utf-8"))

    res = {
        "baselines": {
            "uniform_over_vocab": {
                "bits_per_token": round(math.log2(vocab), 4),
                "bits_per_byte": round(math.log2(vocab) * n_tok / n_bytes, 4),
                "note": f"uniform distribution over the {vocab}-token vocabulary",
            },
            "unigram_token_model": {
                "bits_per_token": round(unigram_bits / n_tok, 4),
                "bits_per_byte": round(unigram_bits / n_bytes, 4),
                "note": "add-one-smoothed unigram over the training split, evaluated on the same "
                        "held-out token stream; no context is used",
            },
            "utf8_bytes": {"bits_per_byte": 8.0,
                           "note": "no model: 8 bits per byte by definition"},
        },
        "val_tokens": n_tok,
        "val_utf8_bytes": n_bytes,
        "vocab_size": vocab,
        "cache_key": key,
        "train_tokens": int(np.asarray(train).size),
        "tokenizer": str(tok_path),
    }
    out = run_dir / "baselines.json"
    out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
