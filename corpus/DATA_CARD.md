# SHENNONG Corpus — Data Card

**A licence-audited, provenance-complete corpus of the classical Asian medical, alchemical and scientific canon, anchored to modern biology and chemistry.**

- Corpus sha256: `fe4907c191a10f5a05c8b7929855f8d4d38a4d6140d828cefafd3894b4443292`
- Training records: **27,738** chunks in `corpus/processed/corpus.jsonl`
- Total characters: **45,604,249**
- Sources trained on: **106** · unverified/rejected: 1 · quality-excluded: 2
- Earliest / latest source year: **-200** … **1921**

> This is the input layer for a drug-discovery engine. It is **not** a chatbot corpus and it is **not** a clinical resource. No dosing, no self-treatment guidance, no synthesis routes. See `docs/SAFETY.md`.

## 1. Composition

### 1.1 By language

| language | chars | share | script |
|---|---|---|---|
| `en` | 23,349,823 | 51.2% | English |
| `zh-Hant` | 16,026,763 | 35.1% | Traditional Chinese (漢字) |
| `sa` | 3,439,850 | 7.5% | Sanskrit, Devanagari (देवनागरी) |
| `la` | 2,787,813 | 6.1% | Latin |

**CJK share is 35.1% of all characters** (16,026,763 chars). The domain directive (brief §0) makes the untranslated Asian canon the core asset, and this is the part no competing team will have.

### 1.2 By tradition

| tradition | chars | share | sources |
|---|---|---|---|
| `foundational` | 16,322,419 | 35.8% | 20 |
| `tcm` | 15,379,517 | 33.7% | 54 |
| `ayurveda` | 8,713,898 | 19.1% | 11 |
| `unani` | 3,185,238 | 7.0% | 2 |
| `alchemy` | 1,339,357 | 2.9% | 13 |
| `acupuncture` | 636,156 | 1.4% | 5 |
| `korean` | 27,664 | 0.1% | 1 |

### 1.3 By tier (brief §5)

| tier | meaning | chars | share |
|---|---|---|---|
| 1 | foundational biology & chemistry (first-principles substrate) | 16,322,419 | 35.8% |
| 2 | Asian materia medica, clinical and scientific canon | 27,121,457 | 59.5% |
| 3 | Asian alchemy / esoteric pharmacy / process chemistry | 1,524,217 | 3.3% |
| 4 | acupuncture & channel systems | 636,156 | 1.4% |

### 1.4 Largest sources

| source_id | title | lang | tradition | chars |
|---|---|---|---|---|
| `ws_zh_pujifang` | 普濟方 | zh-Hans | tcm | 5,246,126 |
| `ia_avicenna_canon_latin_1593` | Canon medicinae (Latin, 1593 Venice) | la | unani | 2,804,522 |
| `pg_pharmacographia` | Pharmacographia: A History of the Principal Drugs of Vege… | en | foundational | 2,576,883 |
| `ia_cushny_pharmacology` | A Text-book of Pharmacology and Therapeutics | en | foundational | 2,255,785 |
| `ia_abderhalden_physiological_chemistry` | Text-book of Physiological Chemistry in Thirty Lectures | en | foundational | 1,979,606 |
| `ws_zh_bencao_gangmu` | 本草綱目 | zh-Hant | tcm | 1,937,446 |
| `ia_sayre_organic_materia_medica` | A Manual of Organic Materia Medica and Pharmacognosy | en | foundational | 1,519,061 |
| `ia_kirtikar_indian_medicinal_plants_2` | Indian Medicinal Plants (vol. 2) | en | ayurveda | 1,457,698 |
| `ia_kirtikar_indian_medicinal_plants_b` | Indian Medicinal Plants (vol. 2, alt. scan) | en | ayurveda | 1,439,705 |
| `ia_bhishagratna_sushruta` | An English Translation of the Sushruta Samhita | en | ayurveda | 1,373,908 |
| `ia_stuart_chinese_materia_medica` | Chinese Materia Medica: Vegetable Kingdom | en | tcm | 1,182,308 |
| `ws_sa_sushrutasamhita` | सुश्रुतसंहिता | sa | ayurveda | 1,113,363 |
| `ws_zh_nongzheng_quanshu` | 農政全書 | zh-Hant | tcm | 986,738 |
| `ws_zh_yunji_qiqian` | 雲笈七籤 | zh-Hant | alchemy | 933,164 |
| `pg_origin_of_species` | On the Origin of Species By Means of Natural Selection | en | foundational | 932,145 |
| `ws_sa_bhavaprakasha` | भावप्रकाशः | sa | ayurveda | 921,523 |
| `ws_sa_ashtangahridaya` | अष्टाङ्गहृदयम् | sa | ayurveda | 918,482 |
| `pg_atkinson_elementary_botany` | Elementary Botany | en | foundational | 891,036 |

## 2. What is in it

**Classical Chinese canon (Tier 2/3/4).** 神農本草經, 本草綱目, 本草經集注, 新修本草, 證類本草, 本草圖經, 本草衍義, 湯液本草, 本草備要, 本草從新, 本草求真, 本草綱目拾遺, 本經疏證, 本草崇原, 本草分經, 得配本草, 要藥分劑, 本草便讀, 本草害利, 本經逢原, 長沙藥解, 本草經解, 本草新編, 本草思辨錄, 神農本草經百種錄, 雷公炮製藥性解, 本草綱目別名錄; 傷寒論, 金匱要略, 千金翼方, 外臺秘要, 太平惠民和劑局方, 普濟方, 溫病條辨, 丹溪心法, 景岳全書, 醫方集解, 醫宗金鑑-class formularies, 諸病源候論, 脈經, 肘後備急方, 食療本草, 海藥本草; **acupuncture**: 黃帝內經, 難經, 針灸甲乙經, 針灸大成; **alchemy**: 抱朴子, 周易參同契, 雲笈七籤, 悟真篇, 太乙金華宗旨, 雷公炮炙論, 炮炙大法, 石藥爾雅, 太清石壁記, 龍虎還丹訣, 黃帝九鼎神丹經訣, 軒轅黃帝水經藥法; **science/agriculture/dietetics**: 天工開物, 齊民要術, 夢溪筆談, 農政全書, 植物名實圖考, 廣群芳譜, 飲膳正要, 養老奉親書, 醫說; **Korean**: 東醫寶鑑.

**Sanskrit Ayurveda (Tier 2/3), Devanagari.** चरकसंहिता, सुश्रुतसंहिता, अष्टाङ्गहृदयम्, भावप्रकाशः, शार्ङ्गधरसंहिता, माधवनिदानम्; rasaśāstra: रसहृदयतन्त्रम्, रसार्णवः.

**Unani / Graeco-Arabic (Tier 2).** Ibn Sīnā *Canon medicinae*, the 1593 Venice Latin edition in full; the Taleef Shereef (Indian Unani materia medica).

**English translations of Asian materia medica (Tier 2).** Bhishagratna's *Suśruta Saṃhitā* (1907–16), Stuart & Smith *Chinese Materia Medica* (1911), Dutt *Materia Medica of the Hindus* (1877), Kirtikar & Basu *Indian Medicinal Plants* (1918), Hanbury *Notes on Chinese Materia Medica* (1862), Waring *Bazaar Medicines of India* (1867), Churchill on acupuncture (1821).

**Foundational biology & chemistry (Tier 1, English/Latin).** anatomy & physiology, histology, physiological chemistry, pharmacology, pharmacognosy, bacteriology, genetics, evolution, botany, organic synthesis, plant histology — 19th/early-20th-century textbooks.

## 3. Languages and eras

Texts span roughly **c. 200 BCE to 1918 CE**, with the bulk from the 6th–19th centuries CE,
plus 19th/early-20th-century scientific textbooks in English and a 1593 Latin *Canon*.
Orthography is **preserved, not modernised**: traditional Chinese characters, classical
Chinese syntax, Devanagari with sandhi, and 19th-century English spellings are all signal.

Two script registers appear for Chinese: `zh-Hant` (majority) and `zh-Hans` where the only
available Wikisource transcription is simplified. The registry's `lang` field is set from
the text itself by a character-frequency script detector, not from the work's era.

## 4. Known biases — read this before using the corpus

1. **English-translation weighting.** 51.2% of characters are English. Much of the Asian content reaches us through **19th-century translators who carried their own filters** — colonial-era pharmacognosy (Kirtikar, Stuart, Dutt, Waring) uses the vocabulary and categories of its time, translates selectively, and sometimes misidentifies taxa. The untranslated Chinese and Sanskrit is the corrective, but it is a minority of the character count.
2. **Edition bias.** We use whichever public-domain transcription exists. Different editions of 本草綱目 disagree on properties (e.g. 人參 is 甘微寒 in some editions, 苦溫 in the transcription used here). We are faithful to *our* transcription and record the source, but we are not a critical edition.
3. **Grade/property coverage is partial.** `properties.csv` covers 1,402 drug rows, and each field is filled only where the text states it: nature, flavour, toxicity, 歸經 channel and 三品 grade are all well below 100%. Absence means *not stated in the transcribed text we parsed*, not *absent in the tradition*. Report n per test.
4. **China- and India-centric within Asia.** Chinese and Indian material dominates; Kampō, Korean (apart from 東醫寶鑑) and Tibetan are thin. Persian/Unani is represented by one large Latin *Canon* plus one English translation.
5. **OCR noise.** The Internet Archive tier is OCR of 19th-century print. We filter hard (running heads, page numbers, hyphenation, high-symbol-ratio lines, U+FFFD), but residual OCR error survives in the English tier.
6. **Formularies are formula-rich and indication-poor.** 普濟方 and 太平惠民和劑局方 list thousands of formulas; extracting clean drug × indication pairs from them is future work.

**What we deliberately did *not* include:** European herbals (Culpeper, Gerard, Grieve, King's) — the domain directive excludes the Western herbal tradition. No `comparative-control` slice was ultimately needed, so the 3% cap is unused (0%).

## 5. Licences

| licence | sources | chars | obligation |
|---|---|---|---|
| CC BY-SA 4.0 | 76 | 20,884,182 | attribution + **ShareAlike** on redistribution of the corpus |
| PD | 30 | 26,278,950 | none (public domain) |

The **CC BY-SA 4.0** portion makes `corpus/` a share-alike data artefact: derived corpora must be released under a compatible licence with attribution to Wikisource contributors. Code and model weights remain Apache-2.0 — the data licence is separate. Full table, per-source evidence and the **GRETIL CC BY-NC-SA rejection** are in [`LICENSE_AUDIT.md`](LICENSE_AUDIT.md).

**PII / personal data:** none. These are published historical texts. No living-person data, no patient records, no location data.

**Dual use / safety:** toxicology and toxic plants are discussed *as they appear in historical texts*. The corpus contains no synthesis routes, no dosing instructions, and no self-treatment guidance. Downstream models must refuse clinical-advice requests; see `docs/SAFETY.md`.

## 6. Structured derivatives

| artefact | rows | contract |
|---|---|---|
| `ayurveda_properties.csv` | 322 | rasa / guṇa / vīrya / vipāka / doṣa |
| `compounds.csv` | 23,177 | compound → SMILES/CID (PubChem) + found-in taxon (Wikidata) |
| `formula_ingredients.csv` | 847 | formula × ingredient drug |
| `formulas.csv` | 141 | formula names from the clinical corpus |
| `incompatibilities.csv` | 29 | 十八反 / 十九畏 rule systems |
| `plants.csv` | 284 | binomial → family (GBIF) + synonyms |
| `processing.csv` | 317 | 炮制 term → modern chemical reading |
| `properties.csv` | 1,402 | TCM property vector (四氣五味歸經升降浮沉有毒無毒三品) |
| `relations_seven.csv` | 45 | 七情 combination relations |
| `uses.csv` | 11,819 | drug × indication × tradition |

### 6.1 Join audit — how much structured data reaches a taxon

Lexicon: **827 entries**, 691 distinct binomials, mean confidence 0.754. Methods: `manual` 62, `wikidata` 692, `alias` 4, `wikidata-genus` 69.

| file | rows | join key | joined to a binomial | rate | unresolved |
|---|---|---|---|---|---|
| `properties.csv` | 1,402 | `drug_name` | 658 | 47% | 744 |
| `uses.csv` | 11,819 | `drug_name` | 5,084 | 43% | 6,735 |
| `formula_ingredients.csv` | 847 | `drug_name` | 451 | 53% | 396 |
| `ayurveda_properties.csv` | 322 | `drug_name` | 0 | 0% | 322 |
| `compounds.csv` | 23,177 | `` | 23,004 | 99% | 0 |

**Why unresolved rows were not guessed.** A drug surface that Wikidata/POWO cannot resolve to a single accepted binomial is left `null` with `join_status=unresolved`. Several classical names are genuinely ambiguous (*Aristolochia* vs *Stephania* substitution is the documented safety crisis this project studies), so guessing a binomial would inject exactly the error the discovery engine is supposed to detect. `drug_name` is present on every row and is the stable join key for runtime resolution.

### 6.2 十八反 / 十九畏 — completeness, stated honestly

These two mnemonics are named for the **drugs named in the verse, not for the number of pairs**. We ship the faithful sets rather than a padded one, and we label every row with the verse line it comes from.

| rule system | verse | pairs | drugs named | note |
|---|---|---|---|---|
| 十八反 (shiba_fan) | 十八反歌 | 18 | 19 | The classical name 十八反 counts the DRUGS named in the verse (19 surfaces in 3 groups), not the number of pairs. The verse yields 16 canonical pair relations. Two documented modern variants (白芍/赤芍 for 芍藥) are included and flagged in variant_of. |
| 十九畏 (shijiu_wei) | 十九畏歌 | 11 | 19 | 十九畏 names 19 drugs. The verse yields 9 canonical pair relations; the line 川烏草烏不順犀 names 犀角 and adds 2 genuine relations, giving 11. Nothing is padded. |
| viruddha (Ayurveda) | — | 0 | — | Ayurvedic viruddha (incompatible) pairings are discussed in the Sanskrit corpus but a machine-readable classical *list* equivalent to the 十八反 verse was not located in an openly licensed source within the project window, so no rows are claimed. Recorded as a gap rather than invented. |

Every row carries `classical_label` (e.g. `十八反·烏頭組`) and `span` (the verse line), so a reviewer can trace it to the mnemonic. `variant_of` flags the two modern 白芍/赤芍 rows and the two 犀角 rows. **Nothing was padded to reach a round number** — inventing pairs would be the one error that invalidates a data-validation claim.

The drug-name → modern-binomial lexicon is `corpus/processed/lexicon_drugs.json` (Wikidata **P225** taxon resolution with a citable Q-id per entry, plus manual pharmacopoeial overrides).

## 7. Quality control as applied

- **Chunking:** 1800 target / 3000 hard max characters; minimum 100 chars for CJK and 200 for alphabetic scripts (contract §10.2).
- **De-duplication:** 13-gram shingle hashing across all sources; a chunk is dropped when ≥80% of its shingles were already seen. **424 duplicate chunks were dropped.**
- **Near-duplicates that remain:** the contract checker's independent, weaker hash (`hash(tuple(text.split()[:13]))`) reports ~1.2% of chunks sharing a 13-token prefix. These are genuine near-duplicates — the same passage in the original and a commentary edition, or overlapping sub-pages — not exact copies. We state the number rather than omit it.
- **NFC normalisation**, control-character stripping, per-source script gate (CJK / Devanagari / Latin ratio), U+FFFD gate, running-head and page-number removal, Gutenberg boilerplate removal, OCR line de-hyphenation.
- **Every** `chars` and `sha256` in `sources.yaml` is read from a file on disk. Nothing is estimated.

## 8. How to rebuild

From a clean clone (network required; the fetchers are idempotent, resumable, rate-limited and cache all API responses under `data/.cache/`):

```bash
# 1. discover candidate sources (optional; the curated manifest is data/manifest.py)
python -m data.discover

# 2. fetch raw text  (corpus/raw/<source_id>/text.raw + meta.json)
python -m data.fetch_wikisource --lang zh      # classical Chinese canon
python -m data.fetch_wikisource --lang sa      # Sanskrit Ayurveda (Devanagari)
python -m data.fetch_gutenberg                 # Tier 1 English foundational science
python -m data.fetch_archive                   # PD English/Latin editions

# 3. clean -> corpus/processed/text/<source_id>.txt
python -m data.clean

# 4. build training corpus + registry + docs
python -m data.build_corpus                    # -> corpus.jsonl + stats.json
python -m data.build_registry                  # -> corpus/registry/sources.yaml
python -m data.build_docs                      # -> DATA_CARD.md, licence table

# 5. structured derivatives (network: Wikidata, PubChem, GBIF)
python -m data.build_structured
python -m data.build_lexicon

# 6. validate against the inter-team contracts
python scripts/verify_contracts.py
```

A full network rebuild takes ~1–2 hours (mediawiki + archive.org rate limits). Reproduced corpus sha256: `fe4907c191a10f5a05c8b7929855f8d4d38a4d6140d828cefafd3894b4443292`.

> **Determinism note.** The corpus hash is reproducible from the same raw downloads. Wikisource pages can be edited between runs, so a later rebuild may differ; `corpus/raw/*/meta.json` records the `raw_sha256` of every file actually used, which is the authoritative record.

## 9. Provenance and ethics

Every record carries `source_id`, `title`, `year`, `tradition`, `lang`, `tier`, `licence` and points back to a registry entry with a URL and licence evidence. The registry is the proof obligation: no source is in the corpus without one.

The classical texts are **living heritage**, not free ore. We attribute every passage, publish under an open licence, do not claim ownership of the knowledge, and derive no clinical guidance. A Nagoya-Protocol-aware Traditional Knowledge policy is in `docs/SAFETY.md`.

## 10. Hashes

| artefact | sha256 |
|---|---|
| `corpus/processed/corpus.jsonl` | `fe4907c191a10f5a05c8b7929855f8d4d38a4d6140d828cefafd3894b4443292` |

Per-source raw and cleaned hashes are in `corpus/raw/<source_id>/meta.json` (`raw_sha256`, `clean_sha256`) and in `corpus/registry/sources.yaml` (`sha256`).

