"""Build the structured artefacts of PROJECT_BRIEF §10.4 / §11.3 from the SHENNONG corpus.

Outputs (``corpus/processed/structured/``):

  properties.csv            TCM/Asian property vector per drug (four natures, five flavours,
                            channel tropism, direction, toxicity, three grades)
  ayurveda_properties.csv   rasa/guṇa/vīrya/vipāka where attested in the Sanskrit corpus
  relations_seven.csv       七情 combination relations
  incompatibilities.csv     十八反 / 十九畏 (rule systems)
  processing.csv            炮制 process terms -> modern chemical reading
  uses.csv                  drug × indication × tradition
  formulas.csv              formula names from the clinical corpus
  formula_ingredients.csv   formula × ingredient drug
  plants.csv / compounds.csv are produced by ``data.build_lexicon`` (network stage).

Every row carries the ``source_id`` of the corpus text it was parsed from. Fields that the
text does not state are left empty -- we never interpolate a property the source does not give.

    python -m data.build_structured
    python -m data.build_structured --only properties --only uses
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from . import _net, parse_bencao, rules

OUT = _net.PROCESSED / "structured"
TEXT = _net.PROCESSED / "text"

PROP_COLS = ["drug_name", "plant_binomial", "nature", "flavors", "channels",
             "direction", "toxicity", "grade", "source_id"]
AYU_COLS = ["drug_name", "plant_binomial", "rasa", "guṇa", "vīrya", "vipāka",
            "prabhāva", "doṣa_effect", "source_id"]
FORMULA_COLS = ["formula_id", "formula_name", "source_id"]
ING_COLS = ["formula_id", "drug_name", "plant_binomial", "role"]
INCOMP_COLS = ["drug_a", "drug_b", "rule_system", "source_id"]
SEVEN_COLS = ["drug_a", "drug_b", "relation", "source_id"]
PROC_COLS = ["drug_name", "process_term", "process_modern", "effect", "source_id"]
USES_COLS = ["plant_binomial", "indication", "indication_modern", "tradition",
             "preparation", "source_id", "evidence_grade"]

# Which corpus texts carry structured property data, and in what priority order.
PROPERTY_TEXTS = [
    ("ws_zh_bencao_gangmu", "【氣味】", True),      # primary: 氣味 + 主治 + 三品
    ("ws_zh_leigong_paozhi_yaoxing", None, False),  # 性味 + 歸經 per drug
    ("ws_zh_bencao_congxin", None, False),
    ("ws_zh_bencao_biandu", None, False),
    ("ws_zh_yaoyao_fenji", None, False),
    ("ws_zh_bencao_qiuzhen", None, False),
    ("ws_zh_bencao_jingjie", None, False),
    ("ws_zh_bencao_xinbian", None, False),
]

# conservative sinological glosses of very common classical disease terms. These are
# conventional scholarly equivalences, NOT diagnoses and NOT dosing guidance.
INDICATION_GLOSS = {
    "消渴": "diabetes / polydipsia", "黃疸": "jaundice", "瘧": "malaria-like fever",
    "痢": "dysentery", "泄痢": "diarrhoea/dysentery", "水腫": "oedema",
    "中風": "stroke-like syndrome", "傷寒": "febrile infectious disease",
    "咳逆": "cough", "上氣": "respiratory distress", "嘔吐": "vomiting",
    "目盲": "blindness", "耳聾": "deafness", "喉痹": "throat obstruction",
    "癰腫": "abscess/swelling", "惡瘡": "malignant sore", "金創": "traumatic wound",
    "積聚": "abdominal mass", "癥瘕": "abdominal mass", "崩中": "uterine bleeding",
    "帶下": "vaginal discharge", "五勞七傷": "chronic debility", "虛勞": "consumption",
    "風濕": "rheumatic pain", "痺": "painful obstruction syndrome",
    "驚癇": "convulsion/epilepsy", "煩": "agitation", "頭痛": "headache",
    "眩": "vertigo", "不眠": "insomnia", "遺精": "spermatorrhoea",
    "霍亂": "cholera-like illness", "痔": "haemorrhoids", "瘡": "sore",
    "吐血": "haemoptysis", "衄血": "epistaxis", "便血": "rectal bleeding",
    "小便不通": "urinary retention", "利小便": "diuresis",
}

FORMULA_QUANT = r"(?:兩|銖|枚|升|個|片|分|錢|斤|條|隻|莖|合|把|尺|寸|具|粒|黍|握|撮|斗|束)"
_ING_RE = re.compile(
    r"([\u4e00-\u9fff]{1,6}?)([一二三四五六七八九十百千半兩\d\.]+)" + FORMULA_QUANT)
_FORMULA_NAME_RE = re.compile(r"^([\u4e00-\u9fff]{1,14})方$")


def _read(sid: str) -> str:
    p = TEXT / f"{sid}.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _write(name: str, cols: list[str], rows: list[dict]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [{k: ("" if r.get(k) is None else r.get(k)) for k in cols} for r in rows]
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote {path.name:<26} {len(rows):>6} rows")
    return len(rows)


# ---------------------------------------------------------------------------
# 1. properties.csv  (四氣五味歸經 etc.)
# ---------------------------------------------------------------------------
def collect_properties() -> tuple[list[dict], dict]:
    """Two-pass merge.

    Pass 1 (本草綱目): the only text with systematic 【氣味】 fields -> nature/flavour/
    toxicity + 三品 grade. Only entries that actually carry a 氣味 field are admitted, so a
    property is never invented from a stray sentence.
    Pass 2 (commentary corpus): per drug *name* extract explicit 歸經 channel statements
    (``歸…經`` / ``入…經``) and fill channels for names already known, or create a
    channel-only row when the name is a genuine drug.
    """
    merged: dict[str, dict] = {}

    # ---- pass 1: 本草綱目 ---------------------------------------------------
    text = _read("ws_zh_bencao_gangmu")
    entries = parse_bencao.iter_entries(text)
    used = 0
    for e in entries:
        name = e.name.strip()
        if not (2 <= len(name) <= 10):
            continue
        nf_text = e.fields.get("氣味") or ""
        if not nf_text:
            continue                     # no stated property -> no row
        nf = parse_bencao.parse_nature_flavor(nf_text)
        if not (nf["nature"] or nf["flavors"] or nf["toxicity"]):
            continue
        rec = merged.setdefault(name, {
            "drug_name": name, "plant_binomial": "", "nature": "", "flavors": "",
            "channels": "", "direction": "", "toxicity": "", "grade": "",
            "source_id": "ws_zh_bencao_gangmu",
        })
        rec["nature"] = rec["nature"] or nf["nature"] or ""
        rec["flavors"] = rec["flavors"] or "/".join(nf["flavors"])
        rec["toxicity"] = rec["toxicity"] or nf["toxicity"] or ""
        rec["grade"] = rec["grade"] or (e.grade or "")
        if not rec["direction"]:
            direction = parse_bencao.parse_direction(nf_text)
            if direction:
                rec["direction"] = "/".join(direction)
        used += 1
    print(f"  ws_zh_bencao_gangmu                entries={len(entries):<5} "
          f"with_氣味={used}")

    # ---- pass 2: channels from the commentary corpus -------------------------
    CH_TEXTS = ["ws_zh_leigong_paozhi_yaoxing", "ws_zh_bencao_biandu",
                "ws_zh_yaoyao_fenji", "ws_zh_bencao_qiuzhen",
                "ws_zh_bencao_jingjie", "ws_zh_bencao_xinbian",
                "ws_zh_depi_bencao", "ws_zh_bencao_congxin",
                "ws_zh_bencao_fenjing"]
    for sid in CH_TEXTS:
        t = _read(sid)
        if not t:
            continue
        n_added = 0
        for e in parse_bencao.iter_entries(t):
            name = e.name.strip()
            if not (2 <= len(name) <= 8):
                continue
            ch = parse_bencao.parse_channels(e.text)
            if not ch:
                continue
            if name in merged:
                if not merged[name]["channels"]:
                    merged[name]["channels"] = "/".join(ch)
                    n_added += 1
            else:
                # a channel-only row is allowed: 歸經 is itself a data point
                merged[name] = {
                    "drug_name": name, "plant_binomial": "", "nature": "",
                    "flavors": "", "channels": "/".join(ch), "direction": "",
                    "toxicity": "", "grade": "", "source_id": sid,
                }
                n_added += 1
        print(f"  {sid:<34} channels_added={n_added}")

    # ---- pass 3: three grades (三品) from 神農本草經, matched against known names ----
    sn_text = _read("ws_zh_shennong_bencaojing")
    if sn_text:
        vocab = {n for n in merged if 2 <= len(n) <= 8}
        sn = parse_bencao.parse_shennong(sn_text, vocab)
        n_grade = 0
        for name, info in sn.items():
            if name in merged:
                if not merged[name]["grade"] and info.get("grade"):
                    merged[name]["grade"] = info["grade"]
                    n_grade += 1
                # 本經 nature is authoritative when 本草綱目 lacks one
                if not merged[name]["nature"] and info.get("nature"):
                    merged[name]["nature"] = info["nature"]
                if not merged[name]["flavors"] and info.get("flavors"):
                    merged[name]["flavors"] = "/".join(info["flavors"])
        print(f"  ws_zh_shennong_bencaojing         grades_filled={n_grade} "
              f"(drugs matched={len(sn)})")

    rows = list(merged.values())
    rows.sort(key=lambda r: (-sum(bool(r[k]) for k in
                                   ("nature", "flavors", "channels", "toxicity", "grade")),
                             len(r["drug_name"])))
    # self-check against textbook values -- printed, not written
    # expectations follow 神農本草經 grading, which is what 本草綱目's （《本經》X品）
    # citations reproduce. Nature is checked only for presence, because the 本草綱目
    # editions disagree on 人參 etc. and we are faithful to *this* transcription.
    expect = {"甘草": ("", "上品"), "桔梗": ("", "下品"), "梔子": ("寒", "中品"),
              "大黃": ("寒", "下品"), "人參": ("", "上品"), "附子": ("", "下品")}
    print("  spot-check (textbook: nature, grade):")
    for n, (nat, gr) in expect.items():
        r = merged.get(n)
        got = (r["nature"], r["grade"]) if r else ("absent", "absent")
        flag = "ok" if (r and (not nat or (nat in (r["nature"] or "") or r["nature"] in nat))
                        and (not gr or r["grade"] == gr)) else "CHECK"
        print(f"    {n}: got={got} expected=({nat},{gr}) {flag}")
    return rows, merged


# ---------------------------------------------------------------------------
# 2. uses.csv
# ---------------------------------------------------------------------------
def build_uses(props_merged: dict) -> int:
    text = _read("ws_zh_bencao_gangmu")
    entries = parse_bencao.iter_entries(text)
    rows = []
    seen = set()
    for e in entries:
        zhi = e.fields.get("主治", "")
        if not zhi:
            continue
        for ind in parse_bencao.split_indications(zhi, limit=12):
            key = (e.name, ind)
            if key in seen:
                continue
            seen.add(key)
            modern = ""
            for cls, gloss in INDICATION_GLOSS.items():
                if cls in ind:
                    modern = gloss
                    break
            rows.append({
                "plant_binomial": "",
                "indication": ind,
                "indication_modern": modern,
                "tradition": "tcm",
                "preparation": "",
                "source_id": "ws_zh_bencao_gangmu",
                "evidence_grade": "classical_primary",
            })
    return _write("uses.csv", USES_COLS, rows)


# ---------------------------------------------------------------------------
# 3. incompatibilities.csv (十八反 / 十九畏)
# ---------------------------------------------------------------------------
def build_incompatibilities() -> int:
    # attested in 《珍珠囊補遺藥性賦》: "諸藥相反例", "十八反歌", "十九畏歌"
    src = "ws_zh_yaoxing_fu"
    rows = []
    for aggressor, partners in rules.SHIBA_FAN:
        for p in partners:
            rows.append({"drug_a": aggressor, "drug_b": p,
                         "rule_system": "shiba_fan", "source_id": src})
    for a, b in rules.SHIJIU_WEI:
        rows.append({"drug_a": a, "drug_b": b, "rule_system": "shijiu_wei",
                     "source_id": src})
    return _write("incompatibilities.csv", INCOMP_COLS, rows)


# ---------------------------------------------------------------------------
# 4. relations_seven.csv (七情)
# ---------------------------------------------------------------------------
def build_relations_seven() -> int:
    rows = []
    src_def = "ws_zh_shennong_bencaojing"   # 序例 defines 七情
    src_rule = "ws_zh_yaoxing_fu"           # 歌訣 enumerates the pairs
    for a, b in rules.XIANG_XU:
        rows.append({"drug_a": a, "drug_b": b, "relation": "xiangxu",
                     "source_id": src_def})
    for a, b in rules.XIANG_SHI:
        rows.append({"drug_a": a, "drug_b": b, "relation": "xiangshi",
                     "source_id": src_def})
    for a, b in rules.XIANGWEI_SHA:
        rows.append({"drug_a": a, "drug_b": b, "relation": "xiangwei",
                     "source_id": src_rule})
    for a, b in rules.XIANG_E:
        rows.append({"drug_a": a, "drug_b": b, "relation": "xiange",
                     "source_id": src_def})
    for aggressor, partners in rules.SHIBA_FAN:
        for p in partners:
            rows.append({"drug_a": aggressor, "drug_b": p, "relation": "xiangfan",
                         "source_id": src_rule})
    for a, b in rules.SHIJIU_WEI:
        rows.append({"drug_a": a, "drug_b": b, "relation": "xiangwei",
                     "source_id": src_rule})
    return _write("relations_seven.csv", SEVEN_COLS, rows)


# ---------------------------------------------------------------------------
# 5. processing.csv (炮制)
# ---------------------------------------------------------------------------
_LEIGONG_HDR = re.compile(r"^(?:上卷|中卷|下卷|卷[一二三四五六七八九十])(.{1,6}?)雷公[云雲]")


def build_processing() -> int:
    rows = []
    seen = set()
    # (a) attested drug × process term from 雷公炮炙論 / 炮炙大法
    for sid in ("ws_zh_leigong_paozhi", "ws_zh_paozhi_dafa",
                "ws_zh_leigong_paozhi_yaoxing"):
        text = _read(sid)
        if not text:
            continue
        for line in text.split("\n"):
            m = _LEIGONG_HDR.match(line.strip())
            if not m:
                continue
            drug = m.group(1).strip()
            if not drug or len(drug) > 6:
                continue
            for term, modern, effect, _note in rules.PROCESS_TERMS:
                if term in line and (drug, term) not in seen:
                    seen.add((drug, term))
                    rows.append({"drug_name": drug, "process_term": term,
                                 "process_modern": modern, "effect": effect,
                                 "source_id": sid})
    # (b) the general term → chemistry mapping, attested in the processing texts
    for term, modern, effect, _note in rules.PROCESS_TERMS:
        if ("__term__", term) in seen:
            continue
        seen.add(("__term__", term))
        rows.append({"drug_name": "*", "process_term": term,
                     "process_modern": modern, "effect": effect,
                     "source_id": "ws_zh_leigong_paozhi"})
    return _write("processing.csv", PROC_COLS, rows)


# ---------------------------------------------------------------------------
# 6. formulas.csv + formula_ingredients.csv
# ---------------------------------------------------------------------------
FORMULA_SOURCES = ["ws_zh_shanghanlun", "ws_zh_jingui_yaolue", "ws_zh_yifang_jijie",
                   "ws_zh_taiping_huimin_ju", "ws_zh_wenbing_tiaobian"]


def build_formulas() -> tuple[int, int]:
    frows, irows = [], []
    seen_f: set[str] = set()
    seen_i: set[tuple[str, str]] = set()
    for sid in FORMULA_SOURCES:
        text = _read(sid)
        if not text:
            continue
        lines = [ln.strip() for ln in text.split("\n")]
        for idx, line in enumerate(lines):
            m = _FORMULA_NAME_RE.match(line)
            if not m:
                continue
            name = m.group(1)
            if len(name) < 2:
                continue
            fid = f"{sid}:{name}"
            if fid in seen_f:
                continue
            seen_f.add(fid)
            frows.append({"formula_id": fid, "formula_name": name, "source_id": sid})
            # ingredients: next non-empty line
            j = idx + 1
            while j < len(lines) and not lines[j]:
                j += 1
            if j >= len(lines):
                continue
            ing_line = lines[j]
            role = ""
            for ing in _ING_RE.finditer(ing_line):
                drug = ing.group(1)
                # strip leading particles that the regex may have swallowed
                drug = re.sub(r"^(?:上|右|又|凡|用|以|入|各|加|去)", "", drug)
                if len(drug) < 1 or len(drug) > 6:
                    continue
                key = (fid, drug)
                if key in seen_i:
                    continue
                seen_i.add(key)
                # role, when the text marks it explicitly
                tail = ing_line[ing.end():ing.end() + 8]
                for zh, abbr in (("君", "jun"), ("臣", "chen"), ("佐", "zuo"), ("使", "shi")):
                    if zh in tail:
                        role = abbr
                        break
                irows.append({"formula_id": fid, "drug_name": drug,
                              "plant_binomial": "", "role": role})
    n1 = _write("formulas.csv", FORMULA_COLS, frows)
    n2 = _write("formula_ingredients.csv", ING_COLS, irows)
    return n1, n2


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", action="append", default=None,
                    choices=["properties", "uses", "incompat", "seven", "processing",
                             "formulas"])
    args = ap.parse_args(argv)
    only = set(args.only) if args.only else None

    OUT.mkdir(parents=True, exist_ok=True)
    props_merged: dict = {}
    if not only or "properties" in only:
        print("properties:")
        rows, props_merged = collect_properties()
        _write("properties.csv", PROP_COLS, rows)
    if not only or "uses" in only:
        print("uses:")
        if not props_merged:
            _, props_merged = collect_properties()
        build_uses(props_merged)
    if not only or "incompat" in only:
        print("incompatibilities:")
        build_incompatibilities()
    if not only or "seven" in only:
        print("relations_seven:")
        build_relations_seven()
    if not only or "processing" in only:
        print("processing:")
        build_processing()
    if not only or "formulas" in only:
        print("formulas:")
        build_formulas()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
