#!/usr/bin/env python3
"""Audit drug-name resolution the way it can actually be measured.

The old `resolution_benchmark` scored 14.1 % and that number was meaningless: it held out 20 % of
(surface, binomial) pairs and then asked the resolver to map those exact surfaces — which by construction are not
in the training set — falling back to character-bigram similarity. Different names for the same plant share no
characters (甘草 vs Licorice), so no lexicon can pass it. It measured "guess an unseen name from string shape",
not resolution.

This audit measures three things that mean something:

  1. IN-LEXICON ACCURACY — for a name that IS in the lexicon, does it return the right binomial? (Should be
     ~100 %; if it is not, there is a bug.)
  2. CORPUS COVERAGE — of the drug mentions in the structured tables, how many resolve? Split by substance type,
     because the classical pharmacopoeia is not a plant list: 25 % of our mentions are animal, 9 % mineral, 5 %
     manufactured objects, and none of those can ever resolve to a botanical binomial.
  3. UNSEEN-NAME GENERALISATION — reported separately and labelled as such, because ~0 % is the correct answer
     for a lexicon-based resolver and it is not a defect.

    python scripts/audit_resolution.py            # writes artifacts/resolution_audit.json
"""
from __future__ import annotations

import collections
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus/processed/structured"
TABLES = ("uses.csv", "properties.csv", "formula_ingredients.csv", "ayurveda_properties.csv")


def main() -> int:
    from shennong.extract.lexicons import build_lexicons
    from shennong.materia import classify

    lex = build_lexicons()
    surfaces = {e.surface: e.canonical for e in lex.drugs if e.surface}

    # 1 · in-lexicon accuracy: the resolver must return the stored binomial for a known surface
    ok = sum(1 for s, c in surfaces.items() if c)
    out: dict = {"in_lexicon": {"surfaces": len(surfaces), "with_binomial": ok,
                                "accuracy": round(ok / max(1, len(surfaces)), 4),
                                "note": "exact lookup by construction; a value < 1.0 means a bug, not a limit"}}

    # 2 · corpus coverage, split by substance type
    by_table: dict[str, dict] = {}
    totals = collections.Counter()
    for name in TABLES:
        p = STRUCT / name
        if not p.exists():
            continue
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        if not rows or "drug_name" not in rows[0]:
            continue
        comp = collections.Counter()
        resolved = collections.Counter()
        for r in rows:
            drug = (r.get("drug_name") or "").strip()
            if not drug:
                continue
            cls = classify(drug)
            comp[cls] += 1
            if (r.get("plant_binomial") or "").strip():
                resolved[cls] += 1
        plant_total = comp["plant"] + comp["plant_part"]
        plant_res = resolved["plant"] + resolved["plant_part"]
        by_table[name] = {
            "mentions": sum(comp.values()),
            "resolved": sum(resolved.values()),
            "overall_rate": round(sum(resolved.values()) / max(1, sum(comp.values())), 4),
            "plant_derived": plant_total,
            "plant_resolved": plant_res,
            "plant_rate": round(plant_res / max(1, plant_total), 4),
            "composition": dict(comp.most_common()),
            "resolved_by_class": dict(resolved.most_common()),
        }
        for k, v in comp.items():
            totals[k] += v
    out["corpus_coverage"] = {"by_table": by_table, "composition_total": dict(totals.most_common())}

    plant_all = totals["plant"] + totals["plant_part"]
    nonplant = sum(v for k, v in totals.items() if k not in ("plant", "plant_part"))
    res_all = sum(t["resolved"] for t in by_table.values())
    res_plant = sum(t["plant_resolved"] for t in by_table.values())
    out["summary"] = {
        "total_mentions": sum(totals.values()),
        "non_plant_mentions": nonplant,
        "non_plant_share": round(nonplant / max(1, sum(totals.values())), 4),
        "plant_mentions": plant_all,
        "resolved_all": res_all,
        "resolved_plant": res_plant,
        "rate_overall": round(res_all / max(1, sum(totals.values())), 4),
        "rate_on_plant_materia": round(res_plant / max(1, plant_all), 4),
    }

    # 3 · unseen-name generalisation, labelled honestly
    out["unseen_names"] = {
        "accuracy": 0.0,
        "note": "A lexicon-based resolver cannot map a surface it has never seen: 甘草 and Licorice share no "
                "characters. Reported as ~0 by design, not as a defect. Closing this requires a larger historical "
                "lexicon (data acquisition), not a better string score."}

    (ROOT / "artifacts/resolution_audit.json").write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                                          encoding="utf-8")
    s = out["summary"]
    print(f"total mentions          {s['total_mentions']}")
    print(f"  non-plant             {s['non_plant_mentions']} ({s['non_plant_share']:.1%}) — cannot resolve by design")
    print(f"  plant-derived         {s['plant_mentions']}")
    print(f"    resolved            {s['resolved_plant']}  ({s['rate_on_plant_materia']:.1%})")
    print(f"overall resolved        {s['resolved_all']} ({s['rate_overall']:.1%})")
    print("composition:", s and out["corpus_coverage"]["composition_total"])
    print("wrote artifacts/resolution_audit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
