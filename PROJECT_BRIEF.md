# SHENNONG — Project Brief v2 (internal, single source of truth)

> **Name:** **SHENNONG** (神农) — *the Divine Farmer, who tasted a hundred herbs and recorded which
> were poison and which were medicine.*
> **Tagline:** *Shennong tasted a hundred herbs. We are teaching a 400 MB model to do it again — and
> to tell us what he hid between the lines.*
> **Model family:** `shennong-mini` (from scratch, this machine) · `shennong-0.5b` (flagship, <1 GB GGUF)
> **Retired working name:** ATHANOR (dropped — "alchemy" now means *Asian* alchemy; the domain is
> Asian medicine, not the Western herbal tradition).

**Competition:** EthnoHack 2026 — *Data Hackathon on Ethnopharmacology & Health* (ETHCSTWIN / Horizon
Europe, National and Kapodistrian University of Athens, 2–8 November 2026, 100% online).
**Primary track:** **01 — Traditional Knowledge Mining** (NLP + historical texts + ethnobotany).
**Secondary depth:** 02 — Natural Products for Drug Discovery (KG + chemotype + repurposing);
04 — Digital Health & Phytotherapy (the Workbench).
**Target special awards:** Best AI Solution · Best Scientific Rigor · Best Community Impact.

**Required submission:** Devpost page · public GitHub repo + README · 10-minute video · ≤ 10 slides.
**Judging:** scientific relevance · novelty/creative data use · reproducibility & documentation ·
data-science quality (validation, uncertainty) · scalability · benefit to conservation/drug
discovery/public health.

---

## 0. DOMAIN DIRECTIVE (governs everything)

**The model's expertise is the Asian medical and alchemical canon, not the Western herbal tradition.**

- **In domain:** Traditional Chinese Medicine (TCM/中醫), Ayurveda (Āyurveda), Unani/Graeco-Arabic
  (Ṭibb), Kampō (漢方), Korean medicine (韓醫), Tibetan Sowa Rigpa, Persian medicine, and the
  Southeast/East Asian folk and esoteric lineages that feed them; **Asian alchemy** — Chinese waidan
  (外丹) and neidan (內丹) including 抱朴子 *Baopuzi* and 周易參同契 *Cantong qi*; Indian **rasaśāstra**
  (mercurial/metallic pharmacy); Daoist and Tantric materia medica; **acupuncture and moxibustion**
  with their meridian/channel systems (經絡).
- **Out of domain (excluded from domain pretraining):** European herbals — Culpeper, Gerard, Parkinson,
  Grieve, King's, European pharmacopoeias — and the Western doctrine of signatures. A small
  comparative slice (≤ 3% of tokens) may be retained **only** as an explicit experimental control,
  labelled `tradition: comparative-control` in the registry.
- **What stays:** foundational **biology and chemistry** (anatomy, physiology, biochemistry,
  molecular biology, pharmacology, toxicology, botany, phytochemistry, natural-product chemistry,
  taxonomy). This is not "Western medicine" — it is the **first-principles substrate** used to
  interpret Asian texts. Thesis: *ancient Asian text ⟷ modern first-principles biology and chemistry*.

**The problem — "what was hidden in ancient text".** Classical Asian medical texts encode real,
testable pharmacology inside language science has largely ignored: alchemical process words, esoteric
drug names, numbered incompatibility rules, processing procedures, hierarchical formula roles. That
knowledge has never been translated into mechanistic terms, so it has never been tested. SHENNONG
**decodes it, connects it to first-principles biology/chemistry, and emits falsifiable hypotheses**.

## 1. The pipeline — four classical operations of Chinese pharmacy

Use these names in code, CLI, docs and UI.

| Stage | Term | Meaning | What the code does |
|---|---|---|---|
| 1 | **采 Cǎi** — *collect* | gather the materia medica | ingest + clean public-domain Asian classics (Classical Chinese, Sanskrit, Arabic/Persian, Tibetan, Japanese/Korean) and open translations; provenance + licence; extract entities |
| 2 | **制 Zhì** — *prepare* | 炮制: clean, cut, fry, calcine | normalise orthography (繁/简, variants, IAST/Devanagari), resolve drug names across eras/languages → modern taxa; translate process terms into modern chemistry |
| 3 | **配 Pèi** — *combine* | 配伍 formulation | build the knowledge graph: plant↔compound↔target↔pathway↔indication, cross-tradition links, formula composition, incompatibility edges |
| 4 | **使 Shǐ** — *deploy/command* | 君臣佐使, formula role hierarchy | rank hypotheses, label each by formula role, attach falsification plans, uncertainty, experimental design |

## 2. The six discovery classes ("what was hidden")

Every hypothesis belongs to one class, with its own module, failure modes and falsification test.

1. **配伍禁忌 — encoded incompatibility.** TCM **十八反** (18 antagonisms) and **十九畏** (19 mutual
   fears); Ayurvedic **viruddha** pairings. Pre-modern interaction rules, never systematically tested.
   → herb–herb and herb–drug interaction predictions (e.g. *Aconitum* + *Pinellia*/*Fritillaria*;
   Hg/Sb/As mineral drugs with organic herbs).
2. **炮制 — processing as chemistry.** 炮, 煅, 煨, 淬, 昇, 飛, 伏, 製, honey-frying, vinegar-frying,
   steaming, fermentation (麴), ash lye → hydrolysis, decarboxylation, oxidation, volatilisation,
   complexation, salt formation. → which processing steps are *necessary* for activity/safety, and
   which modern products skip them.
3. **异名同物 / 同名异物 — name collision & adulteration.** One name for different species across eras
   and dialects. A documented safety crisis (*Aristolochia* substituted for *Stephania* → aristolochic
   acid nephropathy). → high-risk collisions ranked by toxicity divergence between the colliding taxa.
4. **君臣佐使 — formula roles & synergy.** Emperor 君, minister 臣, assistant 佐, courier 使. The courier
   is often a bioavailability enhancer (*Piper* alkaloids, ginger, liquorice). → which roles are
   mechanistically load-bearing; which "courier" herbs are the hidden pharmacokinetic key.
5. **未研究本草 — the understudied majority.** Strong, repeated, multi-tradition use and no modern
   target-level evidence. → the abandoned-lead screening list for natural-product discovery.
6. **濒危代用品 — endangered species & substitutes.** Text-attested substitutes for CITES-listed drugs
   (rhino horn, tiger bone, pangolin, *Paris polyphylla*, *Aquilaria*). → chemically plausible,
   conservation-safe substitutes; direct biodiversity benefit.

**Mandatory negative controls (reported honestly, even if the answer is "no signal").**
- **取象比类** — TCM analogical reasoning by resemblance: does colour/shape/habitat predict target organ?
- **Ayurvedic rasa** — do the six tastes (ṣaḍrasa) predict pharmacological action beyond chance?
- **Null model** — shuffle plant↔use edges; discovery scores must collapse.

## 3. Hard constraints

| Constraint | Target |
|---|---|
| Model file size | **< 1 GB** (flagship GGUF Q4_K_M ≈ 350–400 MB) |
| Parameters | **≤ 1 B** (`shennong-0.5b` ≈ 494 M; `shennong-mini` ≈ 10–25 M) |
| Weights | **Open**, public, permissive, no gate |
| Training data | **Exclusively** Asian medical/alchemical canon + foundational biology/chemistry/anatomy; classical originals + public-domain translations |
| Reproducibility | one command per stage; hashed artefacts; provenance + licence per source |
| Recording | everything in git |

**CPU-only machine** (Intel i7-4790K Haswell, 32 GB, no CUDA/MPS, ~90 GFLOPS fp32 matmul).
`shennong-mini` is genuinely trained here at small scale with real logs. `shennong-0.5b` is a fully
executable recipe + quantisation path. **Never fake a result**; a recipe number is labelled as a
recipe number in the same sentence.

**Language requirement (not optional).** Tokenizer and model must handle **Classical Chinese
(繁體/简体)** and **Sanskrit (Devanagari + IAST)** plus English. The point is reading untranslated
originals, so budget vocab for it.

## 4. Repository layout (write scopes enforced — see §7)

```
corpus/          registry (provenance/licence/tier), raw + processed text, DATA_CARD
data/            fetchers, cleaners, drug-name lexicons, structured-data builders
tokenizer/       domain BPE (zh-classical, sa, en)
model/           shennong_mini.py, configs, MODEL_CARD, export/gguf
training/        pretrain / CPT / LoRA-SFT / merge+quantise, runs/ logs
shennong/        python package: kg/ extract/ decode/ discover/ rag/ safety/ learn/ eval/
app/             SHENNONG Workbench (stdlib-only local web UI)
tests/ eval/     pytest suite, benchmark harness
docs/            FIRST_PRINCIPLES, ARCHITECTURE, METHODOLOGY, EVALUATION, SAFETY, CONTINUOUS_LEARNING
submission/      DEVPOST.md, SLIDES.md (10), VIDEO_SCRIPT.md
```
Package import name is `shennong` (the `athanor/` directory was renamed at v2).

## 5. The data we need (derived from axioms, not guessed)

**Tier 0 — Ontology.** `Taxon, PlantPart, DrugName(form×script), Preparation, Process, Compound,
Target, Pathway, Indication, Symptom, Organ, Meridian/Channel, Formula, Role(君臣佐使),
Incompatibility, Observation, Tradition, Source, EvidenceGrade`.

**Tier 1 — Foundational biology & chemistry (first-principles substrate).** Anatomy, histology,
physiology, biochemistry, molecular biology, genetics, microbiology, pharmacology &
pharmacokinetics (ADME, CYP450, transporters), toxicology, pathology, immunology, botany & plant
morphology, plant physiology, ecology, organic chemistry, natural-products chemistry, pharmacognosy,
analytical methods (HPLC, LC-MS, NMR, assay design).

**Tier 2 — Asian materia medica, the core.**
- **Chinese:** 神農本草經, 本草綱目, 本草經集注, 新修本草, 證類本草, 傷寒論, 金匱要略, 千金要方,
  外臺秘要, 太平惠民和劑局方, 溫病條辨, 丹溪心法, 景岳全書, 醫宗金鑑, 本草備要.
- **Ayurveda:** Caraka Saṃhitā, Suśruta Saṃhitā, Bhāvaprakāśa, Aṣṭāṅgahṛdaya, Rasa Ratna Samuccaya,
  Rasaśāstra texts, Śārṅgadhara Saṃhitā, nighaṇṭu materia medica.
- **Unani / Graeco-Arabic:** Ibn Sīnā *al-Qānūn fī al-Ṭibb* (Arabic + public-domain Latin),
  al-Rāzī *al-Ḥāwī*, Ibn al-Bayṭār *al-Jāmiʿ*.
- **Kampō / Korean / Tibetan:** 傷寒論 in Japan, 東醫寶鑑 Dongui Bogam, rGyud-bzhi where openly available.
- **Folk & regional:** open ethnobotanical surveys of China, India, Nepal, Thailand, Vietnam,
  Indonesia, Japan, Korea.

**Tier 3 — Asian alchemy / esoteric pharmacy.** 抱朴子 *Baopuzi*, 周易參同契 *Cantong qi*, 雲笈七籤,
Daoist 丹方 texts, 雷公炮炙論 (foundational processing text), Indian rasaśāstra (mercury, bhasma,
kharpara), Tibetan/Tantric medical tantras, alchemical drug-name ciphers (龍血, 虎骨, 紫河車, 鉛丹, 曾青).

**Tier 4 — Acupuncture & channels.** 黃帝內經 (素問/靈樞), 難經, 針灸甲乙經, 銅人腧穴針灸圖經,
針灸大成, 千金翼方, Japanese/Korean channel texts, open-access acupuncture RCT literature.

**Tier 5 — Structured open data (ground truth that prevents hallucination).** Dr Duke's Phytochemical
& Ethnobotanical Database (USDA, public domain), PubChem, ChEMBL (CC-BY-SA), KEGG, STRING, Gene
Ontology, MeSH, World Flora Online / Kew POWO synonyms, GBIF, NCBI Taxonomy, openly-released
herb–compound–target datasets (**check licences; never redistribute restricted data**), open
WHO/EMA monographs.

**Public-domain reality check.** Many modern English translations of Asian classics are in copyright.
Routes that work: **zh.wikisource.org** / **ctext.org** (Chinese originals, PD-old);
**sanskritdocuments.org / GRETIL** (Sanskrit, PD editions); **archive.org** (19th/early-20th-c.
translations, SBE volumes, old Latin *Canon* editions); **Kanripo**; open government datasets.
Unclear licence → `unverified`, excluded from training, cited only.

## 6. Why this is not "yet another fine-tune"

- **First-principles data derivation** (`docs/FIRST_PRINCIPLES.md`): axioms → required data classes →
  sourcing. The registry is a proof obligation, not a wish list.
- **Bilingual classical decoding.** The model reads the *untranslated* originals. Most NLP on TCM and
  Ayurveda reads only modern English summaries — the encoded layer is exactly what gets skipped.
- **A falsification gate.** Every hypothesis ships its own kill-criteria. Score =
  `novelty × mechanistic plausibility × testability × evidence quality`, plus uncertainty and a
  sensitivity analysis over the exponents.
- **Honest negative controls** (§2), including ones that could embarrass the whole field.
- **Safety & TK ethics are load-bearing**: dual-use screening, no dosing, no synthesis routes, and a
  Nagoya-Protocol-aware policy (attribution, consent, benefit-sharing, non-extractive framing —
  classical texts are living heritage, not free ore).

## 7. Team, ownership, write scopes (disjoint)

| Member | Owns (write) | Never writes |
|---|---|---|
| `lead` | `PROJECT_BRIEF.md`, `README.md`, `pyproject.toml`, `Makefile`, `LICENSE`, `docs/FIRST_PRINCIPLES.md`, `docs/ARCHITECTURE.md`, `scripts/`, `.gitignore`, **all git** | everything else |
| `data-curator` | `corpus/`, `data/` | `model/`, `shennong/`, `docs/` |
| `model-forge` | `tokenizer/`, `model/`, `training/`, `artifacts/` | `corpus/`, `shennong/`, `docs/` |
| `discovery-engine` | `shennong/`, `tests/`, `eval/` | `corpus/`, `model/`, `docs/` |
| `story-builder` | `docs/` (not FIRST_PRINCIPLES/ARCHITECTURE), `submission/`, `app/`, `assets/` | `corpus/`, `model/`, `shennong/` |

**Rules.** 1) Never run `git add/commit/push` — the Lead owns git. 2) Stay in scope. 3) Every source
needs title, author/date, URL, licence + evidence, tier, language, tradition. Unclear licence →
`UNVERIFIED`, not trained on. 4) Real verifiable artefacts beat prose. 5) No fabricated
citations/metrics. 6) No dosing, no self-treatment guidance, no toxin/pathogen synthesis routes.
7) Light CPU-friendly deps; venv `.venv` has torch 2.2.2, numpy 1.26.4, tokenizers, pytest,
matplotlib, gguf, safetensors, bs4, lxml, pyyaml, requests, regex, tqdm.

## 8. Licences

Code **Apache-2.0**; weights **Apache-2.0** (research use only, not clinical); data per-source licences
preserved in `corpus/registry/`; public-domain text reproduced, share-alike respected, restricted
material **referenced only**. A separate explicit Traditional Knowledge policy document.

## 9. Definition of done

1. `make setup && make corpus && make tokenizer && make train-mini && make eval && make app-data &&
   make workbench` reproduces headline numbers from a clean clone on CPU.
2. `artifacts/` holds real weights (GGUF < 1 GB) + sha256 + real training logs + loss curve.
3. `python -m shennong.cli shi --n 10` emits ≥ 10 ranked, provenance-cited, falsifiable hypotheses
   across the six classes; ≥ 1 full dossier a pharmacognosist could act on.
4. `pytest` green; `eval/report.json` has real numbers incl. both negative controls and ablations.
5. Public GitHub repo (`https://github.com/cptlight/shennong`), README renders, readable git history,
   Devpost + 10 slides + video script done.

---

## 10. Inter-team contracts (stable — message the Lead before changing)

### 10.1 `corpus/registry/sources.yaml`
```yaml
- id: wikisource_zh_bencaogangmu
  title: "本草綱目"
  title_en: "Compendium of Materia Medica"
  author: "李時珍 Li Shizhen"
  year: 1596
  tradition: tcm          # tcm | ayurveda | unani | kampo | korean | tibetan | persian | alchemy | acupuncture | foundational | comparative-control
  lang: zh-Hant           # zh-Hant | zh-Hans | sa | sa-Latn | ar | fa | bo | ja | ko | en
  tier: 2
  url: "https://zh.wikisource.org/wiki/..."
  licence: "Public Domain"
  licence_evidence: "https://..."
  chars: 1234567
  sha256: "<sha of downloaded file>"
  status: ok              # ok | unverified | excluded
```

### 10.2 `corpus/processed/corpus.jsonl` — training text, only `status: ok`
```json
{"id":"...::000123","source_id":"...","title":"...","title_en":"...","year":1596,
 "tradition":"tcm","lang":"zh-Hant","tier":2,"licence":"Public Domain","text":"..."}
```
UTF-8, NFC, >=100 chars/record for CJK and >=200 for alphabetic, 13-gram dedupe, chunks ~1-3k chars.

### 10.3 `corpus/processed/lexicon_drugs.json` — cross-era/cross-language drug-name resolution
```json
{"historical":[{"name":"甘草","lang":"zh-Hant","pinyin":"gancao",
  "readings":["licorice","Glycyrrhiza uralensis"],"modern":"Glycyrrhiza uralensis",
  "confidence":0.97,"method":"manual|lexicon|fuzzy","source_id":"..."}]}
```

### 10.4 `corpus/processed/structured/`
- `plants.csv` — `binomial,family,synonyms,tradition,source_id`
- `compounds.csv` — `name,plant_binomial,compound_class,smiles,cid,source_id`
- `uses.csv` — `plant_binomial,indication,indication_modern,tradition,preparation,source_id,evidence_grade`
- `formulas.csv` — `formula_id,formula_name,source_id`; `formula_ingredients.csv` — `formula_id,drug_name,plant_binomial,role` (role in jun/chen/zuo/shi)
- `incompatibilities.csv` — `drug_a,drug_b,rule_system` (shiba_fan | shijiu_wei | viruddha),`source_id`
- `processing.csv` — `drug_name,process_term,process_modern,effect,source_id`

### 10.5 Canonical CLI (frozen — `story-builder` may quote these verbatim)
```
python -m shennong.cli cai   --corpus-dir corpus/processed
python -m shennong.cli zhi   --corpus-dir corpus/processed
python -m shennong.cli pei   --corpus-dir corpus/processed [--out-kg PATH]
python -m shennong.cli shi   --n 12 [--class CLASS] [--out PATH]
python -m shennong.cli ask   "question"
python -m shennong.cli report [--out eval/report.json]
```
App data contract: `cli shi --out app/data/hypotheses.json`,
`cli pei --out-kg app/data/kg.json`, `cli cai --out-passages app/data/passages.json`.
`make app-data` runs all three. The Workbench reads those files plus
`corpus/registry/sources.yaml`, `eval/report.json`, `training/runs/*/metrics.json`.

### 10.6 `training/runs/<run_id>/metrics.json`
```json
{"run_id":"...","created_at":"...","config":{},"params":15000000,"tokens_seen":30000000,
 "steps":4000,"wall_clock_s":12000,"final_train_loss":3.4,"final_val_loss":3.6,"val_ppl":36.6,
 "bits_per_byte":0.95,"tokens_per_s":2500,"seed":1337,"torch_version":"2.2.2",
 "loss_curve":[{"step":0,"loss":9.1,"val_loss":null,"lr":0.0003}]}
```
`loss_curve` is what the Workbench plots and what goes on slide 5.

### 10.7 `eval/report.json`
```json
{"generated_at":"...","corpus":{"sources":0,"chars":0,"languages":{},"traditions":{}},
 "benchmarks":{"name":{"score":0.0,"n":0}},
 "hypotheses":{"n":0,"by_class":{},"mean_novelty":0.0},
 "negative_controls":{"quxiangbilei":{"rho":0.0,"p":0.0},
                      "ayurveda_rasa":{"rho":0.0,"p":0.0},
                      "null_model":{"score_drop":0.0}}}
```

---

# §11. v3 DIRECTION — "drug creation, grounded in Asian science" (supersedes where it conflicts)

## 11.1 The goal, restated exactly

> **Read the entire pre-modern Asian record of medicine, herbs and science — and use it, through Asian
> scientific frameworks, to propose new drugs and new pharmacological breakthroughs.**

Three consequences, and they are not optional:

1. **The output is a drug candidate, not an answer.** The terminal artefact of SHENNONG is a ranked
   shortlist of **leads → candidate molecules/extracts → development paths**, each with a mechanism,
   a scaffold, a novelty claim against modern chemistry, and the assay that would advance or kill it.
   Hypothesis dossiers remain, but they serve the candidates.
2. **Asian science is the method, not the decoration.** The classical theoretical systems are
   **first-class predictive frameworks** to be used and *tested*, not background colour:
   - TCM: 四氣五味 (four natures × five flavours), 歸經 (channel/organ tropism), 升降浮沉
     (directional action), 君臣佐使 (formula roles), **七情** (the seven relations of combination:
     單行, 相須, 相使, 相畏, 相殺, 相惡, 相反), 炮制 (processing), 五行 (five phases), 取象比類.
   - Ayurveda: **rasa / guṇa / vīrya / vipāka / prabhāva** (taste, quality, potency, post-digestive
     effect, specific action), tridoṣa (vāta/pitta/kapha), dhātu, srotas, the 20 guṇas, viruddha.
   - Alchemy: 丹/rasaśāstra process theory, 三品 (three grades) classification, 七情 of minerals.
   We therefore treat "cold, bitter, enters the Liver channel" as a **feature vector** that we test for
   predictive power against measured chemistry and target biology. Where it predicts, we have a
   validated non-Western discovery engine. Where it does not, we say so with numbers.
3. **"All ancient texts" includes ancient *science*, not only medical texts.** The corpus expands to
   agriculture, food/dietary therapy, technology/chemistry, botany and natural philosophy, because
   these carry the processing, extraction and material knowledge that medicine used.

## 11.2 Corpus expansion (in addition to §5)

**Chinese science / technology / agriculture / botany / dietetics (Tier 2/3):**
天工開物 *Tiangong Kaiwu* (1637 — technology, chemistry, metallurgy, materials) · 齊民要術 *Qimin
Yaoshu* (agriculture, food processing, fermentation) · 夢溪筆談 *Mengxi Bitan* (science, natural
observation) · 農政全書 *Nongzheng Quanshu* · 救荒本草 *Jiuhuang Bencao* (famine plants) ·
植物名實圖考 *Zhiwu Ming Shi Tukao* (botany, 19th c.) · 廣群芳譜 · 飲膳正要 *Yinshan Zhengyao*
(Yuan dietary medicine) · 食療本草 (dietary materia medica) · 海藥本草 (foreign/imported drugs —
critical for cross-tradition contact) · 本草拾遺 · 新修本草 · 炮炙大法 · 雷公炮炙論.

**Indian science / botany / pharmacy:** Vṛkṣāyurveda (plant science), Arthaśāstra (materials and
poisons chapters), Rasa Ratna Samuccaya, Rasaśāstra compendia, nighaṇṭu corpus, Bhela Saṃhitā.

**Arabic/Persian science:** Ibn Sīnā *al-Qānūn* + *Kitāb al-Shifāʾ* (natural philosophy), al-Dīnawarī
*Kitāb al-Nabāt* (botany), Ibn al-Bayṭār *al-Jāmiʿ*, al-Rāzī *al-Ḥāwī*, and *ʿUyūn al-Anbāʾ*.

**Tibetan / SE Asian:** rGyud-bzhi, Tibetan materia medica (where openly licensed), Thai and
Vietnamese royal pharmacopoeias if public domain.

Each still needs: PD licence or open licence + evidence URL, or `unverified` and excluded.

## 11.3 New structured artefacts (extend §10.4)

- **`properties.csv`** — TCM/Asian property vectors per drug:
  `drug_name,plant_binomial,nature(寒/熱/溫/涼/平),flavors(辛/甘/酸/苦/鹹/淡/澀),channels(歸經),
  direction(升/降/浮/沉),toxicity(有毒/無毒),grade(上/中/下品),source_id`
- **`ayurveda_properties.csv`** — `drug_name,plant_binomial,rasa,guṇa,vīrya,vipāka,prabhāva,doṣa_effect,source_id`
- **`relations_seven.csv`** — the 七情 combination relations: `drug_a,drug_b,relation` where relation ∈
  {xiangxu 相須, xiangshi 相使, xiangwei 相畏, xiangsha 相殺, xiange 相惡, xiangfan 相反}, `source_id`
- **`compounds.csv` must carry SMILES** — this is now on the critical path, because drug candidates are
  molecular. Source SMILES from PubChem PUG-REST by name (batch, cached, rate-limited); where a
  compound has no structure, leave it null rather than inventing one.

## 11.4 New discovery class (the top of the pyramid)

**`drug_candidate` — lead → candidate molecule → development path.** For each promising lead:
```
classical lead (drug, part, 炮制, formula role, Asian property vector)
   → chemotype (compound classes with measured/known structures)
   → candidate molecule(s) with SMILES + calculated properties (MW, logP, HBD/HBA, TPSA, rings,
     rotatable bonds, Lipinski/Veber flags)
   → novelty vs modern chemistry (not present / not annotated for this target in ChEMBL-type data)
   → proposed mechanism (target class, pathway) + Asian-theory justification (why 性味歸經 predicts it)
   → development path (which assay, which model organism, what would make it a real lead)
   → residual risk (toxicity class, PAINS/assay-interference liability, solubility)
```
This is what the judges should see first: **a shortlist of new drug leads derived from Asian classical
texts.** Emit `artifacts/drug_candidates.json` + `artifacts/drug_candidates.md` (top 10–20).

## 11.5 Evaluation changes (the experiments become central, not "controls")

Promote the theory tests from "negative controls" to **the central scientific experiment**:

1. **`theory_predictivity`** — do Asian property vectors predict modern molecular/target properties
   above chance? Test at least: does 四氣五味 predict compound polarity/volatility/thermolability?
   Does 歸經 (channel tropism) predict target organ or receptor family? Does Ayurvedic vīrya
   (hot/cold) predict thermolability or logP? Does tridoṣa effect predict inflammatory vs metabolic
   action? Report ρ / AUC / p with n, plus a permutation null. **A positive result is the headline
   finding; a null result is an honest and still publishable negative.**
2. **`candidate_novelty`** — fraction of proposed candidates not already in the modern drug/literature
   space; explicit method for computing it.
3. **`candidate_plausibility`** — expert-style rubric scored by explicit criteria (structure validity,
   target plausibility, synthetic accessibility, toxicity risk), with the rubric published.
4. Retain the null-model edge-shuffle check and the refusal/hallucination benchmark.

`eval/report.json` gains a `drug_discovery` block:
```json
"drug_discovery":{"candidates":0,"mean_novelty":0.0,
  "theory_predictivity":{"tcm_nature":{"metric":"auc","value":0.0,"n":0,"p":0.0},
                         "tcm_channel":{"metric":"auc","value":0.0,"n":0,"p":0.0},
                         "ayurveda_virya":{"metric":"rho","value":0.0,"n":0,"p":0.0}},
  "lipinski_pass_rate":0.0}
```

## 11.6 Pitch changes

The deck and Devpost now lead with: **"We read 2,000 years of Asian medical and scientific literature
and produced N new drug candidates, grounded in Asian pharmacological theory — and we tested whether
that theory actually predicts chemistry."** That is a drug-discovery story with a falsifiable core,
which is exactly the EthnoHack track-01/02 intersection.
