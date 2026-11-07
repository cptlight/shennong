#!/usr/bin/env python3
"""Run both models on the 200-question benchmark and score the difference.

Direct generation, no retrieval. Same decode for both (temperature 0.2, top_p 0.9, seed 1337, 40 tokens).
A question is "correct" if the model's answer contains the gold's key fact (the distinctive CJK run or the
Latin binomial). Reports per-task accuracy for each model, the delta, and writes the raw answers so the
result is auditable.

    python scripts/run_benchmark.py            # -> artifacts/benchmark_results.json
"""
from __future__ import annotations

import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DECODE = {"temperature": 0.2, "top_p": 0.9, "seed": 1337, "max_tokens": 40}


def load():
    from llama_cpp import Llama
    ours = Llama(model_path=str(ROOT / "artifacts/shennong-1.5b-sft-Q4_K_M.gguf"),
                 n_ctx=1024, n_threads=4, verbose=False)
    base = Llama(model_path=str(ROOT / "artifacts/qwen2.5-1.5b-instruct-q4_k_m.gguf"),
                 n_ctx=1024, n_threads=4, verbose=False)
    return ours, base


def correct(key: str, answer: str) -> bool:
    return bool(key) and key in answer


def main() -> int:
    bench = [json.loads(l) for l in (ROOT / "artifacts/benchmark.jsonl").open(encoding="utf-8")]
    ours, base = load()
    rows = []
    per = {}
    t0 = time.time()
    for i, r in enumerate(bench):
        q = r["question"]
        p_ours = f"<|user|>{q}<|assistant|>"
        p_base = f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n"
        a_ours = ours(p_ours, **DECODE)["choices"][0]["text"].strip()
        a_base = base(p_base, **DECODE)["choices"][0]["text"].strip()
        ok_ours = correct(r["key"], a_ours)
        ok_base = correct(r["key"], a_base)
        for model, ok in (("ours", ok_ours), ("base", ok_base)):
            per.setdefault(model, {}).setdefault(r["kind"], [0, 0])
            per[model][r["kind"]][1] += 1
            per[model][r["kind"]][0] += ok
        rows.append({"id": r["id"], "kind": r["kind"], "question": q, "key": r["key"],
                     "ours": a_ours, "base": a_base, "ours_correct": ok_ours, "base_correct": ok_base})
        if (i + 1) % 25 == 0 or (i + 1) == len(bench):
            rate = (i + 1) / (time.time() - t0)
            print(f"  {i+1}/{len(bench)} · {rate:.2f} q/s · {time.time()-t0:.0f}s elapsed", flush=True)
            # incremental snapshot so a partial number is always on disk
            partial = {"partial": True, "done": i + 1, "n": len(bench), "decode": DECODE, "wall_s": round(time.time() - t0, 1),
                       "ours_correct": sum(1 for r in rows if r["ours_correct"]),
                       "base_correct": sum(1 for r in rows if r["base_correct"]),
                       "ours_acc": round(sum(1 for r in rows if r["ours_correct"]) / (i + 1), 4),
                       "base_acc": round(sum(1 for r in rows if r["base_correct"]) / (i + 1), 4)}
            (ROOT / "artifacts/benchmark_results.json").write_text(json.dumps(partial, indent=2, ensure_ascii=False), encoding="utf-8")

    def acc(model, kind=None):
        d = per[model]
        if kind:
            return d.get(kind, [0, 1])
        c = sum(v[0] for v in d.values())
        t = sum(v[1] for v in d.values())
        return c, t

    oc, ot = acc("ours")
    bc, bt = acc("base")
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "n": len(bench), "decode": DECODE,
        "ours": {"correct": oc, "total": ot, "accuracy": round(oc / ot, 4),
                 "per_kind": {k: {"correct": v[0], "total": v[1], "acc": round(v[0]/v[1], 3)}
                              for k, v in sorted(per["ours"].items(), key=lambda x: -x[1][0]/max(x[1][1],1))}},
        "base": {"correct": bc, "total": bt, "accuracy": round(bc / bt, 4),
                 "per_kind": {k: {"correct": v[0], "total": v[1], "acc": round(v[0]/v[1], 3)}
                              for k, v in sorted(per["base"].items(), key=lambda x: -x[1][0]/max(x[1][1],1))}},
        "delta": round(oc / ot - bc / bt, 4),
        "wall_s": round(time.time() - t0, 1),
        "metric": "contains-match of the gold key fact in the generated answer (direct, no retrieval)",
        "results": rows,
    }
    (ROOT / "artifacts/benchmark_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nOURS  {oc}/{ot} = {oc/ot:.1%}")
    print(f"BASE  {bc}/{bt} = {bc/bt:.1%}")
    print(f"DELTA {out['delta']:+.1%}  ({out['wall_s']}s)")
    print("per-kind (ours):", {k: f"{v['correct']}/{v['total']}" for k, v in out['ours']['per_kind'].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
