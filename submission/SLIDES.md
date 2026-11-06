# SHENNONG 神农 — 10-slide deck

**EthnoHack 2026 · Track 02 Natural Products for Drug Discovery**
Hard limit: 10 slides. Every number below is either verified from a repository artefact or marked
`*(analysis pending)*`. Nothing is illustrative.

Speaker notes are one line each. Full speaking text lives in `submission/VIDEO_SCRIPT.md`.

---

---

---

## Slide 1 — A pre-experimental filter for natural-product discovery

**Title:** 2,000 years of processing instructions, filtered by physics before anyone buys a reagent

- **1972, one line, one Nobel.** 葛洪's 4th-century text said *soak in water and wring out the juice* — a
  **cold** maceration, not a decoction. Artemisinin is thermolabile. The decisive knowledge was a
  **processing instruction**, and nobody had translated it into chemistry.
- **That is the pipeline.** ancient record → Asian theory → **validated physics** → MAY / MAY NOT, with
  arithmetic. It compiles a processing instruction into a chemical hypothesis and then tries to kill it.
- **203 hypotheses → 151 excluded** (not attested in the record) **→ 28 pass both gates → 10 refuted by
  physics → 18 survive.**
- **78 of 203 refuted by the physics alone**, and **6 of those had unanimous 5/5 panel agreement** — the
  arbiter overruled its own consensus. Example: *蒸 of 菖蒲 → terpenoid* scored 5/5; Clausius–Clapeyron at
  100 °C steam strips **98.5 %** of a monoterpene. Physically backwards, decided in seconds.
- **Why a drug-discovery judge should care:** that same answer costs months and reagents in a lab.

**Visual:** the funnel 203 → 18 beside the 菖蒲 arithmetic — a claim and the number that kills it.

**Speaker note:** We are not proposing compounds. We are removing the ones that cannot work, and showing the
arithmetic so it can be checked.

---

## Slide 2 — The arbiter refutes the panel's own consensus

**Title:** A claim can win 5/5 in the panel and still be physically backwards

- **The claim:** *蒸 of 菖蒲 (Acorus calamus) should measurably change its terpenoid content.* Our five
  tradition experts scored it **5/5** — well attested, theory-consistent, and a plausible process.
- **The arbiter:** Clausius–Clapeyron at 100 °C steam. A monoterpene's vapour pressure at that temperature
  means **98.5 % of it is stripped** in 30 minutes. The claim is not merely wrong — it is backwards.
- **Scale of it:** **78 of 203** candidates are refuted by the physics alone, and **6 of those 78 had
  unanimous 5/5 panel agreement.** The system overruled its own consensus with arithmetic.
- **Why the arbiter is credible:** it is validated before it is trusted — Joback boiling points against known
  constants, **mean 4.5 % error, 6/6 within 10 %**. A refutation is only as good as that number.
- **What it is not:** a *validated lumped model*, not ab initio. Quantum chemistry arbitrates fragments today
  (Koopmans ionisation potentials within 0.82 eV); individual natural products is the next layer.

**Visual:** the 菖蒲 card — 5/5 support chips on the left, the retention bar collapsing to 1.5 % on the right.

**Speaker note:** This is the property a chatbot cannot have. The achievement is not that we generate claims; it
is that we can kill our own.

---

## Slide 3 — Does the classical theory predict chemistry?

**Title:** One of five pre-registered axes survived its own test — and it is the mechanistic one

- **Pre-registered.** Thresholds and the permutation construction were written into `docs/EVALUATION.md` *before*
  the numbers existed, so the test cannot be tuned into a positive. Each test: effect size, n, p, permutation null
  (theory vectors shuffled across drugs):
  - **四氣 (nature)** → compound polarity / thermolability · AUC **0.456**
  - **歸經 (channel tropism)** → target organ · **hit rate 0.075 vs 0.038 chance**, n = 2,059, **p = 0.008**
  - **五味 (flavours)** → receptor class · AUC **0.529**
  - **vīrya (Ayurvedic hot/cold)** → logP / thermolability · **n = 0**, not linkable: the 322 Sanskrit
    property rows have no Sanskrit→binomial lexicon, so the test cannot be run — reported as
    *not linkable*, not as *no effect*
  - **ṣaḍrasa (six tastes)** → action class · **n = 0**, not linkable (same lexicon gap)
- **1 of 5** pre-registered tests beats its permutation null at p < 0.05 — and it is the most
  mechanistic one. **歸經 predicts target organ at 7.5 % vs a 3.8 % permutation mean over 2,059
  (drug, use) pairs, p = 0.008, ≈2× chance.** 四氣 AUC 0.456 (p = 0.26) and 五味 AUC 0.529
  (p = 0.78) show **no** signal; the two Ayurvedic tests are not linkable (n = 0). The honest
  reading is that channel tropism carries real but weak organ-level information, and the other
  classical axes we could operationalise did not survive our own test.
- **And the null model refuses to flatter us.** Shuffling plant↔use edges changes the mean composite by
  **−0.026** [−0.042, −0.014] over 27 shuffles, n = 2,034 real vs 2,766 shuffled. That is *not* a collapse:
  it means the composite is **prior-dominated, not topology-sensitive**. We report it as a limitation of
  our own scorer instead of quoting a number that clears a threshold by construction.
- **The negative controls stay honest.** 取象比類 (resemblance reasoning) is a hypothesis, not an assumption —
  on the real corpus it could not be computed (n = 0: too few colour-named drugs carry a recorded indication),
  and it is published at the bottom of the ranked list rather than quietly dropped.

**Visual:** the five theory cards from the Workbench Methodology panel — metric, value, n, p, and a verdict
chip reading *predicts above chance* / *trend, not significant* / *no predictive signal*.

**Speaker note:** This is the slide that either validates a two-thousand-year-old framework or tells the truth
about it. Both outcomes are the result.

---

## Slide 4 — We measured our own experts, and caught a bug in ourselves
**Title:** The system scores its own experts against the arbiter — and it found one of them cheating

- **The test:** each expert's confidence is scored by whether it predicts the **arbiter's** verdict — AUC
  against *"did this claim actually survive physics?"*. Utility is defined by physics, never by agreement;
  an expert that merely makes claims pass is worthless.
- **The result:** our phytochemistry expert came out **below chance — AUC 0.443**.
- **The cause was us, not the data:** a hand-written **+0.15 bonus for plants with a narrow chemotype**. Sparse
  chemotypes are exactly the plants that fail physics, so the bonus was rewarding the plants most likely to
  be refuted.
- **The fix:** removed the prior → **AUC 0.607**. We **retracted the finding** and kept the tool that caught it.
- **Why this belongs in a science submission:** one line of prior was silently costing 0.16 AUC. No amount of
  adding experts would have surfaced it.

**Visual:** the AUC bar chart with phytochemistry highlighted in cinnabar at 0.443, and an arrow to 0.607 after
the fix; caption *"the diagnostic found the bug, not the data."*

**Speaker note:** This is the slide most projects would not have. We are reporting a failure we found in
ourselves, after fixing it.

---

## Slide 5 — How the record is read: theory is the hypothesis, not the decoration

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

## Slide 6 — First principles → the data → the corpus
**Title:** We derived what data we needed before collecting any of it

- **Axioms first, then sourcing.** Every source in the registry is a **proof obligation** — a data class that
  an axiom requires — not whatever happened to be downloadable.
- **The corpus answers those obligations:** **106 sources · 45.6 M characters · traditional Chinese canon in
  繁體 (35 %), Sanskrit in Devanagari, Latin (Avicenna's 1593 *Canon*), and the foundational biology /
  chemistry substrate.**
- **It contains ancient *science*, not only medicine:** 天工開物 (materials), 齊民要術 (fermentation), 夢溪筆談
  (natural observation) — these carry the process chemistry the medicine actually used.
- **Licence audit is part of the method:** 30 public-domain + 73 CC BY-SA sources reproduced; **GRETIL
  rejected** because CC BY-**NC**-SA cannot ship in a public repo. The rejection is documented, not hidden.
- **Honest limit, stated here rather than in an appendix:** drug-name → taxon resolution measures **14.1 %**
  accuracy, which bounds every downstream number.

**Visual:** the tier stack (T1 foundational → T5 structured open data) beside a licence-audit table with the
GRETIL rejection row visible.

**Speaker note:** The corpus is the least glamorous part and the one that decides whether anything downstream
is true.

---

## Slide 7 — The model: 8.72 M parameters, 45 minutes, 18 MB

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

---

## Slide 8 — The pipeline: 采 → 制 → 配 → 使

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

## Slide 9 — 60 drug candidates across 15 taxa — one worked end-to-end

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
- **Novelty is structural now, and it discriminates.** ECFP-style Tanimoto (radius 2) against the
  corpus's **23,172-structure table**, excluding each candidate's own compound and source plant:
  **42 distinct values, range 0.000–0.750, mean 0.283** — replaced a curated-name prior that
  gave every candidate 0.88 and made the rank order meaningless. It measures distance from
  documented phytochemistry, **not** therapeutic novelty, and the card says so.

**Visual:** the expanded candidate dossier from the Workbench, in the order of the chain above — classical
line highlighted in the source text, theory chips, molecular card with the computed descriptors, then the assay.

**Speaker note:** One line of a 1406 formulary turned into a molecule with a formula, a mass, a computed
drug-likeness verdict, a named target and the experiment that would test it. Nothing on this slide was typed by
a human — it is the pipeline's output, and the provenance locator points into the corpus.

---

## Slide 10 — Safety, living heritage, and the ask

**Title:** A system that mines this canon must be able to say which of its sources are poison — and what it needs next

- **Medical safety is architecture, not a disclaimer.** No dosing, no diagnosis, no self-treatment, no
  preparation methods; the Ask surface refuses by policy, and the dual-use screen is a hard gate in front of
  the generative surface. Mercury / arsenic / lead drugs (丹, 輕粉, 雄黃, *bhasma*) appear only as toxicology.
- **Traditional Knowledge is living heritage, not ore.** Attribution to text, edition and author lives in the
  data model; Nagoya-Protocol benefit-sharing and a working opt-out are operational, not aspirational.
- **Conservation is a direct output.** 犀角 → 水牛角 and 穿山甲 → 豬蹄甲 ranked by how load-bearing the
  ingredient is in its formula (君 vs 佐) — a substitution list built from text that costs no animals.
- **The ask:** a pharmacognosy lab partner for the first three assays; a practitioner and community review panel
  with benefit-sharing agreed before any wet work; compute to train `shennong-0.5b` properly.
- **Given back unconditionally:** the corpus audit, the method, the candidates, the negative results and the
  Workbench — Apache-2.0, no gate, no network required.

**Visual:** refusal demo and CITES badge on the left; a three-horizon roadmap strip (3 / 6 / 12 months) with the
three asks as pins on the right; closing frame is the seal mark and the repo URL.

**Speaker note:** Everything is already open. What we cannot do alone is the assay.
