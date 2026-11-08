#!/usr/bin/env python3
"""Map every plant binomial to its German/French/Korean/Chinese vernacular names via Wikidata (CC0).

This is the "retrieve from wiki + language domain sources" layer: Track 1 asks to *map plant names across
eras and traditions*, and the German/French/Korean names were missing entirely (our structured data was
Chinese + Indian binomials). Wikidata gives the multilingual labels for free, openly (CC0).

    python scripts/build_wikidata_names.py        # -> corpus/processed/structured/wikidata_names.csv
"""
from __future__ import annotations

import csv
import json
import pathlib
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRUCT = ROOT / "corpus" / "processed" / "structured"
LANGS = ("en", "hi", "de", "fr", "ko", "zh", "ja")
CHUNK = 60

SPARQL = (
    "SELECT ?binomial ?item ?lang ?label WHERE {\n"
    "  VALUES ?binomial { %s }\n"
    "  ?item wdt:P225 ?binomial .\n"
    "  ?item rdfs:label ?label .\n"
    "  FILTER(LANG(?label) IN (%s))\n"
    "  BIND(LANG(?label) AS ?lang)\n"
    "}"
)


def collect_binomials() -> list[str]:
    seen = set()
    non_plant = ("virus", "bacter", "fungus", "sp.", "spp.")
    for f in ("imppat_names.csv", "plants.csv"):
        p = STRUCT / f
        if not p.exists():
            continue
        col = "plant_binomial" if f == "imppat_names.csv" else "binomial"
        for r in csv.DictReader(p.open(encoding="utf-8")):
            b = (r.get(col) or "").strip()
            # a binomial is exactly two Latin words (genus + species)
            if b and b[0].isupper() and len(b.split()) == 2 and not any(n in b.lower() for n in non_plant):
                seen.add(b)
    return sorted(seen)


def query(chunk: list[str]) -> dict:
    vals = " ".join(f'"{b}"' for b in chunk)
    lang_vals = ", ".join(f'"{l}"' for l in LANGS)
    q = SPARQL % (vals, lang_vals)
    body = urllib.parse.urlencode({"query": q}).encode()
    req = urllib.request.Request(
        "https://query.wikidata.org/sparql",
        data=body,
        headers={"Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "shennong/1.0 (ethnohack)"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    out = {}
    for b in data["results"]["bindings"]:
        binom = b["binomial"]["value"]
        out.setdefault(binom, {})[b["lang"]["value"]] = b["label"]["value"]
    return out


def main() -> int:
    binomials = collect_binomials()
    print(f"{len(binomials):,} unique binomials to map")
    result = {}
    t0 = time.time()
    for i in range(0, len(binomials), CHUNK):
        chunk = binomials[i : i + CHUNK]
        for attempt in range(3):
            try:
                result.update(query(chunk))
                break
            except Exception as e:  # noqa: BLE001
                print(f"  chunk {i} retry {attempt}: {e}")
                time.sleep(2)
        if (i // CHUNK) % 10 == 0:
            rate = i / max(time.time() - t0, 1)
            print(f"  {i}/{len(binomials)} · {rate:.0f}/s", flush=True)
        time.sleep(0.4)  # be polite to the endpoint

    matched = len(result)
    out = STRUCT / "wikidata_names.csv"
    rows = 0
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["plant_binomial", "lang", "vernacular_name"])
        for binom, labels in result.items():
            for lang, label in labels.items():
                if lang in LANGS:
                    w.writerow([binom, lang, label])
                    rows += 1
    print(f"\nmapped {matched:,} binomials -> {rows:,} vernacular names")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
