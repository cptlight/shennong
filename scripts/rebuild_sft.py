#!/usr/bin/env python3
"""Reconstruct artifacts/sft/{train,val}.jsonl from the tracked per-domain files.

artifacts/sft/train.jsonl is gitignored (20 MB), but artifacts/sft/domains/*.jsonl are tracked and carry the
same {id, kind, text, split} records. This rebuilds the combined files so a fresh Colab clone can train
without re-running the corpus build.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "artifacts/sft/domains"
OUT = ROOT / "artifacts/sft"


def main() -> int:
    rows: dict[str, dict] = {}
    files = sorted(SRC.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"no domain files under {SRC}")
    for f in files:
        for line in f.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("id") and r.get("text"):
                rows[r["id"]] = r
        print(f"  {f.name}: {sum(1 for _ in f.open(encoding='utf-8'))} lines")
    train = [r for r in rows.values() if r.get("split") == "train"]
    val = [r for r in rows.values() if r.get("split") == "val"]
    if not train or not val:
        raise SystemExit(f"empty split: train={len(train)} val={len(val)} — check the 'split' field")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("train", train), ("val", val)):
        p = OUT / f"{name}.jsonl"
        with p.open("w", encoding="utf-8") as fh:
            for r in data:
                fh.write(json.dumps({"id": r["id"], "kind": r.get("kind", ""), "text": r["text"]},
                                    ensure_ascii=False) + "\n")
        print(f"wrote {p} ({len(data)} rows)")
    kinds: dict[str, int] = {}
    for r in train:
        kinds[r.get("kind", "")] = kinds.get(r.get("kind", ""), 0) + 1
    print("kinds:", dict(sorted(kinds.items(), key=lambda kv: -kv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
