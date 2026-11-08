#!/usr/bin/env python3
"""Three-way benchmark: dense 1.5B fine-tune vs the 1.44B sparse MoE, on the same questions.

Contains-match of the gold key, identical prompt and decode — the same protocol as run_benchmark.py, so the
numbers are directly comparable to the 49.0 % already published for the dense model.

    python scripts/compare_moe.py --n 60
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DECODE = {"temperature": 0.2, "top_p": 0.9, "seed": 1337}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--dense", default="artifacts/shennong-1.5b-sft-Q4_K_M.gguf")
    ap.add_argument("--moe", default="artifacts/shennong-moe-loadable.gguf")
    ap.add_argument("--out", default="artifacts/moe_vs_dense.json")
    args = ap.parse_args()

    from llama_cpp import Llama

    bench = [json.loads(l) for l in (ROOT / "artifacts/benchmark.jsonl").open(encoding="utf-8")]
    # stratified: take every k-th question so both tracks are represented
    step = max(1, len(bench) // args.n)
    qs = bench[::step][: args.n]
    print(f"{len(qs)} questions (stride {step})")

    print(f"loading dense 1.5B ...")
    dense = Llama(model_path=str(ROOT / args.dense), n_ctx=512, n_threads=4, verbose=False)
    print(f"loading MoE 1.44B ...")
    moe = Llama(model_path=str(ROOT / args.moe), n_ctx=512, n_threads=4, verbose=False)

    res = {"n": len(qs), "dense": {"correct": 0, "by_kind": {}}, "moe": {"correct": 0, "by_kind": {}}, "rows": []}
    t0 = time.time()
    for i, q in enumerate(qs):
        prompt = f"<|user|>{q['question']}<|assistant|>"
        row = {"id": q["id"], "kind": q["kind"], "key": q["key"]}
        for name, llm in (("dense", dense), ("moe", moe)):
            t = time.time()
            out = llm(prompt, max_tokens=40, **DECODE)["choices"][0]["text"].strip()
            hit = q["key"].lower() in out.lower()
            row[name] = {"answer": out[:200], "hit": hit, "s": round(time.time() - t, 1)}
            if hit:
                res[name]["correct"] += 1
            k = q["kind"]
            res[name]["by_kind"].setdefault(k, [0, 0])
            res[name]["by_kind"][k][0] += int(hit)
            res[name]["by_kind"][k][1] += 1
        res["rows"].append(row)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(qs)} · dense {res['dense']['correct']} · moe {res['moe']['correct']} "
                  f"· {time.time()-t0:.0f}s", flush=True)

    for name in ("dense", "moe"):
        acc = res[name]["correct"] / len(qs)
        print(f"\n{name:6} {res[name]['correct']}/{len(qs)} = {acc:.1%}")
        for k, (c, n) in sorted(res[name]["by_kind"].items()):
            print(f"    {k:<16} {c}/{n}")
    res["delta"] = (res["moe"]["correct"] - res["dense"]["correct"]) / len(qs)
    print(f"\nMoE − dense = {res['delta']:+.1%}")
    (ROOT / args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
