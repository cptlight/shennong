#!/usr/bin/env python3
"""Train the MoE router: a *learned* classifier that maps a question to the expert that should answer it.

This replaces the hand-written rule router in the answer path. It is trained on the domain labels from the
expert datasets, using character n-grams (which work for Chinese, Latin binomials and English alike) plus
word n-grams, TF-IDF, and a multinomial logistic regression. Small, CPU-only, fast, inspectable.

    python scripts/train_router.py          # -> artifacts/router.pkl + artifacts/router_report.json
"""
from __future__ import annotations

import collections
import gzip
import json
import pathlib
import pickle

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "artifacts" / "sft" / "domains"
OUT = ROOT / "artifacts" / "router.pkl"
REPORT = ROOT / "artifacts" / "router_report.json"
DOMAINS = ("t1_classical", "t2_natprod", "safety")


def question_of(text: str) -> str:
    try:
        return text.split("<|user|>", 1)[1].split("<|assistant|>", 1)[0].strip()
    except IndexError:
        return ""


def main() -> int:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import FeatureUnion, Pipeline

    X, y = [], []
    for dom in DOMAINS:
        p = D / f"{dom}.jsonl"
        if not p.exists():
            print(f"missing {p} — run scripts/build_expert_datasets.py first")
            return 1
        for line in p.open(encoding="utf-8"):
            if not line.strip():
                continue
            ex = json.loads(line)
            if ex.get("split") != "train":
                continue
            q = question_of(ex.get("text") or "")
            if q:
                X.append(q)
                y.append(dom)
    print(f"router training examples: {len(X):,} · {dict(collections.Counter(y))}")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.15, random_state=1337, stratify=y)
    pipe = Pipeline([
        ("feat", FeatureUnion([
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, max_features=120_000,
                                     sublinear_tf=True)),
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, max_features=60_000,
                                     sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")),
        ])),
        ("clf", LogisticRegression(max_iter=1200, C=4.0, class_weight="balanced", n_jobs=-1)),
    ])
    pipe.fit(Xtr, ytr)
    acc = pipe.score(Xte, yte)
    rep = classification_report(yte, pipe.predict(Xte), output_dict=True, zero_division=0)
    print(f"held-out router accuracy: {acc:.3f}")
    for dom in DOMAINS:
        m = rep.get(dom, {})
        print(f"  {dom:<14} precision {m.get('precision', 0):.3f}  recall {m.get('recall', 0):.3f}  "
              f"f1 {m.get('f1-score', 0):.3f}  n {int(m.get('support', 0))}")

    with gzip.open(OUT, "wb") as fh:
        pickle.dump({"pipeline": pipe, "domains": list(pipe.classes_)}, fh, protocol=4)
    REPORT.write_text(json.dumps({"accuracy": round(acc, 4), "report": rep, "n_train": len(Xtr),
                                  "n_test": len(Xte), "domains": DOMAINS},
                                 indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB) + {REPORT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
