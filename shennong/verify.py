"""Claim–span **support** verification.

The repo already verifies that a cited span *exists* and is a real substring of a real source. That
catches a mislocated citation (it found 8 of 10 wrong spans in an earlier candidate artefact) but it
does not check whether the span **supports the claim**. This module closes that gap with signals that
are honest about what they are.

What it checks
--------------
1. **Entity support** — does the span actually name the drug the claim is about (after 繁/简 folding)?
   This is the check that would have caught the mislocated citations automatically.
2. **Relation support** — does the span carry a classical therapeutic cue (治 / 療 / 主 / 止 / 消 / 散 /
   補 …) or a pharmacological action word, i.e. is it a *use* statement rather than incidental prose?
3. **Indication overlap** — character-bigram Jaccard between the claimed indication and the span.
4. **Polarity conflict** — a span that says 不治 / 忌 / 禁 while the claim asserts a use is a
   contradiction, not support.
5. **Length sanity** — a span shorter than a phrase or longer than a passage is not evidence.

What it deliberately does **not** claim to do
---------------------------------------------
This is **not** cross-lingual semantic entailment. The claims are largely English and the classical
spans Chinese/Sanskrit, so a dense multilingual encoder would be required to judge whether a Chinese
passage *entails* an English mechanistic sentence. That is the documented next step. What this module
*can* do is decide — reproducibly and measurably — whether the evidence attached to a claim is about
the same drug, in a use-statement, without a polarity contradiction. Against a shuffled-negative gold
set that is a real, checkable contribution rather than a promise.

Usage
-----
    from shennong.verify import verify_support
    r = verify_support(claim="…", span="甘草，味甘，平。主五臟六腑寒熱邪氣…",
                       drug_names=["甘草", "Glycyrrhiza uralensis"], indication="cough")
    r.supported, r.score, r.signals
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .normalize import char_ngrams, fold_zh, jaccard

# Classical therapeutic-relation cues: a span containing one of these is making a *use* statement.
USE_CUES = (
    # explicit therapeutic verbs
    "治", "療", "疗", "主", "止", "消", "除", "解", "散", "補", "补", "潤", "润",
    "下", "殺", "杀",
    # administration / preparation forms — the classical corpus states use through recipes
    # (「用百部根漬酒」, 「煎服」, 「為末」), not only through the verb 治
    "服", "食", "飲", "饮", "用", "方", "煎", "煮", "漬", "渍", "熏", "燒", "烧",
    "湯", "汤", "丸", "膏", "調", "调", "吞", "含", "漱", "塗", "涂", "敷", "洗", "熨", "貼", "贴",
    "cure", "treat", "relieve", "used for", "indicated", "remedy", "heal", "alleviate",
    "administer", "decoction", "infusion", "apply", "take",
)
# Polarity markers that invert a use statement.
NEGATIONS = ("不治", "勿服", "忌服", "禁用", "不可", "非", "勿", "禁", "莫", "不得", "不可用", "not", "never")
# Words that mark commentary rather than a use statement.
COMMENTARY = ("一名", "又名", "氣味", "气味", "氣味甘", "釋名", "集解", "附方", "校正")

MIN_SPAN_CHARS = 8
MAX_SPAN_CHARS = 600


@dataclass
class SupportResult:
    supported: bool
    score: float
    signals: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"supported": self.supported, "score": round(self.score, 4),
                "signals": self.signals, "reasons": self.reasons}


def _fold_names(names: list[str]) -> list[str]:
    out = []
    for n in names:
        if not n:
            continue
        n = n.strip()
        out.append(n)
        f = fold_zh(n)
        if f != n:
            out.append(f)
    return [n for n in dict.fromkeys(out) if n]


def verify_support(
    claim: str,
    span: str,
    drug_names: list[str] | None = None,
    indication: str = "",
    require_entity: bool = True,
) -> SupportResult:
    """Decide whether `span` supports `claim` about one of `drug_names`."""
    reasons: list[str] = []
    if not span or not span.strip():
        return SupportResult(False, 0.0, {"span_present": 0.0}, ["empty span"])

    span_f = fold_zh(span)
    claim_f = fold_zh(claim or "")
    names = _fold_names([n for n in (drug_names or []) if n])

    # --- 1. entity support -------------------------------------------------------------
    hit_names = [n for n in names if n in span_f]
    entity_present = bool(hit_names)
    if names and not entity_present:
        reasons.append(f"span does not name the claimed drug ({names[0]!r})")

    # --- 2. relation support -----------------------------------------------------------
    cue = next((c for c in USE_CUES if c in span_f), None)
    relation_present = cue is not None
    if not relation_present:
        reasons.append("span contains no therapeutic-relation cue")

    # --- 3. indication overlap ---------------------------------------------------------
    ind = (indication or "").strip()
    overlap = 0.0
    if ind:
        ind_f = fold_zh(ind)
        overlap = jaccard(ind_f, span_f, n=2)
        if len(ind_f) >= 2 and ind_f in span_f:
            overlap = 1.0
    indication_ok = overlap >= 0.10

    # --- 4. polarity conflict ----------------------------------------------------------
    neg = next((n for n in NEGATIONS if n in span_f), None)
    neg_conflict = bool(neg) and relation_present and not any(n in claim_f for n in ("not", "no ", "不"))

    # --- 5. length sanity --------------------------------------------------------------
    n_chars = len(span.strip())
    length_ok = MIN_SPAN_CHARS <= n_chars <= MAX_SPAN_CHARS
    commentary = any(c in span_f for c in COMMENTARY) and not relation_present
    if not length_ok:
        reasons.append(f"span length {n_chars} outside [{MIN_SPAN_CHARS}, {MAX_SPAN_CHARS}]")

    # --- score -------------------------------------------------------------------------
    score = 0.0
    score += 0.45 * float(entity_present)
    score += 0.25 * float(relation_present)
    score += 0.20 * float(indication_ok)
    score += 0.10 * float(length_ok)
    if not entity_present:
        score *= 0.35           # a span about a different drug cannot support the claim
    if neg_conflict:
        score *= 0.30
        reasons.append(f"polarity conflict: span contains {neg!r} against an asserted use")
    if commentary:
        score *= 0.7
        reasons.append("span reads as commentary (name/edition note) rather than a use statement")

    supported = entity_present and length_ok and not neg_conflict and (relation_present or indication_ok)
    if require_entity is False:
        supported = length_ok and not neg_conflict and (relation_present or indication_ok)

    signals = {
        "entity_present": float(entity_present),
        "entity_hits": hit_names[:4],
        "relation_cue": cue,
        "relation_present": float(relation_present),
        "indication_overlap": round(overlap, 4),
        "indication_ok": float(indication_ok),
        "negation": neg,
        "negation_conflict": float(neg_conflict),
        "length_chars": n_chars,
        "length_ok": float(length_ok),
        "commentary_pattern": float(commentary),
    }
    return SupportResult(supported=supported, score=round(min(1.0, score), 4),
                         signals=signals, reasons=reasons)


def auc(pos: list[float], neg: list[float]) -> float:
    """Rank-based AUC (Mann–Whitney U), no dependencies."""
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))
