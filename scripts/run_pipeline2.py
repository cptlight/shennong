#!/usr/bin/env python3
"""Pipeline 2 — feed pipeline 1's hypotheses through the physics and get a deterministic outcome.

    pipeline 1:  ancient record → Asian theory → Asian pharmacy   ⇒  HYPOTHESIS
    pipeline 2:  structure + process conditions   → kinetics      ⇒  MAY / MAY NOT, with arithmetic

Western literature appears here **only as a reference field** — `references_western`, with the explicit
epistemic status *"this is what they think"*. It is never used to compute the outcome and never overrides
it. If a Western paper says a plant does X and the simulation says the class cannot survive the
preparation, the correct conclusion is that either the paper measured something else, or the preparation
differs, or the paper is wrong.

    python scripts/run_pipeline2.py
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shennong.physics.estimators import validate  # noqa: E402
from shennong.physics.simulate import PROCESS, classify, deterministic_verdict, simulate  # noqa: E402


def load_compounds(path: Path) -> dict[tuple[str, str], list[str]]:
    """(plant, chemotype) -> up to 6 SMILES."""
    out: dict[tuple[str, str], list[str]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            plant = (r.get("plant_binomial") or "").strip()
            cls = (r.get("compound_class") or "").strip().lower()
            smi = (r.get("smiles") or "").strip()
            if plant and cls and smi and len(out[(plant, cls)]) < 6:
                out[(plant, cls)].append(smi)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hypotheses", default="artifacts/tradition_first.json")
    ap.add_argument("--compounds", default="corpus/processed/structured/compounds.csv")
    ap.add_argument("--out-json", default="artifacts/deterministic_outcomes.json")
    ap.add_argument("--out-md", default="artifacts/DETERMINISTIC_OUTCOMES.md")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    v = validate()
    print(f"estimator validation: mean {v['mean_rel_error']:.1%} rel error on Tb "
          f"({v['within_10pct']}/{v['n']} within 10%)")

    hyp = json.loads((ROOT / args.hypotheses).read_text(encoding="utf-8"))
    results = hyp.get("results") or []
    if args.limit:
        results = results[: args.limit]
    compounds = load_compounds(ROOT / args.compounds)

    rows = []
    for r in results:
        claim = r.get("claim") or ""
        # recover the item fields from the stage table (kept in the claim string) — the staged
        # runner stores them in the stage proposals, so rebuild from the claim where possible
        stages = {s["stage"]: s for s in r.get("stages", [])}
        s3 = (stages.get(3) or {}).get("proposals") or []
        process = None
        for p in s3:
            for e in p.get("evidence", []):
                if ":" in e:
                    process = e.split(":")[0].strip()
                    break
            if process:
                break
        rows.append({"claim": claim, "record": r, "process": process})

    # The staged artefact does not carry (plant, chemotype) as structured fields, so re-derive them
    # from the original cross-sections and join on the claim text.
    cs = json.loads((ROOT / "artifacts/cross_sections.json").read_text(encoding="utf-8"))
    by_claim = {}
    for it in (cs.get("all") or cs.get("top") or []):
        c = (f"{it.get('process')} of {it.get('drug_surface')} "
             f"({it.get('binomial')}) should measurably change its {it.get('chemotype')} content")
        by_claim[c] = it

    out = []
    for r in rows:
        it = by_claim.get(r["claim"])
        if not it:
            continue
        plant, cls, process = it.get("binomial"), it.get("chemotype"), it.get("process")
        smis = compounds.get((plant, cls), [])[:4]
        if not smis:
            out.append({**it, "record": r, "outcome": {"status": "no structures for this plant x class"}})
            continue
        rets = [x for x in (simulate(s, process) for s in smis) if x]
        if not rets:
            out.append({**it, "record": r, "outcome": {"status": "structures unparseable"}})
            continue
        med = statistics.median(x.retained for x in rets)
        lo = min(x.retained_range[0] for x in rets)
        hi = max(x.retained_range[1] for x in rets)
        mech = max(rets, key=lambda x: x.k_vol + x.k_hyd + x.k_deg).mechanism
        verdict = deterministic_verdict(med, "enrich")
        out.append({
            **it,
            "record": r,
            "outcome": {
                "n_structures_simulated": len(rets),
                "process_conditions": {"T_K": PROCESS.get(process, (None,))[0],
                                       "medium": PROCESS.get(process, (None, None))[1],
                                       "seconds": PROCESS.get(process, (None, None, None))[2]},
                "median_retention": round(med, 4),
                "range": [round(lo, 4), round(hi, 4)],
                "dominant_mechanism": mech,
                "class": classify(med),
                **verdict,
                "per_structure": [x.to_dict() for x in rets],
            },
            "references_western": {
                "epistemic_status": "this is what they think — recorded, not used in the computation",
                "entries": [],
                "note": ("No Western claim is stored for this pair. When present it would be filed "
                         "here as an observation and would NOT alter the physics verdict."),
            },
        })

    # rank: surviving-everything first, then by how large the modelled change is
    def key(x):
        o = x.get("outcome") or {}
        return (1 if x["record"].get("gates_passed") else 0, -abs(o.get("median_retention", 1.0)))

    out.sort(key=key, reverse=True)
    counts = defaultdict(int)
    for x in out:
        counts[(x.get("outcome") or {}).get("class", "no data")] += 1

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "architecture": ("pipeline 1 produces hypotheses (ancient record -> Asian theory -> Asian "
                         "pharmacy); pipeline 2 converts them to a deterministic physical outcome"),
        "arbiter": "kinetics and thermodynamics; Western literature is a reference field only",
        "estimator_validation": v,
        "n": len(out),
        "retention_classes": dict(counts),
        "results": out,
    }
    (ROOT / args.out_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Pipeline 2 — deterministic outcomes", "", payload["generated_at"], "",
         "Pipeline 1 says what the record implies. Pipeline 2 computes what the physics allows.",
         "", "```",
         "pipeline 1   ancient record → Asian theory → Asian pharmacy     ⇒ HYPOTHESIS",
         "pipeline 2   structure + T/medium/time → kinetics                ⇒ MAY / MAY NOT",
         "```", "",
         f"**Estimator validation:** Joback boiling points vs known physical constants — mean relative",
         f"error **{v['mean_rel_error']:.1%}**, {v['within_10pct']}/{v['n']} compounds within 10 %.",
         "The physics layer is only as good as that number, and it is stated here so it can be checked.",
         "", "**Western literature** appears as a `references_western` field on every row, explicitly",
         "marked *\"this is what they think\"*. It is never used to compute the outcome.", "",
         "## Retention classes", "", "| Class | Hypotheses |", "|---|---|"]
    for k, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        L.append(f"| {k} | {n} |")

    L += ["", "## Outcomes", "",
          "| Hypothesis | Prepared at | Modelled retention | Range | Dominant sink | Verdict |",
          "|---|---|---|---|---|---|"]
    for x in out[:25]:
        o = x.get("outcome") or {}
        if "median_retention" not in o:
            L.append(f"| {x.get('drug_surface')}+{x.get('process')} → {x.get('chemotype')} | — | — | "
                     f"— | — | {o.get('status', 'no data')} |")
            continue
        c = o["process_conditions"]
        L.append(f"| {x.get('drug_surface')}+{x.get('process')} → {x.get('chemotype')} | "
                 f"{c['T_K']:.0f} K, {c['medium']}, {c['seconds']} s | "
                 f"**{o['median_retention']:.1%}** | {o['range'][0]:.0%}–{o['range'][1]:.0%} | "
                 f"{o['dominant_mechanism']} | {o['verdict'][:64]} |")

    killed = [x for x in out if (x.get("outcome") or {}).get("class") in ("LARGELY LOST",
                                                                          "EFFECTIVELY DESTROYED")]
    L += ["", f"## Where the physics contradicts the hypothesis ({len(killed)})", "",
          "These are hypotheses that passed the record, the Asian-theory gate and the expert panel,",
          "and are **refuted by the arithmetic** — the preparation cannot do what the hypothesis says.",
          "", "| Hypothesis | Modelled retention | Sink | Why |", "|---|---|---|---|"]
    for x in killed[:15]:
        o = x["outcome"]
        L.append(f"| {x.get('drug_surface')}+{x.get('process')} → {x.get('chemotype')} | "
                 f"{o['median_retention']:.1%} | {o['dominant_mechanism']} | "
                 f"the class does not survive this preparation |")
    (ROOT / args.out_md).write_text("\n".join(L), encoding="utf-8")

    print(f"{len(out)} hypotheses simulated · retention classes {dict(counts)}")
    print(f"refuted by physics: {len(killed)}")
    print(f"wrote {args.out_json} and {args.out_md}")
    for x in out[:8]:
        o = x.get("outcome") or {}
        if "median_retention" in o:
            print(f"  {x.get('drug_surface')}+{x.get('process')} -> {x.get('chemotype'):<11} "
                  f"{o['median_retention']:6.1%} retained  [{o['dominant_mechanism']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
