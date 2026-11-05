"""Measure tokenizer quality honestly: chars/token per language, bytes/token, and
coverage of the Asian-medicine theory vocabulary.

Why this script exists
----------------------
"chars per token" pooled over a multilingual corpus is meaningless: a tokenizer that shreds
Han into UTF-8 bytes and one that has real Han tokens can report the same pooled number.
So every metric here is computed **per language**, and a per-language **UTF-8 byte baseline**
(1 token per byte — the naive baseline) is printed next to it. The optional second baseline is
a ByteLevel-only BPE trained with the same vocab budget, which is what an off-the-shelf
tokenizer effectively is for CJK.

Usage
-----
    python tokenizer/eval_tokenizer.py --tokenizer tokenizer/shennong-bpe \
        --corpus corpus/processed/corpus.jsonl --out tokenizer/eval_results.json
    # add the trained ByteLevel baseline (slower, ~1-2 min on 8M chars):
    python tokenizer/eval_tokenizer.py --bytelevel-baseline --bytelevel-chars 8000000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

# Asian-medicine theory vocabulary (brief §11): must be in-vocabulary for the domain thesis
# to hold. Each entry: label -> list of probe strings.
THEORY_PROBES: dict[str, list[str]] = {
    # 四氣 (four natures)
    "tcm_nature": ["寒", "熱", "溫", "涼", "平"],
    # 五味 (five flavours) + 淡 澀
    "tcm_flavour": ["辛", "甘", "酸", "苦", "鹹", "淡", "澀"],
    # 歸經 channel names
    "tcm_channel": ["肝", "心", "脾", "肺", "腎", "膽", "胃", "大腸", "小腸", "膀胱", "三焦"],
    # 炮制 processing verbs
    "paozhi": ["炮", "煅", "煨", "淬", "蒸", "煮", "炒", "炙", "飛", "伏", "製"],
    # 七情 combination relations
    "seven_relations": ["相須", "相使", "相畏", "相殺", "相惡", "相反"],
    # 三品 (three grades)
    "grades": ["上品", "中品", "下品"],
    # Ayurvedic technical terms in IAST (Latin script)
    "ayurveda_iast": ["rasa", "guṇa", "guṇa", "vīrya", "vipāka", "doṣa", "vāta", "pitta", "kapha"],
    # …and in Devanagari
    "ayurveda_dev": ["रस", "गुण", "वीर्य", "विपाक", "दोष", "वात", "पित्त", "कफ"],
}


def load_chunks(corpus: Path, per_lang: int, seed: int) -> dict[str, list[str]]:
    """Deterministic per-language sample of corpus chunks (hash-selected, order-independent)."""
    by_lang: dict[str, list[str]] = {}
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            lang = rec.get("lang", "unknown")
            text = rec.get("text") or ""
            if len(text) < 100:
                continue
            bucket = int(hashlib.sha1(f"{seed}:{rec.get('id', '')}".encode()).hexdigest()[:8], 16)
            bucket %= 1000
            if bucket < 100:  # ~10% reservoir per language, deterministic
                by_lang.setdefault(lang, []).append(text)
    out = {}
    for lang, docs in by_lang.items():
        rng = random.Random(seed)
        rng.shuffle(docs)
        out[lang] = docs[:per_lang]
    return out


def metrics(tok, docs: list[str]) -> dict:
    chars = sum(len(d) for d in docs)
    nbytes = sum(len(d.encode("utf-8")) for d in docs)
    enc = tok.encode_batch(docs)
    toks = sum(len(e.ids) for e in enc)
    return {
        "docs": len(docs),
        "chars": chars,
        "utf8_bytes": nbytes,
        "tokens": toks,
        "chars_per_token": round(chars / toks, 3),
        "bytes_per_token": round(nbytes / toks, 3),
        "tokens_per_doc": round(toks / max(len(docs), 1), 1),
    }


def coverage(tok) -> dict:
    vocab = tok.get_vocab()
    report = {}
    for label, probes in THEORY_PROBES.items():
        rows = []
        for p in probes:
            ids = tok.encode(p).ids
            rows.append({"probe": p, "in_vocab": p in vocab, "n_tokens": len(ids),
                         "single_token": len(ids) == 1})
        report[label] = {
            "n": len(rows),
            "single_token": sum(r["single_token"] for r in rows),
            "rate": round(sum(r["single_token"] for r in rows) / len(rows), 3),
            "items": rows,
        }
    return report


def train_bytelevel_baseline(corpus: Path, vocab: int, max_chars: int, seed: int = 0):
    """Train a ByteLevel-only BPE (GPT-2 style pretokenizer) with the same vocab budget."""
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    texts, total = [], 0
    with corpus.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("text") or ""
            if not t:
                continue
            texts.append(t)
            total += len(t)
            if total >= max_chars:
                break
    tok = Tokenizer(models.BPE(unk_token=None))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=vocab, min_frequency=2,
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    t0 = time.time()
    tok.train_from_iterator(texts, trainer=trainer)
    return tok, {"trained_on_chars": total, "seconds": round(time.time() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", default="tokenizer/shennong-bpe")
    ap.add_argument("--corpus", default="corpus/processed/corpus.jsonl")
    ap.add_argument("--out", default="tokenizer/eval_results.json")
    ap.add_argument("--per-lang", type=int, default=200, help="held-out docs per language")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--bytelevel-baseline", action="store_true",
                    help="train a ByteLevel-only BPE baseline with the same vocab size")
    ap.add_argument("--bytelevel-chars", type=int, default=8_000_000)
    args = ap.parse_args()

    from tokenizers import Tokenizer

    tok_path = Path(args.tokenizer) / "tokenizer.json"
    ours = Tokenizer.from_file(str(tok_path))
    vocab_size = ours.get_vocab_size()

    chunks = load_chunks(Path(args.corpus), args.per_lang, args.seed)
    print(f"held-out sample: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(chunks.items())))

    results: dict = {
        "tokenizer": str(tok_path),
        "vocab_size": vocab_size,
        "seed": args.seed,
        "per_lang_docs": args.per_lang,
        "baselines": {
            "utf8_byte": "1 token per UTF-8 byte (naive; no merges, no unknown tokens)",
            "bytelevel_bpe": "BPE over ByteLevel GPT-2 pretokenizer, same vocab budget, "
                             "trained on the same corpus prefix",
        },
        "per_language": {},
        "theory_coverage": {},
    }

    baseline_tok = None
    if args.bytelevel_baseline:
        print("training ByteLevel-only BPE baseline …", flush=True)
        baseline_tok, bmeta = train_bytelevel_baseline(
            Path(args.corpus), vocab_size, args.bytelevel_chars, args.seed)
        results["baseline_meta"] = bmeta
        print(f"  baseline trained in {bmeta['seconds']}s on {bmeta['trained_on_chars']:,} chars")

    for lang in sorted(chunks):
        docs = chunks[lang]
        m = metrics(ours, docs)
        b = metrics(baseline_tok, docs) if baseline_tok is not None else None
        m["utf8_byte_baseline_chars_per_token"] = round(m["chars"] / m["utf8_bytes"], 3)
        if b:
            m["bytelevel_bpe_baseline_chars_per_token"] = b["chars_per_token"]
            m["chars_per_token_vs_bytelevel"] = round(m["chars_per_token"] / b["chars_per_token"], 3)
        results["per_language"][lang] = m
        line = (f"{lang:8s} chars/token={m['chars_per_token']:.3f}  "
                f"bytes/token={m['bytes_per_token']:.2f}  tokens/doc={m['tokens_per_doc']:.0f}  "
                f"vs utf8-bytes={m['chars_per_token'] / m['utf8_byte_baseline_chars_per_token']:.2f}x")
        if b:
            line += f"  vs bytelevel-bpe={m['chars_per_token'] / b['chars_per_token']:.2f}x"
        print(line)

    results["theory_coverage"] = coverage(ours)
    print("\ntheory-vocabulary coverage (single-token rate):")
    for label, rep in results["theory_coverage"].items():
        missing = [r["probe"] for r in rep["items"] if not r["single_token"]]
        print(f"  {label:16s} {rep['single_token']:2d}/{rep['n']:2d} = {rep['rate']:.2f}"
              + (f"   not single-token: {missing}" if missing else ""))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
