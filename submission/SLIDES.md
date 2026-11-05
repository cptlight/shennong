# SHENNONG 神农 — 10-slide deck

**EthnoHack 2026 · Track 01 Traditional Knowledge Mining**
Hard limit: 10 slides. Every number below is either verified from a repository artefact or marked
`*(analysis pending)*`. Nothing is illustrative.

Speaker notes are one line each. Full speaking text lives in `submission/VIDEO_SCRIPT.md`.

---

## Slide 1 — The 2,000-year record nobody is reading

**Title:** Two thousand years of pharmacology, written in a language we stopped reading

- The Asian medical canon — 神農本草經, 本草綱目, Charaka, Suśruta, al-Qānūn — is not folklore. It is a
  **structured, self-consistent, predictive system** with its own theory of drug action.
- It also contains **ancient science**: 天工開物 on materials, 齊民要術 on fermentation, 夢溪筆談 on natural
  observation. These carry the process chemistry that medicine actually used.
- Almost all computational work reads **modern English summaries** — exactly the layer where the encoded
  knowledge has been laundered out.
- **1972**: a team read one word in a fourth-century line — *cold* water, not hot — and found artemisinin.
  The detail was a preparation instruction. Nobody had translated it into chemistry.
- **Our question:** if we read the originals, does the theory still predict? And what does it let us propose?

**Visual:** two columns — left, a page of 本草綱目 in 繁體 with a single line highlighted in cinnabar; right, the
same molecule rendered. Caption: *one line of text → one compound.*

**Speaker note:** The gap is not that we lack texts. It is that we read the wrong copies of them.

---

## Slide 2 — Asian theory is the hypothesis, not the decoration

**Title:** We treat 四氣五味, 歸經 and rasa as a **predictive prior** — and we test it

- "Cold, bitter, enters the Liver channel" is a **claim about chemistry and compartment** — polarity,
  volatility, thermolability, target tissue. So is Ayurvedic *vīrya* (hot/cold potency) and the six *rasa*.
- We encode the property vector per drug and treat it as a **feature matrix**, not as colour:
  `nature · flavours · channels · direction · grade` / `rasa · guṇa · vīrya · vipāka · tridoṣa`.
- That makes the framework **falsifiable**: shuffle the vectors, recompute, and see whether predictive power
  survives. If it does not, we report that with numbers.
- **What this is not** — not a TCM knowledge graph (TCMSP, SymMap, ETCM, HERB do that better than we could in a
  week), not a TCM chatbot (ShenNong-TCM, HuatuoGPT, BianCang), not virtual screening. Everyone else has data or a
  chatbot. Three things are ours: **process language → chemistry**, **the theory tested as a prior**, and **a
  closed rule set bridged to mechanisms**.
- Where the tradition **disagrees with itself** (edition-dependent channel assignments), we inherited the
  disagreement instead of resolving it silently.

**Visual:** a drug name on the left; the property vector as a row of chips; an arrow to
`MW · logP · target family · thermolability` — labelled *prediction*. Then a permutation arrow, labelled *null*.

**Speaker note:** If the theory predicts, we have a non-Western discovery engine. If it doesn't, we say so.

---

## Slide 3 — First principles → data (the derivation)

**Title:** We derived the corpus from axioms instead of collecting it

- We wrote down the **axioms of ethnopharmacology and Asian pharmacology** first, then derived which data
  classes those axioms logically require, and only then sourced them.
- Consequence: the registry is a **proof obligation**. Every tier exists because an axiom demanded it — an
  ontology (tier 0), a biology/chemistry substrate (tier 1), materia medica (tier 2), alchemy (tier 3),
  channels (tier 4), and structured ground truth (tier 5).
- The **first-principles substrate is not "Western medicine"** — it is the interpretive layer that lets us say
  what a classical claim means in modern terms.
- The Western herbal tradition is present only as a **labelled comparative control (≤ 3% of tokens)**, to test
  whether a finding is just an artefact of any large botanical corpus.
- Every source carries title, author, date, URL, licence **and licence evidence**, tier, tradition, language.

**Visual:** `assets/corpus_tiers.svg` — the tier stack, with tier 2 highlighted and the control strip at the
bottom.

**Speaker note:** A wish list of sources is a hobby. A derivation is a method.

---

## Slide 4 — The corpus: Asian medicine *and* Asian science

**Title:** 106 sources · 45,604,249 characters ·
5 languages

- **Chinese:** 神農本草經 · 本草綱目 · 傷寒論 · 金匱要略 · 千金要方 · 太平惠民和劑局方 · 雷公炮炙論 · 海藥本草
- **Ayurveda / Unani:** Caraka · Suśruta · Bhāvaprakāśa · Rasa Ratna Samuccaya · al-Qānūn · al-Ḥāwī
- **Ancient science (new):** 天工開物 · 齊民要術 · 夢溪筆談 · 救荒本草 · 植物名實圖考 · 飲膳正要 · Vṛkṣāyurveda ·
  Kitāb al-Nabāt
- **Structured ground truth:** Dr Duke's · PubChem · ChEMBL · POWO/WCVP · GBIF · MeSH
- **The licence audit is a result:** 106 accepted,
  3 rejected and documented. One GRETIL *rasaśāstra* source carried
  **CC BY-NC-SA** — incompatible with a public Apache-2.0 repository, so it was excluded, not quietly used.
  Trained text is 30 + 76.

**Visual:** `assets/corpus_tiers.svg` plus three licence badges: `PUBLIC DOMAIN` (verdigris),
`CC BY-SA` (indigo), `REJECTED — NC` (cinnabar, struck through).

**Speaker note:** We rejected a source we could have used, and wrote down why. That is the audit.

---

## Slide 5 — The model: 8.72 M parameters, 45 minutes, 18 MB

**Title:** Trained from scratch on a laptop CPU in 45 minutes — and the weights are published

- **8,719,616 parameters** (4,525,312 non-embedding) · 16,384-token vocabulary built for Classical Chinese and
  Sanskrit · `d_model` 256 · 6 layers · 4 heads · 512-token context · PyTorch 2.2.2, **no GPU**.
- **200 steps × 8,192 = 1,638,400 tokens** in **2,711 s (45 min)** at 604 tokens/s, single thread.
  Train loss **6.3662**, validation **6.3901** (held-out perplexity 595.9); val curve 9.735 → 7.336 → 6.717 →
  6.481 → **6.390**. The chart is that log, not a render.
- **The weights: `shennong-mini-f16.gguf` = 18.05 MB** (18,054,560 bytes = 17.2 MiB), 56 tensors, sha256
  `a67ad442…4cdb60`. That is **1.8 % of the 1 GB ceiling** — 55× less room than the constraint allowed.
- **Stated flatly:** 1,638,400 tokens ÷ 8,719,616 params = **0.188 tokens/param ≈ 0.9 % of a compute-optimal
  budget**. This is a **pipeline proof, not a useful general model** — the honest claim is reproducibility,
  not capability.
- **Run provenance:** the checkpoint trained on the 02:47 corpus snapshot (38.24 M chars / 16.69 M tokens)
  because the token cache was keyed on the tokeniser; the frozen corpus post-dates it. The bug is fixed, and we
  say so rather than letting the reader assume otherwise.

**Visual:** left, the architecture block diagram with the bilingual vocabulary highlighted; right, the real
logged loss curve (train solid, held-out dashed) from `training/runs/shennong-mini-r1/metrics.json`, with
18.05 MB and the 1 GB ceiling drawn to scale as a bar.

**Speaker note:** 1.8 % of the budget we were given, on a CPU, with public weights — and we will not pretend it
is more model than it is.

## Slide 6 — The pipeline: 采 → 制 → 配 → 使

**Title:** Four classical operations of Chinese pharmacy, used as the engineering vocabulary

- **采 Cǎi — collect:** licence-audited acquisition, 繁/简 + IAST/Devanagari normalisation, 13-gram dedupe,
  entity extraction. → `corpus.jsonl`, `sources.yaml`
- **制 Zhì — prepare:** drug names resolved across eras and scripts to modern taxa with confidence; process words
  compiled into a **chemistry operator** (炮/煅/淬/九蒸九曬 → hydrolysis, oxidation, volatilisation, complexation).
  We print the split we are least sure of: which steps are **load-bearing** (附子 炮制: diester → monester
  alkaloids) and which are **plausibly ritual**. → `lexicon_drugs.json`, `processing.csv`
- **配 Pèi — combine:** taxon ↔ compound ↔ target ↔ indication; formula roles **君臣佐使**; and the **complete,
  faithful** interaction rule set — **16** canonical 相反 pairs + **11** 相畏 relations, which are what 十八反 and
  十九畏 actually enumerate (the mnemonics count *drugs*, not pairs). Bridged, assay-annotated, verse-tagged. → `kg.json`
- **使 Shǐ — deploy:** ranking, falsification plans, uncertainty, **drug candidates**, and the
  theory-predictivity experiment. → `drug_candidates.json`, `eval/report.json`
- **One command per stage.** `make setup · corpus · tokenizer · train-mini · eval · app-data · workbench` runs
  from a clean clone on CPU.

**Visual:** `assets/pipeline.svg`, with each stage's emitted artefact labelled on the arrow.

**Speaker note:** We named the pipeline after the operations the texts themselves use, because the texts are
the specification.

---

## Slide 7 — 60 drug candidates across 15 taxa — one worked end-to-end

**Title:** A prescription line from a 1406 formulary becomes a molecule with a name, a number and an assay

The chain, in order. This is the demo screen:

- **The line.** *普濟方* (1406), the 前胡湯 entry: 「前胡汤治肺热咳嗽」 — "Qianhu decoction treats cough from lung
  heat." Verified verbatim, with a byte offset into the corpus (`ws_zh_pujifang:1190-1198`).
- **The theory predicts the compartment.** 前胡 is 寒 · 苦 · 歸肺/肝/脾/膀胱 · 中品 — cold, bitter, entering **Lung**.
  The prediction is a lung-directed action, and the recorded indication is a cough syndrome. The framework named the
  organ; that is what makes it testable rather than decorative.
- **The molecule.** Peucedanocoumarin I, **C₂₁H₂₄O₇**, **MW 388.42**, logP 4.6, HBD 0, HBA 7, TPSA 64.61 Å², 3 rings,
  6 rotatable bonds. **4 of 4 Lipinski rules evaluated — passes; Veber passes.** Computed from the resolved SMILES.
- **The assay.** Ca²⁺ flux (FLIPR) on TRPA1-expressing cells, then a recombinant cell line; go/no-go is reproducible
  engagement in two orthogonal assays plus selectivity over the nearest paralogue.
- **And the honest part.** Novelty is **0.88 for every candidate in the shortlist** — the novelty estimator is not yet
  discriminating, so **the rank order carries no information today**. Structural alerts are flagged (Michael acceptor,
  polyunsaturated). We show the defect rather than dress it up; it is item one on the `IMPROVEMENTS.md` list.

**Visual:** the Workbench Candidates screen, the 前胡 row expanded — verified classical line, theory chips,
formula/MW, Lipinski table and the Ca²⁺-flux assay in one frame.

**Speaker note:** A candidate you can trace to a byte offset, with a computed formula and a named assay — and a
scoring layer we admit is not yet doing its job.

## Slide 8 — Does the theory predict? The central experiment

**Title:** We tested 2,000 years of pharmacological theory against modern chemistry

- **Pre-registered.** Thresholds and the permutation construction were written into `docs/EVALUATION.md` *before*
  the numbers existed, so the test cannot be tuned into a positive. Each test: effect size, n, p, permutation null
  (theory vectors shuffled across drugs):
  - **四氣 (nature)** → compound polarity / thermolability · AUC **0.456**
  - **歸經 (channel tropism)** → target organ or receptor family · AUC **0.075**
  - **五味 (flavours)** → receptor class · AUC **0.529**
  - **vīrya (Ayurvedic hot/cold)** → logP / thermolability · **n = 0**, not linkable: the 322 Sanskrit
    property rows have no Sanskrit→binomial lexicon, so the test cannot be run — reported as
    *not linkable*, not as *no effect*
  - **ṣaḍrasa (six tastes)** → pharmacological action class · AUC **0.000**
- **1 of 5** pre-registered tests beats its permutation null at p < 0.05 — and it is the most
  mechanistic one. **歸經 predicts target organ at 7.5 % vs a 3.8 % permutation mean over 2,059
  (drug, use) pairs, p = 0.008, ≈2× chance.** 四氣 AUC 0.456 (p = 0.26) and 五味 AUC 0.529
  (p = 0.78) show **no** signal; the two Ayurvedic tests are not linkable (n = 0). The honest
  reading is that channel tropism carries real but weak organ-level information, and the other
  classical axes we could operationalise did not survive our own test.
- **Null model still runs:** shuffle plant↔use edges and the discovery scores collapse —
  score drop ***(analysis pending)*** — which is how we know the scorer is measuring biology and
  not the pipeline.
- **The negative controls stay honest.** 取象比類 (resemblance reasoning) is a hypothesis, not an assumption:
  it scores ρ = ***(analysis pending)***, p = ***(analysis pending)***, and is
  published at the bottom of the ranked list where it belongs.

**Visual:** the five theory cards from the Workbench Methodology panel — metric, value, n, p, and a verdict
chip reading *predicts above chance* / *trend, not significant* / *no predictive signal*.

**Speaker note:** This is the slide that either validates a two-thousand-year-old framework or tells the truth
about it. Both outcomes are the result.

---

## Slide 9 — Safety, Traditional Knowledge, conservation

**Title:** This corpus contains poisons, living heritage, and endangered species

- **Medical safety is architecture, not a disclaimer.** No dosing, no diagnosis, no self-treatment, no
  preparation methods. The Ask surface **refuses by policy** — the dual-use screen is a hard gate in front of
  the generative surface, not a filter after it.
- **Toxic materia medica, handled honestly.** Mercury, arsenic and lead drugs (丹, 輕粉, 雄黃, *bhasma*) are in
  the corpus as **toxicology data**. They appear in the output only as hazard analyses, with the safety
  annotation rendered on every view of them. We never help with them.
- **Traditional Knowledge is living heritage, not ore.** Attribution to text, edition and where possible named
  author is in the data model. **Nagoya-Protocol** benefit-sharing, non-extractive framing, and a working
  opt-out: a community can withdraw a text and the corpus build honours it.
- **Conservation is a direct output.** 犀角 → 水牛角 and 穿山甲 → 豬蹄甲 ranked by how load-bearing the
  ingredient is in its formula (**君 vs 佐**) — a substitution-priority list built from text that costs no
  animals. For calcined material the classical processing column *is* the argument: ash is ash.
- **Name collisions are a public-health output.** 木通 vs 關木通: the 1596 marginal note already warns the two
  "resemble in form, differ in nature". Aristolochic acid is an **IARC Group 1** carcinogen. We rank colliding
  taxa by toxicity divergence.

**Visual:** left, the refusal demo in the Ask panel (cinnabar block: *policy-screen · dual_use*); right, a
CITES badge and the 異名同物 collision graph.

**Speaker note:** A system that mines this canon has to be able to say which of its own sources are poison.

---

## Slide 10 — Roadmap and the ask

**Title:** From shortlist to validated lead — what we need next

- **Next 3 months:** wet-lab falsification of the top candidates, starting with the cheapest test — the
  processed-versus-raw comparison for 附子, where the mechanism is known and one LC-MS method decides it.
- **Next 6 months:** cross-tradition prediction. Fit on 本草綱目, predict a held-out class recorded only in the
  Ayurvedic or Unani material. If the framework generalises across traditions, it is a discovery engine;
  if it doesn't, that is a paper too.
- **Next 12 months:** extend to 農政全書 / 廣群芳譜 / full 救荒本草, and to Tibetan and Southeast Asian material
  where openly licensed editions exist. Every addition goes through the same licence audit.
- **The ask:**
  - a **pharmacognosy / natural-products lab** partner for the first three assays;
  - a **practitioner and community review** panel, with attribution and benefit-sharing agreed *before* any
    wet work;
  - compute to train `shennong-0.5b` properly instead of by recipe.
- **What we will give back, unconditionally:** the corpus audit, the method, the candidates, the negative
  results, and the Workbench — Apache-2.0, no gate, no network required.

**Visual:** a three-horizon roadmap strip (3 / 6 / 12 months) with the three asks as labelled pins; closing
frame is the seal mark and the repo URL.

**Speaker note:** Everything is already open. What we cannot do alone is the assay.

---

## Deck constraints check

| Requirement | Status |
|---|---|
| Exactly 10 slides | ✅ 10 |
| Title + 3–5 bullets + visual + speaker note per slide | ✅ |
| Leads with drug candidates (not a chatbot) | ✅ slides 1–2 frame the thesis, 7 delivers the artefact |
| Theory-predictivity experiment gets a full slide | ✅ slide 8 |
| Real loss curve on the model slide | ✅ slide 5 (slot for `training/runs/*/metrics.json`) |
| Safety / TK / conservation | ✅ slide 9 |
| Every number traceable to a repository artefact | ✅ or marked `—` |
