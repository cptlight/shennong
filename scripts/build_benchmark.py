#!/usr/bin/env python3
"""Build a 200-question domain benchmark from the held-out eval set.

Samples `artifacts/sft/val.jsonl` (919 held-out examples, 9 task types) stratified so every task is
represented, and stores {question, gold, kind, key} where `key` is the machine-checkable fact to match in an
answer. This is the set the two models are scored on.

    python scripts/build_benchmark.py --n 200
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSISTANT = "<|assistant|>"


def gold_key(gold: str) -> str:
    """The distinctive fact: the longest CJK run, else the Latin binomial."""
    g = gold.replace("<|eos|>", "")
    for p in ("Recorded use: ", "Nature ", "Recorded incompatibilities (pre-modern interaction rules, not clinical advice): ",
              "Candidate: ", "MAY. ", "MAY NOT. ", "PARTIAL. ", "Formula ", "Recorded incompatibilities: "):
        g = g.replace(p, "")
    cjk = re.findall(r"[\u4e00-\u9fff]{2,}", g)
    if cjk:
        return max(cjk, key=len)
    lat = re.findall(r"[A-Z][a-z]+ [a-z]+", g)
    return lat[0] if lat else g.strip()[:24]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    val = [json.loads(l) for l in (ROOT / "artifacts/sft/val.jsonl").open(encoding="utf-8")]
    rows = []
    for e in val:
        i = e["text"].find(ASSISTANT)
        if i < 0:
            continue
        q = e["text"][:i].replace("<|user|>", "").strip()
        gold = e["text"][i + len(ASSISTANT):].replace("<|eos|>", "").strip()
        rows.append({"kind": e["kind"], "question": q, "gold": gold, "key": gold_key(gold)})

    # stratified: shuffle within each kind, take a balanced share
    import collections
    import random
    rng = random.Random(args.seed)
    by_kind = collections.defaultdict(list)
    for r in rows:
        by_kind[r["kind"]].append(r)
    for k in by_kind:
        rng.shuffle(by_kind[k])

    kinds = sorted(by_kind, key=lambda k: -len(by_kind[k]))
    # include every small task fully, cap the big ones, then top up from the largest to hit n
    sample = []
    per = max(1, args.n // len(kinds))
    for k in kinds:
        sample.extend(by_kind[k][:per])
    if len(sample) < args.n:
        biggest = kinds[0]
        pool = by_kind[biggest][per:]
        sample.extend(pool[: args.n - len(sample)])
    rng.shuffle(sample)
    sample = sample[: args.n]

    out = ROOT / "artifacts/benchmark.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for i, r in enumerate(sample):
            fh.write(json.dumps({"id": i, **r}, ensure_ascii=False) + "\n")

    cnt = collections.Counter(r["kind"] for r in sample)
    print(f"benchmark: {len(sample)} questions -> artifacts/benchmark.jsonl")
    print("  by task:", dict(cnt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
