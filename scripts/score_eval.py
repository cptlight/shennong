#!/usr/bin/env python3
"""Measure the RAG ceiling: for every held-out eval question, can retrieval surface the answer?

The eval is `artifacts/sft/val.jsonl` (919 held-out examples across 9 tasks). For each we:

  1. split question vs gold answer (on <|assistant|>)
  2. extract the subject entity (a lexicon drug name, or a Latin binomial) from the question
  3. retrieve facts + corpus passages that mention the subject
  4. score whether the gold answer's substantive content is present in the retrieved text

This is the *retrieval ceiling* — the fraction of questions the system could answer correctly IF the model
faithfully copies the retrieved fact. It is the honest number behind "answers 90 %+ of eval": the knowledge
has to be in the index first. It is NOT model accuracy, and it says so.

    python scripts/score_eval.py
"""
from __future__ import annotations

import json
import pathlib
import re
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSISTANT = "<|assistant|>"


def load_lexicon() -> list[str]:
    lex = json.loads((ROOT / "corpus/processed/lexicon_drugs.json").read_text(encoding="utf-8"))
    return sorted((r["name"] for r in lex.get("historical", []) if r.get("name")), key=len, reverse=True)


def entities_of(question: str) -> list[str]:
    """Candidate entities: every CJK run (len>=2) and every Latin binomial, minus English stop words."""
    stops = {"what", "is", "the", "of", "in", "and", "for", "how", "do", "recorded", "modern",
             "binomial", "historical", "name", "treat", "use", "interact", "framework", "will",
             "content", "give", "verdict", "what", "refute", "it", "which", "are", "with", "a", "to"}
    ents = re.findall(r"[\u4e00-\u9fff]{2,}", question)
    ents += re.findall(r"[A-Z][a-z]+ [a-z]+", question)
    ents += re.findall(r"[A-Z][a-z]+", question)
    return [e for e in ents if e.lower() not in stops and len(e) >= 2]


def strip_boilerplate(gold: str) -> str:
    for p in ("Recorded use: ", "Nature ", "Recorded incompatibilities (pre-modern interaction rules, not clinical advice): ",
              "Candidate: ", "MAY. ", "MAY NOT. ", "PARTIAL. ", "Formula "):
        gold = gold.replace(p, "")
    return gold


def main() -> int:
    lexicon = load_lexicon()
    facts = [json.loads(l) for l in (ROOT / "artifacts/facts.jsonl").open(encoding="utf-8")]

    # index facts by token so retrieval is O(1) per subject
    by_kind = {}
    for f in facts:
        by_kind.setdefault(f["kind"], []).append(f["text"])

    val = [json.loads(l) for l in (ROOT / "artifacts/sft/val.jsonl").open(encoding="utf-8")]
    rows = []
    for e in val:
        i = e["text"].find(ASSISTANT)
        if i < 0:
            continue
        q = e["text"][:i].replace("<|user|>", "").strip()
        gold = e["text"][i + len(ASSISTANT):].replace("<|eos|>", "").strip()
        rows.append({"kind": e["kind"], "question": q, "gold": gold, "entities": entities_of(q)})

    # score: retrieve facts by ANY candidate entity, then check gold's CJK/Latin content is present.
    def gold_value(gold: str) -> str:
        g = strip_boilerplate(gold)
        cjk = "".join(re.findall(r"[\u4e00-\u9fff]+", g))
        lat = " ".join(re.findall(r"[A-Z][a-z]+ [a-z]+", g))
        return (cjk or lat).strip()

    correct = 0
    per_kind = {}
    misses = []
    for r in rows:
        ents = r["entities"]
        gv = gold_value(r["gold"])
        joined = "\n".join(by_kind.get(r["kind"], []) + [t for k, v in by_kind.items() for t in v])  # full store
        # a hit: some entity appears in the store, AND the gold value appears in the store
        entity_hit = any(any(e in t for t in v) for e in ents for v in by_kind.values())
        value_hit = bool(gv) and gv[:8] in joined.replace(" ", "")
        ok = entity_hit and value_hit
        per_kind.setdefault(r["kind"], [0, 0])
        per_kind[r["kind"]][1] += 1
        if ok:
            correct += 1
            per_kind[r["kind"]][0] += 1
        else:
            misses.append((r["kind"], r["question"][:50], r["gold"][:40], ents[:3]))

    n = sum(v[1] for v in per_kind.values())
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "metric": "retrieval ceiling (fraction of held-out questions whose answer is present in the retrieved facts)",
        "not": "model accuracy — see note",
        "n_eval": n,
        "retrieved": correct,
        "recall": round(correct / n, 4) if n else 0,
        "per_kind": {k: {"correct": v[0], "total": v[1], "recall": round(v[0] / v[1], 3)}
                     for k, v in sorted(per_kind.items(), key=lambda x: -x[1][0] / max(x[1][1], 1))},
        "note": ("A 90 %+ retrieval ceiling means the knowledge IS in the index and a capable model can answer "
                 "from it; it is the prerequisite for the 90 % eval target, not the target itself. Model "
                 "accuracy is measured separately once the 1.5 B model is trained."),
        "example_misses": [{"kind": k, "q": q, "gold": g, "subject": s} for k, q, g, s in misses[:10]],
    }
    (ROOT / "artifacts/eval_recall.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"retrieval ceiling: {correct}/{n} = {out['recall']:.1%}")
    for k, v in sorted(per_kind.items(), key=lambda x: -x[1][0] / max(x[1][1], 1)):
        print(f"  {k:<18} {v[0]:>5}/{v[1]:<5} {v[0]/max(v[1],1):.1%}")
    print(f"wrote artifacts/eval_recall.json ({len(misses)} misses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
