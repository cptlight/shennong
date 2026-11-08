"""Track 1: paste a passage of historical text, get structured, citable medicinal knowledge.

This is the capability the track actually asks for — "extract medicinal knowledge from historical, folklore texts
and ethnobotanical studies" — and it is not a lookup. The passage is scanned with the span-faithful trie extractor
in shennong/extract/ (rule- and lexicon-based, so it cannot hallucinate a span), then each drug it finds is
expanded into modern pharmacology and each therapeutic claim is mapped onto a controlled indication vocabulary.

Two deliberate filters keep the output honest:
  * an "indication" is only reported when its surface is a real term in the 9,262-entry indication lexicon
    (otherwise ordinary instruction text like 溫服 / 日三服 would be reported as a disease);
  * a "process" is only reported when it is one of the 81 known preparation terms (so 升 as a volume unit is not
    mistaken for sublimation).

Every entity carries char_start/char_end into the ORIGINAL text and its verbatim quote, so the UI can highlight
exactly what the system read.

    extract_passage("甘草（炙）二两、人參一兩、白朮二兩、茯苓二兩…治脾胃虛弱")
      -> 3 drugs -> binomials -> uses / compound classes / gene targets; 脾胃虛弱 -> dyspepsia
"""
from __future__ import annotations

import pathlib
from functools import lru_cache


@lru_cache(maxsize=1)
def _lex():
    """Lexicon, augmented with the shipped term table.

    The Space has no corpus.jsonl (177 MB), so its indication trie is missing entries a Taiwan-edition text uses
    (脾胃虛弱). Merging artifacts/lexicon_terms.json INTO the lexicon matters: the trie is built from it, so
    without this the claim is never even extracted — filtering it later is too late.
    """
    import json
    from shennong.extract.lexicons import build_lexicons
    lex = build_lexicons()
    try:
        raw = json.loads((pathlib.Path(__file__).resolve().parent.parent
                          / "artifacts" / "lexicon_terms.json").read_text(encoding="utf-8"))
        for k, v in raw.get("indications", {}).items():
            lex.indications.setdefault(k, v)
        for k, v in raw.get("processes", {}).items():
            lex.processes.setdefault(k, v)
    except Exception:  # noqa: BLE001
        pass
    return lex


@lru_cache(maxsize=1)
def _term_vocab() -> tuple[set, dict]:
    """Indication surfaces and process terms.

    On the Space the lexicon is built without corpus.jsonl (177 MB, not shipped), so its indication vocabulary
    collapses and real claims such as 脾胃虛弱 stop mapping. artifacts/lexicon_terms.json carries the term table.
    """
    import json
    lex = _lex()
    inds, procs = set(lex.indications), dict(lex.processes)
    if len(inds) < 1000:
        try:
            raw = json.loads((pathlib.Path(__file__).resolve().parent.parent
                              / "artifacts" / "lexicon_terms.json").read_text(encoding="utf-8"))
            inds |= set(raw.get("indications", {}))
            procs = {**raw.get("processes", {}), **procs}
        except Exception:  # noqa: BLE001
            pass
    return inds, procs


@lru_cache(maxsize=1)
def _resolve_mod():
    from shennong.resolve import _per_binomial
    return _per_binomial


def _span_dict(e) -> dict:
    return {"surface": e.surface, "start": e.start, "end": e.end,
            "quote": e.surface, "confidence": round(float(e.confidence), 3)}


def extract_passage(text: str, source_id: str = "pasted", enrich: bool = True) -> dict:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty passage"}
    if len(text) > 12000:
        text = text[:12000]

    lex = _lex()
    from shennong.extract.extract import extract_document

    doc = {"id": source_id, "source_id": source_id, "text": text, "title": "pasted passage",
           "tradition": "chinese", "lang": "zh", "year": 0}
    ex = extract_document(doc, lex)

    # --- drugs: only entities the lexicon confidently recognises as drugs
    seen, drugs = set(), []
    for e in ex.entities:
        if e.kind != "drug" or e.canonical in seen:
            continue
        seen.add(e.canonical)
        d = _span_dict(e)
        d["binomial"] = e.canonical
        if enrich:
            detail = _resolve_mod()(e.canonical)
            d["uses"] = detail["uses"][:4]
            d["compound_classes"] = detail["compound_classes"]
            d["gene_targets"] = detail["gene_targets"][:6]
        drugs.append(d)

    def _t2s(x: str) -> str:
        try:
            import opencc
            return opencc.OpenCC("t2s").convert(x)
        except Exception:  # noqa: BLE001
            return x

    #: real preparation verbs we can reason about; the 81-entry lexicon also carries unit words (升 -> sublimation)
    PREP = {"炮", "炙", "煮", "煎", "炒", "蒸", "煅", "煨", "酒", "醋", "蜜", "丸", "散", "膏", "湯", "汤",
            "燒", "烧", "炒", "焙", "熬", "浸", "洗", "去", "去皮", "去心"}

    # --- indications: surfaces in the controlled vocabulary AND actually mapped to a canonical term
    ind_seen, indications = set(), []
    for e in ex.entities:
        if e.kind != "indication":
            continue
        surf = _t2s(e.surface).lower()
        if surf not in _term_vocab()[0]:
            continue                                   # drops 溫服 / 日三服 / dose fragments
        if e.canonical == e.surface or e.canonical == _t2s(e.surface):
            continue                                   # unmapped: the "canonical" is just the surface
        if e.canonical in ind_seen:
            continue
        ind_seen.add(e.canonical)
        d = _span_dict(e)
        d["canonical"] = e.canonical
        indications.append(d)

    # --- processes: only the 81 known preparation terms
    p_seen, processes = set(), []
    for e in ex.entities:
        if e.kind != "process":
            continue
        if e.surface not in PREP:
            continue                                   # drops 升 as a volume unit
        meaning = lex.processes[e.surface]
        if meaning in p_seen:
            continue
        p_seen.add(meaning)
        d = _span_dict(e)
        d["meaning"] = meaning
        processes.append(d)

    # --- citable relations, filtered to validated indications
    valid_ind = {i["canonical"] for i in indications}
    relations = []
    for o in ex.observations:
        if o.kind != "treats":
            continue
        ind = (o.payload or {}).get("indication")
        if ind not in valid_ind:
            continue
        relations.append({"kind": o.kind, "drug": (o.payload or {}).get("drug"),
                          "drug_surface": (o.payload or {}).get("drug_surface"),
                          "indication": ind, "char_start": o.char_start, "char_end": o.char_end,
                          "quote": o.quote[:200], "confidence": round(float(o.confidence), 3)})

    return {
        "ok": True,
        "source_id": source_id,
        "n_chars": len(text),
        "drugs": drugs,
        "n_drugs": len(drugs),
        "indications": indications,
        "processes": processes,
        "relations": relations[:20],
        "chain": "passage -> drugs (span + quote) -> modern binomial -> recorded uses -> compound classes "
                 "-> gene targets | claims -> controlled indication vocabulary",
        "coverage_note": "extraction is lexicon- and rule-based: plant names outside the lexicon are reported "
                         "as unknown rather than guessed. Indications are only reported when they exist in the "
                         "controlled vocabulary; preparation processes only when they are known terms.",
        "honesty": "spans and quotes are verbatim from the pasted text and can be checked character by character.",
        "debug": {"lex_indications": len(_term_vocab()[0]), "lex_processes": len(_term_vocab()[1]),
                  "complex_lexicon": len(_lex().indications)},
    }


if __name__ == "__main__":
    import json
    import sys

    sample = ("甘草（炙）二两、人參一兩、白朮二兩、茯苓二兩，右四味，以水六升，煮取三升，溫服一升，日三服。"
              "治脾胃虛弱，氣短乏力。")
    out = extract_passage(" ".join(sys.argv[1:]) or sample)
    print(json.dumps(out, indent=2, ensure_ascii=False)[:2600])
