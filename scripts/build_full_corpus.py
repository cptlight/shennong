#!/usr/bin/env python3
"""Merge the base corpus + the CC0 jicheng corpus into one training/retrieval file.

`corpus.jsonl` is our 106-source curated corpus (45.6 M chars). The jicheng ingest adds 1,304 CC0 classical
TCM works (131.7 M chars), shipped as two gzip parts to stay under GitHub's file cap. This merges them into
a single `corpus-full.jsonl` for pretraining and for the attestation/retrieval index.

    python scripts/build_full_corpus.py        # -> corpus/processed/corpus-full.jsonl

The merged file is ~480 MB uncompressed; it is gitignored (it is reproducible from the two committed parts
plus the committed corpus.jsonl.gz).
"""
from __future__ import annotations

import gzip
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROC = ROOT / "corpus" / "processed"


def main() -> int:
    out = PROC / "corpus-full.jsonl"
    n = 0
    chars = 0
    t0 = time.time()
    with out.open("w", encoding="utf-8") as fh:
        # 1) the curated base corpus
        base = PROC / "corpus.jsonl"
        if not base.exists() and (PROC / "corpus.jsonl.gz").exists():
            base_gz = PROC / "corpus.jsonl.gz"
            with gzip.open(base_gz, "rt", encoding="utf-8") as src, base.open("w", encoding="utf-8") as dst:
                dst.write(src.read())
        if base.exists():
            for line in base.open(encoding="utf-8"):
                if line.strip():
                    fh.write(line if line.endswith("\n") else line + "\n")
                    n += 1
                    chars += len(json.loads(line).get("text", ""))
            print(f"  base corpus: {n:,} records")

        # 2) the jicheng parts
        parts = sorted(PROC.glob("jicheng-part*.jsonl.gz"))
        added = 0
        for p in parts:
            with gzip.open(p, "rt", encoding="utf-8") as src:
                for line in src:
                    if line.strip():
                        fh.write(line if line.endswith("\n") else line + "\n")
                        added += 1
                        chars += len(json.loads(line).get("text", ""))
        print(f"  jicheng: {added:,} records from {len(parts)} part(s)")

    print(f"merged {n + added:,} records · {chars/1e6:.1f} M characters · "
          f"{out.stat().st_size/1e6:.0f} MB · {time.time()-t0:.0f}s")
    print(f"wrote {out}  (gitignored; reproducible)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
