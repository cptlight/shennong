"""Build ``corpus/processed/structured/compounds.csv`` with real structures.

Two independent, citable routes are merged:

1. **Wikidata P703 ("found in taxon")** — for every taxon that the drug lexicon resolved, fetch
   the compounds Wikidata records as occurring in that organism, together with **P233
   (canonical SMILES)** and **P662 (PubChem CID)**. This is a machine-readable, per-row citable
   association, not a hand-written guess.
2. **PubChem PUG-REST** for a curated seed list of the natural products a discovery engine is
   most likely to want (alkaloids, flavonoids, terpenoids, saponins).

Where neither route yields a structure, the row keeps ``smiles`` empty. **We never invent a
structure.** The count of nulls is reported so downstream can measure coverage honestly.

    python -m data.build_compounds
    python -m data.build_compounds --skip-seeds
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter

import requests

from . import _net
from .build_lexicon import COMPOUND_SEEDS, _q, classify_compound, pubchem

STRUCT = _net.PROCESSED / "structured"
LEXICON = _net.PROCESSED / "lexicon_drugs.json"
OUT = STRUCT / "compounds.csv"
SPARQL = "https://query.wikidata.org/sparql"
WD_API = "https://www.wikidata.org/w/api.php"
BATCH = 25

# elemental / primary-metabolite noise that P703 returns along with real phytochemistry
_NON_PHYTO = {
    "water", "oxygen", "nitrogen", "carbon dioxide", "carbon", "hydrogen", "germanium",
    "calcium", "potassium", "sodium", "magnesium", "iron", "zinc", "copper", "manganese",
    "silicon", "aluminium", "aluminum", "sulfur", "phosphorus", "chlorine", "selenium",
    "cobalt", "nickel", "molybdenum", "boron", "iodine", "fluorine", "lithium", "lead",
    "cadmium", "mercury", "arsenic", "tin", "silver", "gold", "platinum", "titanium",
    "adenine", "guanine", "cytosine", "thymine", "uracil", "purine", "pyrimidine",
    "uric acid", "urea", "glycerol", "phosphoric acid", "oxalic acid", "citric acid",
    "succinic acid", "fumaric acid", "malic acid", "lactic acid", "glucose", "fructose",
    "sucrose", "ribose", "deoxyribose", "starch", "cellulose", "pectin", "chlorophyll",
    "ammonia", "nitric acid", "sulfuric acid", "hydrochloric acid", "acetic acid",
    "formic acid", "ethanol", "methanol", "acetone", "glycerin",
}
_METAL_SMILES = re.compile(r"^\[[A-Z][a-z]?\]$")


def _sparql(query: str) -> list[dict]:
    try:
        d = _net.get_json(SPARQL, params={"format": "json", "query": query}, timeout=120)
        return d["results"]["bindings"]
    except Exception as e:
        print(f"  ! sparql failed: {e!r}")
        return []


def taxon_to_qid(binomial: str) -> str | None:
    """Resolve a binomial to a Wikidata item whose P225 matches it."""
    try:
        d = _net.get_json(WD_API, params={
            "action": "wbsearchentities", "search": binomial, "language": "en",
            "format": "json", "limit": 3, "type": "item"}, timeout=40)
    except Exception:
        return None
    ids = [h["id"] for h in d.get("search", [])]
    if not ids:
        return None
    try:
        ent = _net.get_json(WD_API, params={
            "action": "wbgetentities", "ids": "|".join(ids), "props": "claims",
            "format": "json"}, timeout=60).get("entities", {})
    except Exception:
        return None
    for qid in ids:
        cl = ent.get(qid, {}).get("claims", {}).get("P225") or []
        for c in cl:
            try:
                if c["mainsnak"]["datavalue"]["value"].split()[0] == binomial.split()[0] \
                        and c["mainsnak"]["datavalue"]["value"] == binomial:
                    return qid
            except Exception:
                continue
    return None


def compounds_for_taxa(taxa_qids: dict[str, str]) -> list[dict]:
    """SPARQL: compounds with P703 (found in taxon) for a batch of taxa."""
    vals = " ".join(f"wd:{q}" for q in taxa_qids.values())
    q = f"""SELECT ?taxon ?compound ?compoundLabel ?smiles ?cid WHERE {{
  VALUES ?taxon {{ {vals} }}
  ?compound wdt:P703 ?taxon .
  OPTIONAL {{ ?compound wdt:P233 ?smiles . }}
  OPTIONAL {{ ?compound wdt:P662 ?cid . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
    bindings = _sparql(q)
    rev = {v: k for k, v in taxa_qids.items()}
    out = []
    for b in bindings:
        taxon_q = b["taxon"]["value"].rsplit("/", 1)[-1]
        binomial = rev.get(taxon_q, "")
        if not binomial:
            continue
        name = (b.get("compoundLabel", {}) or {}).get("value", "")
        smiles = (b.get("smiles", {}) or {}).get("value", "")
        cid = (b.get("cid", {}) or {}).get("value", "")
        out.append({"name": name, "plant_binomial": binomial, "smiles": smiles,
                    "cid": cid, "source_id": "wikidata_p703"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-seeds", action="store_true")
    ap.add_argument("--max-taxa", type=int, default=400)
    args = ap.parse_args(argv)
    STRUCT.mkdir(parents=True, exist_ok=True)

    lex = json.loads(LEXICON.read_text(encoding="utf-8"))
    binomials = []
    seen = set()
    for item in lex.get("historical", []):
        b = item.get("modern", "")
        if " " in b and b not in seen:
            seen.add(b)
            binomials.append(b)
    binomials = binomials[:args.max_taxa]
    print(f"resolving {len(binomials)} binomials to Wikidata taxa ...")

    taxa_qids: dict[str, str] = {}
    for i, b in enumerate(binomials, 1):
        q = taxon_to_qid(b)
        if q:
            taxa_qids[b] = q
        if i % 50 == 0:
            print(f"  {i}/{len(binomials)} resolved={len(taxa_qids)}")
    print(f"  taxa with Q-id: {len(taxa_qids)}")

    rows: dict[tuple[str, str], dict] = {}

    # route 1: Wikidata P703
    items = list(taxa_qids.items())
    for i in range(0, len(items), BATCH):
        batch = dict(items[i:i + BATCH])
        got = compounds_for_taxa(batch)
        for r in got:
            name = r["name"]
            if not name or name.lower() in _NON_PHYTO:
                continue
            if not r["smiles"] and not r["cid"]:
                continue
            key = (name.lower(), r["plant_binomial"])
            rows.setdefault(key, {
                "name": name, "plant_binomial": r["plant_binomial"],
                "compound_class": classify_compound(name),
                "smiles": r["smiles"], "cid": r["cid"],
                "source_id": "wikidata_p703",
            })
        print(f"  batch {i // BATCH + 1}: +{len(got)} rows, total {len(rows)}")

    # route 2: curated seed list via PubChem (guarantees the key natural products exist)
    if not args.skip_seeds:
        print(f"seeding {len(COMPOUND_SEEDS)} curated compounds via PubChem ...")
        plant_of = _seed_plant_map(taxa_qids)
        for i, name in enumerate(COMPOUND_SEEDS, 1):
            pc = pubchem(name)
            if not pc["smiles"]:
                continue
            plant = plant_of.get(name.lower(), "")
            key = (name.lower(), plant)
            if key in rows:
                continue
            rows[key] = {
                "name": name, "plant_binomial": plant,
                "compound_class": classify_compound(name),
                "smiles": pc["smiles"], "cid": pc["cid"],
                "source_id": "pubchem",
            }
            if i % 40 == 0:
                print(f"  {i}/{len(COMPOUND_SEEDS)} ... total {len(rows)}")

    out_rows = list(rows.values())
    out_rows.sort(key=lambda r: (r["plant_binomial"], r["name"]))
    cols = ["name", "plant_binomial", "compound_class", "smiles", "cid", "source_id"]
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    n_sm = sum(1 for r in out_rows if r["smiles"])
    n_null = len(out_rows) - n_sm
    n_taxa = len({r["plant_binomial"] for r in out_rows if r["plant_binomial"]})
    print(f"\nwrote {OUT}: {len(out_rows)} rows")
    print(f"  with SMILES : {n_sm} ({100 * n_sm / max(1, len(out_rows)):.1f}%)")
    print(f"  null SMILES : {n_null}  <-- never invented")
    print(f"  distinct plants: {n_taxa}")
    return 0


def _seed_plant_map(taxa_qids: dict[str, str]) -> dict[str, str]:
    """Ask Wikidata P703 in reverse for the curated seeds, to attach a plant to each."""
    out: dict[str, str] = {}
    try:
        lex = json.loads(LEXICON.read_text(encoding="utf-8"))
    except Exception:
        return out
    names = [i["name"] for i in lex.get("historical", [])][:0]  # unused
    names = COMPOUND_SEEDS
    # one batched query over the seed labels is not possible with labels; use search per seed
    for name in names[:60]:  # keep the request count bounded
        try:
            d = _net.get_json(WD_API, params={
                "action": "wbsearchentities", "search": name, "language": "en",
                "format": "json", "limit": 1, "type": "item"}, timeout=30)
        except Exception:
            continue
        if not d.get("search"):
            continue
        qid = d["search"][0]["id"]
        binds = _sparql(
            "SELECT ?taxonLabel WHERE { wd:%s wdt:P703 ?taxon . "
            "SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". } }"
            " LIMIT 3" % qid)
        for b in binds:
            lab = (b.get("taxonLabel", {}) or {}).get("value", "")
            if " " in lab and lab[0].isupper():
                out[name.lower()] = lab
                break
    return out


if __name__ == "__main__":
    raise SystemExit(main())
