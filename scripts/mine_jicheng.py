#!/usr/bin/env python3
"""Mine the 1,304-work CC0 jicheng corpus: formula + indication -> drugs -> binomials.

jicheng_uses.csv holds 273,334 (indication, formula) pairs extracted from 1,304 classical works, and none of them
was ever resolved to a taxon. That is 23x the size of the uses table the rest of the pipeline relies on, and it is
the single largest source of Track-1 material we hold — so this is where "extract medicinal knowledge from
historical texts" is actually demonstrated at corpus scale rather than on a pasted paragraph.

For every formula the drug trie is scanned (longest match, no hallucination possible), each mention is resolved
through the cross-era lexicon, and the result is written as a drug-indication table plus corpus-level statistics.

    python scripts/mine_jicheng.py --limit 273334        # full run is a few minutes on CPU
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus/processed/structured"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10**9)
    ap.add_argument("--out", default="artifacts/jicheng_mined.json")
    ap.add_argument("--csv", default="artifacts/jicheng_drug_indication.csv")
    args = ap.parse_args()

    from shennong.extract.lexicons import build_lexicons
    from shennong.extract.match import build_drug_trie, scan_drugs

    lex = build_lexicons()
    trie = build_drug_trie(lex.drugs)
    print(f"drug trie: {trie.count} surfaces")

    rows = list(csv.DictReader((STRUCT / "jicheng_uses.csv").open(encoding="utf-8")))[: args.limit]
    print(f"formulas to mine: {len(rows)}")

    t0 = time.time()
    works: set[str] = set()
    pairs: list[dict] = []
    drug_freq: collections.Counter = collections.Counter()
    binom_freq: collections.Counter = collections.Counter()
    ind_freq: collections.Counter = collections.Counter()
    n_mentions = n_resolved = 0
    formulas_with_drug = 0

    for i, r in enumerate(rows):
        formula = (r.get("formula") or "").strip()
        indication = (r.get("indication") or "").strip()
        work = (r.get("work") or "").strip()
        if work:
            works.add(work)
        if not formula:
            continue
        hits = scan_drugs(trie, formula)
        if hits:
            formulas_with_drug += 1
        seen = set()
        for m in hits:
            n_mentions += 1
            drug_freq[m.surface] += 1
            if m.canonical:
                n_resolved += 1
                binom_freq[m.canonical] += 1
            if indication:
                ind_freq[indication] += 1
            if indication and m.canonical and (indication, m.canonical) not in seen:
                seen.add((indication, m.canonical))
                pairs.append({"indication": indication, "drug": m.surface, "binomial": m.canonical,
                              "work": work, "dynasty": r.get("dynasty") or ""})
        if (i + 1) % 25000 == 0:
            print(f"  {i+1}/{len(rows)} · {n_mentions} mentions · {time.time()-t0:.0f}s", flush=True)

    stats = {
        "formulas": len(rows),
        "formulas_with_recognised_drug": formulas_with_drug,
        "works": len(works),
        "drug_mentions": n_mentions,
        "resolved_mentions": n_resolved,
        "resolution_rate": round(n_resolved / max(1, n_mentions), 4),
        "distinct_drug_surfaces": len(drug_freq),
        "distinct_binomials": len(binom_freq),
        "distinct_indications": len(ind_freq),
        "drug_indication_pairs": len(pairs),
        "top_drugs": drug_freq.most_common(25),
        "top_binomials": binom_freq.most_common(15),
        "top_indications": ind_freq.most_common(15),
        "seconds": round(time.time() - t0, 1),
        "source": "jicheng.tw, CC0 1.0",
    }
    (ROOT / args.out).write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    with (ROOT / args.csv).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["indication", "drug", "binomial", "work", "dynasty"])
        w.writeheader()
        w.writerows(pairs[:200000])

    print(json.dumps({k: v for k, v in stats.items() if not isinstance(v, list)}, indent=2, ensure_ascii=False))
    print("top drugs:", stats["top_drugs"][:10])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
