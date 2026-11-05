"""Curated source manifest for the SHENNONG corpus.

Every entry is a source we have actually verified is reachable and whose licence we can
state with evidence. Nothing here is added "because it would be nice": if a work could not
be fetched or its licence is unclear it is absent (or explicitly ``status: unverified``).

Fields follow PROJECT_BRIEF.md §10.1. Fetcher-specific keys (``ws_lang``/``ws_page``/``gid``/
``identifier``) are consumed by the corresponding fetcher and then dropped from the registry.

Tier / tradition vocabulary (brief §5, §10.1):
  tier 1 foundational biology+chemistry · 2 Asian materia medica · 3 Asian alchemy
  tier 4 acupuncture/channels · 5 structured open data

Licence notes, honestly stated
-----------------------------
* Wikisource (zh/sa): the *works* are PD-old (authors dead >100 years). The Wiki* project
  releases its transcription under CC BY-SA 4.0 (zh.wikisource copyright page verified
  2026-11-05). We therefore label the transcription CC-BY-SA-4.0 and attribute the project.
* Project Gutenberg: public domain in the US; PG licence page.
* Internet Archive: all items below were published before 1929 -> US public domain. The item
  page is cited as evidence; IA itself attaches no separate licence to these scans.
* GRETIL is CC BY-NC-SA 4.0 (non-commercial) -> deliberately NOT in the training manifest;
  cited in LICENSE_AUDIT.md as reference-only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# shared licence evidence
# ---------------------------------------------------------------------------
# zh.wikisource copyright policy page (verified 2026-11-05: text released CC BY-SA 4.0 + GFDL).
L_WS_ZH = "https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF"
# sa.wikisource has no local Copyrights page; every page footer links to this deed
# (verified on the चरकसंहिता page footer 2026-11-05).
L_WS_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
L_PG = "https://www.gutenberg.org/policy/license.html"
L_PD_CHART = "https://guides.library.cornell.edu/copyright/publicdomain"


def _ws(lang, page, **kw):
    """Wikisource entry factory."""
    e = {
        "kind": "wikisource",
        "ws_lang": lang,
        "ws_page": page,
        "lang": "zh-Hant" if lang == "zh" else "sa",
        "licence": "CC-BY-SA-4.0",
        "licence_evidence": L_WS_ZH if lang == "zh" else L_WS_SA,
        "licence_note": ("Underlying work is PD-old (author dead >100 y); the Wikisource "
                         "transcription is released CC BY-SA 4.0 and is attributed here."),
        "status": "ok",
    }
    e.update(kw)
    return e


def _pg(gid, **kw):
    e = {
        "kind": "gutenberg",
        "gid": gid,
        "licence": "Public Domain",
        "licence_evidence": L_PG,
        "licence_note": "Project Gutenberg public-domain text (US).",
        "status": "ok",
    }
    e.update(kw)
    return e


def _ia(identifier, **kw):
    e = {
        "kind": "archive",
        "identifier": identifier,
        "licence": "Public Domain",
        "licence_evidence": f"https://archive.org/details/{identifier}",
        "licence_note": "Published before 1929; public domain in the United States "
                        "(" + L_PD_CHART + ").",
        "status": "ok",
    }
    e.update(kw)
    return e


# ---------------------------------------------------------------------------
# TIER 2/3/4 — Classical Chinese canon (zh.wikisource)
# ---------------------------------------------------------------------------
ZH = [
    # --- bencao / materia medica -------------------------------------------
    _ws("zh", "神農本草經", id="ws_zh_shennong_bencaojing",
        title="神農本草經", title_en="Shennong Bencao Jing (Divine Farmer's Materia Medica)",
        author="神農 Shennong (attrib.)", year=200, tradition="tcm", tier=2),
    _ws("zh", "本草綱目", id="ws_zh_bencao_gangmu",
        title="本草綱目", title_en="Bencao Gangmu (Compendium of Materia Medica)",
        author="李時珍 Li Shizhen", year=1596, tradition="tcm", tier=2),
    _ws("zh", "本草經集注", id="ws_zh_bencao_jingjizhu",
        title="本草經集注", title_en="Bencao Jing Jizhu (Collected Commentaries on the Materia Medica)",
        author="陶弘景 Tao Hongjing", year=500, tradition="tcm", tier=2),
    _ws("zh", "新修本草", id="ws_zh_xinxiu_bencao",
        title="新修本草", title_en="Xinxiu Bencao (Newly Revised Materia Medica)",
        author="蘇敬 Su Jing et al.", year=659, tradition="tcm", tier=2),
    _ws("zh", "證類本草", id="ws_zh_zhenglei_bencao",
        title="證類本草", title_en="Zhenglei Bencao (Classified Materia Medica)",
        author="唐慎微 Tang Shenwei", year=1082, tradition="tcm", tier=2),
    _ws("zh", "本草備要", id="ws_zh_bencao_beiyao",
        title="本草備要", title_en="Bencao Beiyao (Essentials of Materia Medica)",
        author="汪昂 Wang Ang", year=1694, tradition="tcm", tier=2),
    _ws("zh", "本草從新", id="ws_zh_bencao_congxin",
        title="本草從新", title_en="Bencao Congxin (New Materia Medica)",
        author="吳儀洛 Wu Yiluo", year=1757, tradition="tcm", tier=2),
    _ws("zh", "本草求真", id="ws_zh_bencao_qiuzhen",
        title="本草求真", title_en="Bencao Qiuzhen (Seeking the Truth of Materia Medica)",
        author="黃宮繡 Huang Gongxiu", year=1769, tradition="tcm", tier=2),
    _ws("zh", "本草綱目拾遺", id="ws_zh_bencao_gangmu_shiyi",
        title="本草綱目拾遺", title_en="Bencao Gangmu Shiyi (Supplement to the Compendium)",
        author="趙學敏 Zhao Xuemin", year=1765, tradition="tcm", tier=2),
    _ws("zh", "本經疏證", id="ws_zh_benjing_shuzheng",
        title="本經疏證", title_en="Benjing Shuzheng (Evidential Commentary on the Classic of Materia Medica)",
        author="鄒澍 Zou Shu", year=1832, tradition="tcm", tier=2),
    _ws("zh", "本草崇原", id="ws_zh_bencao_chongyuan",
        title="本草崇原", title_en="Bencao Chongyuan (Reverting to the Source of Materia Medica)",
        author="張志聰 Zhang Zhicong", year=1674, tradition="tcm", tier=2),
    _ws("zh", "湯液本草", id="ws_zh_tangye_bencao",
        title="湯液本草", title_en="Tangye Bencao (Decoction Materia Medica)",
        author="王好古 Wang Haogu", year=1289, tradition="tcm", tier=2),
    _ws("zh", "藥性賦", id="ws_zh_yaoxing_fu",
        title="珍珠囊補遺藥性賦", title_en="Yaoxing Fu (Rhapsody on Drug Properties)",
        author="李杲 Li Gao (attrib.)", year=1300, tradition="tcm", tier=2),
    _ws("zh", "食療本草", id="ws_zh_shiliao_bencao",
        title="食療本草", title_en="Shiliao Bencao (Dietetic Materia Medica)",
        author="孟詵 Meng Shen", year=700, tradition="tcm", tier=2),
    _ws("zh", "海藥本草", id="ws_zh_haiyao_bencao",
        title="海藥本草", title_en="Haiyao Bencao (Materia Medica of Overseas Drugs)",
        author="李珣 Li Xun", year=800, tradition="tcm", tier=2),
    # --- clinical / formulary ----------------------------------------------
    _ws("zh", "傷寒論", id="ws_zh_shanghanlun",
        title="傷寒論", title_en="Shanghan Lun (Treatise on Cold Damage)",
        author="張仲景 Zhang Zhongjing", year=220, tradition="tcm", tier=2),
    _ws("zh", "金匱要略", id="ws_zh_jingui_yaolue",
        title="金匱要略", title_en="Jingui Yaolue (Essential Prescriptions of the Golden Coffer)",
        author="張仲景 Zhang Zhongjing", year=220, tradition="tcm", tier=2),
    _ws("zh", "千金翼方", id="ws_zh_qianjin_yifang",
        title="千金翼方", title_en="Qianjin Yifang (Supplement to the Thousand Ducat Formulas)",
        author="孫思邈 Sun Simiao", year=682, tradition="tcm", tier=2),
    _ws("zh", "外臺秘要", id="ws_zh_waitai_miyao",
        title="外臺秘要", title_en="Waitai Miyao (Secret Essentials from the Imperial Library)",
        author="王燾 Wang Tao", year=752, tradition="tcm", tier=2),
    _ws("zh", "太平惠民和劑局方", id="ws_zh_taiping_huimin_ju",
        title="太平惠民和劑局方", title_en="Taiping Huimin Heji Ju Fang (Imperial Pharmacy Formulas)",
        author="陳師文 Chen Shiwen et al.", year=1078, tradition="tcm", tier=2),
    _ws("zh", "普濟方", id="ws_zh_pujifang",
        title="普濟方", title_en="Pujifang (Formulas for Universal Relief)",
        author="朱橚 Zhu Su", year=1406, tradition="tcm", tier=2),
    _ws("zh", "溫病條辨", id="ws_zh_wenbing_tiaobian",
        title="溫病條辨", title_en="Wenbing Tiaobian (Systematic Differentiation of Warm Diseases)",
        author="吳鞠通 Wu Jutong", year=1798, tradition="tcm", tier=2),
    _ws("zh", "丹溪心法", id="ws_zh_danxi_xinfa",
        title="丹溪心法", title_en="Danxi Xinfa (Danxi's Heart Method)",
        author="朱震亨 Zhu Zhenheng", year=1481, tradition="tcm", tier=2),
    _ws("zh", "醫方集解", id="ws_zh_yifang_jijie",
        title="醫方集解", title_en="Yifang Jijie (Collected Explanations of Formulas)",
        author="汪昂 Wang Ang", year=1682, tradition="tcm", tier=2),
    _ws("zh", "景岳全書", id="ws_zh_jingyue_quanshu",
        title="景岳全書", title_en="Jingyue Quanshu (Complete Works of Jingyue)",
        author="張介賓 Zhang Jiebin", year=1624, tradition="tcm", tier=2),
    _ws("zh", "諸病源候論", id="ws_zh_zhu_bing_yuanhou",
        title="諸病源候論", title_en="Zhubing Yuanhou Lun (Treatise on the Origins and Symptoms of Diseases)",
        author="巢元方 Chao Yuanfang", year=610, tradition="tcm", tier=2),
    _ws("zh", "脈經", id="ws_zh_maijing",
        title="脈經", title_en="Maijing (Classic of the Pulse)",
        author="王叔和 Wang Shuhe", year=280, tradition="tcm", tier=2),
    _ws("zh", "肘後備急方", id="ws_zh_zhouhou_beiji",
        title="肘後備急方", title_en="Zhouhou Beiji Fang (Emergency Formulas Kept in the Sleeve)",
        author="葛洪 Ge Hong", year=340, tradition="tcm", tier=2),
    # --- Korean -------------------------------------------------------------
    _ws("zh", "東醫寶鑑", id="ws_zh_dongui_bogam",
        title="東醫寶鑑", title_en="Dongui Bogam (Mirror of Eastern Medicine)",
        author="許浚 Heo Jun", year=1613, tradition="korean", tier=2),
    # --- Tier 3: Asian alchemy / esoteric pharmacy --------------------------
    _ws("zh", "雷公炮炙論", id="ws_zh_leigong_paozhi",
        title="雷公炮炙論", title_en="Leigong Paozhi Lun (Master Lei's Treatise on Processing)",
        author="雷斅 Lei Xiao", year=470, tradition="alchemy", tier=3),
    _ws("zh", "抱朴子", id="ws_zh_baopuzi",
        title="抱朴子", title_en="Baopuzi (Master Who Embraces Simplicity)",
        author="葛洪 Ge Hong", year=320, tradition="alchemy", tier=3),
    _ws("zh", "周易參同契", id="ws_zh_cantong_qi",
        title="周易參同契", title_en="Zhouyi Cantong qi (Seal of the Unity of the Three)",
        author="魏伯陽 Wei Boyang", year=142, tradition="alchemy", tier=3),
    _ws("zh", "雲笈七籤", id="ws_zh_yunji_qiqian",
        title="雲笈七籤", title_en="Yunji Qiqian (Seven Lots from the Bookbag of the Clouds)",
        author="張君房 Zhang Junfang", year=1029, tradition="alchemy", tier=3),
    _ws("zh", "悟真篇", id="ws_zh_wuzhen_pian",
        title="悟真篇", title_en="Wuzhen Pian (Chapters on Awakening to Truth)",
        author="張伯端 Zhang Boduan", year=1075, tradition="alchemy", tier=3),
    _ws("zh", "太乙金華宗旨", id="ws_zh_taiyi_jinhua",
        title="太乙金華宗旨", title_en="Taiyi Jinhua Zongzhi (Secret of the Golden Flower)",
        author="attrib. 呂洞賓 Lü Dongbin", year=1670, tradition="alchemy", tier=3),
    # --- Tier 4: acupuncture & channels ------------------------------------
    _ws("zh", "黃帝內經", id="ws_zh_huangdi_neijing",
        title="黃帝內經", title_en="Huangdi Neijing (Inner Canon of the Yellow Emperor)",
        author="attrib. 黃帝 Yellow Emperor", year=-200, tradition="acupuncture", tier=4),
    _ws("zh", "難經", id="ws_zh_nanjing",
        title="難經", title_en="Nanjing (Classic of Difficult Issues)",
        author="attrib. 扁鵲 Bian Que", year=200, tradition="acupuncture", tier=4),
    _ws("zh", "針灸甲乙經", id="ws_zh_zhenjiu_jiayi",
        title="針灸甲乙經", title_en="Zhenjiu Jiayi Jing (Systematic Classic of Acupuncture and Moxibustion)",
        author="皇甫謐 Huangfu Mi", year=282, tradition="acupuncture", tier=4),
    _ws("zh", "針灸大成", id="ws_zh_zhenjiu_dacheng",
        title="針灸大成", title_en="Zhenjiu Dacheng (Great Compendium of Acupuncture and Moxibustion)",
        author="楊繼洲 Yang Jizhou", year=1601, tradition="acupuncture", tier=4),
]

# ---------------------------------------------------------------------------
# TIER 2/3 — Sanskrit Ayurveda and rasaśāstra (sa.wikisource, Devanagari)
# ---------------------------------------------------------------------------
SA = [
    _ws("sa", "चरकसंहिता", id="ws_sa_carakasamhita",
        title="चरकसंहिता", title_en="Caraka Saṃhitā",
        author="Agniveśa / Caraka", year=200, tradition="ayurveda", tier=2),
    _ws("sa", "सुश्रुतसंहिता", id="ws_sa_sushrutasamhita",
        title="सुश्रुतसंहिता", title_en="Suśruta Saṃhitā",
        author="Suśruta", year=400, tradition="ayurveda", tier=2),
    _ws("sa", "अष्टाङ्गहृदयम्", id="ws_sa_ashtangahridaya",
        title="अष्टाङ्गहृदयम्", title_en="Aṣṭāṅgahṛdaya",
        author="Vāgbhaṭa", year=650, tradition="ayurveda", tier=2),
    _ws("sa", "भावप्रकाशः", id="ws_sa_bhavaprakasha",
        title="भावप्रकाशः", title_en="Bhāvaprakāśa",
        author="Bhāvamiśra", year=1600, tradition="ayurveda", tier=2),
    _ws("sa", "शार्ङ्गधरसंहिता", id="ws_sa_sharngadharasamhita",
        title="शार्ङ्गधरसंहिता", title_en="Śārṅgadhara Saṃhitā",
        author="Śārṅgadhara", year=1350, tradition="ayurveda", tier=2),
    _ws("sa", "माधवनिदानम्", id="ws_sa_madhavanidana",
        title="माधवनिदानम्", title_en="Mādhava Nidāna (Rugvinischaya)",
        author="Mādhavakara", year=700, tradition="ayurveda", tier=2),
    _ws("sa", "रसहृदयतन्त्रम्", id="ws_sa_rasahridaya",
        title="रसहृदयतन्त्रम्", title_en="Rasa Hṛdaya Tantra",
        author="Govindabhagavatpāda", year=1300, tradition="alchemy", tier=3),
    _ws("sa", "रसार्णवः", id="ws_sa_rasarnava",
        title="रसार्णवः", title_en="Rasārṇava",
        author="attrib.", year=1100, tradition="alchemy", tier=3),
]

# ---------------------------------------------------------------------------
# TIER 1 — foundational biology / chemistry / pharmacology (English, Gutenberg)
# ---------------------------------------------------------------------------
PG = [
    _pg(64754, id="pg_structure_functions_body",
        title="Structure and Functions of the Body: A Handbook of Anatomy and Physiology",
        title_en="Structure and Functions of the Body",
        author="Annette Fiske", year=1911, tradition="foundational", tier=1, lang="en"),
    _pg(15491, id="pg_micrographia",
        title="Micrographia", title_en="Micrographia",
        author="Robert Hooke", year=1665, tradition="foundational", tier=1, lang="en"),
    _pg(33757, id="pg_gray_elements_botany",
        title="The Elements of Botany, For Beginners and For Schools",
        title_en="The Elements of Botany",
        author="Asa Gray", year=1836, tradition="foundational", tier=1, lang="en"),
    _pg(20390, id="pg_campbell_structural_botany",
        title="Elements of Structural and Systematic Botany",
        title_en="Elements of Structural and Systematic Botany",
        author="Douglas Houghton Campbell", year=1890, tradition="foundational", tier=1, lang="en"),
    _pg(64601, id="pg_atkinson_elementary_botany",
        title="Elementary Botany", title_en="Elementary Botany",
        author="George Francis Atkinson", year=1905, tradition="foundational", tier=1, lang="en"),
    _pg(1234, id="pg_organic_syntheses_v1",
        title="Organic Syntheses", title_en="Organic Syntheses, Vol. 1",
        author="Editorial Board", year=1921, tradition="foundational", tier=1, lang="en"),
    _pg(29842, id="pg_histology_blood",
        title="Histology of the Blood, Normal and Pathological",
        title_en="Histology of the Blood",
        author="Paul Ehrlich and Adolf Lazarus", year=1900, tradition="foundational", tier=1, lang="en"),
    _pg(65569, id="pg_histology_medicinal_plants",
        title="Histology of Medicinal Plants", title_en="Histology of Medicinal Plants",
        author="William James Mansfield", year=1916, tradition="foundational", tier=1, lang="en"),
    _pg(67691, id="pg_pharmacographia",
        title="Pharmacographia: A History of the Principal Drugs of Vegetable Origin",
        title_en="Pharmacographia",
        author="Friedrich A. Flückiger and Daniel Hanbury", year=1879,
        tradition="foundational", tier=1, lang="en"),
    _pg(1228, id="pg_origin_of_species",
        title="On the Origin of Species By Means of Natural Selection",
        title_en="On the Origin of Species",
        author="Charles Darwin", year=1859, tradition="foundational", tier=1, lang="en"),
    _pg(69362, id="pg_mendel_heredity",
        title="Mendel's Principles of Heredity: A Defence",
        title_en="Mendel's Principles of Heredity",
        author="William Bateson", year=1902, tradition="foundational", tier=1, lang="en"),
    _pg(43227, id="pg_fundamentals_bacteriology",
        title="The Fundamentals of Bacteriology", title_en="The Fundamentals of Bacteriology",
        author="Charles Bradfield Morrey", year=1912, tradition="foundational", tier=1, lang="en"),
    _pg(4962, id="pg_story_germ_life",
        title="The Story of Germ Life", title_en="The Story of Germ Life",
        author="H. W. Conn", year=1897, tradition="foundational", tier=1, lang="en"),
    _pg(1566, id="pg_evolution_modern_medicine",
        title="The Evolution of Modern Medicine", title_en="The Evolution of Modern Medicine",
        author="Sir William Osler", year=1913, tradition="foundational", tier=1, lang="en"),
    _pg(24886, id="pg_withering_foxglove",
        title="An Account of the Foxglove and some of its Medical Uses",
        title_en="An Account of the Foxglove",
        author="William Withering", year=1785, tradition="foundational", tier=1, lang="en"),
    _pg(30541, id="pg_cutter_anatomy_physiology",
        title="A Treatise on Anatomy, Physiology, and Hygiene",
        title_en="A Treatise on Anatomy, Physiology, and Hygiene",
        author="Calvin Cutter", year=1884, tradition="foundational", tier=1, lang="en"),
]

# ---------------------------------------------------------------------------
# TIER 2 — Asian materia medica in English translation (Gutenberg, PD)
# ---------------------------------------------------------------------------
PG_ASIAN = [
    _pg(50985, id="pg_churchill_acupuncturation",
        title="A Treatise on Acupuncturation", title_en="A Treatise on Acupuncturation",
        author="James Morss Churchill", year=1821, tradition="acupuncture", tier=4, lang="en"),
    _pg(53755, id="pg_taleef_shereef",
        title="The Taleef Shereef; Or, Indian Materia Medica",
        title_en="The Taleef Shereef (Indian Materia Medica)",
        author="trans. George Playfair", year=1833, tradition="unani", tier=2, lang="en"),
    _pg(58525, id="pg_waring_bazaar_medicines",
        title="Remarks on the Uses of some of the Bazaar Medicines and Common Medical Plants of India",
        title_en="Bazaar Medicines and Common Medical Plants of India",
        author="Edward John Waring", year=1867, tradition="ayurveda", tier=2, lang="en"),
]

# ---------------------------------------------------------------------------
# TIER 1/2 — Internet Archive (PD editions): Asian materia medica + foundational science
# ---------------------------------------------------------------------------
IA = [
    # Asian materia medica
    _ia("BIUSante_00095", id="ia_avicenna_canon_latin_1593",
        title="Canon medicinae (Latin, 1593 Venice)", title_en="Avicenna, Canon of Medicine (Latin)",
        author="Ibn Sīnā (Avicenna)", year=1593, tradition="unani", tier=2, lang="la"),
    _ia("materiamedicahi00kinggoog", id="ia_dutt_materia_medica_hindus",
        title="The Materia Medica of the Hindus, compiled from Sanskrit medical works",
        title_en="Materia Medica of the Hindus",
        author="Uday Chand Dutt; George King", year=1877, tradition="ayurveda", tier=2, lang="en"),
    _ia("englishtranslati00susruoft", id="ia_bhishagratna_sushruta",
        title="An English Translation of the Sushruta Samhita",
        title_en="Suśruta Saṃhitā (English translation)",
        author="Suśruta; trans. Kunja Lal Bhishagratna", year=1907,
        tradition="ayurveda", tier=2, lang="en"),
    _ia("chinesemateriame00stuauoft", id="ia_stuart_chinese_materia_medica",
        title="Chinese Materia Medica: Vegetable Kingdom",
        title_en="Chinese Materia Medica",
        author="G. A. Stuart; F. Porter Smith", year=1911, tradition="tcm", tier=2, lang="en"),
    _ia("indianmedicinalp02kirt", id="ia_kirtikar_indian_medicinal_plants_2",
        title="Indian Medicinal Plants (vol. 2)",
        title_en="Indian Medicinal Plants",
        author="K. R. Kirtikar; B. D. Basu", year=1918, tradition="ayurveda", tier=2, lang="en"),
    _ia("b31359644_0002", id="ia_kirtikar_indian_medicinal_plants_b",
        title="Indian Medicinal Plants (vol. 2, alt. scan)",
        title_en="Indian Medicinal Plants",
        author="K. R. Kirtikar; B. D. Basu", year=1918, tradition="ayurveda", tier=2, lang="en"),
    _ia("notesonchinesem00hanbgoog", id="ia_hanbury_chinese_materia_medica",
        title="Notes on Chinese Materia Medica",
        title_en="Notes on Chinese Materia Medica",
        author="Daniel Hanbury", year=1862, tradition="tcm", tier=2, lang="en"),
    # foundational science
    _ia("textbookofpharma00cush", id="ia_cushny_pharmacology",
        title="A Text-book of Pharmacology and Therapeutics",
        title_en="A Text-book of Pharmacology and Therapeutics",
        author="Arthur R. Cushny", year=1899, tradition="foundational", tier=1, lang="en"),
    _ia("textbookofphysio00abderich", id="ia_abderhalden_physiological_chemistry",
        title="Text-book of Physiological Chemistry in Thirty Lectures",
        title_en="Text-book of Physiological Chemistry",
        author="Emil Abderhalden", year=1908, tradition="foundational", tier=1, lang="en"),
    _ia("principlespharm00flgoog", id="ia_fluckiger_principles_pharmacognosy",
        title="The Principles of Pharmacognosy",
        title_en="The Principles of Pharmacognosy",
        author="Friedrich August Flückiger", year=1887, tradition="foundational", tier=1, lang="en"),
    _ia("organicmateriame0000unse", id="ia_sayre_organic_materia_medica",
        title="A Manual of Organic Materia Medica and Pharmacognosy",
        title_en="A Manual of Organic Materia Medica and Pharmacognosy",
        author="Lucius Elmer Sayre", year=1905, tradition="foundational", tier=1, lang="en"),
]

# ---------------------------------------------------------------------------
# Reference-only (NOT trained on) -- see LICENSE_AUDIT.md
# ---------------------------------------------------------------------------
REFERENCE_ONLY = [
    {
        "id": "gretil_rasaratnasamuccaya",
        "title": "Rasaratnasamuccaya (Vāgbhaṭa)",
        "url": "http://gretil.sub.uni-goettingen.de/gretil.html",
        "licence": "CC-BY-NC-SA-4.0",
        "licence_evidence": "TEI header <licence target='https://creativecommons.org/licenses/by-nc-sa/4.0/'>",
        "reason": "Non-commercial licence: cannot be used for training, may be cited as reference.",
        "status": "unverified",
        "tier": 3,
        "tradition": "alchemy",
        "lang": "sa-Latn",
    },
]

ALL_SOURCES = ZH + SA + PG + PG_ASIAN + IA
