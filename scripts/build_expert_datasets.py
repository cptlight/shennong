#!/usr/bin/env python3
"""Split the SFT set into three domain-tagged expert training sets for the MoE-of-LoRAs.

Each expert is a separate LoRA on the SAME base model, so the split must be by *domain of knowledge*, not by
task name alone:

    t1_classical   Track 1 — names across eras, therapeutic uses, classical properties, formulas
    t2_natprod     Track 2 — compound classes, gene targets, pharmacology, candidates, preparation viability
    safety         toxicity, incompatibility, dosing — the one domain where a wrong answer hurts

    python scripts/build_expert_datasets.py     # -> artifacts/sft/domains/{t1_classical,t2_natprod,safety}.jsonl
"""
from __future__ import annotations

import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFT = ROOT / "artifacts" / "sft"
OUT = SFT / "domains"

# task -> expert domain
TASK_DOMAIN = {
    # Track 1: what the tradition recorded
    "name_mapping": "t1_classical",
    "use": "t1_classical",
    "classical_use": "t1_classical",
    "property": "t1_classical",
    "formula": "t1_classical",
    "relation": "t1_classical",
    # Track 2: natural products and drug discovery
    "compound": "t2_natprod",
    "target": "t2_natprod",
    "pharmacology": "t2_natprod",
    "candidate": "t2_natprod",
    "viability": "t2_natprod",
    # safety
    "incompatibility": "safety",
}

SAFETY_CUES = ("toxic", "毒", "dose", "劑量", "劑", "overdose", "lethal", "safe", "risk", "incompatib",
               "十八反", "十九畏", "contraindicat", "side effect", "adverse")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    buckets: dict[str, list[dict]] = collections.defaultdict(list)
    seen_tasks = collections.Counter()

    for split in ("train", "val"):
        p = SFT / f"{split}.jsonl"
        if not p.exists():
            continue
        for line in p.open(encoding="utf-8"):
            if not line.strip():
                continue
            ex = json.loads(line)
            task = ex.get("kind") or ""
            seen_tasks[task] += 1
            domain = TASK_DOMAIN.get(task, "t1_classical")
            # the record is {id, kind, text}; the question lives between <|user|> and <|assistant|>
            text = ex.get("text") or ""
            try:
                q = text.split("<|user|>", 1)[1].split("<|assistant|>", 1)[0].lower()
            except IndexError:
                q = ""
            if any(c in q for c in SAFETY_CUES):
                domain = "safety"
            buckets[domain].append({**ex, "domain": domain, "split": split})

    total = 0
    for domain, rows in buckets.items():
        out = OUT / f"{domain}.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        total += len(rows)
        print(f"  {domain:<14} {len(rows):>7,} examples -> {out.name}")
    print(f"total {total:,} · tasks seen: {dict(seen_tasks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
