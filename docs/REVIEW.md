# REVIEW — what this project actually does, mapped to the four tracks

Written so a judge (or a contributor) can see in five minutes where the real work is and where it is not.
Every claim below points at an artefact or a command.

---

## The four tracks vs. what exists

| track | asks for | what we have | status |
|---|---|---|---|
| **01 · Traditional knowledge** | NLP/AI to extract medicinal knowledge from historical texts; map plant names across eras; connect ancient knowledge to modern pharmacology | 23,177 compound mentions, 11,819 plant→indication relations, 1,402 property vectors, 45 七情 relations, 29 incompatibility rules, 827/1,027 names mapped to binomials, all span-located | **done by the pipeline** — surfaced in `artifacts/extraction_report.json` and the demo's Extraction tab |
| **02 · Natural products & drug discovery** | ML/cheminformatics, predictive models, screening pipelines | the funnel (203 → 151 → 24 → 28 → 10 → 18), a physics arbiter refuting 78/203 enrichment claims, 60 candidates with SMILES and kill criteria | **done** — the strongest, most measured part |
| 03 · Biodiversity & sustainability | geospatial/ecological data, conservation risk, sustainable harvesting | one substitution list (犀角 → 水牛角, 穿山甲 → 豬蹄甲) ranked by formula load-bearingness | **not pursued** — no geospatial data |
| 04 · Digital health & phytotherapy | apps, decision support, recommendation engines for clinical/patient contexts | the Workbench (offline, CPU-only) with a refusal policy | **deliberately thin** — no clinical validation, no patient-facing claim |

**Declared track: 02** (primary), with 01 as depth. See `docs/TRACK.md`.

---

## The honest problem, and the honest fix

For most of this project the pitch has been about the **MoE model**, and the model is a 19.3 M-parameter
transformer trained on ~5.5 M tokens — about **1.4 % of compute-optimal**. It reads the register; it does not
produce reliable text. Anyone who queries it sees that, and a judge will.

The tracks are not "have a small LLM". They are "extract, map, screen, decide". The extraction and the
screening are done — by the **deterministic pipeline**, not the weights — and for most of the project's life
that work was buried in CSVs and JSON while the demo led with the one thing that was weakest.

**The fix was not to train more** (that is a GPU problem, and the recipe exists: `make train-flagship`).
**The fix was to make the solved parts visible and measured:**

- `scripts/extraction_report.py` → `artifacts/extraction_report.json`: every extracted entity count, the
  80.5 % name-mapping resolution, and a worked relation triple (烏頭 × 半夏, 相反) traced to its verse span.
- a **Extraction & name mapping** tab on the demo, so Track 1 is judged on the work that exists.
- `docs/TRACK.md` records why Track 02 is primary and what the choice costs.

## What the LLM actually is, and is not

| is | is not |
|---|---|
| a **structured-output interface** — the fine-tune (`make sft`) taught it the Track-02 answer shape (`Nature 寒, flavours 甘, …`) with a −5.28 nat answer-only loss | a domain expert — its values on unseen herbs are wrong |
| a demonstration that a sparse MoE buys **1.58× capacity per FLOP** on CPU (`docs/COMPUTE.md`) | a NER/RE engine — that is the pipeline, and it should be |
| a **retrieval+physics system** where every answer carries a `source_id:char_start-char_end` | a chatbot — the refusal policy exists precisely because it is not one |

## What would close the remaining gaps

| gap | fix | cost |
|---|---|---|
| model capability (generation quality) | train to ~390 M tokens (`make train-flagship`) | a GPU, hours — not this machine |
| Track 03 biodiversity | add GBIF occurrence data + a conservation-risk layer | new data, a day |
| Track 04 | a clinician-reviewed decision-support card | ethics + a clinician, not code |
| name-mapping 19.5 % unresolved | extend the lexicon | manual curation |

## The five numbers to remember

1. **203 → 151 → 24 → 28 → 10 → 18** — the screening funnel (`artifacts/tradition_first.json`)
2. **78 of 203** refuted by physics, **6** despite unanimous 5/5 panel (`artifacts/consensus_vs_arbiter.json`)
3. **歸經 7.48 % vs 3.80 %**, n = 2,059, **p = 0.008** (`eval/report.json`)
4. **827 / 1,027** historical names mapped to a binomial (`artifacts/extraction_report.json`)
5. **−0.907 nats** MoE vs dense at identical token budget; **1.58× capacity per FLOP** (`artifacts/compute_budget.json`)
