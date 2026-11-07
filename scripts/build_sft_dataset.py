#!/usr/bin/env python3
"""Build Track-02 supervised fine-tuning data from the project's own artefacts.

Why fine-tune at all
--------------------
Pre-training on the corpus teaches the *register* — the model has seen 本草綱目 and 炮製. It has not been
taught the **task shape** of this project: given a preparation, decide whether the claimed enrichment can
survive it; given a lead, state the candidate, the target class and what would kill it. That is what SFT is
for, and it is Track-02 work, not Track-01 text mining.

Four task types, all derived from artefacts (no synthesis, no invented chemistry):

  1 viability     preparation + chemotype -> may/may not, retention, mechanism, what would refute it
  2 candidate     lead herb -> candidate molecule, target class, kill criteria
  3 incompatibility  herb -> recorded incompatible pair(s) with the classical label
  4 property      herb -> nature/flavour/channel vector

Every example is a real row from `artifacts/` or `corpus/processed/structured/`. The output format matches
the prompt style the demo uses, so what the model trains on is what a judge will see.

    python scripts/build_sft_dataset.py        # -> artifacts/sft/{train,val}.jsonl
"""
from __future__ import annotations

import csv
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "artifacts" / "sft"


def load(rel, default=None):
    p = ROOT / rel
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def ex(user: str, assistant: str, kind: str) -> dict:
    # Use the tokenizer's own chat tokens (<|user|>/<|assistant|>/<|eos|>, ids 4/5/2). The first SFT run
    # used plain "Question:/Answer:" and appended `token_to_id("</s>") or 0`, which is None -> 0 = <|pad|>,
    # so every answer was trained to end with a pad token and generation collapsed to commas.
    text = f"<|user|>{user}<|assistant|>{assistant}<|eos|>"
    return {"kind": kind, "text": text}


def build() -> list[dict]:
    rows: list[dict] = []

    # ---- 1. viability: the core Track-02 task --------------------------------
    det = load("artifacts/deterministic_outcomes.json", {}) or {}
    for r in det.get("results", []):
        o = r.get("outcome") or {}
        if "median_retention" not in o:
            continue
        rng = o.get("range") or [0, 0]
        verdict = "MAY NOT" if o["median_retention"] < 0.35 else (
            "PARTIAL" if o["median_retention"] < 0.75 else "MAY")
        assistant = (
            f"{verdict}. The claimed enrichment of {r['chemotype']} by {r['process']} is not supported: "
            f"modelled median retention is {o['median_retention']*100:.0f}% "
            f"(range {rng[0]*100:.0f}-{rng[1]*100:.0f}%), dominant loss mechanism {o.get('dominant_mechanism')}. "
            f"Refuted if a measured retention exceeds 75% — that would contradict the physical model.")
        rows.append(ex(
            f"For {r['drug_surface']} ({r.get('binomial')}), will {r['process']} enrich its "
            f"{r['chemotype']} content? Give a verdict, the modelled retention and what would refute it.",
            assistant, "viability"))

    # ---- 2. candidate cards --------------------------------------------------
    cands = (load("artifacts/drug_candidates.json", {}) or {}).get("candidates", [])
    for c in cands:
        lead = (c.get("lead") or {}).get("drug") or c.get("name_cn") or ""
        mech = c.get("mechanism") or {}
        des = c.get("descriptors") or {}
        kill = (c.get("falsification") or {}).get("kill_criteria") or "no engagement below solubility limit"
        assistant = (
            f"Candidate: {c.get('name')} ({c.get('formula') or 'formula n/a'}), from {lead}. "
            f"MW {c.get('mw')}, logP {des.get('logp_estimate')}, structural novelty {c.get('scores',{}).get('novelty')}. "
            f"Proposed target class: {mech.get('target_class')} — class-level prior only. "
            f"Kill criteria: {kill}")
        rows.append(ex(
            f"What candidate does {lead} suggest under Track 02, and what would kill it?",
            assistant, "candidate"))

    # ---- 3. incompatibilities ------------------------------------------------
    p = ROOT / "corpus/processed/structured/incompatibilities.csv"
    if p.exists():
        groups: dict[str, list[dict]] = {}
        for r in csv.DictReader(p.open(encoding="utf-8")):
            groups.setdefault(r["drug_a"], []).append(r)
        for drug, rs in groups.items():
            parts = "; ".join(f"{r['drug_b']} ({r.get('classical_label') or r.get('rule_system')})" for r in rs[:6])
            rows.append(ex(
                f"Which herbs are recorded as incompatible with {drug}?",
                f"Recorded incompatibilities (pre-modern interaction rules, not clinical advice): {parts}.",
                "incompatibility"))

    # ---- 4. property vectors -------------------------------------------------
    p = ROOT / "corpus/processed/structured/properties.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if not (r.get("nature") or r.get("flavors") or r.get("channels")):
                continue
            chan = r.get("channels") or "not recorded"
            rows.append(ex(
                f"What is the recorded nature, flavour and channel tropism of {r['drug_name']}?",
                f"Nature {r['nature'] or '—'}, flavours {r['flavors'] or '—'}, channels {chan}, "
                f"toxicity {r['toxicity'] or '—'}, grade {r['grade'] or '—'}.",
                "property"))


    # ---- 5. era-to-era name mapping (Track 1: cross-era cross-referencing) ----
    lex = load("corpus/processed/lexicon_drugs.json", {}) or {}
    for r in lex.get("historical", []):
        if r.get("name") and r.get("modern"):
            rows.append(ex(
                f"What is the modern botanical binomial of the historical name {r['name']}?",
                f"{r['name']} -> {r['modern']} (resolved by {r.get('method','lexicon')}, "
                f"confidence {r.get('confidence','—')}).",
                "name_mapping"))

    # ---- 6. therapeutic use (Track 1: identify therapeutic uses) --------------
    p = ROOT / "corpus/processed/structured/uses.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            drug, ind = (r.get("drug_name") or "").strip(), (r.get("indication") or "").strip()
            prep = (r.get("preparation") or "").strip()
            if len(drug) < 2 or len(ind) < 2:
                continue
            ans = f"Recorded use: {ind}."
            if prep:
                ans += f" Preparation: {prep}."
            if r.get("indication_modern"):
                ans += f" Modern reading: {r['indication_modern']}."
            ans += " (pre-modern claim; not clinical advice)"
            rows.append(ex(f"What is {drug} recorded to treat?", ans, "use"))

    # ---- 7. 七情 relation extraction (Track 1: relation extraction) ----------
    SEVEN = {"xiangxu": "相須 (mutual assistance)", "xiangshi": "相使 (mutual enhancement)",
             "xiangwei": "相畏 (mutual restraint)", "xiangfan": "相反 (antagonistic)",
             "xiange": "相惡 (mutual aversion)"}
    p = ROOT / "corpus/processed/structured/relations_seven.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r.get("drug_a") and r.get("drug_b") and r.get("relation"):
                label = SEVEN.get(r["relation"], r["relation"])
                rows.append(ex(
                    f"In the 七情 framework, how do {r['drug_a']} and {r['drug_b']} interact?",
                    f"{r['drug_a']} and {r['drug_b']} are recorded as {label}.",
                    "relation"))

    # ---- 8. compound-class knowledge (Track 2: chemistry) --------------------
    p = ROOT / "corpus/processed/structured/compounds.csv"
    if p.exists():
        seen = set()
        for r in csv.DictReader(p.open(encoding="utf-8")):
            plant = (r.get("plant_binomial") or "").strip()
            cls = (r.get("compound_class") or "").strip()
            if not plant or not cls or (plant, cls) in seen:
                continue
            seen.add((plant, cls))
            rows.append(ex(
                f"What compound class is recorded in {plant}?",
                f"{plant} contains {cls} compounds (per the corpus compound table).",
                "compound"))

    # ---- 9. formula composition (Track 2: knowledge graph) -------------------
    p = ROOT / "corpus/processed/structured/formula_ingredients.csv"
    if p.exists():
        from collections import defaultdict
        grp = defaultdict(list)
        for r in csv.DictReader(p.open(encoding="utf-8")):
            grp[r.get("formula_id")].append(r.get("drug_name"))
        for fid, drugs in list(grp.items())[:600]:
            if not fid or not drugs:
                continue
            rows.append(ex(
                f"What ingredients are recorded in formula {fid}?",
                f"Formula {fid}: " + ", ".join(d for d in drugs if d) + ".",
                "formula"))

    # ---- 10. pharmacology (Track 2: plant-derived compounds for specific disease targets) ----
    p = ROOT / "corpus/processed/structured/pharmacology.csv"
    if p.exists():
        seen = set()
        for r in csv.DictReader(p.open(encoding="utf-8")):
            plant, cls = r["plant_binomial"], r["compound_class"]
            target, disease = r["molecular_target"], r["disease"]
            if (plant, target) in seen:
                continue
            seen.add((plant, target))
            rows.append(ex(
                f"What disease target does {plant} affect, and through which compound class?",
                f"{plant} contains {cls} compounds, which act on {target} — relevant to {disease}.",
                "pharmacology"))

    # ---- 11. IMPPAT: Indian-medicine therapeutic uses (Track 1: therapeutic uses) ----
    p = ROOT / "corpus/processed/structured/imppat_uses.csv"
    if p.exists():
        allu = list(csv.DictReader(p.open(encoding="utf-8")))
        rng = random.Random(1337)
        rng.shuffle(allu)
        for r in allu[:20000]:
            rows.append(ex(
                f"What is {r['plant_binomial']} used for in Indian medicine?",
                f"Recorded use: {r['therapeutic_use']} ({r['system_of_medicine'] or 'Indian medicine'}).",
                "use"))

    # ---- 12. IMPPAT: cross-tradition name mapping (Track 1: map names across eras) ----
    p = ROOT / "corpus/processed/structured/imppat_names.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r.get("common_name"):
                rows.append(ex(
                    f"What is the modern botanical name of {r['common_name']}?",
                    f"{r['common_name']} -> {r['plant_binomial']}.", "name_mapping"))
            if r.get("synonym"):
                rows.append(ex(
                    f"What is {r['plant_binomial']} also known as?",
                    f"Synonym: {r['synonym']} (botanical synonym).", "name_mapping"))

    # ---- 12b. Wikidata: multilingual name mapping (Track 1: map names across traditions) ----
    p = ROOT / "corpus/processed/structured/wikidata_names.csv"
    if p.exists():
        lang = {"de": "German", "fr": "French", "ko": "Korean", "zh": "Chinese", "ja": "Japanese"}
        alln = list(csv.DictReader(p.open(encoding="utf-8")))
        rng = random.Random(1337)
        rng.shuffle(alln)
        for r in alln[:4000]:
            lname = lang.get(r["lang"], r["lang"])
            rows.append(ex(
                f"What is the {lname} name of {r['plant_binomial']}?",
                f"{r['plant_binomial']} is called {r['vernacular_name']} in {lname}.",
                "name_mapping"))

    # ---- 13. IMPPAT: plant -> gene target (Track 2: compounds for specific disease targets) ----
    p = ROOT / "corpus/processed/structured/imppat_targets.csv"
    if p.exists():
        allt = list(csv.DictReader(p.open(encoding="utf-8")))
        rng = random.Random(1337)
        rng.shuffle(allt)
        for r in allt[:20000]:
            rows.append(ex(
                f"What gene target does {r['plant_binomial']} affect?",
                f"{r['plant_binomial']} contains phytochemicals that target {r['gene_target']}.",
                "target"))

    return rows


def main() -> int:
    rows = build()
    if not rows:
        print("no rows built")
        return 1
    rng = random.Random(1337)
    rng.shuffle(rows)
    cut = int(len(rows) * 0.94)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", rows[:cut]), ("val", rows[cut:])):
        with (OUT / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for i, r in enumerate(part):
                fh.write(json.dumps({"id": f"{name}-{i}", "kind": r["kind"], "text": r["text"]},
                                    ensure_ascii=False) + "\n")
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    chars = sum(len(r["text"]) for r in rows)
    print(f"built {len(rows)} SFT examples ({chars/1e6:.2f} M chars)")
    print(f"  by task: {by_kind}")
    print(f"  train {cut} · val {len(rows)-cut} -> artifacts/sft/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
