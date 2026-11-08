"""Classify historical materia medica by substance type.

Why this exists: the drug-name→taxon resolution rate looked catastrophic (43 %) because every unresolved name
was counted as a failure. But the classical pharmacopoeia is not a plant list. It includes

    縛豬繩 (a rope used to tie pigs)      亂髮 (human hair)         溺白垽 (urine sediment)
    秋石 (urine crystal)                  海蛤 (clam shell)          貝子 (cowrie shell)
    汗衫 (an undershirt)                  死人枕席 (a dead man's mat) 伏龍肝 (furnace earth)

None of these can resolve to a botanical binomial, and they are not errors. Splitting the corpus by substance
type turns one misleading number into two honest ones: how much of the corpus is plant material at all, and how
well we resolve that part.

Classification is keyword-based and deliberately conservative: it is reported as a coarse split, never as a
taxonomy, and any name it cannot classify stays `plant` (the default) so the plant resolution rate is not
flattered by shuffling hard names into other buckets.

    classify("甘草")    -> "plant"
    classify("甘草根")  -> "plant_part"
    classify("汗衫")    -> "object"
"""
from __future__ import annotations

import re

# order matters: the first category whose pattern matches wins
RULES: list[tuple[str, re.Pattern]] = [
    ("object", re.compile(r"(繩|绳|索|器|具|衣|衫|布|紙|纸|瓦|罐|瓶|盒|匣|盤|盘|刀|針|针|線|线|網|网|枕|席|"
                          r"門|门|戶|户|窗|牆|墙|車|车|船|橋|桥|燈|灯|燭|烛|傘|伞|扇|鏡|镜|梳|刷|帶|带|"
                          r"巾|帕|襪|袜|鞋|帽|冠|釵|钗|環|环|釧|钏|鎖|锁|鑰|钥)")),
    ("human_derived", re.compile(r"(亂髮|乱发|頭髮|头发|髮|髮灰|溺|尿|糞|粪|人屎|人中白|人中黃|人中黄|"
                                 r"乳汁|人乳|血餘|血余|紫河車|紫河车|胎盤|胎盘|臍帶|脐带|指甲|爪甲|"
                                 r"月經|月经|經血|经血|汗|淚|泪|涕|唾|精|髓|腦|脑|胞衣|陰毛|阴毛)")),
    ("animal", re.compile(r"(骨|肉|毛|角|甲|殼|壳|爪|翅|膽|胆|血|腸|肠|胃|肝|肺|腎|肾|胎|筋|蛹|蛾|卵|鱗|鳞|"
                          r"羽|尾|足|蹄|皮|脂|膏|膠|胶|酥|酪|乳|腦|脑|心|舌|牙|齒|齿|眼|目|耳|鼻|喉|"
                          r"蟲|虫|蠍|蝎|蛇|龜|龟|鱉|鳖|魚|鱼|鳥|鸟|雞|鸡|鴨|鸭|鵝|鹅|豬|猪|羊|牛|馬|马|驢|驴|"
                          r"虎|鹿|麝|犀|象|猴|鼠|兔|犬|狗|蟹|蝦|虾|蚌|螺|蛤|蠣|蛎|貝|贝|蠶|蚕|蜂|蟬|蝉)")),
    ("mineral", re.compile(r"(石|土|砂|沙|鹽|盐|礬|矾|硝|硫|汞|鉛|铅|銅|铜|鐵|铁|錫|锡|鋅|锌|鈣|钙|鎂|镁|"
                           r"丹|礞|磁|雲母|云母|石膏|滑石|雄黃|雄黄|雌黃|雌黄|硃砂|朱砂|秋石|伏龍肝|"
                           r"黃丹|黄丹|鉛丹|铅丹|密陀僧|爐甘石|炉甘石|鐘乳|钟乳|膽礬|胆矾|無名異|无名异)")),
    ("plant_part", re.compile(r"(莖|茎|葉|叶|花|果|皮|子|仁|苗|枝|心|汁|根|梢|梗|莢|荚|穗|茸|蕊|蒂|柄|"
                              r"核|瓤|膜|絲|丝|絡|络|節|节|芽|實|实|殼|壳|屑|粉|霜|露|液|漿|浆)")),
]


def classify(name: str) -> str:
    """Return one of: object, human_derived, animal, mineral, plant_part, plant."""
    n = (name or "").strip()
    if not n:
        return "unknown"
    for label, pat in RULES:
        if pat.search(n):
            return label
    return "plant"


def is_plant_derived(label: str) -> bool:
    """Only `plant` and `plant_part` names could ever resolve to a botanical binomial."""
    return label in ("plant", "plant_part")


def explain(name: str) -> dict:
    label = classify(name)
    return {"name": name, "class": label,
            "resolvable_to_binomial": is_plant_derived(label),
            "note": {"object": "manufactured object, not a botanical",
                     "human_derived": "human-derived substance, not a botanical",
                     "animal": "animal-derived substance, not a botanical",
                     "mineral": "mineral substance, not a botanical",
                     "plant_part": "plant part — resolves only if the parent plant is known",
                     "plant": "candidate botanical name"}.get(label, "")}
