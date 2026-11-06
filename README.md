<div align="center">

# 神农 SHENNONG

**▶ [Test it in your browser — no install, no login](https://cptlight.github.io/shennong/)**

**Shennong tasted a hundred herbs. We are teaching a 400 MB model to do it again — and to tell us what he hid between the lines.**

*A <1 GB, open-weights, classical-Asian-medicine language model and first-principles discovery engine for ethnopharmacology.*

[![Devpost](https://img.shields.io/badge/EthnoHack-2026-coral)](https://ethnohack2026.devpost.com/)
[![Track](https://img.shields.io/badge/track-01%20Traditional%20Knowledge%20Mining-teal)](https://ethnohack2026.devpost.com/)
[![Licence](https://img.shields.io/badge/code%20%26%20weights-Apache--2.0-blue)](LICENSE)
[![Model](https://img.shields.io/badge/model-<1%20GB%20%7C%20<1B%20params-green)](#the-model)
[![CPU](https://img.shields.io/badge/runs%20on-CPU%20only-lightgrey)](#quickstart)

</div>

---

## Headline result

**We pre-registered five classical property axes against measured chemistry and target biology. One
survived — the most mechanistic one.**

| Axis | Statistic | Result | n | p | Verdict |
|---|---|---|---|---|---|
| **歸經** channel tropism → target organ | hit rate vs permutation | **7.48 % vs 3.80 % (≈2×)** | **2,059** pairs | **0.008** | **predicts** |
| 四氣 four natures → polarity/volatility | AUC | 0.456 | 193 | 0.261 | null |
| 五味 five flavours → compound class | AUC | 0.529 | 201 | 0.779 | null |
| Ayurvedic vīrya → logP | ρ | — | 0 | — | not linkable |
| Ayurvedic ṣaḍrasa → action class | AUC | — | 0 | — | not linkable |

And three numbers that limit what it means — published here rather than below the fold:

- **Drug-name → taxon resolution is 14.1 % accurate (n = 368).** Every downstream layer inherits that
  error. It is the weakest link in the chain and the first thing we would fix.
- **Our own composite failed its topology check.** Shuffling plant↔use edges changes the mean score by
  **−0.026** [−0.042, −0.014]: the ranking is driven by evidence and plausibility priors, not by graph
  structure. Reported as a limitation of the scorer.
- **5 of 18 十八反 rows have a mechanism bridge**, and the Ayurvedic tests could not run because there is
  no Sanskrit→binomial lexicon yet.

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
| Parameters | **8,719,616** (4,525,312 non-embedding) | ~494 M (≤ 1 B) |
| Weights file | `shennong-mini-f16.gguf` — **18,054,560 B (18.05 MB)** | ~350–400 MB GGUF Q4_K_M (estimate) |
| Training | **from scratch on this machine, CPU only** | recipe: Qwen2.5-0.5B → domain CPT → LoRA SFT → merge → Q4_K_M |
| Vocab | 16,384 (en · la · zh-Hant; Devanagari present but **not** in vocab) | 151,936 (Qwen) |
| Trained on | **1,638,400 tokens** (0.19 tok/param · **0.9 % of compute-optimal** — deliberately undertrained) | recipe only — **not run at this scale** |

### Sparse MoE vs dense — measured, not assumed

We trained both at **identical token budget (1,638,400 tokens)** on the same CPU:

| | dense | **sparse MoE** |
|---|---|---|
| Parameters | 8,719,616 | **19,342,616 total / 12,264,728 active** (4 experts, top-2) |
| Held-out val loss | 6.3901 | **5.4828** (−0.91 nats) |
| Throughput | 604 tok/s | **769 tok/s (+27 %)** |
| Wall clock | 45.2 min | **35.5 min** |
| Weights | 18.05 MB f16 GGUF | **47.1 MB f16 safetensors** |

**Why it wins:** 2.2× the capacity for only 1.4× the active compute per token — the FFN is where the
knowledge sits, and routing lets four specialists cover Chinese, Latin, Sanskrit and English
pharmaceutical text without every token paying for all of them.

**And the router independently rediscovered the script structure.** Mean gate weight per expert, then
Jensen–Shannon distance between the routing distributions per language (0 = identical, 1 = disjoint):

| pair | JS distance |
|---|---|
| la ↔ zh-Hant | **0.709** |
| en ↔ zh-Hant | **0.605** |
| la ↔ sa | 0.462 |
| sa ↔ zh-Hant | 0.332 |
| en ↔ sa | 0.330 |
| en ↔ la | 0.179 |

No dead experts (usage share 0.29 / 0.04 / 0.23 / 0.44). Classical Chinese routes almost disjointly from
Latin and English — nobody told the router which script was which. That is a small, genuine result: the
traditions are separable in representation space, not just in the corpus manifest.

*Caveat, stated plainly:* this is a single seed, and the two runs used different corpus snapshots (the
MoE on the frozen 45.6 M-char corpus, the dense run on the 38.24 M snapshot), so it is strong evidence
but not a clean controlled ablation. A 3-seed paired run is the next experiment.

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

## Results

| | |
|---|---|
| **Corpus** | **106 sources · 45,604,249 chars · 27,738 records** — zh-Hant 16.03 M (35.1 %), en 23.35 M, sa 3.44 M, la 2.79 M |
| **Licence audit** | 103 trained-on sources (30 public domain + 73 CC BY-SA-4.0); GRETIL **rejected** (CC BY-**NC**-SA) |
| **Structured data** | 23,177 compounds (**23,176 with real SMILES**), 11,819 uses, 1,402 property vectors, 822 lexicon entries |
| **Model** | 8,719,616 params, from scratch, **45 min on one laptop CPU** (no GPU), 604 tok/s |
| **Held-out quality** | val loss **6.390** · ppl **605.3** · **2.526 bits/byte** vs unigram baseline **3.076 bpb** (1.22× better) |
| **Weights** | `shennong-mini-f16.gguf` **18,054,560 B**, sha256 `a67ad442…4cdb60`, 56 tensors, 8,719,616 elements — GGUF↔HF bit-exact, tokenizer parity 100 % |
| **Candidates** | **60** drug candidates across 15 taxa, all classical lines verified against corpus spans |
| **Honest gaps** | Per-language bpb: en 2.56 · zh-Hant 3.34 · la 4.58 · **sa 13.46** (Devanagari never trained) · drug-name→taxon **accuracy 14.1 % (n=368)** — the weakest link in the whole chain |

### The pre-registered theory experiment — the result

Five tests, fixed thresholds (AUC ≥ 0.60 or |ρ| ≥ 0.15 **and** permutation p < 0.05), Holm–Bonferroni
corrected, run on the real corpus (`eval/report.json` → `drug_discovery.theory_predictivity`):

| Test | Statistic | Value | n | p | Verdict |
|---|---|---|---|---|---|
| **T2 歸經** → target organ | hit rate vs permutation mean | **7.48 % vs 3.8 %** (≈2×) | **2,059** pairs / 26 drugs | **0.008** | **predicts — weakly but significantly** |
| T1 四氣 → polarity/volatility | AUC | 0.456 | 193 | 0.261 | no signal |
| T3 五味 → compound-class family | AUC | 0.529 | 201 | 0.779 | no signal |
| T4 vīrya → logP | ρ | — | **0** | — | not linkable (no Sanskrit→binomial lexicon) |
| T5 ṣaḍrasa → action class | AUC | — | **0** | — | not linkable |
| **取象比類 control** | ρ | — | 0 | — | insufficient colour-named drugs |
| **Null model** (shuffled plant↔use edges, 27 shuffles) | score drop | **−0.026** [−0.042, −0.014] | 2,034 vs 2,766 | — | **composite is prior-dominated, not topology-sensitive** |

**How to read that honestly.** Channel tropism carries real but weak organ-level information — about
twice chance, and the only one of the five axes to survive its own pre-registered test. The other
classical axes we could operationalise did **not** survive, and the two Ayurvedic tests could not be run
at all. And our own composite **failed its topology check**: shuffling the graph does not lower the
scores, which means the ranking is driven by evidence grade and plausibility priors rather than by
learned graph structure. We report that as a limitation of the scorer, not as a success.


## Two pipelines: hypothesis, then deterministic outcome

```
pipeline 1   ancient record → Asian theory → Asian pharmacy     ⇒  HYPOTHESIS
pipeline 2   structure + T/medium/time → kinetics/thermodynamics ⇒  MAY / MAY NOT, with arithmetic
```

Pipeline 2 is not a second opinion — it is a **calculation**. Given a compound's structure and a
preparation's actual temperature, medium and duration, it models three physical sinks (volatilisation
via Clausius–Clapeyron, hydrolysis via Arrhenius with bond-class activation energies, thermal
degradation above 0.85·Tb) and returns a **retention fraction with a sensitivity range**. Same inputs,
same number, every time.

**The estimator is validated before it is trusted:** Joback group-contribution boiling points against
known physical constants — **mean relative error 4.5 %, 6/6 compounds within 10 %**.

**Results over the hypotheses that had resolvable structures (n = 60):**

| Retention class | n |
|---|---|
| RETAINED (≥90 %) | 28 |
| PARTIALLY RETAINED (50–90 %) | 23 |
| LARGELY LOST (10–50 %) | 7 |
| EFFECTIVELY DESTROYED (<10 %) | **2** |

**9 hypotheses are refuted by physics** — they passed the ancient-record gate, the Asian-theory gate and
the five-expert panel, and the arithmetic shows the preparation cannot do what the hypothesis claims.
Example: *蒸 of 菖蒲 → alkaloid* models at **28 % retention**; the claim of enrichment is physically
backwards.

**Western literature appears on every row as `references_western`,** marked *"this is what they think —
recorded, not used in the computation"*. It cannot alter the verdict. If a paper disagrees with the
physics, the paper is wrong, or it measured a derivative, or it used a different preparation — those are
the three things to check, and none of them is "the tradition is false".

[`artifacts/DETERMINISTIC_OUTCOMES.md`](artifacts/) · `shennong/physics/{estimators,simulate}.py`

## The order: ancient record → Asian medicine → Western medicine

This is not a slogan; it is a set of gates, enforced in `shennong/experts/stages.py`:

```
STAGE 1  ANCIENT RECORD       attested in the classical corpus?            GATE
STAGE 2  ASIAN THEORY         四氣/五味/歸經 (rasa/vīrya) frame it?        GATE
STAGE 3  ASIAN PHARMACY       炮制 / formula layer support it?             score
STAGE 4  VALIDATED PHYSICS    thermodynamics · kinetics · biophysics      GATE + ARBITER
STAGE 5  WESTERN LITERATURE   recorded as an observation                  no decision weight
```

Most computational ethnopharmacology runs the opposite way round: start from a compound–target database,
find a plant that might contain the compound, then cite a traditional use as colour. That makes the
tradition a marketing layer. Here **a claim failing either gate is out, however strong the Western
evidence is** — modern data may strengthen a tradition-grounded hypothesis, never substitute for one.

**What arbitrates is validated physical chemistry, not consensus.** Stage 4 applies mass conservation,
Clausius–Clapeyron phase partitioning, Arrhenius kinetics and the biophysics of delivery. A claim that
violates them is out.

To be precise about the strength, because a sharp judge will ask: this is a **validated lumped model**,
not ab initio physics. Its boiling-point estimator is checked against known constants (**mean 4.5 %
error, 6/6 within 10 %**), and a quantum-chemistry layer (RHF/6-31G(d); Koopmans ionisation potentials
within **0.82 eV** of experiment) sits behind it at **fragment level**. Quantum chemistry arbitrating
individual natural products is the next layer, not a current claim.

**Western literature is an observation, not an arbiter.** It is read, and its disagreement is a
**puzzle worth explaining** — wrong species, wrong preparation, wrong dose, wrong endpoint, or untested.
What it cannot do is *promote* a hypothesis the record does not attest, or *rescue* one physics has
refuted. It participates in interpretation; it does not hold the gavel. Most of the chemistry this
pipeline uses **is** Western science — the point is the **order of evidence**, not a rejection of it.

**Measured over 203 candidates — and stable across panel sizes.** The identical funnel was produced by
the 7-expert and the 12-expert panel; adding five experts moved **not one count**, because the gates are
structural and the arbiter is physics ([`docs/DIAGNOSTICS.md`](docs/DIAGNOSTICS.md) §1):

| | n | |
|---|---|---|
| candidates | 203 | |
| excluded at the ancient-record gate | **151** | never attested — a Western screen with a footnote |
| excluded at the Asian-theory gate | 24 | attested, but the tradition's framework does not frame it |
| **pass both gates** | **28** | the stable headline number |
| **refuted by validated physics** | **10** | physically impossible *as stated* |
| **survive everything** | **18** | tradition-grounded **and** physically consistent |

The 10 physics exclusions are the most interesting number in the repo: they include claims that scored
**5/5 in the expert panel**, e.g. *"蒸 of 菖蒲 should enrich its terpenoids"* — terpenoids are volatile
and 蒸 runs at 100 °C, so the claim is physically backwards. The arbiter overruled the panel's own
consensus, which is what an arbiter is for. (The *tradition* may still be right; our *formulation* was
wrong — steaming may serve a different purpose.)

The 28 that survive are split into **tradition-grounded + modern-corroborated** (the strongest class) and
**tradition-grounded, awaiting corroboration** (the pre-clinical class a pharmacognosist would want
before any assay). [`artifacts/TRADITION_FIRST.md`](artifacts/) · [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)

## Modular MoE — the architecture, and how to extend it

Three layers that change at different speeds:

```
  DATA PIPELINE   ancient records · Asian DBs · chemistry/biology   ← additive, updatable
        ↓
  EXPERTS         12 domain modules, routed per item and per question ← add / upgrade / remove freely
        ↓
  FIRST-PRINCIPLES CORE  15 laws across physics, chemistry, biology   ← FIXED. Not negotiable.
```

### The invariant: the first-principles core

`shennong/physics/laws.py` holds the laws every claim must satisfy — **5 physics, 5 chemistry, 5 biology**.
Eight are **hard** (violation is fatal), seven are **soft** (violation raises the evidential burden).
Keeping them as data means a new expert declares which laws it appeals to, and a reviewer can see exactly
what the system is committed to.

| Domain | Hard laws | Examples |
|---|---|---|
| physics | P1 mass conservation · P2 energy source · P3 phase partitioning · P4 permeation window | a process cannot create matter |
| chemistry | C1 atom/charge balance · C2 Arrhenius kinetics · C4 solvent polarity | a bond class cannot survive conditions that hydrolyse it |
| biology | B3 enzymes cannot make the impossible possible | catalysis accelerates, it does not permit |

**The core can say no, never yes.** It falsifies; it does not prove. That asymmetry is the design.

### How to add an expert (the whole process)

An expert is a pure function with this signature — nothing else is required:

```python
from shennong.experts.base import Proposal

def my_expert(world, item: dict) -> Proposal:
    # world: read-only view of every table (attestation, chemistry, operators, theory, …)
    # item:  {drug_surface, binomial, process, chemotype, ...}
    if not item.get("binomial"):
        return Proposal("my_expert", 0.20, "not applicable", [])
    score, note = ...          # your reasoning, 0..1, with the evidence
    return Proposal("my_expert", score, note, ["evidence reference", ...])
```

Then three registrations:

1. `shennong/experts/extra.py` → `EXTRA_EXPERTS = {"my_expert": my_expert, ...}`
2. `shennong/experts/stages.py` → `STAGE_OF_DOMAIN["my_expert"] = Stage.<stage>`
3. `shennong/experts/router.py` → add a feature rule saying **when** it should fire

That is it. The fusion layer, the Workbench, pipeline 2 and the research loop pick it up automatically,
because they all consume the expert dict rather than named experts.

**Rules an expert must follow:** return a `Proposal` (never raise), declare its evidence, never lower a
threshold, and never claim more than its data supports. An expert that cannot evaluate an item should
say so with a low score and a reason, not guess.

### Activation: per item and per question

- **Per item** (pipeline): `route(item)` fires experts by content features — a binomial activates taxonomy,
  chemotaxonomy and phytochemistry; a structure activates mechanics, quantum and ADME; a 炮制 term
  activates operator and extraction. Measured on a mixed 389-item stream: **2.25 experts per item = 18.7 %
  of the panel**; plain text items activate one.
- **Per question** (conversation): `route_query(question)` does the same for natural language, so
  *"What dose of 麻黃 is safe?"* activates 6 experts and *"How does berberine reach its target?"* activates
  7 — different sets, because they are different questions.

```bash
python -m shennong.experts.router      # activation statistics + conversation routing demo
```

### Updating the data pipeline

The experts read `world`, a read-only view rebuilt from disk on every run. So learning more is a data
operation, not a code change:

```bash
python scripts/ingest.py --input new_texts.jsonl --source-id X --licence "Public Domain" \
    --licence-evidence URL          # licence gate is non-overridable
python -m shennong.cli cai && zhi && pei && shi
python scripts/extract_discoveries.py && python scripts/extrapolate.py && python scripts/run_pipeline2.py
```

Every expert automatically sees the new evidence on the next run. Nothing is retrained, nothing is
forgotten, and provenance is preserved because the registry and corpus version are written by `ingest`.

### What you may change, and what you may not

| | |
|---|---|
| ✅ add, upgrade, remove experts | ❌ change a law to make a hypothesis pass |
| ✅ ingest new corpora | ❌ lower a gate threshold |
| ✅ retrain the MoE model | ❌ let Western literature vote |
| ✅ add tables the experts read | ❌ present a fixture as live data |

## Multi-domain experts, and a system that adjusts itself

**A hypothesis is an interpolation only if independent domains agree.** Five experts, each grounded in
a *different* table, score the same claim without seeing each other's evidence:

| Expert | Grounded in | Question |
|---|---|---|
| `ethnobotany` | corpus attestation | is the use independently attested, across how many sources/traditions? |
| `phytochemistry` | 23,172 structures | does the plant actually contain the chemotype, and how narrowly? |
| `operator` | 炮制 ontology | does the preparation physically act on that chemotype? |
| `theory` | 四氣/五味/歸經 | does the classical property vector point the same way? |
| `toxicology` | 毒 marking + alerts | is there a safety signal that makes this worth (or risky to) test? |

Fusion counts **distinct supporting domains** and reports disagreement instead of averaging it away.
Of 203 cross-sections: **28 at 5/5**, 59 at 4/5, 41 at 3/5, 75 at 2/5. A 2/5 claim is an assertion; a
5/5 claim is a cross-domain interpolation worth an assay. ([`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md),
[`docs/EXPERTS.md`](docs/EXPERTS.md))

### The system adjusts itself by acquiring evidence — never by moving the threshold

```bash
python -m shennong.research.loop      # diagnose → acquire → re-run → accept/reject → record
```

When a claim is unsupported, the loop identifies **which domain is blocking** it and runs the action
that acquires the missing evidence for *that* domain — expand attestation by scanning the corpus,
resolve a drug surface to a binomial, recover a 炮制 operator. Then it re-runs the panel.

| Round | Mean agreement | Effective actions | Hypotheses upgraded | Accepted |
|---|---|---|---|---|
| 1 | 3.197 → **3.695** | 30 | **108** | yes |
| 2 | 3.695 → 3.695 | 0 | 0 | **no** — nothing left to acquire |

The invariant is in the code and in the report: **the loop may acquire evidence; it may not lower a
threshold.** Round 2 is recorded as a rejection, because a loop that only ever accepts its own ideas is
a random walk with good PR. ([`artifacts/RESEARCH_LOG.md`](artifacts/))

## The loop: ingest → derive → extrapolate

The corpus is not a fixed dump. It grows, and every growth re-derives the graph and the discoveries.

```bash
python scripts/ingest.py --input new_texts.jsonl --source-id my_source \
    --title "…" --year 1700 --tradition tcm --lang zh-Hant \
    --licence "Public Domain" --licence-evidence "https://…"   # refuses anything not open
python -m shennong.cli cai && zhi && pei && shi                # re-derive graph + hypotheses
python scripts/extract_discoveries.py && python scripts/extrapolate.py   # re-derive findings
```

**Grounded generation.** `python -m shennong.generate "Why is 附子 processed before use?"` retrieves
spans with BM25, refuses when retrieval is weak, and lets the MoE phrase an answer **over the retrieved
spans only** — the model phrases, the corpus carries the facts.

### What the extraction actually found (text-level, across 106 sources)

| Finding | Count | What it is |
|---|---|---|
| **F1** cross-tradition convergence | **439 surfaces** | drug attested in ≥2 traditions — quasi-independent corroboration |
| **F2** single-attestation | **43 surfaces** | entire textual record is one source — a preservation priority |
| **F3** orphan procedures | **174 drug×process pairs** | a 炮制 step attested once while the drug has several — candidate lost methods |
| **F4** corroborated core | **251 surfaces ≥20 sources** | where the tradition agrees — the screening shortlist and the calibration set |
| **F5** cross-sections | **203 (drug, process, chemotype)** | combinations **no text states**: practice × documented chemistry × operator semantics |

See [`artifacts/DISCOVERIES.md`](artifacts/) and [`artifacts/CROSS_SECTIONS.md`](artifacts/).

**Why these are real and the earlier hypotheses were not.** The previous pass generated grammatically
perfect claims with real citations and false content — including *"去節 of Aconitum enriches alkaloid
via standardising ephedrine"*, a sentence about the wrong plant. These five findings cannot be
templated: they are counts over 106 sources, each checkable in one lookup, each decision-relevant
(screening · preservation · method recovery · calibration · extrapolation).

**One honest gap:** cross-tradition convergence (F1) was originally computed from `uses.csv` and returned
zero — because all 5,084 joined use-records come from a *single* source and some joined binomials were
not plants (*Phycodurus eques*, a seahorse). F1 is now computed from the text itself; the structured
join still needs fixing, and that is the same 14.1 % resolution problem.

## Evidence, refusal and the operator ontology

Four standalone, citable artefacts — each reproducible by a command in this repo:

| Artefact | What it is | Number |
|---|---|---|
| [`artifacts/support_verification.json`](artifacts/) | claim–span **support** check per candidate (entity, relation cue, polarity, length) + the verifier's own gold-set metrics | 60/60 candidates supported · AUC 0.95 on a shuffled-negative set |
| [`artifacts/falsification_cards.json`](artifacts/) | one card per candidate: claim, verified span, prediction, **kill criteria** | 10 cards |
| [`artifacts/discovery_ledger.json`](artifacts/) | every candidate with its span-verification and kill-criteria status | 60 entries · 60/60 spans · 60/60 kill criteria |
| [`artifacts/refusal_corpus.json`](artifacts/) | prompts that **must** be blocked (toxin synthesis, dosing, self-treatment, toxic materia medica) and research questions that must **not** be | 40 cases · recall 1.00 · precision 1.00 |
| [`artifacts/operator_ontology.json`](artifacts/) | the 炮制/alchemical **operator table**: classical term → modern chemical operation(s), attested substances, sources | 25 operators · 317 attestations |

**What the support verifier does and does not do.** It decides whether a cited span is *about the
claimed drug*, carries a therapeutic/administration relation (治 … or 用 … 漬酒), has no polarity
contradiction, and is the right length. It does **not** perform cross-lingual entailment — judging
whether a Chinese passage *entails* an English mechanistic sentence needs a multilingual encoder. On a
shuffled-negative gold set it separates cleanly (entity presence does most of the work), which is why
we report its value as *"a strong entity-and-relation gate"* rather than as semantic verification, and
why the same check is what caught **8 of 10 mislocated citations** in an earlier candidate artefact.

## Honest limitations

## Honest limitations

- **`shennong-mini` is 106× undertrained** (0.19 tokens/parameter vs ~20 compute-optimal). It learns
  the register and beats a unigram baseline; it is **not** a factual oracle. Every factual claim is
  meant to be grounded in a retrieved span, and the system refuses when it cannot cite.
- **Sanskrit is effectively unmodelled.** The tokenizer was trained before the Devanagari corpus
  arrived, so `sa` scores 13.46 bpb — worse than a unigram baseline. The 3.44 M Sanskrit characters
  are in the corpus but not in the model's competence. This is a real gap, not a footnote.
- **Drug-name → taxon resolution is the weakest link**: 43 % of use rows and 47 % of property rows
  resolve to a binomial. We chose precision over coverage after finding real false joins, and the
  graph is only as good as that join.
- **Candidate scores are currently degenerate** — novelty is 0.88 for all 60 candidates, so the rank
  order carries no information today. The shortlist is real, the *ranking* is not yet.
- **Span support is checked, cross-lingual entailment is not.** The verifier confirms the evidence is
  about the right drug and is a use statement; it cannot yet confirm that the Chinese passage entails
  the English mechanistic claim. That is the next encoder-shaped job, not a solved problem.
- **Hypotheses are hypotheses.** Nothing here is medical advice, and nothing has been tested in vitro
  or in vivo. The output is a ranked list of experiments, not a list of cures.
- The corpus skews Chinese because that is where the largest public-domain original-language canon is;
  the DATA_CARD quantifies the imbalance rather than hiding it.


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
Track **02 — Natural Products for Drug Discovery**, with depth in track 01 (knowledge mining for
product discovery) and track 04 (a phytotherapy decision-support Workbench).

<div align="center">

*「青蒿一握，以水二升漬，絞取汁，盡服之。」*

</div>
