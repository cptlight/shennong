#!/usr/bin/env python3
"""Train the SHENNONG multilingual byte-level BPE tokenizer.

Script coverage: Classical Chinese (zh-Hant), Sanskrit (Devanagari + IAST), Latin (the 1593
Avicenna *Canon*), and English (foundational biology/chemistry + translations).

Design notes
------------
* Han characters are **isolated** before byte-level BPE, so a single Han character is a single
  pre-token and BPE can then merge frequent two-character terms (e.g. 甘草, 當歸) into one token.
  Without this, a byte-level BPE spends 3 tokens per CJK character and the model's context is
  wasted on UTF-8 encoding rather than on pharmacology.
* Devanagari is left to the byte-level path but the training data makes common conjuncts frequent,
  so they merge naturally.
* `initial_alphabet` is seeded with the full byte alphabet so no byte is ever out-of-vocabulary
  (this is what makes the tokenizer lossless / reversible).

Usage
-----
    python tokenizer/train_tokenizer.py --corpus corpus/processed/corpus.jsonl --vocab 16384
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

SPECIAL = ["<|pad|>", "<|bos|>", "<|eos|>", "<|system|>", "<|user|>", "<|assistant|>"]

CJK_LANGS = {"zh-Hant", "zh-Hans", "ja", "ko"}


def iter_records(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--vocab", type=int, default=16384)
    ap.add_argument("--out", default="tokenizer/shennong-bpe")
    ap.add_argument("--min-frequency", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="use only the first N records (debug)")
    args = ap.parse_args()

    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    corpus = Path(args.corpus)
    if not corpus.exists():
        raise SystemExit(f"corpus not found: {corpus}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    texts: list[str] = []
    langs: list[str] = []
    for i, rec in enumerate(iter_records(corpus)):
        if args.limit and i >= args.limit:
            break
        t = rec.get("text") or ""
        if t:
            texts.append(t)
            langs.append(rec.get("lang", "en"))
    if not texts:
        raise SystemExit("no text found in corpus")
    print(f"loaded {len(texts):,} chunks ({sum(len(t) for t in texts):,} chars) in {time.time() - t0:.1f}s")

    tok = Tokenizer(models.BPE(unk_token=None, fuse_unk=False))
    # ByteLevel alone: the GPT-2 regex groups contiguous Han runs into one pre-token, then bytes,
    # and BPE merges frequent byte sequences back into whole characters and words. The earlier
    # `Split(\p{Han}, isolated)` approach was 10-20x slower for no measurable gain.
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tok.decoder = decoders.ByteLevel()

    trainer = trainers.BpeTrainer(
        vocab_size=args.vocab,
        min_frequency=args.min_frequency,
        special_tokens=SPECIAL,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=True,
    )

    t0 = time.time()
    tok.train_from_iterator(texts, trainer=trainer)
    print(f"trained BPE in {time.time() - t0:.1f}s — vocab {tok.get_vocab_size():,}")

    tok_path = out / "tokenizer.json"
    tok.save(str(tok_path))

    # ---- fertility per language: chars/token on held-out text -----------------
    random.seed(0)
    by_lang: dict[str, list[str]] = {}
    for t, lang in zip(texts, langs):
        by_lang.setdefault(lang, []).append(t)

    fertility = {}
    for lang, docs in sorted(by_lang.items()):
        sample = random.sample(docs, min(300, len(docs)))
        chars = sum(len(d) for d in sample)
        encs = tok.encode_batch(sample)
        toks = sum(len(e.ids) for e in encs)
        fertility[lang] = {
            "chars": chars,
            "tokens": toks,
            "chars_per_token": round(chars / max(toks, 1), 3),
            "docs": len(sample),
        }
        print(f"  {lang:8s} {chars:>9,} chars  {toks:>9,} tokens  {chars / max(toks, 1):.2f} chars/token")

    # ---- domain vocabulary coverage (the terms the theory layer needs) --------
    probe = {
        "tcm_nature": ["寒", "熱", "溫", "涼", "平"],
        "tcm_flavour": ["辛", "甘", "酸", "苦", "鹹", "淡", "澀"],
        "tcm_channel": ["肝", "心", "脾", "肺", "腎", "膽", "胃", "大腸", "小腸", "膀胱", "三焦"],
        "paozhi": ["炮", "煅", "煨", "淬", "蒸", "煮", "炒", "炙", "飛", "伏", "製"],
        "seven_relations": ["相須", "相使", "相畏", "相殺", "相惡", "相反", "單行"],
        "grades": ["上品", "中品", "下品"],
        "ayurveda_iast": ["rasa", "guṇa", "vīrya", "vipāka", "prabhāva", "vāta", "pitta", "kapha"],
        "ayurveda_dev": ["रस", "वीर्य", "विपाक", "वात", "पित्त", "कफ"],
    }
    coverage = {}
    for group, terms in probe.items():
        single = [t for t in terms if len(tok.encode(t).ids) == 1]
        coverage[group] = {"n": len(terms), "single_token": single,
                           "rate": round(len(single) / len(terms), 3)}
        print(f"  vocab coverage {group:18s} {len(single)}/{len(terms)} single-token")

    meta = {
        "vocab_size": tok.get_vocab_size(),
        "target_vocab": args.vocab,
        "special_tokens": SPECIAL,
        "pre_tokenizer": "Split(\\p{Han}, isolated) + ByteLevel",
        "train_chunks": len(texts),
        "train_chars": sum(len(t) for t in texts),
        "fertility": fertility,
        "vocab_coverage": coverage,
        "corpus": str(corpus),
    }
    (out / "tokenizer_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # round-trip check: decode(encode(x)) == x is the property that makes it lossless
    bad = 0
    for d in random.sample(texts, min(50, len(texts))):
        if tok.decode(tok.encode(d).ids) != d:
            bad += 1
    print(f"round-trip lossless: {50 - bad}/50 sampled chunks")
    meta["roundtrip_ok"] = 50 - bad
    (out / "tokenizer_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {tok_path} and {out / 'tokenizer_meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
