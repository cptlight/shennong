#!/usr/bin/env python3
"""Rescore the 200-question benchmark with a correct key for the 'use' questions.

The original scorer does a contains-match of `key` in the answer. For the 113 use/classical_use questions the
stored key is not the therapeutic use — it is the tradition string ("Indian medicine") or a preparation phrase,
so a correct answer scores zero:

    Q: What is Heimia salicifolia used for in Indian medicine?
    gold: Recorded use: emetics (Indian medicine).     key: "Indian medicine"
    answer: "emetics"                                  -> scored WRONG

This rescore takes the recorded use from `gold` instead, accepts a match in either direction (the answer naming
the use, or the use containing the answer), and reports both the old and corrected numbers so the correction is
auditable rather than a quiet improvement.

    python scripts/rescore_benchmark.py            # prints and writes artifacts/benchmark_rescored.json

Nothing is re-generated: the model answers saved in benchmark_results.json are reused verbatim.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

USE_KINDS = {"use", "classical_use"}
USE_RE = re.compile(r"Recorded use:\s*(.+?)\s*(?:\(|$)", re.S)


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").lower())


def core_use(gold: str) -> str:
    m = USE_RE.search(gold or "")
    return (m.group(1) if m else (gold or "")).strip(" .。")


def main() -> int:
    bench = {b["id"]: b for b in (json.loads(l) for l in
                                  (ROOT / "artifacts/benchmark.jsonl").open(encoding="utf-8"))}
    res = json.loads((ROOT / "artifacts/benchmark_results.json").read_text())
    rows = res["results"]

    out = {"n": len(rows), "old": {}, "corrected": {}, "changes": []}
    for arm in ("ours", "base"):
        old_c = sum(1 for r in rows if r.get(f"{arm}_correct"))
        new_c = 0
        per_kind: dict[str, list[int]] = {}
        for r in rows:
            b = bench[r["id"]]
            ans = norm(r.get(arm) or "")
            kind = r["kind"]
            if kind in USE_KINDS:
                use = norm(core_use(b.get("gold", "")))
                hit = bool(use) and (use in ans or (ans and ans in use))
            else:
                key = norm(r.get("key") or "")
                hit = bool(key) and key in ans
            if hit:
                new_c += 1
            per_kind.setdefault(kind, [0, 0])
            per_kind[kind][0] += int(hit)
            per_kind[kind][1] += 1
            if arm == "ours" and hit != bool(r.get(f"{arm}_correct")):
                out["changes"].append({"id": r["id"], "kind": kind, "was": bool(r.get(f"{arm}_correct")),
                                       "now": hit, "answer": (r.get(arm) or "")[:90]})
        out["old"][arm] = {"correct": old_c, "acc": round(old_c / len(rows), 4)}
        out["corrected"][arm] = {"correct": new_c, "acc": round(new_c / len(rows), 4),
                                 "by_kind": {k: {"correct": c, "total": t, "acc": round(c / t, 3)}
                                             for k, (c, t) in sorted(per_kind.items())}}

    o, b_ = out["old"], out["corrected"]
    print(f"{'':<8}{'old':>12}{'corrected':>14}")
    for arm in ("ours", "base"):
        print(f"{arm:<8}{o[arm]['correct']:>5}/{len(rows)} {o[arm]['acc']:>6.1%}"
              f"{b_[arm]['correct']:>8}/{len(rows)} {b_[arm]['acc']:>6.1%}")
    print(f"delta: {o['ours']['acc']-o['base']['acc']:+.1%} -> {b_['ours']['acc']-b_['base']['acc']:+.1%}")
    print("\ncorrected per-kind (ours):")
    for k, v in b_["ours"]["by_kind"].items():
        print(f"  {k:<16}{v['correct']:>4}/{v['total']:<4} {v['acc']:.1%}")
    print(f"\nrows whose verdict changed for 'ours': {len(out['changes'])}")
    (ROOT / "artifacts/benchmark_rescored.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote artifacts/benchmark_rescored.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
