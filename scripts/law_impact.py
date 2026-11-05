#!/usr/bin/env python3
"""Which first-principles laws actually fired, and how many verdicts did each change?

A registry of fifteen laws is impressive only if most of them are doing work. This ran the arbiter over
every candidate and counts, per law-check, how many claims it evaluated and how many it turned into a
rejection. A law that never fires is either mis-scoped or not yet operationalised, and saying so is more
honest than listing it as if it were load-bearing.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shennong.experts.first_principles import arbitrate  # noqa: E402


def main() -> int:
    cs = json.loads((ROOT / "artifacts/cross_sections.json").read_text(encoding="utf-8"))
    items = cs.get("all") or cs.get("top") or []

    evaluated = Counter()
    violations = Counter()
    consequential = Counter()
    examples: dict[str, list[str]] = {}

    for it in items:
        claim = (f"{it.get('process')} of {it.get('drug_surface')} ({it.get('binomial')}) should "
                 f"measurably change its {it.get('chemotype')} content")
        r = arbitrate(it.get("process") or "", it.get("chemotype") or "", None, claim)
        for c in r["checks"]:
            name = c["check"]
            evaluated[name] += 1
            if c["passed"] is False:
                violations[name] += 1
                consequential[name] += 1
                examples.setdefault(name, []).append(
                    f"{it.get('drug_surface')}+{it.get('process')}→{it.get('chemotype')}")
        # the arbiter's overall rejection counts once per claim
    rejected = sum(1 for it in items
                   if arbitrate(it.get("process") or "", it.get("chemotype") or "", None,
                                f"{it.get('process')} of {it.get('drug_surface')} should measurably "
                                f"change its {it.get('chemotype')} content")["violations"])

    table = [{"check": k, "evaluated": evaluated[k], "violations": violations[k],
              "examples": (examples.get(k) or [])[:4]} for k in sorted(evaluated)]
    payload = {
        "n_candidates": len(items),
        "claims_rejected_by_physics": rejected,
        "laws_that_fired": [t for t in table if t["violations"] > 0],
        "laws_that_did_not_fire": [t["check"] for t in table if t["violations"] == 0],
        "table": table,
        "note": ("'violations' is the number of claims this check turned into a rejection. A check with "
                 "zero violations is either correctly scoped and rarely triggered, or not yet "
                 "operationalised — both are worth stating rather than hiding."),
    }
    (ROOT / "artifacts/law_impact.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"candidates {len(items)} · rejected by physics {rejected}")
    print(f"{'check':<22} {'evaluated':>10} {'violations':>11}")
    for t in table:
        print(f"  {t['check']:<22} {t['evaluated']:>10} {t['violations']:>11}")
    print("wrote artifacts/law_impact.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
