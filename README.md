<div align="center">

# 神农 SHENNONG

**Shennong tasted a hundred herbs. We are teaching a 400 MB model to do it again — and to tell us what he hid between the lines.**

*A <1 GB, open-weights, classical-Asian-medicine language model and first-principles discovery engine for ethnopharmacology.*

[![Devpost](https://img.shields.io/badge/EthnoHack-2026-coral)](https://ethnohack2026.devpost.com/)
[![Track](https://img.shields.io/badge/track-01%20Traditional%20Knowledge%20Mining-teal)](https://ethnohack2026.devpost.com/)
[![Licence](https://img.shields.io/badge/code%20%26%20weights-Apache--2.0-blue)](LICENSE)
[![Model](https://img.shields.io/badge/model-<1%20GB%20%7C%20<1B%20params-green)](#the-model)
[![CPU](https://img.shields.io/badge/runs%20on-CPU%20only-lightgrey)](#quickstart)

</div>

---

## The problem

Classical Asian medical texts — 本草綱目, 神農本草經, Charaka Saṃhitā, Suśruta Saṃhitā, al-Qānūn,
the 黃帝內經, the rasaśāstra corpus — contain real, testable pharmacology encoded in a language that
modern science has never decoded:

- **process words** that specify physical chemistry (炮, 煅, 醋炙, 先煎, 後下, *śodhana*, *bhāṣma*),
- **numbered rule systems** that encode interactions (十八反, 十九畏, *viruddha*),
- **role hierarchies** inside formulas that encode synergy and bioavailability (君臣佐使, *yogavāhi*),
- **drug names** that silently change referent across eras, dialects and languages.

This is not folklore to be dismissed and not data to be grepped. It is an **untranslated record**, and
the binding constraint on discovering drugs from it has never been data volume — it is *translation*.

> **Why this matters, concretely.** In 1969 Tu Youyou found 青蒿 (*Artemisia annua*) in 葛洪's
> 4th-century 肘後備急方, but every aqueous decoction failed in the lab. The text said
> **「以水二升漬，絞取汁」** — *soak and wring out the juice*, a **cold maceration**, not a boil.
> Artemisinin is thermolabile. The decisive information was a **processing instruction**, not an
> indication. That reading led to the 2015 Nobel Prize in Physiology or Medicine.

SHENNONG builds the translation layer at scale.

## What it does

1. **采 Cǎi — collects** a licence-audited, provenance-complete corpus of the Asian medical and
   alchemical canon in the **original languages** (Classical Chinese 繁體, Sanskrit Devanagari,
   Arabic, Persian, plus public-domain translations and the foundational biology/chemistry substrate).
2. **制 Zhì — decodes.** Resolves drug names across eras and scripts into modern taxa; translates
   炮制 / alchemical process vocabulary into modern extraction chemistry; normalises historical
   orthography without modernising the text.
3. **配 Pèi — combines** into a knowledge graph: `drug ↔ compound ↔ target ↔ pathway ↔ indication`,
   formula composition with 君臣佐使 roles, and incompatibility edges from the rule systems.
4. **使 Shǐ — deploys** six classes of **falsifiable hypotheses**, each with a provenance chain to a
   real span in a real text, a novelty estimate against the modern literature, an explicit
   uncertainty, and **the experiment that would kill it**.

## What is actually new here (the honest version)

We are **not** claiming a TCM knowledge graph, a TCM chatbot, another entity-extraction paper, or
Lipinski filtering — those are commodities, and TCMSP/SymMap/ETCM already curate better graphs than we
could build in a week. ([`docs/NOVELTY.md`](docs/NOVELTY.md) does the full subtractive analysis, and
we are explicit that a 2023 project named *ShenNong-TCM* exists — a TCM assistant; different goal,
not affiliated.)

Four things are ours:

1. **We test the classical theory as a predictive framework.** Everyone *uses* 四氣五味 · 歸經 ·
   rasa/guṇa/vīrya as features. We ask the prior question and report the answer with a permutation
   null: **does the classical property system predict measured molecular chemistry and target biology
   above chance?** Pre-registered thresholds, published either way. This is the only claim here that
   can be wrong in an interesting way — and it is the number that matters.
2. **Process language compiled into a chemistry operator.** 炮 · 煅 · 煨 · 淬 · 醋炙 · 水飛 · 發酵 ·
   *śodhana* · *bhasma* are an instruction set for physical chemistry that modern NLP discards. We
   compile each term to what it does to a molecule (hydrolysis, decarboxylation, volatilisation,
   esterification, complexation) and use it **generatively**: which constituents does a preparation
   destroy or enrich, and is the traditional step *load-bearing* or *plausibly ritual*?
3. **Rules as a finite, bridged, testable set.** All 18 十八反 + 19 十九畏 pairs (+ *viruddha*),
   enumerated with citations, each bridged to a modern mechanism (CYP450, P-gp, chelation,
   precipitation, shared toxic constituents) and given the assay that would kill it. Completeness is
   the contribution.
4. **Auditable by construction.** < 1 GB open weights that run on a CPU; every claim resolves to a
   span in a real text; a hypothesis whose citation fails to resolve is **dropped, not softened**; and
   the licence audit includes the sources we *rejected* (GRETIL, because CC BY-**NC**-SA cannot ship
   in a public repo).

> **The one sentence:** everyone else built a chatbot over ancient Asian medicine. We built the
> missing translation layer — and tested whether the classical theory actually predicts chemistry,
> because that is what turns 2,000 years of text into drug candidates.

## The six discovery classes

| # | Class | The hidden thing | Why it matters |
|---|---|---|---|
| 1 | **配伍禁忌** `incompatibility` | 十八反 / 十九畏 / *viruddha* interaction rules | herb–herb and herb–drug interaction prediction |
| 2 | **炮制** `processing` | process → chemistry: what a preparation destroys, enriches or conjugates | explains *why* the old protocol was necessary — and which modern products skip it |
| 3 | **異名同物** `name_collision` | drug names whose referent drifted across eras | adulteration safety (the *Aristolochia* nephropathy case) |
| 4 | **君臣佐使** `formula_role` | the courier 使 herb as hidden pharmacokinetics | synergy and bioavailability, from formula structure |
| 5 | **未研究本草** `understudied` | strong multi-tradition use, zero modern mechanistic study | the abandoned-lead screening list |
| 6 | **瀕危代用品** `endangered` | text-attested substitutes for CITES-listed drugs | conservation-safe alternatives |

**With honest negative controls**, because a system that proposes medicine must be able to embarrass
itself: does 取象比类 (TCM analogical reasoning by resemblance) predict pharmacology? Do the six
Ayurvedic tastes (ṣaḍrasa)? Does the whole ranking collapse under a shuffled-edge null model?
Published whether or not we like the answer.

## The model

| | `shennong-mini` | `shennong-0.5b` |
|---|---|---|
| Parameters | <!--FILL: mini params--> | ~494 M (≤ 1 B) |
| Weights file | <!--FILL: gguf size--> GGUF | <!--FILL: flagship gguf size--> GGUF Q4_K_M |
| Training | **from scratch on this machine, CPU only** | recipe: Qwen2.5-0.5B → domain CPT → LoRA SFT → merge → Q4_K_M |
| Vocab | <!--FILL: vocab--> (zh-Hant + sa + en) | <!--FILL--> |
| Trained on | <!--FILL: tokens seen--> tokens of domain-exclusive corpus | recipe only — **not yet run at this scale**, and labelled as such |

**Why a tiny model is the right answer, not a compromise:** knowledge lives in the **index**, structure
in the **graph**, reasoning in a **small model**, provenance **everywhere**. A <1 GB quantised model
runs offline on a laptop in a clinic in Yunnan or Kerala — that is a different product from a hosted
API. And a model we can enumerate the training corpus of is a model whose claims we can audit.
See [`docs/FIRST_PRINCIPLES.md`](docs/FIRST_PRINCIPLES.md) §4.

## Quickstart (CPU only, no GPU, no network at inference)

```bash
git clone https://github.com/cptlight/shennong && cd shennong
make setup          # CPU venv (torch 2.2.2 + numpy<2 + tokenizers)
make corpus         # fetch + licence-audit + clean → corpus/processed/corpus.jsonl
make tokenizer      # multilingual BPE (zh-Hant / sa / en)
make train-mini     # train shennong-mini from scratch — real run, real logs
make export         # → artifacts/shennong-mini-f16.gguf (< 1 GB) + sha256
make eval           # → eval/report.json (benchmarks, controls, ablations)
make app-data       # materialise the Workbench data
make workbench      # http://127.0.0.1:8000 — the SHENNONG Workbench
```

Ask it something:

```bash
python -m shennong.cli ask "Why is 附子 processed before use?"
python -m shennong.cli shi --n 10 --class incompatibility
```

## Repository map

```
corpus/     provenance registry (licence + evidence per source), processed corpus, DATA_CARD
data/       fetchers, cleaners, licence audit, drug-name lexicon builders
tokenizer/  multilingual byte-level BPE
model/      shennong_mini.py (Llama-style), configs, MODEL_CARD, GGUF export
training/   from-scratch pretraining, domain CPT, LoRA SFT, merge+quantise, runs/ with real logs
shennong/   the package: ontology · kg · extract · decode · discover · rag · safety · learn · eval
app/        SHENNONG Workbench — stdlib-only local UI, vanilla JS, offline
tests/      behavioural tests (extraction, resolution, safety, retrieval, CLI)
eval/       benchmark harness, negative controls, ablations, self-improvement rounds
docs/       FIRST_PRINCIPLES · ARCHITECTURE · METHODOLOGY · EVALUATION · SAFETY · CONTINUOUS_LEARNING
submission/ Devpost text · 10 slides · 10-minute video script
```

## The four operations, in code

```bash
python -m shennong.cli cai   --corpus-dir corpus/processed    # collect → passages + entities
python -m shennong.cli zhi   --corpus-dir corpus/processed    # decode  → drug names, processes
python -m shennong.cli pei   --corpus-dir corpus/processed    # combine → knowledge graph
python -m shennong.cli shi   --n 12 --out app/data/hypotheses.json   # deploy → hypotheses
python -m shennong.cli report --out eval/report.json          # evaluate
```

## Results

<!--FILL: results table — corpus stats, model metrics, eval table, negative controls, ablations.
     Every number must come from eval/report.json, corpus/DATA_CARD.md or training/runs/*/metrics.json. -->

## Honest limitations

<!--FILL: keep this section brutally honest and specific. -->

- `shennong-mini` is a **small** model trained on a **modest** corpus on a **CPU**. It writes domain-
  register text; it is not a reliable factual oracle. Every factual claim in the system is meant to be
  grounded in a retrieved span, and the system is designed to **refuse** when it cannot cite.
- Drug-name → taxon resolution is the weakest link in the chain. Its measured F1 is reported *before*
  any discovery claim, because a graph built on bad resolution is a graph built on sand.
- Hypotheses are **hypotheses**. Nothing here is medical advice, and nothing here has been tested
  in vitro or in vivo. The output is a ranked list of experiments, not a list of cures.
- The corpus skews toward the Chinese tradition, because that is where the largest public-domain
  original-language canon exists. Sanskrit, Arabic, Persian and Tibetan coverage is real but thinner;
  the DATA_CARD quantifies the imbalance per tradition rather than hiding it.

## Safety, ethics and Traditional Knowledge

- **Research use only.** No dosing, no self-treatment guidance, no synthesis routes for toxins or
  pathogens. The safety module enforces this in code, and the red-team tests live in `tests/`.
- **Toxic drugs are data, not recommendations.** The Asian materia medica contains mercury, arsenic
  and lead preparations (丹, 輕粉, 雄黃, *bhasma*). SHENNONG analyses these as **toxicology and
  safety evidence** — for example, to flag name collisions that put patients at risk — and never
  suggests their use.
- **Traditional Knowledge policy.** Classical Asian medical texts are living heritage, not free ore.
  We use public-domain editions, attribute every source, operate a non-extractive framing, and
  document a benefit-sharing and opt-out position in
  [`docs/SAFETY_AND_ETHICS.md`](docs/SAFETY_AND_ETHICS.md). Nagoya Protocol considerations are
  explicit, not decorative.

## Licence

Code and weights: **Apache-2.0**. Data: per-source licences preserved in
[`corpus/registry/`](corpus/registry/); public-domain material reproduced, share-alike respected,
restricted material **referenced only, never redistributed**. See
[`corpus/LICENSE_AUDIT.md`](corpus/LICENSE_AUDIT.md).

## Built for

**EthnoHack 2026** — *Data Hackathon on Ethnopharmacology & Health*, ETHCSTWIN (Horizon Europe),
National and Kapodistrian University of Athens, 2–8 November 2026.
Track **01 — Traditional Knowledge Mining**, with depth into track 02 (knowledge graphs for natural
product discovery) and track 04 (a phytotherapy decision-support Workbench).

<div align="center">

*「青蒿一握，以水二升漬，絞取汁，盡服之。」*

</div>
