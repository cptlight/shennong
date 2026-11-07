#!/usr/bin/env python3
"""Extract classical therapeutic-use pairs from the jicheng CC0 corpus -> SFT training data.

The jicheng corpus is 131.7 M chars of punctuated classical TCM text across 1,304 works. Its dominant
structure is the formula entry:

    治<indication>。 <recipe>        ("treats <indication>. <recipe>")

That is a ready-made (indication, formula) pair — exactly Track 1's "identify therapeutic uses". This script
extracts those pairs, filters the meta-text false positives, dedupes, and writes a structured CSV that the SFT
builder turns into question/answer examples.

    python scripts/extract_jicheng.py     # -> corpus/processed/structured/jicheng_uses.csv
"""
from __future__ import annotations

import csv
import gzip
import json
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROC = ROOT / "corpus" / "processed"
OUT = PROC / "structured" / "jicheng_uses.csv"

# 治<indication> followed by any of these punctuation marks
IND = re.compile(r"治([^。，；\n]{2,28})([。，；])")
# meta-text markers that mean the span is an editorial/preface artefact, not an indication
META = ("方選", "本", "書", "經", "卷", "案", "序", "目錄", "石印", "合訂", "何啻", "其末")
# a valid indication must contain at least one disease/symptom marker (classical TCM vocabulary)
DISEASE = set("病症疾熱寒痛癢虛損風濕痰血氣瘡痢瘧咳喘腫癩癘疸積痞嘔瀉泄淋癃閉痺痿瘈癇驚癲狂癭瘤癰疽疔疥癬痔漏崩帶產胎乳目耳鼻咽喉齒牙頭胸腹腰背肢毒蟲蛇犬傷跌打金焠瘡")
# grammatical fragments that are never indications
BAD = ("之法", "法也", "之也", "之而", "而愈", "者也", "云云", "一人", "下篩", "其標", "之症", "之", "也", "者")
MAX_RECIPE = 180
# dosage/processing markers: the formula clause contains at least one of these
DOSAGE = ("兩", "錢", "分", "枚", "片", "個", "粒", "斤", "升", "合", "研末", "為末", "煎服", "煎湯",
          "炮", "炒", "炙", "煅", "浸", "焙", "丸", "散", "湯服", "酒服", "調服", "搗", "汁")


def pick_formula(seg: str) -> str:
    """From the text after '治<indication>', pick the clause that carries the actual recipe."""
    clauses = [clean(c) for c in re.split(r"[。；]", seg) if clean(c)]
    scored = [(sum(1 for d in DOSAGE if d in c), i, c) for i, c in enumerate(clauses)]
    scored = [x for x in scored if x[0] > 0]
    if scored:
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[0][2][:MAX_RECIPE]
    return (clauses[0][:MAX_RECIPE] if clauses else "")


def clean(s: str) -> str:
    return re.sub(r"\s+", "", s or "").strip()


def main() -> int:
    works = []
    for part in (1, 2):
        p = PROC / f"jicheng-part{part}.jsonl.gz"
        if p.exists():
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                works.extend(json.loads(l) for l in fh if l.strip())
    print(f"works: {len(works):,}")

    pairs: dict[tuple[str, str], dict] = {}
    scanned = 0
    for w in works:
        text = w["text"]
        scanned += len(text)
        for m in IND.finditer(text):
            ind = clean(m.group(1))
            if not ind or len(ind) < 2 or len(ind) > 24:
                continue
            if any(x in ind for x in META) or ind.endswith(BAD):
                continue
            if not any(ch in DISEASE for ch in ind):      # must name a disease/symptom
                continue
            # the recipe is the text after the indication, up to the next 治 or a hard stop
            start = m.end()
            tail = text[start:start + 320]
            nxt = tail.find("治")
            if nxt > 12:
                tail = tail[:nxt]
            recipe = pick_formula(tail)
            if len(recipe) < 4:
                continue
            key = (ind, recipe[:60])
            if key in pairs:
                continue
            pairs[key] = {"indication": ind, "formula": recipe,
                          "work": w["title"], "dynasty": w.get("dynasty", ""),
                          "source": "jicheng.tw", "licence": "CC0-1.0"}

    print(f"scanned {scanned/1e6:.1f} M chars · {len(pairs):,} unique (indication, formula) pairs")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=["indication", "formula", "work", "dynasty", "source", "licence"])
        wtr.writeheader()
        wtr.writerows(pairs.values())
    print(f"wrote {OUT}")

    # quick sanity: most common indications
    top = defaultdict(int)
    for (ind, _), _v in pairs.items():
        top[ind] += 1
    print("top indications:", [k for k, _ in sorted(top.items(), key=lambda x: -x[1])[:10]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
