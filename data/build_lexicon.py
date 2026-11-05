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

# Surfaces that must NEVER be mapped to a binomial: human-derived materia medica (no taxon),
# and body-part / mineral terms that Wikidata has mislabelled with a taxon (e.g. 爪甲 ->
# Aspergillus unguis, which is a Wikidata label error). Leaving them unresolved is correct.
MANUAL_UNRESOLVED = {
    # human-derived
    "爪甲", "人髮", "亂髮", "髮髲", "頭垢", "耳垢", "人乳", "乳汁", "人中白", "童便",
    "人尿", "糞清", "紫河車", "人胞", "天靈蓋", "人牙", "人骨", "月水", "血餘",
    # mineral / inorganic single substances with no organism binomial
    "石膏", "芒硝", "朴硝", "玄明粉", "滑石", "磁石", "代赭石", "禹餘糧", "爐甘石",
    "無名異", "食鹽", "光明鹽", "硝石", "硼砂", "硇砂", "白礬", "綠礬", "膽礬",
    "硫黃", "雄黃", "雌黃", "硃砂", "朱砂", "水銀", "輕粉", "鉛丹", "密陀僧",
    "白堊", "赤石脂", "白石脂", "黃土", "伏龍肝", "百草霜", "墨", "鐵", "銅", "鉛",
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
    # only names that look like real drug surfaces -- drop prose fragments that the
    # commentary parser occasionally emits ("一名…", "…者", sentence tails)
    procedure = {"煮取", "溫服", "去滓", "上味", "溫酒", "以水", "水煮", "研末", "為末",
                 "搗汁", "煎服", "空心", "食前", "食後", "日三", "分服", "取汁", "微火",
                 "更煎", "再服", "頓服", "少許", "不拘", "時服", "湯調", "酒調", "米飲",
                 "白湯", "生用", "炒用", "蜜丸", "糊丸", "醋丸", "粥飲", "相須", "相使",
                 "相畏", "相殺", "相惡", "相反", "單行", "有毒", "無毒", "一名", "方中"}
    bad = ("一名", "一种", "一種", "者", "云", "曰", "按", "此", "其", "之", "而",
           "上焦", "下焦", "中焦", "丈夫", "婦人", "小兒", "孕婦", "人", "病", "痛",
           "氣", "血", "陰", "陽", "虛", "實", "寒", "熱", "風", "濕")
    out = []
    for n, c in names.most_common():
        if not (2 <= len(n) <= 6):
            continue
        if n in procedure:
            continue
        if any(n.startswith(b) or n.endswith(b) for b in bad):
            continue
        if any(ch in n for ch in "。，、；：（）()"):
            continue
        out.append(n)
    return out


def build_lexicon(limit: int | None = None) -> dict:
    """Resolve drug names, batching the wbgetentities calls to keep requests reasonable.

    ``wbsearchentities`` handles Chinese script variants (人參 / 人参) server-side, so the
    search is done for every name; the (much cheaper) entity fetch is batched 50 ids at a time.
    """
    cands = _candidate_drug_names()
    if limit:
        cands = cands[:limit]
    print(f"lexicon: resolving {len(cands)} candidate drug names via Wikidata ...")

    hits: dict[str, list[str]] = {}
    todo = [n for n in cands if n not in MANUAL_OVERRIDES]
    from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: F401
    done = 0
    # Wikimedia tolerates a handful of parallel reads; stay polite with a small pool.
    for name in todo:
        ids = _wd_search(name)
        if ids:
            hits[name] = ids
        done += 1
        if done % 250 == 0:
            print(f"  search {done}/{len(todo)} (found {len(hits)})")

    all_ids = sorted({q for ids in hits.values() for q in ids})
    ents: dict = {}
    for i in range(0, len(all_ids), 50):
        ents.update(_wd_entities(all_ids[i:i + 50]))
        print(f"  entities {min(i + 50, len(all_ids))}/{len(all_ids)}")

    entries = []
    unresolved = []
    # manual overrides first -- highest confidence
    for name in cands:
        if name in MANUAL_OVERRIDES:
            entries.append({
                "name": name, "lang": "zh-Hant",
                "readings": [MANUAL_OVERRIDES[name]],
                "modern": MANUAL_OVERRIDES[name],
                "method": "manual", "confidence": 0.95,
                "source_id": "manual_override",
            })
    for name, ids in hits.items():
        if name in MANUAL_UNRESOLVED:
            unresolved.append(name)
            continue
        best = None
        for qid in ids:
            ent = ents.get(qid)
            if not ent:
                continue
            taxon = _taxon_of(ent)
            if not taxon:
                continue
            zh = (ent.get("labels", {}).get("zh", {}) or {}).get("value", "")
            exact = (zh == name) or (zh.replace(" ", "") == name)
            score = (2 if exact else 0) + (1 if " " in taxon else 0)
            if best is None or score > best[0]:
                best = (score, taxon, qid, exact)
        if not best:
            unresolved.append(name)
            continue
        _score, taxon, qid, exact = best
        if exact and " " in taxon:
            method, conf = "wikidata", 0.90
        elif " " in taxon:
            method, conf = "wikidata", 0.70
        else:
            method, conf = "wikidata-genus", 0.55
        entries.append({
            "name": name, "lang": "zh-Hant",
            "readings": [taxon], "modern": taxon, "method": method,
            "confidence": conf, "source_id": "wikidata", "wikidata": qid,
        })

    # ---- alias heuristics: processing prefixes/suffixes and compound names ----
    # "炙甘草"/"炒白芍"/"生薑" are the same drug as their base name; 川烏頭 contains 烏頭.
    resolved = {e["name"]: e for e in entries}
    def _base_variants(name: str) -> list[str]:
        out = []
        for pre in ("生", "炒", "炙", "酒", "醋", "鹽", "盐", "蜜", "煅", "煆", "薑",
                    "姜", "製", "制", "焦", "熟", "乾", "干", "鮮", "鲜", "炮", "煨"):
            if name.startswith(pre) and len(name) > len(pre) + 1:
                out.append(name[len(pre):])
        for suf in ("炭", "炒", "片", "末", "粉", "霜", "汁", "汁子"):
            if name.endswith(suf) and len(name) > len(suf) + 1:
                out.append(name[: -len(suf)])
        return out

    added = 0
    for name in cands:
        if name in resolved or name in MANUAL_OVERRIDES or name in MANUAL_UNRESOLVED:
            continue
        src = None
        for v in _base_variants(name):
            if v in resolved:
                src = resolved[v]
                break
        # NOTE: no substring/containment matching. It produced false joins (body-part surfaces
        # matched to unrelated taxa), and a wrong binomial is worse than a null one.
        if src is None:
            continue
        entries.append({
            "name": name, "lang": "zh-Hant", "readings": [src["modern"]],
            "modern": src["modern"], "method": "alias",
            "confidence": round(max(0.55, src["confidence"] - 0.25), 2),
            "source_id": src.get("source_id", "wikidata"),
            "alias_of": src["name"],
        })
        resolved[name] = entries[-1]
        added += 1
    print(f"  alias additions: {added}")

    entries.sort(key=lambda e: (-e["confidence"], e["name"]))
    doc = {
        "generated_by": "data/build_lexicon.py",
        "note": ("Classical Chinese drug name -> modern binomial. method=manual is a "
                 "pharmacopoeial/standard identification; method=wikidata is resolved via "
                 "Wikidata P225 (taxon name), citable by Q-id. confidence is a heuristic, "
                 "not a calibrated probability."),
        "count": len(entries),
        "unresolved_count": len(unresolved),
        "unresolved": sorted(unresolved)[:200],
        "historical": entries,
    }
    OUT_JSON.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {OUT_JSON} ({len(entries)} entries, {len(unresolved)} unresolved)")
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
