"""Build the cross-era drug lexicon and the plant/compound tables.

Network stage (all cached + rate limited by ``data/_net.py``):

* **Wikidata** (CC0) resolves a classical Chinese drug name to its taxon:
  ``wbsearchentities`` finds the entity, ``wbgetentities`` reads **P225 (taxon name)**.
  This is a *verifiable* mapping with a citable Q-id -- not a hand-written guess.
* **PubChem** PUG-REST returns CanonicalSMILES / MolecularFormula / CID for a compound name.
  Where PubChem has no structure the row keeps an empty ``smiles`` -- we never invent one.
* **GBIF** supplies family + accepted name for a binomial.

Outputs
-------
``corpus/processed/lexicon_drugs.json``   historical name -> readings -> modern binomial
``corpus/processed/structured/plants.csv``
``corpus/processed/structured/compounds.csv``

    python -m data.build_lexicon
    python -m data.build_lexicon --limit 100
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import Counter

from . import _net

WD_API = "https://www.wikidata.org/w/api.php"
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/{props}/JSON"
GBIF = "https://api.gbif.org/v1/species/match"
OUT_JSON = _net.PROCESSED / "lexicon_drugs.json"
STRUCT = _net.PROCESSED / "structured"

# Chronic drug names that Wikidata mis-resolves or maps to the wrong species.
# Each override is the universally accepted pharmacopoeial binomial.
MANUAL_OVERRIDES = {
    "大黃": "Rheum palmatum",
    "桂枝": "Cinnamomum cassia",
    "麻黃": "Ephedra sinica",
    "芍藥": "Paeonia lactiflora",
    "白朮": "Atractylodes macrocephala",
    "蒼朮": "Atractylodes lancea",
    "茯苓": "Wolfiporia cocos",
    "甘草": "Glycyrrhiza uralensis",
    "人參": "Panax ginseng",
    "黨參": "Codonopsis pilosula",
    "當歸": "Angelica sinensis",
    "川芎": "Ligusticum chuanxiong",
    "地黃": "Rehmannia glutinosa",
    "熟地黃": "Rehmannia glutinosa",
    "黃耆": "Astragalus membranaceus",
    "黃芪": "Astragalus membranaceus",
    "黃連": "Coptis chinensis",
    "黃芩": "Scutellaria baicalensis",
    "黃柏": "Phellodendron amurense",
    "半夏": "Pinellia ternata",
    "附子": "Aconitum carmichaelii",
    "烏頭": "Aconitum carmichaelii",
    "肉桂": "Cinnamomum cassia",
    "陳皮": "Citrus reticulata",
    "枳殼": "Citrus aurantium",
    "枳實": "Citrus aurantium",
    "薄荷": "Mentha canadensis",
    "紫蘇": "Perilla frutescens",
    "荊芥": "Schizonepeta tenuifolia",
    "防風": "Saposhnikovia divaricata",
    "柴胡": "Bupleurum chinense",
    "桔梗": "Platycodon grandiflorus",
    "五味子": "Schisandra chinensis",
    "枸杞": "Lycium barbarum",
    "菊花": "Chrysanthemum morifolium",
    "金銀花": "Lonicera japonica",
    "連翹": "Forsythia suspensa",
    "牡丹皮": "Paeonia suffruticosa",
    "丹參": "Salvia miltiorrhiza",
    "赤芍": "Paeonia lactiflora",
    "澤瀉": "Alisma plantago-aquatica",
    "豬苓": "Polyporus umbellatus",
    "蒼耳子": "Xanthium sibiricum",
    "知母": "Anemarrhena asphodeloides",
    "石膏": "Gypsum",
    "芒硝": "Sodium sulfate",
    "大棗": "Ziziphus jujuba",
    "生薑": "Zingiber officinale",
    "乾薑": "Zingiber officinale",
    "山藥": "Dioscorea polystachya",
    "山楂": "Crataegus pinnatifida",
    "麥芽": "Hordeum vulgare",
    "神麴": "Aspergillus oryzae",
    "何首烏": "Polygonum multiflorum",
    "牛膝": "Achyranthes bidentata",
    "杜仲": "Eucommia ulmoides",
    "續斷": "Dipsacus asper",
    "骨碎補": "Drynaria fortunei",
    "菟絲子": "Cuscuta chinensis",
    "淫羊藿": "Epimedium brevicornu",
    "仙茅": "Curculigo orchioides",
    "巴戟天": "Morinda officinalis",
    "補骨脂": "Cullen corylifolium",
    "益智子": "Alpinia oxyphylla",
    "肉蓯蓉": "Cistanche deserticola",
    "鎖陽": "Cynomorium songaricum",
    "鹿茸": "Cervus nippon",
    "阿膠": "Equus asinus",
    "龍骨": "Fossilia Ossis Mastodi",
    "牡蠣": "Crassostrea gigas",
    "珍珠": "Pinctada margaritifera",
    "硃砂": "Cinnabar",
    "朱砂": "Cinnabar",
    "雄黃": "Realgar",
    "硫黃": "Sulfur",
    "代赭石": "Hematite",
    "磁石": "Magnetite",
    "禹餘糧": "Limonite",
    "滑石": "Talc",
    "爐甘石": "Smithsonite",
    "蟬蛻": "Cryptotympana atrata",
    "僵蠶": "Bombyx mori",
    "全蠍": "Mesobuthus martensii",
    "蜈蚣": "Scolopendra subspinipes",
    "地龍": "Pheretima aspergillum",
    "水蛭": "Hirudo nipponia",
    "土鱉蟲": "Eupolyphaga sinensis",
    "斑蝥": "Mylabris phalerata",
    "蟾酥": "Bufo bufo",
    "麝香": "Moschus moschiferus",
    "犀角": "Rhinoceros unicornis",
    "虎骨": "Panthera tigris",
    "羚羊角": "Saiga tatarica",
    "穿山甲": "Manis pentadactyla",
    "龜甲": "Chinemys reevesii",
    "鱉甲": "Pelodiscus sinensis",
}

# Natural products whose structures anchor the discovery engine. PubChem supplies the
# SMILES; Wikidata P703 supplies the "found in taxon" association.
COMPOUND_SEEDS = [
    "berberine", "palmatine", "coptisine", "jatrorrhizine", "magnoflorine",
    "ginsenoside Rb1", "ginsenoside Rg1", "ginsenoside Rg3", "notoginsenoside R1",
    "artemisinin", "artesunate", "dihydroartemisinin", "scopoletin",
    "curcumin", "demethoxycurcumin", "bisdemethoxycurcumin",
    "baicalein", "baicalin", "wogonin", "oroxylin A",
    "glycyrrhizin", "glycyrrhetinic acid", "liquiritin", "isoliquiritigenin",
    "paeoniflorin", "albiflorin", "paeonol",
    "salvianolic acid B", "tanshinone IIA", "cryptotanshinone", "danshensu",
    "astragaloside IV", "calycosin", "formononetin",
    "schisandrin", "schisandrin A", "gomisin A",
    "ephedrine", "pseudoephedrine",
    "aconitine", "mesaconitine", "hypaconitine",
    "cinobufagin", "bufalin", "resibufogenin",
    "podophyllotoxin", "camptothecin", "paclitaxel", "vincristine", "vinblastine",
    "colchicine", "emetine", "quinine", "quinidine",
    "morphine", "codeine", "papaverine", "thebaine",
    "caffeine", "theophylline", "theobromine",
    "digoxin", "digitoxin", "ouabain",
    "reserpine", "ajmaline", "yohimbine",
    "atropine", "scopolamine", "hyoscyamine",
    "nicotine", "arecoline", "pilocarpine",
    "andrographolide", "neoandrographolide",
    "ginkgolide A", "ginkgolide B", "bilobalide",
    "hypericin", "hyperforin",
    "silybin", "silymarin", "taxifolin",
    "quercetin", "kaempferol", "apigenin", "luteolin", "naringenin", "hesperidin",
    "rutin", "isorhamnetin", "myricetin", "fisetin", "galangin", "chrysin",
    "catechin", "epigallocatechin gallate", "theaflavin",
    "cyanidin", "delphinidin", "pelargonidin",
    "cinnamaldehyde", "eugenol", "cinnamic acid", "coumarin",
    "thymol", "carvacrol", "menthol", "limonene", "pinene", "camphene",
    "linalool", "geraniol", "nerol", "citral", "cineole", "camphor", "borneol",
    "safrole", "myristicin", "apiole", "asarone",
    "capsaicin", "piperine", "gingerol", "shogaol", "zingerone",
    "allicin", "ajoene", "diallyl disulfide", "S-allyl cysteine",
    "sulforaphane", "indole-3-carbinol", "glucoraphanin",
    "betulinic acid", "ursolic acid", "oleanolic acid", "maslinic acid",
    "lupeol", "beta-sitosterol", "stigmasterol", "campesterol",
    "solanine", "tomatine", "alpha-chaconine",
    "aristolochic acid", "aristolactam", "safrole",
    "tetrahydropalmatine", "corydaline", "protopine",
    "sinomenine", "cepharanthine", "tetrandrine", "fangchinoline",
    "matrine", "oxymatrine", "sophoridine",
    "oxymatrine", "dicentrine", "liriodenine",
    "arctigenin", "arctiin", "honokiol", "magnolol",
    "emodin", "rhein", "chrysophanol", "physcion", "aloe-emodin",
    "sennoside A", "sennoside B",
    "puerarin", "daidzein", "genistein", "biochanin A",
    "loganin", "morroniside", "cornel iridoid glycoside",
    "catalpol", "aucubin", "harpagoside",
    "paenol", "paeonol",
    "pseudolaric acid B", "triptolide",
    "celastrol", "pristimerin",
    "ordnin", "salvinorin A",
    "huperzine A", "galantamine",
    "tetrodotoxin", "saxitoxin",
    "sanguinarine", "chelerythrine",
    "piperlongumine", "piperine",
    "withaferin A", "withanolide",
    "boswellic acid", "guggulsterone",
    "commiphoric acid", "myrrh",
    "crocin", "crocetin", "safranal",
    "picrocrocin", "geniposide",
    "kainic acid", "domoic acid",
    "gastrodin", "gastrodigenin",
    "ligustrazine", "ferulic acid",
    "paeoniflorin", "benzoylmesaconine",
    "aconine", "hypognavine",
    "corynoline", "acetylcorynoline",
    "imperatorin", "osthole", "psoralen", "bergapten", "xanthotoxin",
    "isoimperatorin", "cnidicin",
    "esculin", "aescin", "fraxin",
    "higenamine", "nuciferine",
    "lutein", "zeaxanthin", "lycopene", "beta-carotene", "astaxanthin",
    "squalene", "salidroside", "rhodiola",
    "cordycepin", "adenosine",
    "polysaccharide",  # placeholder rejected by PubChem -> row keeps empty smiles
]


# ---------------------------------------------------------------------------
# Wikidata
# ---------------------------------------------------------------------------
def _wd_search(name: str) -> list[str]:
    try:
        d = _net.get_json(WD_API, params={
            "action": "wbsearchentities", "search": name, "language": "zh",
            "format": "json", "limit": 5, "type": "item"}, timeout=40)
        return [h["id"] for h in d.get("search", [])]
    except Exception:
        return []


def _wd_entities(ids: list[str]) -> dict:
    if not ids:
        return {}
    try:
        return _net.get_json(WD_API, params={
            "action": "wbgetentities", "ids": "|".join(ids),
            "props": "claims|labels", "languages": "zh|en",
            "format": "json"}, timeout=60).get("entities", {})
    except Exception:
        return {}


def _taxon_of(ent: dict) -> str | None:
    claims = ent.get("claims", {}).get("P225")
    if not claims:
        return None
    try:
        return claims[0]["mainsnak"]["datavalue"]["value"]
    except Exception:
        return None


def resolve_taxon(name: str) -> tuple[str | None, str, float, str]:
    """Return (binomial, method, confidence, evidence_qid)."""
    if name in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[name], "manual", 0.95, ""
    ids = _wd_search(name)
    if not ids:
        return None, "unresolved", 0.0, ""
    ents = _wd_entities(ids)
    best = None
    for qid in ids:
        ent = ents.get(qid)
        if not ent:
            continue
        taxon = _taxon_of(ent)
        if not taxon:
            continue
        zh = (ent.get("labels", {}).get("zh", {}) or {}).get("value", "")
        exact = (zh == name)
        score = (2 if exact else 0) + (1 if " " in taxon else 0)
        if best is None or score > best[0]:
            best = (score, taxon, qid, exact)
    if not best:
        return None, "unresolved", 0.0, ""
    _score, taxon, qid, exact = best
    if exact and " " in taxon:
        return taxon, "wikidata", 0.90, qid
    if " " in taxon:
        return taxon, "wikidata", 0.70, qid
    return taxon, "wikidata-genus", 0.55, qid


# ---------------------------------------------------------------------------
# GBIF family lookup (cached)
# ---------------------------------------------------------------------------
_GBIF_CACHE: dict[str, dict] = {}


def gbif_lookup(binomial: str) -> dict:
    if binomial in _GBIF_CACHE:
        return _GBIF_CACHE[binomial]
    try:
        d = _net.get_json(GBIF, params={"name": binomial}, timeout=40)
    except Exception:
        d = {}
    _GBIF_CACHE[binomial] = d
    return d


def gbif_family(binomial: str) -> tuple[str, str]:
    d = gbif_lookup(binomial)
    fam = d.get("family") or ""
    accepted = d.get("scientificName") or binomial
    syn = d.get("canonicalName") or binomial
    synonyms = "" if syn == binomial else syn
    return fam, synonyms or accepted


# ---------------------------------------------------------------------------
# PubChem
# ---------------------------------------------------------------------------
def pubchem(name: str) -> dict:
    try:
        d = _net.get_json(PUBCHEM.format(
            name=_q(name), props="CanonicalSMILES,MolecularFormula,IUPACName"),
            timeout=45)
        props = d["PropertyTable"]["Properties"][0]
        return {
            "cid": str(props.get("CID", "")),
            "smiles": props.get("CanonicalSMILES") or props.get("ConnectivitySMILES") or "",
            "formula": props.get("MolecularFormula", ""),
        }
    except Exception:
        return {"cid": "", "smiles": "", "formula": ""}


def _q(s: str) -> str:
    from urllib.parse import quote
    return quote(s, safe="")


# ---------------------------------------------------------------------------
# drivers
# ---------------------------------------------------------------------------
def _candidate_drug_names() -> list[str]:
    names: Counter[str] = Counter()
    struct = STRUCT
    if (struct / "properties.csv").exists():
        for r in csv.DictReader(open(struct / "properties.csv", encoding="utf-8")):
            names[r["drug_name"]] += 3
    for extra in ("formula_ingredients.csv", "uses.csv", "processing.csv"):
        p = struct / extra
        if not p.exists():
            continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            n = r.get("drug_name", "")
            if n and n != "*":
                names[n] += 1
    # only names that look like real 1-4 character drug names
    return [n for n, _ in names.most_common() if 2 <= len(n) <= 6]


def build_lexicon(limit: int | None = None) -> dict:
    cands = _candidate_drug_names()
    if limit:
        cands = cands[:limit]
    print(f"lexicon: resolving {len(cands)} candidate drug names via Wikidata ...")
    entries = []
    for i, name in enumerate(cands, 1):
        binomial, method, conf, qid = resolve_taxon(name)
        if not binomial:
            continue
        item = {
            "name": name,
            "lang": "zh-Hant",
            "readings": [binomial],
            "modern": binomial,
            "method": method,
            "confidence": conf,
            "source_id": "wikidata" if method.startswith("wikidata") else "manual_override",
        }
        if qid:
            item["wikidata"] = qid
        entries.append(item)
        if i % 100 == 0:
            print(f"  {i}/{len(cands)} ... resolved={len(entries)}")
    doc = {
        "generated_by": "data/build_lexicon.py",
        "note": ("Classical Chinese drug name -> modern binomial. method=manual is a "
                 "pharmacopoeial/standard identification; method=wikidata is resolved via "
                 "Wikidata P225 (taxon name), citable by Q-id. confidence is a heuristic, "
                 "not a calibrated probability."),
        "count": len(entries),
        "historical": entries,
    }
    OUT_JSON.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {OUT_JSON} ({len(entries)} entries)")
    return doc


def build_plants(lexicon: dict) -> int:
    rows = {}
    for item in lexicon["historical"]:
        b = item["modern"]
        if b in rows:
            continue
        fam, syn = gbif_family(b)
        rows[b] = {"binomial": b, "family": fam, "synonyms": syn,
                   "tradition": "tcm", "source_id": "gbif+wikidata"}
    out = STRUCT / "plants.csv"
    cols = ["binomial", "family", "synonyms", "tradition", "source_id"]
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows.values():
            w.writerow(r)
    print(f"  wrote {out.name} {len(rows)} rows")
    return len(rows)


def build_compounds(lexicon: dict) -> int:
    # plant <- binomial from the lexicon, used to attach a plausible lead taxon to a compound
    seed_taxa = sorted({i["modern"] for i in lexicon["historical"] if " " in i["modern"]})
    rows = []
    print(f"compounds: querying PubChem + Wikidata for {len(COMPOUND_SEEDS)} seeds ...")
    for i, name in enumerate(COMPOUND_SEEDS, 1):
        pc = pubchem(name)
        # Wikidata "found in taxon" (P703) gives an attestable compound->plant edge
        plant = ""
        ids = _wd_search(name)
        ents = _wd_entities(ids)
        for qid in ids:
            ent = ents.get(qid, {})
            claims = ent.get("claims", {}).get("P703") or []
            for c in claims:
                try:
                    tq = c["mainsnak"]["datavalue"]["value"]["id"]
                except Exception:
                    continue
                tent = _wd_entities([tq]).get(tq, {})
                tax = _taxon_of(tent)
                if tax and " " in tax:
                    plant = tax
                    break
            if plant:
                break
        rows.append({
            "name": name,
            "plant_binomial": plant,
            "compound_class": classify_compound(name),
            "smiles": pc["smiles"],
            "cid": pc["cid"],
            "source_id": "pubchem+wikidata",
        })
        if i % 25 == 0:
            print(f"  {i}/{len(COMPOUND_SEEDS)} ... with_smiles={sum(1 for r in rows if r['smiles'])}")
    out = STRUCT / "compounds.csv"
    cols = ["name", "plant_binomial", "compound_class", "smiles", "cid", "source_id"]
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_sm = sum(1 for r in rows if r["smiles"])
    print(f"  wrote {out.name} {len(rows)} rows ({n_sm} with SMILES)")
    return len(rows)


_CLASS_RULES = [
    ("alkaloid", ("ine", "idine", "amine", "matrine", "berberine", "caffeine")),
    ("terpenoid", ("ol", "ene", "oside", "ginkgolide", "artemisinin", "paclitaxel")),
    ("flavonoid", ("flavone", "flavonol", "flavan", "catechin", "quercetin",
                   "kaempferol", "apigenin", "luteolin", "anthocyan")),
    ("phenylpropanoid", ("cinnam", "coumarin", "ferulic", "eugenol", "safrole")),
    ("polyketide", ("curcumin", "emodin", "rhein", "chrysophanol")),
    ("steroid", ("sterol", "saponin", "ginsenoside", "digoxin", "bufalin")),
    ("organosulfur", ("allicin", "sulforaphane", "disulfide")),
]


def classify_compound(name: str) -> str:
    low = name.lower()
    for cls, keys in _CLASS_RULES:
        if any(k in low for k in keys):
            return cls
    return "unclassified"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None,
                    help="only resolve the N most frequent drug names (debug)")
    ap.add_argument("--only", action="append",
                    choices=["lexicon", "plants", "compounds"], default=None)
    args = ap.parse_args(argv)
    only = set(args.only) if args.only else None
    STRUCT.mkdir(parents=True, exist_ok=True)

    lex = None
    if (not only or "lexicon" in only):
        lex = build_lexicon(args.limit)
    else:
        lex = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if not only or "plants" in only:
        build_plants(lex)
    if not only or "compounds" in only:
        build_compounds(lex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
