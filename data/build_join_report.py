"""Write ``corpus/registry/join_report.json`` — a machine-readable join audit.

Downstream teams (`discovery-engine`, `story-builder`, the Lead) need one canonical number
for "how much of the structured data actually resolves to a taxon", so it is produced here
rather than re-derived in three places.

    python -m data.build_join_report
"""

from __future__ import annotations

import csv
import json
from collections import Counter

from . import _net

STRUCT = _net.PROCESSED / "structured"
LEXICON = _net.PROCESSED / "lexicon_drugs.json"
OUT = _net.REGISTRY / "join_report.json"

FILES = ["properties.csv", "uses.csv", "formula_ingredients.csv",
         "ayurveda_properties.csv", "compounds.csv"]


def _read(name: str) -> list[dict]:
    p = STRUCT / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    lex = json.loads(LEXICON.read_text(encoding="utf-8")) if LEXICON.exists() else {}
    entries = lex.get("historical", [])
    methods = Counter(e.get("method", "") for e in entries)
    conf = [e.get("confidence", 0) for e in entries]

    report: dict = {
        "lexicon": {
            "file": "corpus/processed/lexicon_drugs.json",
            "entries": len(entries),
            "distinct_binomials": len({e.get("modern") for e in entries
                                       if " " in (e.get("modern") or "")}),
            "by_method": dict(methods),
            "mean_confidence": round(sum(conf) / len(conf), 3) if conf else 0.0,
            "unresolved_surfaces": lex.get("unresolved_count", 0),
        },
        "files": {},
        "note": ("join_status values: joined = drug_name resolved to a binomial via "
                 "lexicon_drugs.json; unresolved = no verified binomial, left null rather "
                 "than guessed. drug_name is the stable join key in every file."),
    }

    for name in FILES:
        rows = _read(name)
        if not rows:
            report["files"][name] = {"present": False}
            continue
        key = "drug_name" if "drug_name" in rows[0] else None
        has_binomial = "plant_binomial" in rows[0]
        joined = sum(1 for r in rows
                     if r.get("join_status") == "joined"
                     or (has_binomial and r.get("plant_binomial")))
        status = Counter(r.get("join_status", "") for r in rows) if "join_status" in rows[0] else {}
        report["files"][name] = {
            "present": True,
            "rows": len(rows),
            "has_join_key": bool(key),
            "join_key": key or "",
            "plant_binomial_filled": joined,
            "join_rate": round(joined / len(rows), 4) if rows else 0.0,
            "by_status": dict(status),
            "distinct_join_keys": len({r[key] for r in rows if key and r.get(key)}),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  lexicon entries: {report['lexicon']['entries']} "
          f"(binomials: {report['lexicon']['distinct_binomials']})")
    for name, info in report["files"].items():
        if info.get("present"):
            print(f"  {name:<28} rows={info['rows']:>6} joined={info['plant_binomial_filled']:>6} "
                  f"({info['join_rate']:.1%}) key={info['join_key']}")
        else:
            print(f"  {name:<28} MISSING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
