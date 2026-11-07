"""Runtime router for the MoE-of-LoRAs: question -> expert domain.

Loads the trained TF-IDF + logistic-regression pipeline from artifacts/router.pkl and returns the expert that
should answer. This is a *learned* model, not a keyword table — its conditional probabilities are what choose
the expert, and they are returned so the decision is inspectable.
"""
from __future__ import annotations

import gzip
import pathlib
import pickle
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKL = ROOT / "artifacts" / "router.pkl"

DOMAIN_LABELS = {
    "t1_classical": "Track 1 — classical knowledge (names, uses, properties)",
    "t2_natprod": "Track 2 — natural products (compounds, targets, pharmacology)",
    "safety": "safety — toxicity, incompatibility, dosing",
}


@lru_cache(maxsize=1)
def _load():
    if not PKL.exists():
        return None
    with gzip.open(PKL, "rb") as fh:
        return pickle.load(fh)


def available() -> bool:
    return _load() is not None


def route(question: str, top_k: int = 3) -> dict:
    """Return the expert domain for a question plus the router's probabilities."""
    blob = _load()
    if blob is None:
        return {"ok": False, "error": "no router.pkl — run scripts/train_router.py"}
    pipe = blob["pipeline"]
    q = (question or "").strip()
    if not q:
        return {"ok": False, "error": "empty question"}
    probs = pipe.predict_proba([q])[0]
    order = probs.argsort()[::-1][:top_k]
    ranked = [{"expert": pipe.classes_[i], "label": DOMAIN_LABELS.get(pipe.classes_[i], pipe.classes_[i]),
               "p": round(float(probs[i]), 4)} for i in order]
    return {"ok": True, "question": q, "expert": ranked[0]["expert"], "confidence": ranked[0]["p"],
            "ranked": ranked, "model": "tfidf(char2-4 + word1-2) + logistic-regression"}
