#!/usr/bin/env python3
"""
SHENNONG Workbench — DEMO FIXTURE generator (v2: Asian materia medica).

WHY THIS FILE EXISTS
--------------------
The Workbench must run *before* the real pipeline artefacts exist, and the repo must stay honest:
nothing here is a measured result. Everything is stamped ``"fixture": true`` and the UI renders a
permanent ``DEMO FIXTURE`` badge on any panel fed by it.

The real artefacts replace these automatically (app/serve.py prefers them, file by file):

    eval/report.json                        -> 使 Shǐ evaluation panel + negative controls
    training/runs/*/metrics.json            -> loss curve (brief §10.6 `loss_curve`)
    corpus/registry/sources.yaml            -> 采 Cǎi provenance panel (brief §10.1)
    app/data/hypotheses.json                -> `cli shi --out app/data/hypotheses.json`
    app/data/kg.json                        -> `cli pei --out-kg app/data/kg.json`
    app/data/passages.json                  -> `cli cai --out-passages app/data/passages.json`

Classical Chinese quoted here is from public-domain editions of 神農本草經 / 傷寒論 / 金匱要略 /
儒門事親 / 抱朴子 and is marked ``span_kind: "verbatim"``; everything else is a paraphrase and is
marked as such. No URLs are invented: fixture sources carry real public-domain repository roots
(zh.wikisource, GRETIL, sanskritdocuments, archive.org).

Run:  python app/data/make_fixtures.py
Deterministic (fixed seed). Safe to delete once `make app-data` has produced the real files.
"""

from __future__ import annotations

import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
GENERATED_AT = "2026-11-05T09:00:00Z"

# Ranking rule, identical to docs/METHODOLOGY.md:
#   composite = novelty^0.30 * plausibility^0.30 * testability^0.25 * evidence^0.15
W = {"novelty": 0.30, "plausibility": 0.30, "testability": 0.25, "evidence": 0.15}

CLASS_LABEL = {
    "peiwu_jinji": "配伍禁忌 · encoded incompatibility",
    "paozhi": "炮制 · processing as chemistry",
    "yiming_tongwu": "异名同物 · name collision & adulteration",
    "junchen_zuoshi": "君臣佐使 · formula roles",
    "weiyanjiu": "未研究本草 · the understudied majority",
    "binwei_daiyong": "濒危代用品 · endangered & substitutes",
    "control": "negative control",
}


def composite(s: dict) -> float:
    return round(math.exp(sum(w * math.log(max(s[k], 0.02)) for k, w in W.items())), 3)


# --------------------------------------------------------------------------------------------
# Sources (fixture). Real PD repository roots; fixture counts, shown only under the DEMO badge.
# --------------------------------------------------------------------------------------------
SOURCES = [
    dict(id="fx_shennong_bencao", title="神農本草經", title_en="Shennong Bencao Jing",
         author="神農 (attrib.)", year=-200, tradition="tcm", lang="zh-Hant", tier=2, licence="Public Domain",
         url="https://zh.wikisource.org/wiki/神農本草經", chars=38_400, status="ok"),
    dict(id="fx_bencao_gangmu", title="本草綱目", title_en="Bencao Gangmu",
         author="李時珍 Li Shizhen", year=1596, tradition="tcm", lang="zh-Hant", tier=2, licence="Public Domain",
         url="https://zh.wikisource.org/wiki/本草綱目", chars=2_740_000, status="ok"),
    dict(id="fx_bencao_jing_jizhu", title="本草經集注", title_en="Collected Commentaries on the Materia Medica",
         author="陶弘景 Tao Hongjing", year=500, tradition="tcm", lang="zh-Hant", tier=2, licence="Public Domain",
         url="https://zh.wikisource.org/wiki/本草經集注", chars=142_000, status="ok"),
    dict(id="fx_xinxiu_bencao", title="新修本草", title_en="Newly Revised Materia Medica",
         author="蘇敬 Su Jing et al.", year=659, tradition="tcm", lang="zh-Hant", tier=2, licence="Public Domain",
         url="https://zh.wikisource.org/wiki/新修本草", chars=310_000, status="ok"),
    dict(id="fx_shanghanlun", title="傷寒論", title_en="Treatise on Cold Damage",
         author="張仲景 Zhang Zhongjing", year=220, tradition="tcm", lang="zh-Hant", tier=2,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/傷寒論", chars=96_000, status="ok"),
    dict(id="fx_jingui_yaolue", title="金匱要略", title_en="Essentials of the Golden Cabinet",
         author="張仲景 Zhang Zhongjing", year=220, tradition="tcm", lang="zh-Hant", tier=2,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/金匱要略", chars=88_000, status="ok"),
    dict(id="fx_qianjin_yaofang", title="備急千金要方", title_en="Essential Prescriptions Worth a Thousand in Gold",
         author="孫思邈 Sun Simiao", year=652, tradition="tcm", lang="zh-Hant", tier=2,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/備急千金要方", chars=720_000, status="ok"),
    dict(id="fx_taiping_huimin", title="太平惠民和劑局方", title_en="Imperial Pharmacy Formulary",
         author="陳師文 Chen Shiwen et al.", year=1151, tradition="tcm", lang="zh-Hant", tier=2,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/太平惠民和劑局方", chars=268_000, status="ok"),
    dict(id="fx_leigong_paozhi", title="雷公炮炙論", title_en="Master Lei's Treatise on Processing",
         author="雷斆 Lei Xiao", year=520, tradition="alchemy", lang="zh-Hant", tier=3,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/雷公炮炙論", chars=22_400, status="ok"),
    dict(id="fx_ru-men-shi-qin", title="儒門事親", title_en="Confucians' Duties to Their Parents",
         author="張從正 Zhang Congzheng", year=1228, tradition="tcm", lang="zh-Hant", tier=2,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/儒門事親", chars=124_000, status="ok"),
    dict(id="fx_baopuzi", title="抱朴子內篇", title_en="Baopuzi, Inner Chapters",
         author="葛洪 Ge Hong", year=320, tradition="alchemy", lang="zh-Hant", tier=3,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/抱朴子", chars=118_000, status="ok"),
    dict(id="fx_cantong_qi", title="周易參同契", title_en="Cantong qi",
         author="魏伯陽 Wei Boyang", year=142, tradition="alchemy", lang="zh-Hant", tier=3,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/周易參同契", chars=9_800, status="ok"),
    dict(id="fx_huangdi_neijing", title="黃帝內經·素問", title_en="Huangdi Neijing — Suwen",
         author="黃帝 (attrib.)", year=-100, tradition="tcm", lang="zh-Hant", tier=4, licence="Public Domain",
         url="https://zh.wikisource.org/wiki/黃帝內經", chars=168_000, status="ok"),
    dict(id="fx_nanjing", title="難經", title_en="Classic of Difficult Issues",
         author="扁鵲 (attrib.)", year=150, tradition="acupuncture", lang="zh-Hant", tier=4,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/難經", chars=26_000, status="ok"),
    dict(id="fx_zhenjiu_jiayi", title="針灸甲乙經", title_en="Systematic Classic of Acupuncture",
         author="皇甫謐 Huangfu Mi", year=282, tradition="acupuncture", lang="zh-Hant", tier=4,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/針灸甲乙經", chars=94_000, status="ok"),
    dict(id="fx_zhenjiu_dacheng", title="針灸大成", title_en="Great Compendium of Acupuncture",
         author="楊繼洲 Yang Jizhou", year=1601, tradition="acupuncture", lang="zh-Hant", tier=4,
         licence="Public Domain", url="https://zh.wikisource.org/wiki/針灸大成", chars=320_000, status="ok"),
    dict(id="fx_dongui_bogam", title="東醫寶鑑", title_en="Dongui Bogam",
         author="許浚 Heo Jun", year=1613, tradition="korean", lang="zh-Hant", tier=2, licence="Public Domain",
         url="https://archive.org/details/donguibogam", chars=940_000, status="ok"),
    dict(id="fx_charaka", title="Caraka Saṃhitā", title_en="Caraka Saṃhitā (Sanskrit)",
         author="Agniveśa / Caraka", year=100, tradition="ayurveda", lang="sa", tier=2, licence="Public Domain",
         url="https://sanskritdocuments.org/", chars=1_180_000, status="ok"),
    dict(id="fx_susruta", title="Suśruta Saṃhitā", title_en="Suśruta Saṃhitā (Sanskrit)",
         author="Suśruta", year=-300, tradition="ayurveda", lang="sa", tier=2, licence="Public Domain",
         url="https://sanskritdocuments.org/", chars=880_000, status="ok"),
    dict(id="fx_bhavaprakasa", title="Bhāvaprakāśa", title_en="Bhāvaprakāśa Nighaṇṭu",
         author="Bhāvamiśra", year=1600, tradition="ayurveda", lang="sa", tier=2, licence="Public Domain",
         url="https://sanskritdocuments.org/", chars=410_000, status="ok"),
    dict(id="fx_rasa_ratna", title="Rasa Ratna Samuccaya", title_en="Rasa Ratna Samuccaya (rasaśāstra)",
         author="Vāgbhaṭa (attr.)", year=1200, tradition="alchemy", lang="sa", tier=3,
         licence="Public Domain", url="https://sanskritdocuments.org/", chars=98_000, status="ok"),
    dict(id="fx_astangahridaya", title="Aṣṭāṅgahṛdaya", title_en="Aṣṭāṅgahṛdaya",
         author="Vāgbhaṭa", year=600, tradition="ayurveda", lang="sa", tier=2, licence="Public Domain",
         url="https://sanskritdocuments.org/", chars=360_000, status="ok"),
    dict(id="fx_kanun", title="القانون في الطب", title_en="The Canon of Medicine",
         author="Ibn Sīnā", year=1025, tradition="unani", lang="ar", tier=2, licence="Public Domain",
         url="https://archive.org/details/canonofmedicineof01avic", chars=1_420_000, status="ok"),
    dict(id="fx_hawi", title="الحاوي في الطب", title_en="The Comprehensive Book on Medicine",
         author="al-Rāzī", year=920, tradition="unani", lang="ar", tier=2, licence="Public Domain",
         url="https://archive.org/details/alhawifialtibb", chars=2_100_000, status="ok"),
    dict(id="fx_gretil", title="GRETIL Sanskrit corpus (selected medical texts)",
         title_en="Göttingen Register of Electronic Texts in Indian Languages", author="GRETIL",
         year=2000, tradition="ayurveda", lang="sa-Latn", tier=2, licence="CC-BY-SA-4.0",
         url="http://gretil.sub.uni-goettingen.de/", chars=210_000, status="ok"),
    dict(id="fx_duke", title="Dr Duke's Phytochemical & Ethnobotanical Databases",
         title_en="Dr Duke's Phytochemical and Ethnobotanical Databases", author="James A. Duke (USDA ARS)",
         year=2003, tradition="foundational", lang="en", tier=5, licence="Public Domain",
         url="https://phytochem.nal.usda.gov/", chars=8_910_000, status="ok"),
    dict(id="fx_chembl", title="ChEMBL bioactivity (subset)", title_en="ChEMBL", author="EMBL-EBI",
         year=2025, tradition="foundational", lang="en", tier=5, licence="CC-BY-SA-4.0",
         url="https://www.ebi.ac.uk/chembl/", chars=2_207_000, status="ok"),
    dict(id="fx_powo", title="Plants of the World Online / WCVP", title_en="Kew POWO",
         author="Royal Botanic Gardens Kew", year=2024, tradition="foundational", lang="en", tier=5,
         licence="CC-BY-4.0", url="https://powo.science.kew.org/", chars=744_500, status="ok"),
    dict(id="fx_gbif", title="GBIF taxonomy backbone", title_en="GBIF", author="GBIF Secretariat",
         year=2024, tradition="foundational", lang="en", tier=5, licence="CC-BY-4.0",
         url="https://www.gbif.org/", chars=402_000, status="ok"),
    dict(id="fx_culpeper_control", title="The Complete Herbal", title_en="Culpeper's Complete Herbal",
         author="Nicholas Culpeper", year=1653, tradition="comparative-control", lang="en", tier=2,
         licence="Public Domain", url="https://www.gutenberg.org/ebooks/49537", chars=1_187_600, status="ok"),
    dict(id="fx_unclear_scan", title="Unidentified Tibetan medical tantra scan", title_en="(unidentified)",
         author="unknown", year=1750, tradition="tibetan", lang="bo", tier=2, licence="UNVERIFIED",
         url="", chars=0, status="excluded"),
]
SRC = {s["id"]: s for s in SOURCES}


def _src(sid):
    """Tolerate fx-duke / fx_duke spellings; return the canonical source id."""
    if sid in SRC:
        return sid
    alt = sid.replace("-", "_")
    if alt in SRC:
        return alt
    raise KeyError(f"unknown fixture source: {sid}")


def ps(pid, sid, text, kind="paraphrase", locator="", **kw):
    sid = _src(sid)
    s = SRC[sid]
    d = dict(id=pid, source_id=sid, title=s["title"], title_en=s["title_en"], author=s["author"],
             year=s["year"], tradition=s["tradition"], lang=s["lang"], tier=s["tier"],
             licence=s["licence"], text=text, span_kind=kind, locator=locator, fixture=True)
    d.update(kw)
    return d


# --------------------------------------------------------------------------------------------
# Passages — the Ask panel's retrieval index
# --------------------------------------------------------------------------------------------
PASSAGES = [
    ps("fx-snj-001", "fx_shennong_bencao",
       "甘草，味甘平。主五臟六腑寒熱邪氣，堅筋骨，長肌肉，倍力，金瘡腫，解毒。", "verbatim", "上品·甘草"),
    ps("fx-snj-002", "fx_shennong_bencao",
       "人參，味甘微寒。主補五臟，安精神，定魂魄，止驚悸，除邪氣，明目，開心益智。", "verbatim", "上品·人參"),
    ps("fx-snj-003", "fx_shennong_bencao",
       "麻黃，味苦溫。主中風傷寒頭痛，溫瘧，發表出汗，去邪熱氣，止咳逆上氣，除寒熱，破癥堅積聚。",
       "verbatim", "中品·麻黃"),
    ps("fx-snj-004", "fx_shennong_bencao",
       "大黃，味苦寒。主下瘀血，血閉寒熱，破癥瘕積聚，留飲宿食，蕩滌腸胃，推陳致新，通利水穀，調中化食，安和五臟。",
       "verbatim", "下品·大黃"),
    ps("fx-snj-005", "fx_shennong_bencao",
       "附子，味辛溫。主風寒咳逆邪氣，溫中，金瘡，破癥堅積聚，血瘕，寒濕踒躄，拘攣膝痛，不能行步。",
       "verbatim", "下品·附子"),
    ps("fx-snj-006", "fx_shennong_bencao",
       "乾漆，味辛溫，有毒。主絕傷補中，續筋骨，填髓腦，安五臟。生漆去長蟲。", "verbatim", "上品·乾漆"),
    ps("fx-bcgm-001", "fx_bencao_gangmu",
       "木通：古方所用木通，即今之通草；後世以有細孔者可通氣，故謂之木通。今有一種關木通，色黃味苦，與木通形似而性不同，不可不辨。",
       "paraphrase", "草部·木通"),
    ps("fx-bcgm-002", "fx_bencao_gangmu",
       "防己：漢防己主水氣，木防己療風。又有馬兜鈴根，形似防己而味惡，誤用殺人，鬻者多以之充。",
       "paraphrase", "草部·防己"),
    ps("fx-bcgm-003", "fx_bencao_gangmu",
       "三七：味甘微苦，性溫，無毒。止血散血定痛，金刃箭傷跌撲杖瘡血出不止者，嚼爛罨之即止。產廣西者最良。",
       "paraphrase", "草部·三七"),
    ps("fx-bcgm-004", "fx_bencao_gangmu",
       "菊三七：葉似菊，根如三七而大，南人亦呼為三七，以之治血。其力大而性猛，久服令人腹痛。按此非真三七也。",
       "paraphrase", "草部·菊三七"),
    ps("fx-bcgm-005", "fx_bencao_gangmu",
       "胡椒：味辛大溫，無毒。主下氣溫中，去痰，除臟腑中風冷。近世食品多賴此以行藥力。",
       "paraphrase", "果部·胡椒"),
    ps("fx-bcgm-006", "fx_bencao_gangmu",
       "犀角：苦酸鹹寒，無毒。主百毒蠱疰，邪鬼瘴氣。今禁採，官方以水牛角代之。", "paraphrase", "獸部·犀角"),
    ps("fx-bcgm-007", "fx_bencao_gangmu",
       "何首烏：味苦澀微溫。生者有毒，制者無毒。九蒸九曬，黑豆同蒸，則補益之功成而毒去。生用則令人發熱、腹瀉。",
       "paraphrase", "草部·何首烏"),
    ps("fx-bcgm-008", "fx_bencao_gangmu",
       "核桃：味甘，性熱，無毒。食之令人肥健，潤肌黑髮。其形似腦，故近人謂之補腦，然古方未有此說。",
       "paraphrase", "果部·胡桃"),
    ps("fx-bcgm-009", "fx_bencao_gangmu",
       "半枝蓮：味辛苦，性寒。清熱解毒，化瘀利尿。近人用以治癰腫瘡毒、蛇傷。", "paraphrase", "草部·半枝蓮"),
    ps("fx-bcgm-010", "fx_bencao_gangmu",
       "貓爪草：近世方書始載，主瘰癧結核，消腫散結，南人用以治瘡瘍。", "paraphrase", "草部·貓爪草"),
    ps("fx-bcgm-011", "fx_bencao_gangmu",
       "穿山甲：味鹹微寒，有毒。主五邪驚啼悲傷，燒之作灰，以酒或水和方寸匕。近世以之通乳、消癰。",
       "paraphrase", "鱗部·穿山甲"),
    ps("fx-shl-001", "fx_shanghanlun",
       "太陽病，頭痛發熱，身疼腰痛，骨節疼痛，惡風，無汗而喘者，麻黃湯主之。", "verbatim", "太陽病中篇"),
    ps("fx-shl-002", "fx_shanghanlun",
       "麻黃湯方：麻黃三兩去節，桂枝二兩去皮，甘草一兩炙，杏仁七十箇去皮尖。上四味，以水九升，先煮麻黃，減二升，去上沫，內諸藥，煮取二升半，去滓，溫服八合。",
       "verbatim", "太陽病中篇"),
    ps("fx-shl-003", "fx_shanghanlun",
       "四逆湯方：甘草二兩炙，乾薑一兩半，附子一枚生用去皮破八片。", "verbatim", "少陰病篇"),
    ps("fx-jg-001", "fx_jingui_yaolue",
       "夫病痼疾加以卒病，當先治其卒病，後乃治其痼疾也。", "verbatim", "臟腑經絡先後病脈證第一"),
    ps("fx-jg-002", "fx_jingui_yaolue",
       "問曰：上工治未病，何也？師曰：夫治未病者，見肝之病，知肝傳脾，當先實脾。", "verbatim",
       "臟腑經絡先後病脈證第一"),
    ps("fx-lg-001", "fx_leigong_paozhi",
       "凡使附子，先於文武火上炮令裂，去皮臍，乘熱切之；又以蜜水煮，令毒去而力存。炮之得法，則毒輕而效速。",
       "paraphrase", "草部·附子"),
    ps("fx-lg-002", "fx_leigong_paozhi",
       "凡使大黃，須銼碎，以酒浸一宿，蒸之，曬乾用。酒製則上行，生用則下行，此製法之別也。",
       "paraphrase", "草部·大黃"),
    ps("fx-lg-003", "fx_leigong_paozhi",
       "凡使甘草，須去頭尾尖處，以蜜炙之。炙則補中，生則瀉火。炮製失宜，則藥性反背。",
       "paraphrase", "草部·甘草"),
    ps("fx-lg-004", "fx_leigong_paozhi",
       "凡使杏仁，以湯浸去皮尖，雙仁者不用，熬令黃。煮之則毒去，生用則殺人。", "paraphrase", "草部·杏仁"),
    ps("fx-lg-005", "fx_leigong_paozhi",
       "凡使半夏，以湯洗去滑，生薑汁製之，或礬水煮之，令其毒散。不製則戟人咽喉。", "paraphrase", "草部·半夏"),
    ps("fx-rm-001", "fx_ru-men-shi-qin",
       "本草明言十八反：半蔞貝蘞及攻烏，藻戟遂芫俱戰草，諸參辛芍叛藜蘆。", "verbatim", "十八反"),
    ps("fx-rm-002", "fx_ru-men-shi-qin",
       "十九畏：硫黃原是火中精，朴硝一見便相爭；水銀莫與砒霜見，狼毒最怕密陀僧。", "verbatim", "十九畏"),
    ps("fx-thm-001", "fx_taiping_huimin",
       "參蘇飲：治感冒發熱，頭痛咳嗽。人參為君，紫蘇為臣，前胡、半夏、茯苓為佐，陳皮、枳殼、桔梗為使。",
       "paraphrase", "卷二·參蘇飲"),
    ps("fx-thm-002", "fx_taiping_huimin",
       "君臣佐使者，制方之要也。君為主，臣為輔，佐為制，使為引。主病之謂君，佐君之謂臣，應臣之謂使。",
       "paraphrase", "卷首·論方"),
    ps("fx-qj-001", "fx_qianjin_yaofang",
       "夫為醫者，當須先洞曉病源，知其所犯，以食治之；食療不愈，然後命藥。", "verbatim", "食治"),
    ps("fx-hdnj-001", "fx_huangdi_neijing",
       "正氣存內，邪不可干；邪之所湊，其氣必虛。", "verbatim", "素問·遺篇刺法論"),
    ps("fx-hdnj-002", "fx_huangdi_neijing",
       "東方生風，風生木，木生酸，酸生肝，肝生筋。其在天為風，在地為木，在人為肝，在色為蒼，在味為酸。",
       "verbatim", "素問·陰陽應象大論"),
    ps("fx-hdnj-003", "fx_huangdi_neijing",
       "諸風掉眩，皆屬於肝；諸寒收引，皆屬於腎；諸氣膹鬱，皆屬於肺；諸濕腫滿，皆屬於脾。",
       "verbatim", "素問·至真要大論"),
    ps("fx-zj-001", "fx_zhenjiu_jiayi",
       "足三里，在膝下三寸，胻骨外廉。主胃中寒，腹脹，腸鳴，食不化。", "paraphrase", "卷三·足陽明"),
    ps("fx-nj-001", "fx_nanjing",
       "脈有三部，寸關尺也。上部法天，主胸以上至頭之有疾；中部法人，主膈以下至臍之有疾；下部法地，主臍以下至足之有疾。",
       "paraphrase", "十八難"),
    ps("fx-bpz-001", "fx_baopuzi",
       "夫金丹之為物，燒之愈久，變化愈妙；黃金入火，百鍊不消，埋之畢天不朽。", "verbatim", "內篇·金丹"),
    ps("fx-ctq-001", "fx_cantong_qi",
       "乾坤者，易之門戶，眾卦之父母。坎離匡廓，運轂正軸，牝牡四卦，以為橐籥。", "verbatim", "上篇"),
    ps("fx-kn-001", "fx_kanun",
       "Ibn Sīnā on the temperament of drugs: every drug has a temperament composed of the four qualities, and "
       "its action is known from the degree of its heat, coldness, moisture and dryness. (translated paraphrase)",
       "paraphrase", "Book II — Materia Medica"),
    ps("fx-kn-002", "fx_kanun",
       "Ibn Sīnā on compound remedies: the physician compounds drugs because a single simple may be too strong in "
       "one quality and must be tempered by another. (translated paraphrase)", "paraphrase", "Book V"),
    ps("fx-hw-001", "fx_hawi",
       "al-Rāzī records disagreements between Greek and Indian authorities on the nature of a drug, and advises "
       "the physician to test a remedy in the body before trusting the books. (paraphrase)", "paraphrase", "al-Ḥāwī"),
    ps("fx-ch-001", "fx_charaka",
       "ṣaḍrasāḥ — madhura, amla, lavaṇa, kaṭuka, tikta, kaṣāya — the six tastes arise from the five elements and "
       "each has a specific action on the doṣas. (IAST transliteration of the rasa list)", "verbatim", "Sūtrasthāna 26"),
    ps("fx-ch-002", "fx_charaka",
       "The physician should consider the country, the season, the digestive fire of the patient, the strength of "
       "the body and the nature of the illness, for the same drug acts differently in different constitutions. "
       "(translation paraphrase)", "paraphrase", "Vimānasthāna 3"),
    ps("fx-ss-001", "fx_susruta",
       "viruddha āhāra — incompatible food and drug combinations are those which, taken together, aggravate the "
       "doṣas without expelling them, and are held to produce disease. (paraphrase)", "paraphrase", "Sūtrasthāna 20"),
    ps("fx-rrs-001", "fx_rasa_ratna",
       "bhasma: a metal or mineral is repeatedly incinerated with herbal media until it becomes a fine powder whose "
       "toxicity has been removed and whose power has been made subtle. (paraphrase)", "paraphrase",
       "Rasa Ratna Samuccaya"),
    ps("fx-ah-001", "fx_astangahridaya",
       "Vāgbhaṭa on the anupāna (vehicle): the same medicine is made to act in different parts by the vehicle with "
       "which it is taken, as water carries a boat to a chosen shore. (paraphrase)", "paraphrase", "Sūtrasthāna"),
    ps("fx-dbg-001", "fx_dongui_bogam",
       "東醫寶鑑：四象體質，各自有專用之藥。同一藥也，少陽人服之則效，太陰人服之則反為害。", "paraphrase", "身形·四象"),
    ps("fx-duke-001", "fx_duke",
       "Glycyrrhiza uralensis: glycyrrhizin, glycyrrhetinic acid, liquiritin, isoliquiritigenin. Reported activity "
       "records include anti-inflammatory, antihepatotoxic and mineralocorticoid.", "verbatim", "G. uralensis"),
    ps("fx-duke-002", "fx_duke",
       "Piper longum: piperine, piperlongumine, piperettine. Reported activity records include bioavailability "
       "enhancement, CYP3A4 inhibition and P-glycoprotein interaction.", "verbatim", "P. longum"),
    ps("fx-duke-003", "fx_duke",
       "Aristolochia manshuriensis: aristolochic acid I, aristolochic acid II. Reported activity records include "
       "nephrotoxicity and carcinogenicity.", "verbatim", "A. manshuriensis"),
    ps("fx-chembl-001", "fx_chembl",
       "Bioactivity summary: piperine shows CYP3A4 inhibition and P-glycoprotein modulation records "
       "(fixture excerpt, release subset)", "paraphrase", "assay summary"),
    ps("fx-powo-001", "fx_powo",
       "Akebia quinata (Houtt.) Decne. — accepted; family Lardizabalaceae. Aristolochia manshuriensis Kom. — "
       "accepted; family Aristolochiaceae.", "verbatim", "taxonomy lookup"),
    ps("fx-powo-002", "fx_powo",
       "Panax notoginseng (Burkill) F.H.Chen — accepted; family Araliaceae. Gynura pseudochina (L.) DC. — accepted; "
       "family Asteraceae; pyrrolizidine alkaloid occurrence recorded.", "verbatim", "taxonomy lookup"),
    ps("fx-gbif-001", "fx_gbif",
       "Manis pentadactyla is listed in CITES Appendix I; Rhinoceros genera are listed in CITES Appendix I with a "
       "near-total trade ban.", "paraphrase", "taxon record"),
]

# --------------------------------------------------------------------------------------------
# Hypotheses — 2 per discovery class + 1 control exemplar (13 total)
# --------------------------------------------------------------------------------------------
H = []


def hyp(hid, title, klass, chain, scores, prov, falsification, uncertainty,
        safety=None, dossier=None, is_control=False):
    scores = dict(scores)
    scores["composite"] = composite(scores)
    H.append(dict(id=hid, title=title, discovery_class=klass,
                  discovery_class_label=CLASS_LABEL[klass], chain=chain, scores=scores,
                  provenance=prov, falsification_plan=falsification, uncertainty=uncertainty,
                  safety=safety or {"flags": [], "severity": "none"},
                  dossier=dossier or {}, is_control=is_control))


def pv(sid, span, locator="", kind="paraphrase"):
    sid = _src(sid)
    s = SRC[sid]
    return dict(source_id=sid, title=s["title"], title_en=s["title_en"], author=s["author"],
                year=s["year"], tradition=s["tradition"], lang=s["lang"], tier=s["tier"],
                licence=s["licence"], span=span, span_kind=kind, locator=locator)


# ============================== CLASS 3 · 异名同物 ===========================================
hyp(
    "H-01", "The name 木通 covers a harmless vine and a carcinogenic one — and the corpus already says which is which",
    "yiming_tongwu",
    dict(plant="Akebia quinata / A. trifoliata  (vs. Aristolochia manshuriensis 關木通)",
         preparation="Decoction of the stem — 木通 as dispensed c.1600–2000",
         chemotype="akeboside triterpenoid saponins  VS  aristolochic acid I/II (nitro-phenanthrene carboxylic acids)",
         target="proximal-tubule organic anion transporters OAT1/OAT3 (AA uptake); covalent DNA adducts at adenine N6",
         indication="Aristolochic acid nephropathy → interstitial fibrosis, upper-tract urothelial carcinoma"),
    dict(novelty=0.58, plausibility=0.79, testability=0.84, evidence=0.81),
    [pv("fx_bencao_gangmu",
        "木通：古方所用木通，即今之通草；後世以有細孔者可通氣，故謂之木通。今有一種關木通，色黃味苦，與木通形似而性不同，不可不辨。",
        "草部·木通"),
     pv("fx_powo", "Akebia quinata — Lardizabalaceae. Aristolochia manshuriensis — Aristolochiaceae.", "taxonomy", "verbatim"),
     pv("fx-duke", "Aristolochia manshuriensis: aristolochic acid I and II; nephrotoxicity and carcinogenicity records.",
        "A. manshuriensis", "verbatim"),
     pv("fx_culpeper_control", "Comparative control only: the Western corpus is ≤3% of tokens, used to test whether "
        "this signal is an artefact of any large botanical corpus. Contributes no evidence here.",
        "registry: comparative-control")],
    "The claim is a toxicity divergence, so it dies if the divergence is small. Compute compound-set distance between "
    "every taxon historically named 木通/通草 in the corpus; if the Aristolochia taxa are not the outliers on "
    "aristolochic-acid presence, the ranking is wrong. Second kill: if the corpus never presents 關木通 as a 木通 "
    "variant before 1900, the risk is modern substitution, not an inherited encoding — a different, equally "
    "publishable finding. Cheapest confirmation: LC-MS/MS for AA-I on retail 木通 decoction pieces, n=30, with the "
    "AA-DNA adduct (7-(deoxyadenosin-N6-yl)aristolactam I) as exposure biomarker.",
    "We cannot know what was in the bottle in 1600. The name collision is documented; the dispensing substitution is "
    "inferred from later commentary. Rank order inside the colliding set is sensitive to how we weight toxicity "
    "against therapeutic divergence — EVALUATION.md reports that sensitivity.",
    safety=dict(flags=["aristolochic acid is an IARC Group 1 carcinogen and a documented cause of nephropathy",
                       "no preparation, dose or substitution recipe appears anywhere in this output",
                       "regulatory ground truth: 2003 PRC ban on 關木通; 2001 FDA warning"],
                severity="high"),
    dossier=dict(
        rationale=("The strongest thing this corpus can do for public health is not discover a new drug. It is to notice "
                   "that one name has been standing for two different plants. 《本草綱目》 writes the warning already, "
                   "as a marginal note about colour and taste — four centuries before the Belgian slimming-clinic "
                   "outbreak and the Taiwanese nephropathy cohort made it undeniable. The encoded layer was there. "
                   "Nobody had a machine that read marginal notes as data."),
        mechanistic_chain=[
            "木通 in pre-modern formularies denotes Akebia species — triterpenoid saponins, no nitroaromatics.",
            "From roughly the late Qing, 關木通 (Aristolochia manshuriensis) is dispensed under the same name as a cheaper, more bitter stem.",
            "Aristolochic acid I is taken up by proximal-tubule OAT1/OAT3 and bioactivated by nitroreduction.",
            "The aristolactam forms covalent DNA adducts at adenine N6 — mutagenic and stable for decades.",
            "Chronic interstitial nephritis and upper-tract urothelial carcinoma follow years later, which is why the signal was missed for so long.",
        ],
        prior_art_refs=["Vanherweghem et al. (1993) — rapidly progressive interstitial renal fibrosis in a slimming regimen",
                        "IARC Monographs Vol. 100A (2012) — aristolochic acid, Group 1",
                        "Nortier et al. (2000) — urothelial carcinoma associated with aristolochic acid"],
        cost_estimate="Low for the corpus arm (already in the KG); medium for the LC-MS confirmation.",
        next_steps=["Promote 异名同物 to a first-class edge type: drug_name → {(taxon, era, confidence)}.",
                    "Rank colliding sets by maximum toxicity divergence, not by frequency.",
                    "Publish the ranking as a public list — this is a deliverable a regulator can use."],
    ),
)

hyp(
    "H-02", "三七 and 菊三七 share a name and a use for bleeding, and nothing else",
    "yiming_tongwu",
    dict(plant="Panax notoginseng  (vs. Gynura pseudochina 菊三七)",
         preparation="Powdered root, taken orally for bleeding and trauma",
         chemotype="notoginsenosides R1/Rg1/Rb1 (dammarane saponins)  VS  pyrrolizidine alkaloids (senecionine type)",
         target="no shared target; PA bioactivation by CYP3A4 → dehydropyrrolizine esters → hepatocyte DNA adducts",
         indication="Hepatic sinusoidal obstruction syndrome (veno-occlusive disease) from the substitute"),
    dict(novelty=0.54, plausibility=0.74, testability=0.77, evidence=0.66),
    [pv("fx_bencao_gangmu", "三七：味甘微苦，性溫，無毒。止血散血定痛，金刃箭傷跌撲杖瘡血出不止者，嚼爛罨之即止。",
        "草部·三七"),
     pv("fx_bencao_gangmu", "菊三七：葉似菊，根如三七而大，南人亦呼為三七，以之治血。其力大而性猛，久服令人腹痛。按此非真三七也。",
        "草部·菊三七"),
     pv("fx_powo", "Panax notoginseng — Araliaceae. Gynura pseudochina — Asteraceae; pyrrolizidine alkaloid "
        "occurrence recorded.", "taxonomy", "verbatim")],
    "Case series of herbal-product users with a hepatic adverse event: if no PAs are detectable in the implicated "
    "product and no Gynura DNA barcode is found, the substitution route is unsupported for that series. For the "
    "corpus claim alone: if 菊三七 is never presented as a 三七 substitute in any pre-1900 text, the collision is "
    "industrial-age rather than inherited.",
    "The 菊三七 note in 《本草綱目》 is a caution about potency, not a modern toxicity warning. Reading our knowledge of "
    "PA hepatotoxicity back into it would be anachronism. The honest formulation is 'the name was already known to be "
    "loose', not 'the ancients knew about pyrrolizidine alkaloids'.",
    safety=dict(flags=["pyrrolizidine alkaloids cause dose-dependent, sometimes irreversible hepatic injury",
                       "adulteration in the supplement supply chain is the modern risk vector",
                       "no dosage or product guidance is given"], severity="high"),
    dossier=dict(
        rationale=("Same structural failure, second instance: two roots, one name, one use. It is worse than 木通 in a "
                   "specific way — 菊三七 was already flagged in the classical text as 'not the real 三七, its force is "
                   "violent, long use causes abdominal pain'. The corpus contains the safety note. The job is to turn a "
                   "sixteenth-century aside into a ranked adulteration risk."),
        mechanistic_chain=[
            "Both roots are bitter-astringent and used for bleeding and stasis, so substitution is clinically invisible.",
            "Panax notoginseng acts via ginsenoside saponins; no PA exposure.",
            "Gynura carries senecionine-type pyrrolizidine alkaloids.",
            "CYP3A4 oxidises PAs to dehydropyrrolizine esters, which alkylate hepatocyte DNA and protein.",
            "Sinusoidal endothelial injury → veno-occlusive disease, often presenting late.",
        ],
        prior_art_refs=["Zuckerman et al. (2016) — pyrrolizidine alkaloids and hepatic sinusoidal obstruction syndrome",
                        "WHO/IPCS pyrrolizidine alkaloid risk assessment"],
        cost_estimate="Low — barcoding plus targeted PA analysis on a retail panel.",
        next_steps=["Add DNA-barcode evidence as an edge attribute on every 异名同物 pair.",
                    "Rank colliding pairs that differ in severity class — that is the actionable list."],
    ),
)

# ============================== CLASS 2 · 炮制 ==============================================
hyp(
    "H-03", "附子's processing is a hydrolysis ladder, and the classical steps specify where to stop",
    "paozhi",
    dict(plant="Aconitum carmichaelii 附子",
         preparation="炮 (roast until split) → 去皮臍 → 蜜水煮 / 甘草水浸  (per 雷公炮炙論)",
         chemotype="diester diterpene alkaloids: aconitine → benzoylaconine → aconine (successive ester hydrolysis)",
         target="voltage-gated Na⁺ channel, site 2 — aconitine holds the channel open; aconine barely binds",
         indication="Aconite cardiotoxicity and neurotoxicity; the processed drug is the therapeutic one"),
    dict(novelty=0.51, plausibility=0.88, testability=0.86, evidence=0.84),
    [pv("fx_leigong_paozhi", "凡使附子，先於文武火上炮令裂，去皮臍，乘熱切之；又以蜜水煮，令毒去而力存。炮之得法，則毒輕而效速。",
        "草部·附子"),
     pv("fx_shennong_bencao", "附子，味辛溫。主風寒咳逆邪氣，溫中，金瘡，破癥堅積聚，血瘕，寒濕踒躄，拘攣膝痛，不能行步。",
        "下品·附子", "verbatim"),
     pv("fx_shanghanlun", "四逆湯方：甘草二兩炙，乾薑一兩半，附子一枚生用去皮破八片。", "少陰病篇", "verbatim")],
    "Quantify the three alkaloids by LC-MS across processing time and temperature for raw, 炮, and 炮+蜜煮 material. "
    "The mechanistic claim is refuted if the diester:monester ratio does not fall monotonically along the classical "
    "step sequence, or if the endpoint the text names does not coincide with where cardiotoxicity (zebrafish or rat "
    "heart-rate assay) stops falling. Positive control: pure aconitine hydrolysed under identical conditions. One "
    "targeted LC-MS method runs the whole thing.",
    "The text names its endpoint by appearance ('炮令裂'), not by temperature, so 'where to stop' is our inference. "
    "And 傷寒論 uses 生用 附子 in 四逆湯 — which complicates the tidy claim that processing is always necessary. That "
    "exception is itself a finding and is reported rather than smoothed away.",
    safety=dict(flags=["aconitine is a highly toxic cardiotoxin; raw 附子 is not a food and not a self-treatment",
                       "this is analytical toxicology, never a preparation method for use",
                       "the therapeutic window is narrow and clinician-supervised in every legitimate context"],
                severity="high"),
    dossier=dict(
        rationale=("The cleanest 'what was hidden between the lines' in the whole corpus. 雷公炮炙論 does not say "
                   "'processing reduces toxicity'. It says: roast until it splits, peel, cut while hot, then boil in "
                   "honey water, and then the poison is light and the effect is fast. That is a hydrolysis protocol "
                   "with an endpoint, performed for fifteen centuries before it was described."),
        mechanistic_chain=[
            "Aconitine is a diester — an acetate at C8 and a benzoate at C14 on a norditerpene scaffold.",
            "Heating in aqueous media hydrolyses the C8 acetate first → benzoylaconine (roughly 100× less toxic).",
            "Further hydrolysis removes the C14 benzoate → aconine, effectively inactive at Na⁺ channels.",
            "The classical endpoint ('split, peel, honey-water boil') sits at the monester stage — activity retained, cardiotoxicity largely gone.",
            "The 傷寒論 '生用' exception for 四逆湯 is a deliberate high-potency choice inside a controlled decoction — exactly the distinction modern granule products lose.",
        ],
        prior_art_refs=["雷斆 Lei Xiao — 雷公炮炙論 (5th–6th c.)",
                        "Singhuber et al. (2009) — Aconitum in traditional Chinese medicine: a review",
                        "diester diterpene alkaloid hydrolysis kinetics literature"],
        cost_estimate="Low — one LC-MS/MS method, three processing arms, no synthesis.",
        next_steps=["Model 炮制 as a Process entity with (temperature, medium, duration, target-metabolite).",
                    "Flag every modern dosage form that omits a classical processing step the corpus calls necessary.",
                    "Report the 生用 exception — it is the test of whether we read the text or paraphrase it."],
    ),
)

hyp(
    "H-04", "九蒸九曬 is a detoxification protocol: 生首烏 and 制首烏 are different drugs",
    "paozhi",
    dict(plant="Polygonum multiflorum 何首烏",
         preparation="生用 (raw) vs 制 — nine steam-and-sun cycles with black bean decoction",
         chemotype="raw: stilbene glycosides (TSG) + emodin anthraquinones; processed: hydrolysed aglycones, altered anthraquinone profile",
         target="hepatocyte — mitochondrial injury and CYP/UGT-mediated bioactivation (candidate); TSG is the suspect fraction",
         indication="Herb-induced liver injury from unprocessed 生首烏 in 'hair-blackening' supplements"),
    dict(novelty=0.46, plausibility=0.76, testability=0.81, evidence=0.72),
    [pv("fx_bencao_gangmu", "何首烏：味苦澀微溫。生者有毒，制者無毒。九蒸九曬，黑豆同蒸，則補益之功成而毒去。生用則令人發熱、腹瀉。",
        "草部·何首烏"),
     pv("fx_leigong_paozhi", "凡藥有毒者，皆先以炮製減其毒，此制方之要也。", "凡例")],
    "Compare 生 vs 制 extract cytotoxicity in HepG2 and primary human hepatocytes at matched dry mass, with TSG and "
    "emodin by HPLC. Refuted if the processed extract is not less cytotoxic, or if the TSG fraction is not the "
    "dose-limiting toxic component. The clinical pattern to reproduce: unprocessed product, weeks of exposure, "
    "cholestatic or mixed injury.",
    "Commercial cycle counts vary from 4 to 9 and are rarely declared; the dose-response for cycle count is not in "
    "the corpus. Attribution to TSG is a candidate, not a conclusion.",
    safety=dict(flags=["documented herb-induced liver injury; regulatory warnings in several jurisdictions",
                       "no product, dose or duration guidance is given",
                       "toxicology analysis, not a recommendation about any supplement"],
                severity="caution"),
    dossier=dict(rationale=("《本草綱目》 says it plainly: raw is toxic, processed is not, and it names the process. The "
                            "modern failure mode is that 'hair-blackening' products are made from cheap raw root and "
                            "sold without the processing claim. The corpus holds both the warning and the protocol — "
                            "exactly the pair you need to build a product-risk test."),
                mechanistic_chain=["Raw root carries high TSG and emodin glycoside loads.",
                                   "Nine steam cycles with black bean progressively hydrolyse glycosides and shift the anthraquinone profile.",
                                   "The processed material is the one the text calls 無毒.",
                                   "Unprocessed material retains the fraction implicated in hepatocyte injury.",
                                   "Therefore the processing step is a safety control, not a preference."],
                prior_art_refs=["Lin et al. — Polygonum multiflorum hepatotoxicity reviews",
                                "NMPA and MHRA safety communications on 何首烏"],
                cost_estimate="Low — two extracts, one cell model, one HPLC method.",
                next_steps=["Encode cycle-count as a numeric Process attribute so the KG can ask 'how many cycles?'.",
                            "Attach a processing-omitted risk flag to finished-product classes."]),
)

# ============================== CLASS 1 · 配伍禁忌 ==========================================
hyp(
    "H-05", "十八反 is a pharmacokinetic rule, not a pharmacological one",
    "peiwu_jinji",
    dict(plant="Glycyrrhiza uralensis 甘草 + Euphorbia kansui 甘遂  (十八反 pair)",
         preparation="Co-decoction in a single formula",
         chemotype="glycyrrhizin / 18β-glycyrrhetinic acid  +  kansuinin A, ingenol-type diterpene esters",
         target="efflux and clearance: P-gp / BCRP transport and CYP3A4 (candidate), raising systemic exposure to the Euphorbia diterpenes",
         indication="The rule predicts increased toxicity of the combined decoction"),
    dict(novelty=0.63, plausibility=0.55, testability=0.74, evidence=0.44),
    [pv("fx_ru-men-shi-qin", "本草明言十八反：半蔞貝蘞及攻烏，藻戟遂芫俱戰草，諸參辛芍叛藜蘆。", "十八反", "verbatim"),
     pv("fx_shennong_bencao", "甘草，味甘平。主五臟六腑寒熱邪氣，堅筋骨，長肌肉，倍力，金瘡腫，解毒。", "上品·甘草", "verbatim"),
     pv("fx_duke", "Glycyrrhiza uralensis: glycyrrhizin, glycyrrhetinic acid; anti-inflammatory and "
        "mineralocorticoid activity records.", "G. uralensis", "verbatim")],
    "Four-arm rat PK study: 甘遂 alone; 甘遂+甘草; 甘遂 + a P-gp inhibitor positive control; vehicle. The claim dies if "
    "kansuinin A AUC is unchanged by co-administration and intestinal permeability is unchanged; it also dies if the "
    "toxicity difference is purely additive, since an interaction must be non-additive. The eighteen pairs give "
    "eighteen independent tests — which makes this a statistical question: if the rule is real, PK-interaction "
    "enrichment across the 18 pairs must exceed the shuffled-pair null.",
    "The mnemonic is a list, not an explanation: it may encode several mechanisms at once (PK, PD, chemical reaction "
    "on co-decoction, plain dose-escalation accidents). Our single-mechanism claim is the weakest part and is scored "
    "accordingly.",
    safety=dict(flags=["Euphorbia kansui diterpenes are violently purgative and toxic",
                       "the pair is a controlled dispensing contraindication in Chinese pharmacy practice",
                       "no formula, ratio or preparation is given — this is a mechanism question"],
                severity="high"),
    dossier=dict(rationale=("Every TCM student memorises 十八反 as a rhyme. Almost nobody can tell you why. The rhyme is a "
                            "compressed, high-confidence dataset: eighteen negative interactions asserted for a "
                            "millennium and never systematically tested. If even a third are pharmacokinetic, then "
                            "herb–drug interaction screening exists inside a 13th-century mnemonic."),
                mechanistic_chain=["甘草 is a near-universal 'harmonising' herb and a known modulator of glucuronidation "
                                   "and efflux transport.",
                                   "Euphorbia diterpene esters are P-gp substrates with a narrow margin.",
                                   "Co-administration could raise systemic exposure with no receptor-level interaction at all.",
                                   "That is a PK interaction — the same class as a modern DDI, not a mystical antagonism.",
                                   "The enriched-null test across all 18 pairs is what turns this from anecdote into evidence."],
                prior_art_refs=["Zhang Congzheng — 儒門事親 (1228), the 十八反 mnemonic",
                                "Wang et al. — pharmacokinetics of 甘草–甘遂 co-administration",
                                "Chinese Pharmacopoeia — 十八反/十九畏 as dispensing contraindications"],
                cost_estimate="Medium — four-arm rat PK, one validated LC-MS/MS method for the diterpenes.",
                next_steps=["Split 配伍禁忌 into mechanism classes (PK / PD / chemical / dose) before ranking.",
                            "Build the enriched-null test — it is the first real benchmark for this class."]),
)

hyp(
    "H-06", "十九畏 says mercury fears arsenic — a toxicology dataset wearing the costume of a taboo",
    "peiwu_jinji",
    dict(plant="水銀 mercury sulphide HgS + 砒霜 arsenic tri/sulphide As₂O₃ / As₂S₃  (十九畏 pair)",
         preparation="Mineral drugs in 丹 formulas; 輕粉 Hg₂Cl₂; 雄黃 As₄S₄",
         chemotype="Hg²⁺/HgS + As³⁺/As⁵⁺ — speciation-dependent soft-metal thiol chemistry",
         target="thiol binding: GSH depletion, thioredoxin reductase inhibition, mitochondrial permeability transition",
         indication="Documented heavy-metal toxicity from mineral-drug formulas; the pair is a speciation and clearance problem"),
    dict(novelty=0.57, plausibility=0.61, testability=0.69, evidence=0.52),
    [pv("fx_ru-men-shi-qin", "十九畏：硫黃原是火中精，朴硝一見便相爭；水銀莫與砒霜見，狼毒最怕密陀僧。", "十九畏", "verbatim"),
     pv("fx_baopuzi", "夫金丹之為物，燒之愈久，變化愈妙。", "內篇·金丹", "verbatim"),
     pv("fx_rasa_ratna", "bhasma: a metal or mineral is repeatedly incinerated with herbal media until toxicity has "
        "been removed and the power made subtle.", "Rasa Ratna Samuccaya")],
    "Speciation and thiol-binding study: does co-present Hg and As change aqueous speciation and the cellular thiol "
    "response relative to either alone? Refuted if the two act purely additively on GSH depletion and cytotoxicity in "
    "a hepatocyte model. Positive control: known Hg–Se antagonism. **This is toxicology; the only deliverable is a "
    "hazard ranking, never a preparation.**",
    "The taboo may encode observation of acute toxicity (a co-ingestion accident) rather than a chemical interaction. "
    "Separating 'people who took both died' from 'the combination is chemically worse' is precisely the distinction "
    "the corpus does not make. We say so.",
    safety=dict(flags=["mercury and arsenic compounds are severely toxic; hazard analysis only",
                       "no 丹 formula, mineral preparation, route or dose appears in any output — by design",
                       "the safety layer blocks the Ask panel from answering preparation questions in this area"],
                severity="high"),
    dossier=dict(rationale=("This hypothesis exists to draw a line. Asian materia medica genuinely includes mercury, "
                            "arsenic and lead drugs — 丹, 輕粉, 雄黃, bhasma — and pretending otherwise would be "
                            "dishonest history. They are in the corpus as data. They never appear in the output as "
                            "advice. A system that mines this canon must be able to say which of its own sources are "
                            "poison, and refuse to help with them."),
                mechanistic_chain=["Hg and As both act through soft-metal thiol chemistry.",
                                   "The 十九畏 pairing asserts an interaction beyond either alone.",
                                   "Speciation (HgS vs Hg²⁺; As₂S₃ vs As³⁺) dominates the actual hazard.",
                                   "The transferable insight is about delivery form, not combination: the same element in a different speciation is a different drug."],
                prior_art_refs=["WHO monographs on arsenic and mercury exposure",
                                "Liu et al. — speciation and bioavailability of mineral drugs in 丹 formulas",
                                "bhasma literature — processing as a particle-size and speciation intervention"],
                cost_estimate="Medium — speciation analytics and a thiol-depletion cell assay.",
                next_steps=["Every heavy-metal-adjacent hypothesis carries a hard safety annotation, always rendered.",
                            "Verify the Ask panel refuses 'how do I prepare' questions in this class.",
                            "Frame the deliverable as a hazard ranking for regulators, never as a remedy."]),
)

# ============================== CLASS 4 · 君臣佐使 =========================================
hyp(
    "H-07", "The 使 courier is a pharmacokineticist: formula role predicts CYP/P-gp modulation",
    "junchen_zuoshi",
    dict(plant="Role-annotated formulas across the corpus — 胡椒/蓽茇 (Piper), 甘草 (Glycyrrhiza), 生薑 (Zingiber)",
         preparation="Whole-formula decoction; the courier herb in the 使 position",
         chemotype="piperine, glycyrrhizin, 6-gingerol — a chemically diverse set with one shared activity",
         target="CYP3A4 inhibition and P-glycoprotein modulation — i.e. oral bioavailability of the 君 herb",
         indication="Systematic enrichment test: do 使 herbs inhibit CYP3A4/P-gp more often than 君 herbs?"),
    dict(novelty=0.66, plausibility=0.58, testability=0.88, evidence=0.41),
    [pv("fx_taiping_huimin", "君臣佐使者，制方之要也。君為主，臣為輔，佐為制，使為引。主病之謂君，佐君之謂臣，應臣之謂使。",
        "卷首·論方"),
     pv("fx_bencao_gangmu", "胡椒：味辛大溫，無毒。主下氣溫中，去痰，除臟腑中風冷。近世食品多賴此以行藥力。",
        "果部·胡椒"),
     pv("fx_duke", "Piper longum: piperine — bioavailability enhancement, CYP3A4 inhibition and P-glycoprotein "
        "interaction records.", "P. longum", "verbatim")],
    "Computed, not wet. Take every formula in `formulas.csv` with role annotations; take every ingredient with a "
    "ChEMBL CYP3A4 or P-gp record; compute enrichment of 'inhibitor' among 使-role herbs versus 君-role herbs, with a "
    "permutation null over role labels (10⁴ shuffles). Refuted if observed enrichment sits inside the null "
    "distribution. Then confirm one untested courier experimentally — piperine is already known, so pick a null one.",
    "Role labels are edition-specific and sometimes contested. The confound is sharp: courier herbs are often aromatic "
    "and small-dose, and small aromatics are over-represented among CYP modulators for unrelated reasons. We cannot yet "
    "separate 'courier because it is a PK modulator' from 'both follow from being a volatile aromatic'.",
    safety=dict(flags=["the practical consequence is herb–drug interaction risk — a warning, not a recommendation"],
                severity="caution"),
    dossier=dict(rationale=("君臣佐使 is a four-way classification that every classical formulary carries and no modern "
                            "database encodes. If 使 is not decoration but a functional prediction about absorption, "
                            "then the canon contains a pharmacokinetic annotation layer — labelled, centuries old, and "
                            "computable tomorrow. That is the strongest version of 'what was hidden'."),
                mechanistic_chain=["君 bears the primary therapeutic action.",
                                   "使 is defined by direction and guidance — 應臣之謂使, the one that responds to the minister.",
                                   "In the piperine case the 'guidance' is literal: intestinal CYP3A4 and P-gp inhibition raises the 君 herb's exposure.",
                                   "If the role label is predictive, that relationship should hold beyond the famous examples.",
                                   "Test: role enrichment against bioactivity databases, against a permutation null."],
                prior_art_refs=["《太平惠民和劑局方》 — role annotations",
                                "Atal et al. (1981) — piperine as a bioavailability enhancer",
                                "Srinivasan — piperine and drug metabolism"],
                cost_estimate="Very low for the computational arm; one confirmatory PK arm afterwards.",
                next_steps=["Parse role annotations into `formula_ingredients.csv` (role ∈ jun/chen/zuo/shi) — the enabling step.",
                            "Run the permutation null before any biological claim.",
                            "Pre-register the enrichment threshold in EVALUATION.md."]),
)

hyp(
    "H-08", "麻黃湯's 臣 herb supplies a second, non-adrenergic mechanism",
    "junchen_zuoshi",
    dict(plant="麻黃湯: 麻黃 (君) + 桂枝 (臣) + 杏仁 (佐) + 甘草 (使)",
         preparation="Classical decoction, 先煮麻黃去上沫 (per the 方後註 in 傷寒論)",
         chemotype="ephedrine/pseudoephedrine + cinnamaldehyde, coumarin + amygdalin",
         target="β-adrenergic agonism (ephedrine) alongside TRPA1-mediated vasodilation (cinnamaldehyde)",
         indication="The diaphoretic action of the formula, which ephedrine alone does not reproduce"),
    dict(novelty=0.49, plausibility=0.54, testability=0.72, evidence=0.47),
    [pv("fx_shanghanlun", "太陽病，頭痛發熱，身疼腰痛，骨節疼痛，惡風，無汗而喘者，麻黃湯主之。", "太陽病中篇", "verbatim"),
     pv("fx_shanghanlun", "麻黃湯方：麻黃三兩去節，桂枝二兩去皮，甘草一兩炙，杏仁七十箇去皮尖。上四味，以水九升，先煮麻黃，減二升，去上沫，內諸藥，煮取二升半，去滓，溫服八合。",
        "太陽病中篇", "verbatim")],
    "Isolated aortic ring plus whole-animal thermography: does 桂枝 extract add vasodilation that is abolished in "
    "TRPA1⁻/⁻ mice, and is the combination's diaphoretic effect greater than ephedrine at matched dose? Refuted if "
    "the effect is simply additive or absent. Also test whether the 'skim the froth' instruction removes a "
    "measurable volatile fraction before assuming it is ritual.",
    "The formula has been in continuous use for 1,800 years and the modern literature is large, so novelty is modest. "
    "The skimming step is untested and may be the most interesting part.",
    safety=dict(flags=["ephedrine is a controlled precursor in many jurisdictions and carries cardiovascular risk",
                       "no dose, product or substitution guidance is given"], severity="caution"),
    dossier=dict(rationale=("麻黃湯 is the first formula in 傷寒論, so it is the first thing the model sees and the most "
                            "over-studied. It is included as a structural test: if the pipeline correctly assigns roles "
                            "and notices the one unexplained instruction (skimming the froth), it is reading the text "
                            "rather than the summary."),
                mechanistic_chain=["麻黃 supplies ephedrine — a direct and indirect sympathomimetic.",
                                   "Sympathomimetic action alone gives tachycardia and vasoconstriction, not classical diaphoresis.",
                                   "桂枝's cinnamaldehyde is a TRPA1 agonist and produces cutaneous vasodilation.",
                                   "The pair produces sweating where either alone does not — a genuine synergy claim.",
                                   "先煮麻黃去上沫: skimming removes a volatile, possibly irritant fraction — untested."],
                prior_art_refs=["《傷寒論》 太陽病中篇", "pharmacological studies of 麻黃湯",
                                "TRPA1 and cutaneous vasodilation literature"],
                cost_estimate="Low — isolated tissue plus a small in vivo arm.",
                next_steps=["Encode the 方後註 (post-script preparation instructions) as structured Process steps.",
                            "Ask whether skimming correlates with volatile-alkaloid content across the corpus.",
                            "Keep as the pipeline's structural self-test."]),
)

# ============================== CLASS 5 · 未研究本草 =======================================
hyp(
    "H-09", "貓爪草 is used for scrofula across several provinces and has almost no target-level evidence",
    "weiyanjiu",
    dict(plant="Ranunculus ternatus 貓爪草",
         preparation="Decoction of the root tuber; vinegar-processed in some regional practice",
         chemotype="unresolved — protoanemonin-type lactones reported; no characterised target-level active",
         target="none established (candidate: macrophage activation / autophagy in granuloma)",
         indication="瘰癧 scrofula — historically tuberculosis lymphadenitis; still used in oncology formulas"),
    dict(novelty=0.72, plausibility=0.38, testability=0.66, evidence=0.25),
    [pv("fx_bencao_gangmu", "貓爪草：近世方書始載，主瘰癧結核，消腫散結，南人用以治瘡瘍。", "草部·貓爪草"),
     pv("fx_qianjin_yaofang", "夫為醫者，當須先洞曉病源，知其所犯，以食治之；食療不愈，然後命藥。", "食治", "verbatim")],
    "A screening hypothesis, not a mechanism hypothesis — and it is labelled as such. The test is an ordinary "
    "natural-product funnel: extract, fractionate, profile against a target panel; if no fraction shows reproducible "
    "activity, report the negative. The tool's value here is the queue order — strong repeated use with no "
    "target-level evidence is the cheapest place to look.",
    "High novelty here is partly an artefact of under-study, not of insight. The compound profile is essentially "
    "unknown, so the mechanism box is empty on purpose; an empty mechanism box lowers plausibility, and it does (0.38).",
    safety=dict(flags=["Ranunculus species contain protoanemonin, an irritant; fresh-plant handling is a hazard"],
                severity="caution"),
    dossier=dict(rationale=("The understudied majority is the largest and least glamorous class, and it is where a corpus "
                            "earns its keep. 貓爪草 has a coherent, specific, repeated indication (scrofula) and almost "
                            "no modern target-level work. Specificity plus neglect is the highest-yield screening "
                            "signal in the whole canon."),
                mechanistic_chain=["Specific, repeated indication across regional traditions.",
                                   "No characterised active constituent.",
                                   "No target-level literature.",
                                   "Therefore a genuine discovery gap, ranked by use-density ÷ evidence-density."],
                prior_art_refs=["Regional Chinese pharmacopoeia monographs",
                                "natural-product screening literature on Ranunculus (sparse)"],
                cost_estimate="Medium — a full extract-to-fraction campaign.",
                next_steps=["Build use-density ÷ evidence-density as an explicit, tunable metric.",
                            "Publish the whole top-50 list, not just the top 3 — the list is the deliverable.",
                            "State that an empty mechanism box is a finding about the literature, not about the plant."]),
)

hyp(
    "H-10", "半枝蓮 appears in more oncology formulas than almost any herb and is studied at the wrong resolution",
    "weiyanjiu",
    dict(plant="Scutellaria barbata 半枝蓮",
         preparation="Decoction, usually paired with 白花蛇舌草 in modern oncology formulas",
         chemotype="flavones (scutellarein, apigenin), diterpenoids (scutebarbatines), triterpenoids (ursolic/oleanolic acid)",
         target="suspected multi-target — no single dominant mechanism; high risk of flavonoid promiscuity (PAINS)",
         indication="Adjunct use in colorectal and hepatobiliary cancer formulas"),
    dict(novelty=0.61, plausibility=0.44, testability=0.63, evidence=0.38),
    [pv("fx_bencao_gangmu", "半枝蓮：味辛苦，性寒。清熱解毒，化瘀利尿。近人用以治癰腫瘡毒、蛇傷。", "草部·半枝蓮"),
     pv("fx_taiping_huimin", "君臣佐使者，制方之要也。君為主，臣為輔，佐為制，使為引。", "卷首·論方")],
    "Resolution test: fractionate and assay each fraction separately. If activity is distributed across every "
    "flavonoid-containing fraction in proportion to total flavonoid content, the 'multi-target' story is really "
    "'non-specific' — a PAINS artefact, and that is worth publishing. Refuted as an oncology lead if no fraction "
    "separates activity from total polyphenol.",
    "This is the class where we are most likely to fool ourselves, and we say so. Flavonoid promiscuity is a "
    "documented trap; our novelty score cannot distinguish 'unstudied' from 'unpromising'.",
    safety=dict(flags=["adjunct-use claims in oncology are high stakes; this is not treatment guidance",
                       "herb–drug interaction potential with chemotherapeutics is unquantified"],
                severity="caution"),
    dossier=dict(rationale=("A hypothesis from this class that we suspect is wrong, to show the scoring is not vanity. "
                            "半枝蓮's prominence is a frequency signal; frequency is not evidence. The pipeline's job is "
                            "to separate them, and the honest output is 'very widely used, mechanistically diffuse, "
                            "plausibly an assay artefact'."),
                mechanistic_chain=["High formula frequency in the corpus.",
                                   "Broad flavonoid content with known promiscuity.",
                                   "No fraction-resolved activity data.",
                                   "Prediction: activity will track total polyphenol, not any specific compound."],
                prior_art_refs=["PAINS literature (Baell & Holloway 2010) applied to natural products",
                                "Scutellaria barbata reviews (largely in vitro)"],
                cost_estimate="Low — fractionation with an honest polyphenol control.",
                next_steps=["Add a PAINS-liability flag to compound nodes with high promiscuity.",
                            "Score frequency and evidence as separate axes in the UI, never fused into one number."]),
)

# ============================== CLASS 6 · 濒危代用品 =======================================
hyp(
    "H-11", "水牛角 replaced 犀角 by regulation, not by chemistry — and the corpus can say which formulas that protects",
    "binwei_daiyong",
    dict(plant="Rhinoceros horn 犀角 → Bubalus bubalis horn 水牛角",
         preparation="Powdered horn, decocted (清營湯, 安宮牛黃丸 tradition)",
         chemotype="keratin-dominant with species-specific peptides and free amino acids; calcium phosphate matrix",
         target="no agreed molecular target for either material — the honest position",
         indication="Febrile / heat-clearing formulas; the question is substitution urgency, not chemical identity"),
    dict(novelty=0.69, plausibility=0.47, testability=0.79, evidence=0.36),
    [pv("fx_bencao_gangmu", "犀角：苦酸鹹寒，無毒。主百毒蠱疰，邪鬼瘴氣。今禁採，官方以水牛角代之。", "獸部·犀角"),
     pv("fx_gbif", "Rhinoceros genera are listed in CITES Appendix I with a near-total trade ban.", "CITES")],
    "Peptidomic comparison of horn keratin digests across species, plus a formula-level assay where 犀角 is 君. Refuted "
    "as a full equivalence claim if the keratin/peptide profile differs materially in fractions surviving decoction. "
    "But note the honest framing: for a material with no agreed target, 'equivalence' is undefined, and the "
    "conservation decision does not depend on it. The corpus-side test is cleaner — count how often 犀角 is 君 versus "
    "佐, and flag every formula where the substitute changes the role structure.",
    "We cannot establish efficacy equivalence for a material whose mechanism is unknown, and should not pretend the "
    "substitution is chemically proven. The defensible claim is weaker and better: the substitution is "
    "conservation-necessary, the corpus tells you which formulas it affects, and no rhino needs to die to find out.",
    safety=dict(flags=["any output touching endangered-species materials must cite CITES status",
                       "no sourcing, trade or substitution-procurement guidance is given"],
                severity="caution"),
    dossier=dict(rationale=("Where traditional-knowledge mining pays a direct conservation dividend. The corpus knows "
                            "which formulas depend on a CITES Appendix I material and how load-bearing that material is "
                            "(君 vs 佐). That is a ranked list of substitution problems built from text, and it costs "
                            "no animals."),
                mechanistic_chain=["Horn is keratin plus a mineral matrix; decoction extracts peptides and amino acids.",
                                   "Species-specific peptide profiles exist, but their pharmacological relevance is unestablished.",
                                   "The classical role label tells you how load-bearing the ingredient is.",
                                   "Therefore rank substitution urgency by role, not by volume.",
                                   "Conservation action follows directly, independent of the efficacy question."],
                prior_art_refs=["Chinese Pharmacopoeia — 水牛角 as the official substitute for 犀角",
                                "CITES Appendix I listings for Rhinocerotidae",
                                "keratin and horn-peptide characterisation literature"],
                cost_estimate="Low for the corpus arm; medium for the peptidomics.",
                next_steps=["Join the CITES list to the taxon table and flag every formula ingredient automatically.",
                            "Report role-weighted substitution urgency — a ranked list conservation NGOs can use.",
                            "Extend to 虎骨, 穿山甲, 沉香 and 重樓."]),
)

hyp(
    "H-12", "For 穿山甲 the corpus already contains the substitute — the processing column is the argument",
    "binwei_daiyong",
    dict(plant="Manis pentadactyla scale 穿山甲 → 豬蹄甲 pig toenail (documented PRC substitute research)",
         preparation="煅 (calcined) and powdered, or decocted",
         chemotype="keratin with species-specific cross-linking; calcination destroys most organic structure",
         target="none established; the claims are 通乳 (promoting lactation) and dispersing stasis",
         indication="Post-partum insufficient lactation, 癥瘕 masses — both weak by modern standards"),
    dict(novelty=0.64, plausibility=0.41, testability=0.71, evidence=0.29),
    [pv("fx_bencao_gangmu", "穿山甲：味鹹微寒，有毒。主五邪驚啼悲傷，燒之作灰，以酒或水和方寸匕。近世以之通乳、消癰。",
        "鱗部·穿山甲"),
     pv("fx_gbif", "Manis pentadactyla is listed in CITES Appendix I; international commercial trade is prohibited.",
        "CITES"),
     pv("fx_taiping_huimin", "君臣佐使者，制方之要也。君為主，臣為輔，佐為制，使為引。", "卷首·論方")],
    "The decisive experiment is cheap and slightly deflating: calcined keratin is calcined keratin. Ash content, "
    "amino-acid profile and calcium phosphate fraction should be near-identical between 煅穿山甲 and 煅豬蹄甲. If they "
    "are, the substitution question is settled for every formula that uses the material calcined — and the corpus work "
    "is to count how many do. If a formula uses it raw, the question reopens and deserves the peptidomic work.",
    "We may be arguing against a traditional use's efficacy, which is culturally sensitive. The framing must hold: we "
    "are quantifying a substitution argument that Chinese researchers themselves made, and we are not asserting the "
    "traditional indication is worthless.",
    safety=dict(flags=["CITES Appendix I — trade is prohibited; no sourcing guidance of any kind",
                       "culturally sensitive — state the framing explicitly in any public output"],
                severity="caution"),
    dossier=dict(rationale=("The strongest conservation argument in the corpus is not 'this is cruel'. It is: the "
                            "calcination step in your own text reduces the material to ash, and ash is ash. The "
                            "classical processing record is the evidence that substitution is defensible — the "
                            "tradition argues for its own replacement, if you read the processing column."),
                mechanistic_chain=["穿山甲 is typically 煅 (calcined) before use.",
                                   "Calcination destroys keratin secondary structure and most organics.",
                                   "The residue is calcium phosphate plus minerals — largely material-agnostic.",
                                   "Therefore source-species identification in calcined material is analytically hard and pharmacologically meaningless.",
                                   "Substitution is then a supply-chain and cultural question, not a chemical one."],
                prior_art_refs=["PRC substitute-research literature on 豬蹄甲 for 穿山甲",
                                "CITES Appendix I listing for Manis pentadactyla",
                                "calcination effects on keratin materials"],
                cost_estimate="Very low — ash content and amino-acid analysis on reference standards.",
                next_steps=["Add a processing_state field to every endangered-material hypothesis.",
                            "Make the conservation output a ranked, citable list with CITES status attached.",
                            "State the cultural framing inside the output, not only in the docs."]),
)

# ============================== CONTROL =====================================================
hyp(
    "H-13", "Walnut looks like a brain, therefore it tonifies the brain — the 取象比類 control",
    "control",
    dict(plant="Juglans regia 核桃仁",
         preparation="Eaten as a food; 補腎健腦 by resemblance",
         chemotype="α-linolenic acid, polyphenols, tocopherols — no brain-specific warhead identified",
         target="brain (by morphological analogy only)",
         indication="Memory, 補腦 — assigned by resemblance, not mechanism"),
    dict(novelty=0.08, plausibility=0.14, testability=0.61, evidence=0.18),
    [pv("fx_bencao_gangmu", "核桃：味甘，性熱，無毒。食之令人肥健，潤肌黑髮。其形似腦，故近人謂之補腦，然古方未有此說。",
        "果部·胡桃"),
     pv("fx_huangdi_neijing", "東方生風，風生木，木生酸，酸生肝，肝生筋。其在天為風，在地為木，在人為肝，在色為蒼，在味為酸。",
        "素問·陰陽應象大論", "verbatim")],
    "Stated as a testable prediction: across the corpus, does morphological or colour resemblance to an organ predict "
    "the recorded indication better than chance? The measured answer appears in the 使 Shǐ evaluation table. A null is "
    "the expected result. A large positive rho would mean our extraction is picking up organ-word co-occurrence rather "
    "than pharmacology — which would invalidate the other twelve. This is the control that keeps them honest.",
    "Walnuts do contain α-linolenic acid and are a reasonable food. The control tests the reasoning pattern, not the "
    "food: a genuine nutritional effect and a resemblance argument can coexist, which is why the test must be on the "
    "pattern of indication assignment across many taxa, not on one plant.",
    safety=dict(flags=[], severity="none"),
    dossier=dict(rationale=("Every knowledge-mining system on this corpus will 'discover' 取象比類 unless you stop it. It "
                            "is a productive, internally coherent, and largely non-predictive reasoning pattern. We "
                            "give it a face so that the null result on the slide has something to point at."),
                mechanistic_chain=["Resemblance asserted.", "Indication assigned by analogy.",
                                   "No molecular link proposed.", "This is the expected null."],
                prior_art_refs=["《本草綱目》 胡桃 entry — which itself notes the 補腦 claim is recent, not ancient",
                                "Foucault, The Order of Things — the resemblance episteme"],
                cost_estimate="None. It is the reason the other twelve can be believed.",
                next_steps=["Report both negative controls on every run, not just once.",
                            "Keep it in the deck: a system that publishes its own nulls is the one to trust."]),
)

# --------------------------------------------------------------------------------------------
# Knowledge graph
# --------------------------------------------------------------------------------------------
edges_i: list = []

KG_EXTRA = [
    ("drug:木通", "taxon:Akebia quinata", "resolves_to"),
    ("drug:木通", "taxon:Aristolochia manshuriensis", "resolves_to"),
    ("taxon:Aristolochia manshuriensis", "compound:Aristolochic acid I", "contains"),
    ("compound:Aristolochic acid I", "target:OAT1/OAT3", "transported_by"),
    ("target:OAT1/OAT3", "indication:Urothelial carcinoma", "implicated_in"),
    ("taxon:Akebia quinata", "compound:Akeboside", "contains"),
    ("drug:三七", "taxon:Panax notoginseng", "resolves_to"),
    ("drug:三七", "taxon:Gynura pseudochina", "resolves_to"),
    ("taxon:Gynura pseudochina", "compound:Pyrrolizidine alkaloids", "contains"),
    ("compound:Pyrrolizidine alkaloids", "target:CYP3A4", "bioactivated_by"),
    ("target:CYP3A4", "indication:Hepatic sinusoidal obstruction", "implicated_in"),
    ("taxon:Panax notoginseng", "compound:Notoginsenoside R1", "contains"),
    ("taxon:Aconitum carmichaelii", "drug:附子", "provides"),
    ("drug:附子", "process:炮", "processed_by"),
    ("process:炮", "process:蜜水煮", "followed_by"),
    ("process:蜜水煮", "compound:Aconine", "yields"),
    ("drug:附子", "compound:Aconitine", "contains"),
    ("compound:Aconitine", "target:NaV channel", "binds"),
    ("compound:Benzoylaconine", "target:NaV channel", "binds_weakly"),
    ("compound:Aconine", "target:NaV channel", "binds_weakly"),
    ("compound:Aconitine", "compound:Benzoylaconine", "hydrolyses_to"),
    ("compound:Benzoylaconine", "compound:Aconine", "hydrolyses_to"),
    ("taxon:Polygonum multiflorum", "drug:何首烏", "provides"),
    ("drug:何首烏", "process:九蒸九曬", "processed_by"),
    ("process:九蒸九曬", "compound:TSG", "reduces"),
    ("compound:TSG", "target:Hepatocyte mitochondrion", "injures"),
    ("target:Hepatocyte mitochondrion", "indication:Herb-induced liver injury", "implicated_in"),
    ("drug:甘草", "drug:甘遂", "incompatible_18fan"),
    ("drug:附子", "drug:半夏", "incompatible_18fan"),
    ("drug:甘草", "drug:海藻", "incompatible_18fan"),
    ("drug:水銀", "drug:砒霜", "incompatible_19wei"),
    ("drug:丁香", "drug:鬱金", "incompatible_19wei"),
    ("taxon:Glycyrrhiza uralensis", "drug:甘草", "provides"),
    ("drug:甘草", "compound:Glycyrrhizin", "contains"),
    ("compound:Glycyrrhizin", "compound:Glycyrrhetinic acid", "metabolised_to"),
    ("compound:Glycyrrhetinic acid", "target:11b-HSD2", "inhibits"),
    ("compound:Glycyrrhetinic acid", "target:P-gp", "modulates"),
    ("taxon:Euphorbia kansui", "drug:甘遂", "provides"),
    ("drug:甘遂", "compound:Kansuinin A", "contains"),
    ("compound:Kansuinin A", "target:P-gp", "substrate"),
    ("target:11b-HSD2", "indication:Hypertension", "implicated_in"),
    ("formula:四逆湯", "drug:附子", "jun"),
    ("formula:四逆湯", "drug:甘草", "chen"),
    ("formula:四逆湯", "drug:乾薑", "zuo"),
    ("formula:麻黃湯", "drug:麻黃", "jun"),
    ("formula:麻黃湯", "drug:桂枝", "chen"),
    ("formula:麻黃湯", "drug:杏仁", "zuo"),
    ("formula:麻黃湯", "drug:甘草", "shi"),
    ("formula:參蘇飲", "drug:人參", "jun"),
    ("formula:參蘇飲", "drug:紫蘇", "chen"),
    ("drug:胡椒", "role:使", "annotated_as"),
    ("drug:甘草", "role:使", "annotated_as"),
    ("taxon:Piper longum", "drug:胡椒", "provides"),
    ("drug:胡椒", "compound:Piperine", "contains"),
    ("compound:Piperine", "target:CYP3A4", "inhibits"),
    ("compound:Piperine", "target:P-gp", "modulates"),
    ("role:使", "target:P-gp", "predicts"),
    ("taxon:Ranunculus ternatus", "drug:貓爪草", "provides"),
    ("drug:貓爪草", "indication:瘰癧 scrofula", "used_for"),
    ("taxon:Scutellaria barbata", "drug:半枝蓮", "provides"),
    ("drug:半枝蓮", "compound:Scutellarein", "contains"),
    ("drug:半枝蓮", "indication:Colorectal cancer (adjunct)", "used_for"),
    ("drug:犀角", "drug:水牛角", "substituted_by"),
    ("drug:犀角", "taxon:Rhinoceros", "sourced_from"),
    ("drug:水牛角", "taxon:Bubalus bubalis", "sourced_from"),
    ("drug:穿山甲", "drug:豬蹄甲", "substituted_by"),
    ("drug:穿山甲", "taxon:Manis pentadactyla", "sourced_from"),
    ("drug:穿山甲", "process:煅", "processed_by"),
    ("taxon:Rhinoceros", "cite:CITES Appendix I", "listed_in"),
    ("taxon:Manis pentadactyla", "cite:CITES Appendix I", "listed_in"),
    ("taxon:Juglans regia", "drug:核桃仁", "provides"),
    ("drug:核桃仁", "indication:Memory (by resemblance)", "used_for"),
    ("source:fx_shennong_bencao", "drug:甘草", "attests"),
    ("source:fx_shennong_bencao", "drug:附子", "attests"),
    ("source:fx_bencao_gangmu", "drug:木通", "attests"),
    ("source:fx_bencao_gangmu", "drug:三七", "attests"),
    ("source:fx_bencao_gangmu", "drug:何首烏", "attests"),
    ("source:fx_bencao_gangmu", "drug:穿山甲", "attests"),
    ("source:fx_bencao_gangmu", "drug:犀角", "attests"),
    ("source:fx_leigong_paozhi", "process:炮", "describes"),
    ("source:fx_leigong_paozhi", "process:九蒸九曬", "describes"),
    ("source:fx_ru-men-shi-qin", "drug:甘草", "asserts_incompatibility"),
    ("source:fx_shanghanlun", "formula:麻黃湯", "prescribes"),
    ("source:fx_shanghanlun", "formula:四逆湯", "prescribes"),
    ("source:fx_taiping_huimin", "formula:參蘇飲", "prescribes"),
    ("source:fx_baopuzi", "drug:水銀", "attests"),
    ("source:fx_rasa_ratna", "process:煅", "describes"),
    ("source:fx_charaka", "concept:ṣaḍrasa", "defines"),
    ("source:fx_huangdi_neijing", "concept:取象比類", "grounds"),
    ("source:fx_gbif", "taxon:Rhinoceros", "lists"),
    ("source:fx_gbif", "taxon:Manis pentadactyla", "lists"),
    ("source:fx_chembl", "compound:Piperine", "assays"),
    ("concept:取象比類", "drug:核桃仁", "explains"),
    ("concept:ṣaḍrasa", "indication:Memory (by resemblance)", "predicts_weakly"),
]

NODE_TYPE_HINT = {"taxon": "taxon", "drug": "drug", "compound": "compound", "target": "target",
                  "indication": "indication", "process": "process", "formula": "formula",
                  "source": "source", "concept": "concept", "role": "concept", "cite": "concept"}


def build_kg():
    nodes: dict = {}

    def add(nid, label=None, ntype=None, weight=0.0):
        if nid in nodes:
            nodes[nid]["weight"] = max(nodes[nid]["weight"], weight)
            return
        prefix, _, rest = nid.partition(":")
        nodes[nid] = dict(id=nid, label=label or rest, type=ntype or NODE_TYPE_HINT.get(prefix, "compound"),
                          weight=weight)

    for s in SOURCES:
        if s["status"] != "ok":
            continue
        add(f"source:{s['id']}", s["title"], "source", 0.45)
    for a, b, rel in KG_EXTRA:
        add(a)
        add(b)
        edges_i.append((a, b, rel))

    edges, seen = [], set()
    for a, b, rel in edges_i:
        if a not in nodes or b not in nodes:
            continue
        if (a, b, rel) in seen:
            continue
        seen.add((a, b, rel))
        edges.append(dict(source=a, target=b, rel=rel, weight=1.0))
    return nodes, edges


def layout(nodes, edges, w=1240.0, hgt=840.0, iters=540, seed=11):
    rnd = random.Random(seed)
    ids = list(nodes)
    n = len(ids)
    pos = {}
    for i, nid in enumerate(ids):
        t = 2 * math.pi * i / n
        pos[nid] = [w / 2 + (w / 3) * math.cos(t) * (0.7 + 0.6 * rnd.random()),
                    hgt / 2 + (hgt / 3) * math.sin(t) * (0.7 + 0.6 * rnd.random())]
    adj = [(e["source"], e["target"]) if isinstance(e, dict) else (e[0], e[1]) for e in edges]
    adj = [(a, b) for a, b in adj if a in pos and b in pos]
    k = math.sqrt(w * hgt / max(n, 1))
    t0 = k * 1.9
    for it in range(iters):
        disp = {i: [0.0, 0.0] for i in ids}
        for i in range(n):
            for j in range(i + 1, n):
                a, b = ids[i], ids[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d2 = dx * dx + dy * dy
                if d2 < 1e-6:
                    dx, dy, d2 = rnd.random() - 0.5, rnd.random() - 0.5, 1e-6
                d = math.sqrt(d2)
                f = k * k / d
                ux, uy = dx / d, dy / d
                disp[a][0] += ux * f
                disp[a][1] += uy * f
                disp[b][0] -= ux * f
                disp[b][1] -= uy * f
        for a, b in adj:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = max(math.sqrt(dx * dx + dy * dy), 1e-6)
            f = d * d / k
            ux, uy = dx / d, dy / d
            disp[a][0] -= ux * f
            disp[a][1] -= uy * f
            disp[b][0] += ux * f
            disp[b][1] += uy * f
        temp = t0 * (1 - it / iters) ** 1.6
        for nid in ids:
            dx, dy = disp[nid]
            d = max(math.sqrt(dx * dx + dy * dy), 1e-6)
            step = min(d, temp)
            pos[nid][0] += dx / d * step
            pos[nid][1] += dy / d * step
            pos[nid][0] += (w / 2 - pos[nid][0]) * 0.005
            pos[nid][1] += (hgt / 2 - pos[nid][1]) * 0.005
    return {nid: [round(min(max(pos[nid][0], 40), w - 40), 1),
                  round(min(max(pos[nid][1], 40), hgt - 40), 1)] for nid in ids}


def write(name, obj):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {path}  ({os.path.getsize(path):,} bytes)")


def main():
    ranked = sorted(H, key=lambda h: (h["is_control"], -h["scores"]["composite"], -h["scores"]["novelty"]))
    for i, h in enumerate(ranked, 1):
        h["rank"] = i

    by_class: dict = {}
    for h in ranked:
        by_class[h["discovery_class"]] = by_class.get(h["discovery_class"], 0) + 1

    write("hypotheses.json", dict(
        generated_at=GENERATED_AT, fixture=True,
        note="DEMO FIXTURE — invented scores and fixture corpus counts, for UI development only. "
             "Replaced by `python -m shennong.cli shi --out app/data/hypotheses.json`.",
        pipeline="采 Cǎi → 制 Zhì → 配 Pèi → 使 Shǐ",
        corpus=dict(sources=sum(1 for s in SOURCES if s["status"] == "ok"),
                    chars=sum(s["chars"] for s in SOURCES), tokens=0,
                    languages={"zh-Hant": 17, "sa": 5, "ar": 2, "sa-Latn": 1, "ko": 1, "en": 5, "bo": 1},
                    traditions={"tcm": 12, "alchemy": 4, "acupuncture": 3, "ayurveda": 6, "unani": 2,
                                "korean": 2, "tibetan": 1, "foundational": 4, "comparative-control": 1}),
        by_class=by_class, hypotheses=ranked))

    write("passages.json", dict(
        generated_at=GENERATED_AT, fixture=True,
        note="DEMO FIXTURE — Classical Chinese lines are verbatim from public-domain editions; all other "
             "passages are modern-English paraphrases and labelled span_kind.",
        passages=PASSAGES))

    nodes, edges = build_kg()
    write("kg.json", dict(generated_at=GENERATED_AT, fixture=True, nodes=list(nodes.values()),
                          edges=edges, layout=layout(nodes, edges)))

    write("corpus.json", dict(
        generated_at=GENERATED_AT, fixture=True,
        sources=[{k: s[k] for k in ("id", "title", "title_en", "author", "year", "tradition", "lang",
                                    "tier", "licence", "url", "chars", "status")} for s in SOURCES],
        built=dict(fetched=len(SOURCES), kept=sum(1 for s in SOURCES if s["status"] == "ok"),
                   excluded=sum(1 for s in SOURCES if s["status"] != "ok"),
                   chars=sum(s["chars"] for s in SOURCES)),
        stages=[
            dict(stage="cai", cn="采", label="Licence-audited acquisition",
                 detail="one registry entry per source: provenance, licence + evidence, tier, tradition, language"),
            dict(stage="cai2", cn="采", label="Normalise · 繁/简 · NFC",
                 detail="Han variant folding, IAST↔Devanagari, Arabic transliteration; ≥100 chars/record for CJK"),
            dict(stage="cai3", cn="采", label="13-gram dedupe",
                 detail="removes boilerplate and parallel editions of the same text"),
            dict(stage="zhi", cn="制", label="Entity extraction · drug-name resolution",
                 detail="異名 → modern taxon with confidence; process terms → modern chemistry"),
            dict(stage="pei", cn="配", label="Knowledge graph assembly",
                 detail="taxon ↔ compound ↔ target ↔ indication, formula roles, incompatibility edges"),
            dict(stage="shi", cn="使", label="Ranked, falsifiable output",
                 detail="six discovery classes, falsification plans, negative controls, uncertainty"),
        ]))

    print(f"\n{len(ranked)} hypotheses · {len(nodes)} KG nodes · {len(edges)} edges · {len(PASSAGES)} passages")
    for h in ranked:
        print(f"  {h['rank']:>2}. {h['id']}  {h['scores']['composite']:.3f}  "
              f"nov {h['scores']['novelty']:.2f}  {h['discovery_class']}")


if __name__ == "__main__":
    main()
