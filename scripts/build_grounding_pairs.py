#!/usr/bin/env python3
"""Build (passages, question, answer) training pairs that teach **citation discipline**.

Two kinds of example, because grounding is a two-sided skill:

  POSITIVE — the answer is in the retrieved passages, so the model quotes it and cites the source.
  NEGATIVE — the passages do not contain the answer, so the correct output is "the corpus does not record
             this". A model trained only on positives learns to always answer; that is confabulation.

Written to artifacts/grounding_pairs.jsonl, consumed by the curriculum's stage 6.
"""
from __future__ import annotations
import csv, json, pathlib, random, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main() -> int:
    out = (ROOT / "artifacts/grounding_pairs.jsonl").open("w", encoding="utf-8")
    rng = random.Random(1337)
    rows = []
    base = ROOT / "corpus/processed/structured"
    props = list(csv.DictReader((base / "properties.csv").open(encoding="utf-8")))
    for r in props:
        name, nat, flav, chan = r.get("drug_name"), r.get("nature"), r.get("flavors"), r.get("channels")
        if not name or not chan:
            continue
        passage = f"{name}：性 {nat or '—'}，味 {flav or '—'}，歸經 {chan}，毒性 {r.get('toxicity') or '—'}。"
        rows.append({
            "passages": [f"[1] 本草類 (recorded): {passage}"],
            "question": f"What is the 歸經 of {name}?",
            "answer": f"According to the record: {passage}",
        })
    # negatives: a question whose answer is not in the supplied passage
    for r in rng.sample(props, min(600, len(props))):
        other = rng.choice(props)
        if other.get("drug_name") == r.get("drug_name"):
            continue
        passage = f"{other.get('drug_name')}：性 {other.get('nature') or '—'}，味 {other.get('flavors') or '—'}。"
        rows.append({
            "passages": [f"[1] 本草類 (recorded): {passage}"],
            "question": f"What is the 歸經 of {r.get('drug_name')}?",
            "answer": "The corpus does not record this. The supplied passage is about "
                      f"{other.get('drug_name')}, not {r.get('drug_name')}.",
        })
    rng.shuffle(rows)
    for i, r in enumerate(rows):
        text = ("Passages:\n" + "\n".join(r["passages"]) +
                f"\n\nQuestion: {r['question']}\nAnswer: {r['answer']}")
        out.write(json.dumps({"id": f"g{i}", "text": text}) + "\n")
    out.close()
    print(f"wrote artifacts/grounding_pairs.jsonl — {len(rows)} pairs "
          f"({sum(1 for r in rows if 'does not record' in r['answer'])} negatives)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
