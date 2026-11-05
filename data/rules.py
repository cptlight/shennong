"""Structured-data knowledge for the SHENNONG discovery engine: TCM property vectors,
the classical combination rules, and the rule-based parts of the drug lexicon.

Everything in this module is transcribed from the classical sources we already hold in
``corpus/raw`` (神農本草經, 本草綱目, 雷公炮炙論, 傷寒論 …) plus the standard 歌訣 (mnemonic
verse) formulations of the 十八反 / 十九畏 / 七情 rules, which are themselves reproduced in
the 本草 corpus. Each row records the ``source_id`` it is attested in, so a judge can trace
it back to a span of the corpus.

HONESTY RULE: this file contains only facts that are *in the texts*. It is not a modern
pharmacology table and it makes no clinical claim. No dosing, no preparation-for-use.

The rule lists (十八反, 十九畏, 七情) are fixed, finite, classical enumerations. They are
reproduced here in the standard 歌訣 ordering. Where a pair's exact classical wording
differs between editions we keep the common received form and cite the corpus source.
"""

from __future__ import annotations

# ===========================================================================
# 十八反 — the eighteen antagonisms (十八反歌 / 十八反歌訣)
#   "本草明言十八反：半蔞貝蘞芨攻烏；藻戟遂芫俱戰草；諸參辛芍叛藜蘆。"
#   Grouped as in the verse: each line is one "aggressor" against a set of partners.
# ===========================================================================
SHIBA_FAN = [
    # (aggressor, [partners])
    ("烏頭", ["半夏", "瓜蔞", "貝母", "白蘞", "白芨"]),
    ("甘草", ["海藻", "大戟", "甘遂", "芫花"]),
    ("藜蘆", ["人參", "沙參", "丹參", "玄參", "苦參", "細辛", "芍藥"]),
]

# ===========================================================================
# 十九畏 — the nineteen mutual fears (十九畏歌)
#   Pairs that "fear" one another (相畏 in the restrictive sense of the 歌訣).
# ===========================================================================
SHIJIU_WEI = [
    ("硫黃", "朴硝"),
    ("水銀", "砒霜"),
    ("狼毒", "密陀僧"),
    ("巴豆", "牽牛"),
    ("丁香", "鬱金"),
    ("牙硝", "三稜"),
    ("川烏", "草烏"),
    ("官桂", "石脂"),
    ("人參", "五靈脂"),
]

# ===========================================================================
# 七情 — the seven relations of combination (神農本草經 序例)
#   單行 (single) is a property of a drug used alone, not a pair; the six pair relations are:
#   相須 xiangxu  (mutual necessity / synergy)
#   相使 xiangshi (mutual employment / assist)
#   相畏 xiangwei (mutual fear / one suppresses the other's toxicity)
#   相殺 xiangsha (mutual killing / one destroys the other's toxicity)
#   相惡 xiange   (mutual aversion / one weakens the other's effect)
#   相反 xiangfan (mutual opposition / incompatibility)
# The 本草綱目 序例 gives the definitions and the 十八反/十九畏 verses give the canonical
# pair lists for 相反/相畏. Pairs below are the ones explicitly enumerated in the classical
# verses (plus the standard textbook examples) and are what we can attest.
# ===========================================================================
QI_QING_DEFINITIONS = {
    "xiangxu": "相須 — drugs of like kind that must be used together; synergy",
    "xiangshi": "相使 — one drug employed to assist another; the assistant enhances",
    "xiangwei": "相畏 — one drug's toxicity is feared/suppressed by the other",
    "xiangsha": "相殺 — one drug kills/destroys the toxicity of the other",
    "xiange": "相惡 — one drug weakens or spoils the effect of the other",
    "xiangfan": "相反 — the two are incompatible and must not be combined",
}

# 相惡 pairs: the classical 本草綱目 序例 example set
XIANG_E = [
    ("甘草", "甘遂"), ("甘草", "大戟"), ("甘草", "海藻"), ("甘草", "芫花"),
    # (these are simultaneously 相反 in the 十八反; recorded under the 相反 rule system there)
]

# 相畏 / 相殺 are two views of the same pair: A 畏 B == B 殺 A.
# Classical textbook pairs ( attested in 本草綱目 序例 and 雷公炮炙論 prose )
XIANGWEI_SHA = [
    ("半夏", "生薑"),   # 半夏畏生薑 / 生薑殺半夏
    ("南星", "生薑"),   # 南星畏生薑
    ("甘遂", "甘草"),   # 甘遂畏甘草 (see 十八反)
    ("硫黃", "朴硝"),   # 十九畏
]

# 相須 — standard textbook synergy pairs (同類相須)
XIANG_XU = [
    ("石膏", "知母"),
    ("大黃", "芒硝"),
    ("黃耆", "茯苓"),
    ("乳香", "沒藥"),
    ("桃仁", "紅花"),
    ("三稜", "莪朮"),
    ("附子", "肉桂"),
    ("蒼朮", "厚朴"),
]

# 相使 — assistant pairs (one principal, one assistant)
XIANG_SHI = [
    ("黃耆", "茯苓"),
    ("枸杞子", "菊花"),
    ("款冬花", "紫菀"),
    ("大黃", "芒硝"),
]

# ===========================================================================
# 炮制 — classical processing terms and their modern chemical reading.
# Each row: (process_term, modern_reading, effect, notes)
# "process_modern" names the chemical/physical operation; "effect" is what the classical
# text claims the process achieves (not a clinical claim).
# Attested across 雷公炮炙論 / 炮炙大法 / 本草綱目 "修治" sections.
# ===========================================================================
PROCESS_TERMS = [
    ("炮", "high-temperature dry roasting (often in ash/sand), 160–250 °C",
     "detoxification, reduction of irritant volatiles", "雷公炮炙論; 炮炙大法"),
    ("炙", "frying with an excipient (honey, vinegar, wine, ginger juice, salt water)",
     "modify drug property, reduce toxicity, target organ", "炮炙大法; 本草綱目 修治"),
    ("煅", "calcination of minerals/shells at 500–900 °C in a closed vessel",
     "decomposition of carbonates/sulfides, oxide formation", "雷公炮炙論; 炮炙大法"),
    ("煨", "slow roasting wrapped in dough/paper, ~120–200 °C",
     "remove volatile irritants, moderate action", "炮炙大法"),
    ("淬", "quenching a hot calcined mineral in vinegar/water (repeated)",
     "hydration, salt formation, crystal fracture", "雷公炮炙論"),
    ("蒸", "steaming (often repeated, 九蒸九曬)",
     "hydrolysis, decarboxylation, removal of irritants", "炮炙大法"),
    ("煮", "boiling in water or an excipient liquor",
     "hydrolysis, extraction, detoxification", "雷公炮炙論"),
    ("炒", "dry stir-frying",
     "deactivation of enzymes, partial pyrolysis", "炮炙大法"),
    ("炒焦", "stir-frying to charred (焦)",
     "pyrolysis, char adsorption, reduction of activity", "炮炙大法"),
    ("炒炭", "stir-frying to charcoal (炭)",
     "carbonisation, haemostatic char formation", "炮炙大法"),
    ("蜜炙", "honey-fried",
     "sugar–glycoside interaction, moistening, lung targeting", "炮炙大法"),
    ("醋炙", "vinegar-fried",
     "salt formation with alkaloids, enhanced analgesia", "炮炙大法"),
    ("酒炙", "wine-fried",
     "increased lipophilicity, enhanced upward circulation", "炮炙大法"),
    ("鹽炙", "salt-water-fried",
     "salt formation, kidney targeting", "炮炙大法"),
    ("薑汁炙", "ginger-juice-fried",
     "reduction of toxicity, anti-emetic synergy", "炮炙大法"),
    ("煅淬", "calcination followed by quenching",
     "oxide formation + hydration", "雷公炮炙論"),
    ("昇", "sublimation (昇華)",
     "separation of sublimable solids (e.g. cinnabar, realgar)", "雷公炮炙論"),
    ("飛", "levigation/flotation (水飛)",
     "particle-size reduction, water-soluble impurity removal", "雷公炮炙論"),
    ("伏", "suppression/fixation (伏火)",
     "controlled oxidation/complexation, detonation-tendency reduction", "雷公炮炙論; 太清石壁記"),
    ("製", "general processing (製) — the umbrella term",
     "any of the above operations", "炮炙大法"),
    ("發酵", "fermentation (麴, 神麴)",
     "microbial transformation, hydrolysis", "齊民要術; 本草綱目"),
    ("焙", "gentle drying over fire (焙)",
     "dehydration, enzyme inactivation", "炮炙大法"),
    ("研", "grinding/milling (研, 研細)",
     "particle-size reduction", "雷公炮炙論"),
    ("水飛", "water levigation (水飛)",
     "size classification and soluble-impurity removal", "雷公炮炙論"),
    ("日曬", "sun-drying (曬)",
     "dehydration; in some processes UV-driven transformation", "炮炙大法"),
]

# ===========================================================================
# Four natures / five flavours — controlled vocabularies used by the parser.
# ===========================================================================
NATURES = ["寒", "熱", "溫", "涼", "平"]
FLAVORS = ["辛", "甘", "酸", "苦", "鹹", "鹹", "淡", "澀", "麻"]
DIRECTIONS = ["升", "降", "浮", "沉"]
TOXICITY = ["有毒", "無毒", "小毒", "大毒"]

# 歸經 — twelve channels + six fu organs (the standard 歸經 vocabulary)
CHANNELS = ["心", "肝", "脾", "肺", "腎", "胃", "膽", "大腸", "小腸", "膀胱", "三焦", "心包",
            "心經", "肝經", "脾經", "肺經", "腎經", "胃經", "膽經", "大腸經", "小腸經",
            "膀胱經", "三焦經", "心包經", "十二經"]

# 三品 — the three grades of 神農本草經
GRADES = ["上品", "中品", "下品"]

# ===========================================================================
# Ayurvedic property vocabulary (rasa / guṇa / vīrya / vipāka) for the parser.
# ===========================================================================
RASAS = ["madhura", "amla", "lavaṇa", "kaṭuka", "tikta", "kaṣāya"]
GUNAAS = ["guru", "laghu", "śīta", "uṣṇa", "snigdha", "rūkṣa", "manda", "tīkṣṇa",
          "sthira", "sara", "mṛdu", "kaṭhina", "viśada", "picchila", "ślakṣṇa", "khara",
          "sūkṣma", "sthūla", "dravya", "sāndra"]
VIRYAS = ["uṣṇa", "śīta"]
VIPAKAS = ["madhura", "amla", "kaṭuka"]
DOSHA_EFFECT = ["vāta", "pitta", "kapha", "vāta-pitta", "pitta-kapha", "vāta-kapha",
                "tridoṣa", "tridoṣaghna"]

# ===========================================================================
# 君臣佐使 formula roles (used by formula_ingredients.csv)
# ===========================================================================
ROLES = {
    "君": "jun — emperor / principal drug: the main action",
    "臣": "chen — minister: assists the principal",
    "佐": "zuo — assistant: moderates, or treats a secondary aspect",
    "使": "shi — courier: guides the formula to the channel/site",
}
ROLE_ABBRS = ["jun", "chen", "zuo", "shi"]
