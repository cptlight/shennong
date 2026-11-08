"""Track 1 demonstration: resolve a plant name from ANY era or language, then follow it to modern pharmacology.

The problem this solves: a 16th-century Chinese drug name, an Ayurvedic Sanskrit name, a Latin binomial and a
modern English common name can all denote the same plant, and no single lexicon links them. Our corpus does —
827 historical Chinese names, 4,154 Indian plants with synonyms, and 7,764 vernacular names in
de/fr/ko/zh/ja — plus the therapeutic uses, compound classes and gene targets for the resolved plant.

    resolve_plant("丹參")
      -> Salvia miltiorrhiza
      -> names in 5 languages, 3 recorded uses, terpenoid class, 2 gene targets

This is the chain the track asks for: map names across eras -> identify uses -> connect to modern pharmacology.
"""
from __future__ import annotations

import csv
import json
import pathlib
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus" / "processed" / "structured"
LANG_NAMES = {"zh": "Chinese", "en": "English", "de": "German", "fr": "French",
              "ko": "Korean", "ja": "Japanese", "la": "Latin"}


def _rows(name: str) -> list[dict]:
    p = STRUCT / name
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, str]:
    p = ROOT / "corpus/processed/lexicon_drugs.json"
    try:
        lex = json.loads(p.read_text(encoding="utf-8"))
        return {r["name"]: r["modern"] for r in lex.get("historical", []) if r.get("name") and r.get("modern")}
    except Exception:  # noqa: BLE001
        return {}


@lru_cache(maxsize=1)
def _index():
    """name (any script) -> (binomial, provenance)."""
    idx: dict[str, tuple[str, str]] = {}
    for n, b in _lexicon().items():                       # historical Chinese -> binomial
        idx.setdefault(n.strip().lower(), (b, "historical Chinese lexicon"))
    for r in _rows("imppat_names.csv"):                   # Indian synonyms + common names
        b = (r.get("plant_binomial") or "").strip()
        for k, how in (("synonym", "Indian botanical synonym"), ("common_name", "common name (Indian medicine)")):
            v = (r.get(k) or "").strip()
            if v and b:
                idx.setdefault(v.lower(), (b, how))
    for r in _rows("wikidata_names.csv"):                 # multilingual vernacular
        b = (r.get("plant_binomial") or "").strip()
        v = (r.get("vernacular_name") or "").strip()
        lang = r.get("lang") or ""
        if v and b:
            idx.setdefault(v.lower(), (b, f"Wikidata {LANG_NAMES.get(lang, lang)} name"))
    for r in _rows("plants.csv"):
        b = (r.get("binomial") or "").strip()
        if b:
            idx.setdefault(b.lower(), (b, "modern botanical binomial"))
    # every binomial that appears in ANY structured table — plants.csv only covers 284 of the 4,716 we hold
    import csv as _csv
    for f in sorted(STRUCT.glob("*.csv")):
        with f.open(encoding="utf-8") as fh:
            rd = _csv.DictReader(fh)
            col = next((c for c in (rd.fieldnames or []) if "binomial" in (c or "")), None)
            if not col:
                continue
            for r in rd:
                b = (r.get(col) or "").strip()
                if b:
                    idx.setdefault(b.lower(), (b, f"modern botanical binomial ({f.stem})"))
    # alias traditional forms onto the same entries (人參 -> 人参)
    for k in [k for k in idx if _is_cjk(k)]:
        simple = _t2s(k)
        if simple != k:
            idx.setdefault(simple, idx[k])
    return idx


def _t2s(text: str) -> str:
    """Traditional -> simplified Chinese, so 人參 and 人参 hit the same lexicon entry."""
    try:
        import opencc
        return opencc.OpenCC("t2s").convert(text)
    except Exception:  # noqa: BLE001
        return text


def _is_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def _per_binomial(binomial: str) -> dict:
    b = binomial.strip().lower()
    names = {}
    for r in _rows("wikidata_names.csv"):
        if (r.get("plant_binomial") or "").strip().lower() == b:
            names[r.get("lang")] = r.get("vernacular_name")
    uses = []
    for r in _rows("uses.csv"):
        if (r.get("plant_binomial") or "").strip().lower() == b:
            uses.append({"use": r.get("indication", ""), "tradition": r.get("tradition", ""),
                         "modern": r.get("indication_modern", "")})
    for r in _rows("imppat_uses.csv"):
        if (r.get("plant_binomial") or "").strip().lower() == b:
            uses.append({"use": r.get("therapeutic_use", ""),
                         "tradition": r.get("system_of_medicine", "") or "Indian medicine", "modern": ""})
    classes, targets, pharm = set(), set(), []
    for r in _rows("compounds.csv"):
        if (r.get("plant_binomial") or "").strip().lower() == b:
            c = (r.get("compound_class") or "").strip()
            if c and c != "unclassified":
                classes.add(c)
    for r in _rows("imppat_targets.csv"):
        if (r.get("plant_binomial") or "").strip().lower() == b:
            targets.add(r.get("gene_target", ""))
    for r in _rows("pharmacology.csv"):
        if (r.get("plant_binomial") or "").strip().lower() == b:
            pharm.append({"compound_class": r.get("compound_class"),
                          "molecular_target": r.get("molecular_target"), "disease": r.get("disease")})
    return {"names": {k: v for k, v in names.items() if v},
            "uses": uses[:8],
            "compound_classes": sorted(classes)[:6],
            "gene_targets": sorted(t for t in targets if t)[:10],
            "pharmacology": pharm[:6]}


def resolve_plant(name: str) -> dict:
    q = (name or "").strip()
    if not q:
        return {"ok": False, "error": "empty name"}
    idx = _index()
    hit = idx.get(q.lower())
    matched_via = "query did not match any lexicon"
    binomial = None
    if hit:
        binomial, matched_via = hit
    else:
        # substring matching ONLY for CJK keys: Latin substring matching is unsafe
        # ("liquorice" contains "rice", which resolved Glycyrrhiza to Oryza sativa)
        ql = q.lower()
        for k in sorted(idx, key=len, reverse=True):
            if len(k) >= 2 and _is_cjk(k) and k in ql:
                binomial, matched_via = idx[k]
                matched_via += " (embedded in the query)"
                break
    if not binomial:
        import difflib
        close = difflib.get_close_matches(q.lower(), list(idx), n=5, cutoff=0.72)
        if not close and _is_cjk(q):
            # CJK: rank entries by character overlap so a variant spelling still gets near matches
            qs = set(q)
            scored = sorted(((len(qs & set(k)), k) for k in idx if _is_cjk(k)), reverse=True)
            close = [k for sc, k in scored[:5] if sc >= 1]
        return {"ok": False, "query": q, "error": "name not resolved in the corpus lexicon",
                "suggestions": [{"name": c, "binomial": idx[c][0], "via": idx[c][1]} for c in close],
                "note": "index covers historical Chinese, Indian synonyms/common names and 5 vernacular "
                        "languages; see suggestions for near matches"}
    detail = _per_binomial(binomial)
    return {"ok": True, "query": q, "binomial": binomial, "matched_via": matched_via,
            "names": detail["names"], "uses": detail["uses"],
            "compound_classes": detail["compound_classes"], "gene_targets": detail["gene_targets"],
            "pharmacology": detail["pharmacology"],
            "chain": "name (any era/language) -> modern binomial -> recorded uses -> compound classes -> "
                     "gene targets -> modern pharmacology"}


if __name__ == "__main__":
    import sys
    print(json.dumps(resolve_plant(" ".join(sys.argv[1:]) or "丹參"), indent=2, ensure_ascii=False)[:2500])
