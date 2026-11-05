# SHENNONG — Licence Audit

Every source that has ever been considered for the SHENNONG corpus, with its licence, the
evidence for that licence, and the redistribution decision. This file is the legal companion to
`corpus/registry/sources.yaml` (the machine-readable ledger); the two are generated from the same
per-source `meta.json` sidecars, so they cannot drift apart in content.

**Summary counts** (generated from `corpus/registry/sources.yaml`):

| status | sources | meaning |
|---|---|---|
| `ok` | 105 | licence verified open/PD → redistributed and trained on |
| `unverified` | 1 | licence restricts use → **not** redistributed, **not** trained on |
| `excluded` | 3 | licence fine but text failed the quality gate → not trained on |

---

## 1. Licence families and what each obliges us to do

### 1.1 Public Domain (PD) — 24 sources
Project Gutenberg texts and Internet Archive scans first published before 1929. No copyright
restriction on redistribution in the United States (Cornell public-domain chart). We redistribute
the cleaned text and retain the source URL in the registry.

### 1.2 CC BY-SA 4.0 — 84 sources (zh.wikisource + sa.wikisource)

**This is the licence that carries an obligation, and we state it explicitly.**

- The *underlying classical works* are PD-old: every author died more than 100 years ago.
- The *transcriptions we actually download* are contributed by Wikisource volunteers and released
  by the Wikimedia Foundation under **Creative Commons Attribution-ShareAlike 4.0 International**.
  Evidence: `https://zh.wikisource.org/wiki/Wikisource:版权信息` ("本站的全部文字在知识共享 署名-相同方式共享 4.0协议之条款下提供") and the footer licence link on every `sa.wikisource.org` page
  (verified 2026-11-05).
- **ShareAlike obligation:** the derived corpus (`corpus/processed/*`) is a derivative work of
  these transcriptions and is therefore distributed **under CC BY-SA 4.0**, not under the
  repository's Apache-2.0 code licence. Attribution: "Wikisource contributors, CC BY-SA 4.0".
- **Distinction that matters for a public repo:** Apache-2.0 applies to *code* and to *model
  weights*. The **data** under `corpus/` is dual-licensed: the PD portions are PD, the
  Wikisource-derived portions are CC BY-SA 4.0. Downstream users of the corpus inherit ShareAlike;
  downstream users of the code and weights do not.

### 1.3 Unverified / restrictive — 1 source, rejected

| source | licence | evidence | decision |
|---|---|---|---|
| **GRETIL** (Göttingen Register of Electronic Texts in Indian Languages), e.g. *Rasaratnasamuccaya* | **CC BY-NC-SA 4.0** | TEI header `<licence target="https://creativecommons.org/licenses/by-nc-sa/4.0/">Distributed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.</licence>` | **REJECTED for training and redistribution.** |

**Why this rejection matters.** GRETIL is the obvious first choice for Sanskrit e-texts and was
recommended to us. Its texts are, however, licensed **NonCommercial** — a clause that would
contaminate the licence of a public, reusable corpus and of anything trained on it. We therefore:

1. did **not** download GRETIL text into `corpus/raw/`;
2. recorded the rejection here and as `status: unverified` in `sources.yaml`;
3. sourced Sanskrit instead from **sa.wikisource.org** (CC BY-SA 4.0), which has full
   Devanagari texts of the Caraka Saṃhitā, Suśruta Saṃhitā, Aṣṭāṅgahṛdaya, Bhāvaprakāśa,
   Śārṅgadhara Saṃhitā and Mādhava Nidāna.

A documented rejection is stronger evidence of rigour than another accepted source. The
Sanskrit in this corpus is **not** GRETIL-derived.

---

## 2. Per-source licence table

Legend — **R** = redistribute cleaned text, **T** = used in training, **Ref** = referenced only.

| source_id | title | year | tra-dition | lang | tier | chars | licence | decision | evidence |
|---|---|---|---|---|---|---|---|---|---|
| `ia_abderhalden_physiological_chemistry` | Text-book of Physiological Chemistry in Thirt… | 1908 | foundational | en | 1 | 1,979,606 | Public Domain | R + T | https://archive.org/details/textbookofphysio00abderich |
| `ia_cushny_pharmacology` | A Text-book of Pharmacology and Therapeutics | 1899 | foundational | en | 1 | 2,255,785 | Public Domain | R + T | https://archive.org/details/textbookofpharma00cush |
| `ia_fluckiger_principles_pharmacognosy` | The Principles of Pharmacognosy | 1887 | foundational | en | 1 | 497,969 | Public Domain | R + T | https://archive.org/details/principlespharm00flgoog |
| `ia_sayre_organic_materia_medica` | A Manual of Organic Materia Medica and Pharma… | 1905 | foundational | en | 1 | 1,519,061 | Public Domain | R + T | https://archive.org/details/organicmateriame0000unse |
| `pg_atkinson_elementary_botany` | Elementary Botany | 1905 | foundational | en | 1 | 891,036 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_campbell_structural_botany` | Elements of Structural and Systematic Botany | 1890 | foundational | en | 1 | 469,065 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_cutter_anatomy_physiology` | A Treatise on Anatomy, Physiology, and Hygiene | 1884 | foundational | en | 1 | 836,532 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_evolution_modern_medicine` | The Evolution of Modern Medicine | 1913 | foundational | en | 1 | 392,225 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_fundamentals_bacteriology` | The Fundamentals of Bacteriology | 1912 | foundational | en | 1 | 518,399 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_gray_elements_botany` | The Elements of Botany, For Beginners and For… | 1836 | foundational | en | 1 | 525,890 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_histology_blood` | Histology of the Blood, Normal and Pathological | 1900 | foundational | en | 1 | 363,152 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_histology_medicinal_plants` | Histology of Medicinal Plants | 1916 | foundational | en | 1 | 331,963 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_mendel_heredity` | Mendel's Principles of Heredity: A Defence | 1902 | foundational | en | 1 | 381,993 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_micrographia` | Micrographia | 1665 | foundational | en | 1 | 868,523 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_organic_syntheses_v1` | Organic Syntheses | 1921 | foundational | en | 1 | 136,910 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_origin_of_species` | On the Origin of Species By Means of Natural … | 1859 | foundational | en | 1 | 932,145 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_pharmacographia` | Pharmacographia: A History of the Principal D… | 1879 | foundational | en | 1 | 2,576,883 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_story_germ_life` | The Story of Germ Life | 1897 | foundational | en | 1 | 296,021 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_structure_functions_body` | Structure and Functions of the Body: A Handbo… | 1911 | foundational | en | 1 | 360,284 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_withering_foxglove` | An Account of the Foxglove and some of its Me… | 1785 | foundational | en | 1 | 270,542 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `ia_avicenna_canon_latin_1593` | Canon medicinae (Latin, 1593 Venice) | 1593 | unani | la | 2 | 2,804,522 | Public Domain | R + T | https://archive.org/details/BIUSante_00095 |
| `ia_bhishagratna_sushruta` | An English Translation of the Sushruta Samhita | 1907 | ayurveda | en | 2 | 1,373,908 | Public Domain | R + T | https://archive.org/details/englishtranslati00susruoft |
| `ia_dutt_materia_medica_hindus` | The Materia Medica of the Hindus, compiled fr… | 1877 | ayurveda | en | 2 | 607,175 | Public Domain | R + T | https://archive.org/details/materiamedicahi00kinggoog |
| `ia_hanbury_chinese_materia_medica` | Notes on Chinese Materia Medica | 1862 | tcm | en | 2 | 128,000 | Public Domain | R + T | https://archive.org/details/notesonchinesem00hanbgoog |
| `ia_kirtikar_indian_medicinal_plants_2` | Indian Medicinal Plants (vol. 2) | 1918 | ayurveda | en | 2 | 1,457,698 | Public Domain | R + T | https://archive.org/details/indianmedicinalp02kirt |
| `ia_kirtikar_indian_medicinal_plants_b` | Indian Medicinal Plants (vol. 2, alt. scan) | 1918 | ayurveda | en | 2 | 1,439,705 | Public Domain | R + T | https://archive.org/details/b31359644_0002 |
| `ia_stuart_chinese_materia_medica` | Chinese Materia Medica: Vegetable Kingdom | 1911 | tcm | en | 2 | 1,182,308 | Public Domain | R + T | https://archive.org/details/chinesemateriame00stuauoft |
| `pg_taleef_shereef` | The Taleef Shereef; Or, Indian Materia Medica | 1833 | unani | en | 2 | 399,032 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `pg_waring_bazaar_medicines` | Remarks on the Uses of some of the Bazaar Med… | 1867 | ayurveda | en | 2 | 428,621 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `ws_sa_ashtangahridaya` | अष्टाङ्गहृदयम् | 650 | ayurveda | sa | 2 | 918,482 | CC-BY-SA-4.0 | R + T | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_sa_bhavaprakasha` | भावप्रकाशः | 1600 | ayurveda | sa | 2 | 921,523 | CC-BY-SA-4.0 | R + T | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_sa_carakasamhita` | चरकसंहिता | 200 | ayurveda | sa | 2 | 201,829 | CC-BY-SA-4.0 | R + T | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_sa_madhavanidana` | माधवनिदानम् | 700 | ayurveda | sa | 2 | 151,132 | CC-BY-SA-4.0 | R + T | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_sa_sharngadharasamhita` | शार्ङ्गधरसंहिता | 1350 | ayurveda | sa | 2 | 321,849 | CC-BY-SA-4.0 | R + T | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_sa_sushrutasamhita` | सुश्रुतसंहिता | 400 | ayurveda | sa | 2 | 1,113,363 | CC-BY-SA-4.0 | R + T | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_zh_bencao_beiyao` | 本草備要 | 1694 | tcm | zh-Hans | 2 | 134,941 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_biandu` | 本草便讀 | 1887 | tcm | zh-Hans | 2 | 81,901 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_chongyuan` | 本草崇原 | 1674 | tcm | zh-Hans | 2 | 95,721 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_congxin` | 本草從新 | 1757 | tcm | zh-Hant | 2 | 173,447 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_fenjing` | 本草分經 | 1840 | tcm | zh-Hans | 2 | 65,455 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_gangmu` | 本草綱目 | 1596 | tcm | zh-Hant | 2 | 1,937,446 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_gangmu_bieninglu` | 本草綱目別名錄 | 1596 | tcm | zh-Hans | 2 | 21,092 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_gangmu_shiyi` | 本草綱目拾遺 | 1765 | tcm | zh-Hant | 2 | 267,572 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_haili` | 本草害利 | 1882 | tcm | zh-Hans | 2 | 63,739 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_jingjie` | 本草經解 | 1745 | tcm | zh-Hans | 2 | 72,835 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_jingjizhu` | 本草經集注 | 500 | tcm | zh-Hant | 2 | 127,156 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_qiuzhen` | 本草求真 | 1769 | tcm | zh-Hans | 2 | 274,878 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_sibian` | 本草思辨錄 | 1904 | tcm | zh-Hans | 2 | 102,318 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_tujing` | 本草圖經 | 1061 | tcm | zh-Hant | 2 | 116,827 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_xinbian` | 本草新編 | 1687 | tcm | zh-Hans | 2 | 203,791 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_bencao_yanyi` | 本草衍義 | 1116 | tcm | zh-Hant | 2 | 62,524 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_benjing_fengyuan` | 本經逢原 | 1695 | tcm | zh-Hant | 2 | 181,785 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_benjing_shuzheng` | 本經疏證 | 1832 | tcm | zh-Hans | 2 | 23,380 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_changsha_yaojie` | 長沙藥解 | 1753 | tcm | zh-Hans | 2 | 89,705 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_danxi_xinfa` | 丹溪心法 | 1481 | tcm | zh-Hans | 2 | 152,025 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_depi_bencao` | 得配本草 | 1761 | tcm | zh-Hans | 2 | 107,562 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_dongui_bogam` | 東醫寶鑑 | 1613 | korean | zh-Hant | 2 | 30,241 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_guangqunfangpu` | 廣群芳譜 | 1708 | tcm | zh-Hant | 2 | 890,774 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_haiyao_bencao` | 海藥本草 | 800 | tcm | zh-Hans | 2 | 14,555 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_jingui_yaolue` | 金匱要略 | 220 | tcm | zh-Hant | 2 | 29,748 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_jingyue_quanshu` | 景岳全書 | 1624 | tcm | zh-Hant | 2 | 4,435 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_maijing` | 脈經 | 280 | tcm | zh-Hant | 2 | 94,205 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_nongzheng_quanshu` | 農政全書 | 1639 | tcm | zh-Hant | 2 | 986,738 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_pujifang` | 普濟方 | 1406 | tcm | zh-Hans | 2 | 5,246,126 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_qianjin_yifang` | 千金翼方 | 682 | tcm | zh-Hans | 2 | 427,108 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_qimin_yaoshu` | 齊民要術 | 540 | tcm | zh-Hant | 2 | 143,388 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_shanghanlun` | 傷寒論 | 220 | tcm | zh-Hant | 2 | 42,506 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_shennong_bencao_baihzong` | 神農本草經百種錄 | 1736 | tcm | zh-Hant | 2 | 22,708 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_shennong_bencaojing` | 神農本草經 | 200 | tcm | zh-Hant | 2 | 17,743 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_shiliao_bencao` | 食療本草 | 700 | tcm | zh-Hans | 2 | 38,966 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_taiping_huimin_ju` | 太平惠民和劑局方 | 1078 | tcm | zh-Hant | 2 | 174,776 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_tangye_bencao` | 湯液本草 | 1289 | tcm | zh-Hant | 2 | 57,477 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_waitai_miyao` | 外臺秘要 | 752 | tcm | zh-Hant | 2 | 71,992 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_wenbing_tiaobian` | 溫病條辨 | 1798 | tcm | zh-Hant | 2 | 119,698 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_xinxiu_bencao` | 新修本草 | 659 | tcm | zh-Hant | 2 | 166,063 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yanglao_fengqin_shu` | 養老奉親書 | 1085 | tcm | zh-Hans | 2 | 31,187 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yaoxing_fu` | 珍珠囊補遺藥性賦 | 1300 | tcm | zh-Hans | 2 | 33,687 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yaoyao_fenji` | 要藥分劑 | 1773 | tcm | zh-Hant | 2 | 90,561 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yifang_jijie` | 醫方集解 | 1682 | tcm | zh-Hans | 2 | 177,765 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yinshan_zhengyao` | 飲膳正要 | 1330 | tcm | zh-Hant | 2 | 38,807 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yishuo` | 醫說 | 1224 | tcm | zh-Hans | 2 | 125,859 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yixue_zhongzhong_canxi` | 醫學衷中參西錄 | 1918 | tcm | zh-Hans | 2 | 550,796 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_zhenglei_bencao` | 證類本草 | 1082 | tcm | zh-Hans | 2 | 789,819 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_zhiwu_mingshi_tukao` | 植物名實圖考 | 1848 | tcm | zh-Hant | 2 | 5,375 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_zhouhou_beiji` | 肘後備急方 | 340 | tcm | zh-Hant | 2 | 102,786 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_zhu_bing_yuanhou` | 諸病源候論 | 610 | tcm | zh-Hans | 2 | 215,401 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `gretil_rasaratnasamuccaya` | Rasaratnasamuccaya (Vāgbhaṭa) | None | alchemy | sa-Latn | 3 | 0 | CC-BY-NC-SA-4.0 | Ref only | TEI header <licence target='https://creativecommons.org/licenses/by-nc-sa/4.0/'> |
| `ws_sa_rasahridaya` | रसहृदयतन्त्रम् | 1300 | alchemy | sa | 3 | 1 | CC-BY-SA-4.0 | Ref only | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_sa_rasarnava` | रसार्णवः | 1100 | alchemy | sa | 3 | 555 | CC-BY-SA-4.0 | Ref only | https://creativecommons.org/licenses/by-sa/4.0/ |
| `ws_zh_baopuzi` | 抱朴子 | 320 | alchemy | zh-Hant | 3 | 197,991 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_cantong_qi` | 周易參同契 | 142 | alchemy | zh-Hant | 3 | 16,133 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_huangdi_jiuding_shendan` | 黃帝九鼎神丹經訣 | 700 | alchemy | zh-Hant | 3 | 64,970 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_leigong_paozhi` | 雷公炮炙論 | 470 | alchemy | zh-Hans | 3 | 25,959 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_leigong_paozhi_yaoxing` | 雷公炮製藥性解 | 1640 | alchemy | zh-Hans | 3 | 66,375 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_longhu_huandan_jue` | 龍虎還丹訣 | 700 | alchemy | zh-Hant | 3 | 5,209 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_mengxi_bitan` | 夢溪筆談 | 1088 | tcm | zh-Hant | 3 | 127,190 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_paozhi_dafa` | 炮炙大法 | 1622 | alchemy | zh-Hans | 3 | 28,659 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_shiyao_erya` | 石藥爾雅 | 800 | alchemy | zh-Hant | 3 | 7,304 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_taiqing_shibi_ji` | 太清石壁記 | 700 | alchemy | zh-Hant | 3 | 14,503 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_taiyi_jinhua` | 太乙金華宗旨 | 1670 | alchemy | zh-Hant | 3 | 10,040 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_tiangong_kaiwu` | 天工開物 | 1637 | tcm | zh-Hant | 3 | 58,266 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_wuzhen_pian` | 悟真篇 | 1075 | alchemy | zh-Hant | 3 | 7,819 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_xuanyuan_shuijing_yaofa` | 軒轅黃帝水經藥法 | 700 | alchemy | zh-Hant | 3 | 4,586 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_yunji_qiqian` | 雲笈七籤 | 1029 | alchemy | zh-Hant | 3 | 933,164 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `pg_churchill_acupuncturation` | A Treatise on Acupuncturation | 1821 | acupuncture | en | 4 | 53,997 | Public Domain | R + T | https://www.gutenberg.org/policy/license.html |
| `ws_zh_huangdi_neijing` | 黃帝內經 | -200 | acupuncture | zh-Hant | 4 | 190,095 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_nanjing` | 難經 | 200 | acupuncture | zh-Hant | 4 | 15,386 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_zhenjiu_dacheng` | 針灸大成 | 1601 | acupuncture | zh-Hant | 4 | 247,369 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
| `ws_zh_zhenjiu_jiayi` | 針灸甲乙經 | 282 | acupuncture | zh-Hant | 4 | 137,596 | CC-BY-SA-4.0 | R + T | https://zh.wikisource.org/wiki/Wikisource:%E7%89%88%E6%9D%83%E4%BF%A1%E6%81%AF |
---

## 3. Sources we looked at and did **not** use

| candidate | why not |
|---|---|
| GRETIL (all texts) | CC BY-NC-SA 4.0 — NonCommercial clause (see §1.3) |
| ctext.org API | `ERR_REQUIRES_AUTHENTICATION`; bulk access is gated, licence not confirmed |
| Kanripo (GitHub) | repository layout/licences not verified in the time available; not claimed as PD |
| Dr Duke's *Handbook of Phytochemical Constituents* (archive.org scans) | the scanned book is not openly licensed on archive.org; the tabular Duke data was not located at a verifiable open URL, so **no Duke rows were used** rather than guess a licence |
| Modern English translations of the Asian classics (e.g. 1960s–2000s academic translations) | in copyright — referenced only, never copied |
| WHO / EMA monographs | not openly licensed for bulk redistribution; not used |

---

## 4. Traditional Knowledge statement

The classical texts in this corpus are **living heritage**, not free ore. They are pre-modern
works in the public domain / CC BY-SA; the *knowledge* they encode is held by communities that
still practise it. SHENNONG uses the texts for computational research only, attributes every
passage to its source, publishes under an open licence, and does not and must not claim ownership
of the knowledge. No modern clinical guidance, dosing or self-treatment instruction is derived or
published. See `docs/SAFETY.md` for the project-level policy.

---

*Generated for SHENNONG (EthnoHack 2026). Regenerate with:*
`python -m data.build_registry && python -m data.build_docs`
