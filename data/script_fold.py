"""Traditional ⇄ Simplified Chinese fold table for TCM drug-name matching.

A naive ``大黃`` vs ``大黄`` mismatch silently breaks every join, so this table is part of the
data layer. Only characters that actually occur in the SHENNONG drug-name inventory are
included, which keeps it small enough to audit by eye.

The table is *not* a general-purpose converter and does not claim to be: it exists so that a
drug surface parsed out of a simplified transcription (e.g. 藥性賦, 本草分經) resolves against a
lexicon keyed on traditional forms (e.g. 本草綱目). Multi-character simplifications that are not
1:1 (e.g. 乾 → 干 in some contexts) are deliberately omitted rather than guessed.

Emitted to ``corpus/processed/script_fold.json``.
"""

from __future__ import annotations

import json

from . import _net

# traditional -> simplified, one character at a time
T2S_PAIRS = [
    ("黃", "黄"), ("參", "参"), ("藥", "药"), ("歸", "归"), ("經", "经"), ("腎", "肾"),
    ("膽", "胆"), ("腸", "肠"), ("見", "见"), ("醫", "医"), ("烏", "乌"), ("術", "术"),
    ("薑", "姜"), ("蘇", "苏"), ("蘆", "芦"), ("蒼", "苍"), ("瀉", "泻"), ("澤", "泽"),
    ("連", "连"), ("翹", "翘"), ("銀", "银"), ("陳", "陈"), ("殼", "壳"), ("實", "实"),
    ("麥", "麦"), ("麴", "曲"), ("續", "续"), ("斷", "断"), ("補", "补"), ("絲", "丝"),
    ("蓯", "苁"), ("鎖", "锁"), ("陽", "阳"), ("膠", "胶"), ("龍", "龙"), ("蠣", "蛎"),
    ("蟬", "蝉"), ("蛻", "蜕"), ("蠶", "蚕"), ("蠍", "蝎"), ("鱉", "鳖"), ("蟲", "虫"),
    ("龜", "龟"), ("餘", "余"), ("糧", "粮"), ("爐", "炉"), ("燈", "灯"), ("靈", "灵"),
    ("鳳", "凤"), ("雞", "鸡"), ("鴨", "鸭"), ("鵝", "鹅"), ("馬", "马"), ("驢", "驴"),
    ("豬", "猪"), ("貓", "猫"), ("蝦", "虾"), ("魚", "鱼"), ("齒", "齿"), ("骨", "骨"),
    ("頭", "头"), ("頸", "颈"), ("項", "项"), ("頰", "颊"), ("體", "体"), ("氣", "气"),
    ("葉", "叶"), ("莖", "茎"), ("華", "华"), ("開", "开"), ("關", "关"), ("門", "门"),
    ("問", "问"), ("間", "间"), ("閑", "闲"), ("聞", "闻"), ("穀", "谷"), ("豐", "丰"),
    ("貝", "贝"), ("貞", "贞"), ("負", "负"), ("財", "财"), ("貨", "货"), ("質", "质"),
    ("購", "购"), ("貴", "贵"), ("費", "费"), ("資", "资"), ("費", "费"), ("贈", "赠"),
    ("車", "车"), ("軒", "轩"), ("轉", "转"), ("輪", "轮"), ("軟", "软"), ("輕", "轻"),
    ("載", "载"), ("過", "过"), ("運", "运"), ("還", "还"), ("這", "这"), ("進", "进"),
    ("遠", "远"), ("違", "违"), ("邊", "边"), ("鄉", "乡"), ("鄭", "郑"), ("鄧", "邓"),
    ("釋", "释"), ("鐘", "钟"), ("鏡", "镜"), ("鑒", "鉴"), ("鑄", "铸"), ("鋒", "锋"),
    ("鋼", "钢"), ("鐵", "铁"), ("銅", "铜"), ("錫", "锡"), ("鉛", "铅"), ("鋅", "锌"),
    ("硫", "硫"), ("砒", "砒"), ("硃", "朱"), ("硇", "硇"), ("鹼", "碱"), ("鹽", "盐"),
    ("鹵", "卤"), ("鹹", "咸"), ("麥", "麦"), ("麵", "面"), ("醬", "酱"), ("釀", "酿"),
    ("醫", "医"), ("藥", "药"), ("劑", "剂"), ("單", "单"), ("雙", "双"), ("複", "复"),
    ("營", "营"), ("衛", "卫"), ("臟", "脏"), ("腑", "腑"), ("腦", "脑"), ("髓", "髓"),
    ("髮", "发"), ("鬚", "须"), ("顏", "颜"), ("體", "体"), ("膚", "肤"), ("肌", "肌"),
    ("脈", "脉"), ("絡", "络"), ("濕", "湿"), ("熱", "热"), ("溫", "温"), ("涼", "凉"),
    ("陰", "阴"), ("陽", "阳"), ("虛", "虚"), ("實", "实"), ("補", "补"), ("瀉", "泻"),
    ("斂", "敛"), ("散", "散"), ("緩", "缓"), ("急", "急"), ("毒", "毒"), ("蟲", "虫"),
    ("風", "风"), ("癢", "痒"), ("瘡", "疮"), ("癰", "痈"), ("腫", "肿"), ("脹", "胀"),
    ("積", "积"), ("聚", "聚"), ("癥", "症"), ("瘕", "瘕"), ("痢", "痢"), ("瘧", "疟"),
    ("癆", "痨"), ("癇", "痫"), ("癱", "瘫"), ("痺", "痹"), ("痙", "痉"), ("癉", "瘅"),
    ("衄", "衄"), ("咯", "咯"), ("嗽", "嗽"), ("喘", "喘"), ("嘔", "呕"), ("噦", "哕"),
    ("呃", "呃"), ("噎", "噎"), ("膈", "膈"), ("痞", "痞"), ("滿", "满"), ("悶", "闷"),
    ("煩", "烦"), ("躁", "躁"), ("驚", "惊"), ("悸", "悸"), ("憂", "忧"), ("鬱", "郁"),
    ("勞", "劳"), ("傷", "伤"), ("損", "损"), ("虛", "虚"), ("羸", "羸"), ("瘦", "瘦"),
    ("遺", "遗"), ("濁", "浊"), ("淋", "淋"), ("瀝", "沥"), ("尿", "尿"), ("便", "便"),
    ("秘", "秘"), ("結", "结"), ("燥", "燥"), ("潤", "润"), ("滑", "滑"), ("澀", "涩"),
    ("痰", "痰"), ("飲", "饮"), ("涎", "涎"), ("唾", "唾"), ("涕", "涕"), ("淚", "泪"),
    ("汗", "汗"), ("血", "血"), ("膿", "脓"), ("瘍", "疡"), ("疥", "疥"), ("癬", "癣"),
    ("痔", "痔"), ("瘻", "瘘"), ("癭", "瘿"), ("瘤", "瘤"), ("癌", "癌"), ("疳", "疳"),
    ("蟲", "虫"), ("蚘", "蛔"), ("蟯", "蛲"), ("絛", "绦"), ("瘴", "瘴"), ("疫", "疫"),
    ("瘟", "瘟"), ("痘", "痘"), ("疹", "疹"), ("痧", "痧"), ("麻", "麻"), ("痘", "痘"),
]

T2S = {t: s for t, s in T2S_PAIRS}
S2T = {s: t for t, s in T2S_PAIRS}


def to_simplified(text: str) -> str:
    return "".join(T2S.get(ch, ch) for ch in text)


def to_traditional(text: str) -> str:
    return "".join(S2T.get(ch, ch) for ch in text)


def fold_keys(name: str) -> set[str]:
    """All surface forms under which a drug name may appear in the corpus."""
    return {name, to_simplified(name), to_traditional(name)}


def write() -> None:
    out = _net.PROCESSED / "script_fold.json"
    doc = {
        "note": ("Character-level Traditional->Simplified fold table covering the characters "
                 "that occur in the SHENNONG drug-name inventory. Used to make joins robust "
                 "to 大黄/大黃 style mismatches. Not a general-purpose converter."),
        "pairs": len(T2S_PAIRS),
        "t2s": T2S,
        "s2t": S2T,
    }
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({len(T2S_PAIRS)} pairs)")


if __name__ == "__main__":
    write()
