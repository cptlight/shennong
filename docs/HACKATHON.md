# HACKATHON — how SHENNONG maps to EthnoHack 2026

Written so a judge can tick boxes in under ten minutes. Every row points at a file, a panel or a slide.

**Event:** EthnoHack 2026 — *Data Hackathon on Ethnopharmacology & Health* (ETHCSTWIN / Horizon Europe,
National and Kapodistrian University of Athens).
**Repository:** https://github.com/cptlight/shennong

---

## 1. Deliverables checklist

| Required | Where | Status |
|---|---|---|
| Devpost project page | `submission/DEVPOST.md` | ✅ ready to paste |
| Public GitHub repo + README | `README.md` | ✅ |
| 10-minute pitch video | `submission/VIDEO_SCRIPT.md` (timed 10:00) | ✅ script complete |
| Slide deck, ≤ 10 slides | `submission/SLIDES.md` → `submission/slides.json` | ✅ **exactly 10**, validated by `submission/build_slides_json.py --final` |

---

## 2. Track selection

**Primary: Track 02 — Natural Products for Drug Discovery.**
The project is a **pre-experimental screening pipeline** for plant-derived compounds: it lifts a processing
instruction out of the classical record, compiles it into a chemical hypothesis, and uses validated physics
to decide whether the hypothesis is physically possible before any wet-lab work. That is a screening and
validation pipeline for natural products, which is what track 02 asks for.

**Why track 02 rather than track 01:** the strongest, most judge-visible results are quantitative
statements about compound viability — **78 of 203 candidates refuted by physics**, **6 of those despite
unanimous 5/5 panel agreement** (菖蒲 + 蒸 → terpenoid: 98.5 % of a monoterpene stripped at 100 °C), and the
stable funnel **203 → 151 → 28 → 10 → 18**. Those are drug-discovery statements, not text-mining
statements.

**Depth in track 01:** the corpus, entity resolution and classical-theory encoding remain the front half of
the pipeline and are documented throughout.

**Secondary depth:**

| Track | How SHENNONG contributes | Where to look |
|---|---|---|
| **02 — Natural Products for Drug Discovery** | knowledge graph, chemotype bridges, mechanism proposals, ranked drug candidates with structure/formula, computed properties and development paths | `artifacts/drug_candidates.json`, Workbench → Candidates, slide 7 |
| **04 — Digital Health & Phytotherapy** | the Workbench: a local-first research cockpit with grounded Q&A, refusal behaviour, provenance-first corpus browsing | `app/`, Workbench → Ask / Corpus |

---

## 3. Judging axes — where the evidence is

> **Axis 1 · Scientific relevance**
> Does it address a real problem in ethnopharmacology, with methods the field recognises?

| Evidence | Location |
|---|---|
| The problem is stated as a testable question: does Asian pharmacological theory predict modern chemistry? | `docs/EVALUATION.md` §2, slide 2 |
| Five pre-registered tests with effect size, n, p and a permutation null | `docs/EVALUATION.md` §2.1–2.3, Workbench → Methodology |
| Falsification plans with named readouts, discriminating arms, positive controls and retraction conditions | every hypothesis dossier; `docs/METHODOLOGY.md` §6 |
| Mechanism-specific claims (NF-κB p65 Cys38 alkylation, 11β-HSD2 inhibition, KEAP1/Nrf2, NaV site 2) rather than generic "anti-inflammatory" | hypothesis dossiers + candidate mechanisms |
| Negative controls that could embarrass the project are published | `docs/EVALUATION.md` §3, slide 8 |

> **Axis 2 · Novelty and creative use of data**

| Evidence | Location |
|---|---|
| Asian pharmacological theory used as a **feature vector** and tested, not as decoration | `docs/METHODOLOGY.md` §3, `properties.csv`, slide 2 |
| Ancient **science** texts (天工開物, 齊民要術, 夢溪筆談) as a source of process chemistry, not just medical texts | `assets/corpus_tiers.svg`, `corpus/registry/sources.yaml`, slide 4 |
| Processing vocabulary (炮/煅/淬/九蒸九曬) translated into modern extraction chemistry | `corpus/processed/structured/processing.csv`, `docs/METHODOLOGY.md` §2.2 |
| Two classical modelling systems used as first-class predictors: TCM (四氣五味, 歸經, 七情) and Ayurveda (rasa/guṇa/vīrya/vipāka) | `docs/GLOSSARY.md`, `ayurveda_properties.csv` |
| Bilingual classical model — reads 繁體 and Devanagari originals rather than English summaries | `tokenizer/`, `model/MODEL_CARD.md`, slide 5 |

> **Axis 3 · Technical reproducibility and documentation**

| Evidence | Location |
|---|---|
| One command per stage, from a clean clone, CPU-only | `Makefile`, `README.md` |
| Every artefact hashed; every source has provenance + licence + licence evidence | `corpus/registry/sources.yaml` |
| The registry is generated and machine-validated (not hand-maintained prose) | `pytest`, `scripts/` |
| Determinism documented per component, including what is *not* deterministic | `docs/METHODOLOGY.md` §8 |
| The Workbench itself runs on the standard library, offline, no build step | `app/serve.py` (stdlib only), `app/README.md` |
| Documentation set | `docs/METHODOLOGY.md`, `EVALUATION.md`, `SAFETY_AND_ETHICS.md`, `CONTINUOUS_LEARNING.md`, `FAQ.md`, `GLOSSARY.md`, `CONTRIBUTING.md` |

> **Axis 4 · Data-science quality (validation, uncertainty)**

| Evidence | Location |
|---|---|
| Pre-registered tests and thresholds, written before results | `docs/EVALUATION.md` §1–2 |
| Permutation nulls (10,000 draws, seed recorded) for every statistic | `docs/EVALUATION.md` §2.2 |
| Multiple-comparison correction disclosed alongside uncorrected values | `docs/EVALUATION.md` §2.3 |
| Three categories of uncertainty reported separately (statistical / source / structural) | `docs/METHODOLOGY.md` §7 |
| Sensitivity sweep over ranking exponents, reported as rank correlation | `docs/EVALUATION.md` §6 |
| Refusal + grounding benchmarks, including **over-refusal** | `docs/EVALUATION.md` §7 |
| Written pre-registration of what would falsify the project | `docs/EVALUATION.md` §9 |
| Null model on every run; controls are automatic rejects in the learning gate | `docs/CONTINUOUS_LEARNING.md` §2 |

> **Axis 5 · Scalability beyond the hackathon**

| Evidence | Location |
|---|---|
| Corpus is a registry, not a fixed dump — new sources are a diff, not a rewrite | `corpus/registry/sources.yaml`, `docs/CONTINUOUS_LEARNING.md` §3 |
| Eval-gated improvement loop with a mechanical gate | `docs/CONTINUOUS_LEARNING.md` |
| Cross-tradition generalisation is the next experiment (fit on 本草綱目, predict Ayurvedic/Unani held-out) | `docs/EVALUATION.md` §6, slide 10 |
| Apache-2.0, open weights, no gate, no network dependency | `LICENSE`, `model/MODEL_CARD.md` |
| Runs on a consumer CPU with no GPU — the barrier to a research group adopting it is near zero | `README.md`, `app/README.md` |

> **Axis 6 · Benefit to conservation, drug discovery and public health**

| Benefit | Evidence | Where |
|---|---|---|
| **Drug discovery** | ranked candidates with mechanism, structure/formula, computed drug-likeness, development path | `artifacts/drug_candidates.json`, slide 7 |
| **Conservation** | CITES-listed ingredients tagged; substitution urgency ranked by formula role (君 vs 佐); 犀角→水牛角, 穿山甲→豬蹄甲 | `docs/SAFETY_AND_ETHICS.md` §6 |
| **Public health — adulteration** | 異名同物 collisions ranked by toxicity divergence; the documented 木通/關木通 and 三七/菊三七 cases | `docs/SAFETY_AND_ETHICS.md`, hypothesis H-01/H-02 |
| **Public health — interaction** | 十八反 / 十九畏 / *viruddha* encoded as a testable interaction dataset | hypothesis H-05/H-06, `docs/GLOSSARY.md` |
| **Public health — toxicology** | mercury/arsenic/lead drugs handled as hazard rankings, never as advice | `docs/SAFETY_AND_ETHICS.md` §2 |

---

## 4. Special awards

### Best AI Solution

- A **bilingual classical** model (Classical Chinese 繁/简 + Sanskrit Devanagari + IAST + Arabic), trained
  from scratch on a consumer CPU, under 1 GB — the constraint is the contribution, not a limitation to excuse.
- **Theory as a feature vector**: the AI's predictive prior is a 2,000-year-old pharmacological framework,
  encoded and tested rather than assumed.
- **Retrieval that refuses.** The Ask surface answers extractively with per-sentence citations or refuses;
  hallucination is treated as a design failure, not a benchmark score.
- Where to look: slide 5, `model/MODEL_CARD.md`, Workbench → Ask.

### Best Scientific Rigor

- Pre-registered tests, pre-registered thresholds, permutation nulls, disclosed multiple comparisons.
- **Negative controls published even when they could invalidate the project**, including 取象比類 — a
  foundational TCM reasoning principle treated as a hypothesis.
- A written, numbered list of **what would make us wrong** (`docs/EVALUATION.md` §9).
- The losing tests are reported with the same apparatus as the winning ones.
- Where to look: `docs/EVALUATION.md` (the whole document), slide 8.

### Best Community Impact

- **Adulteration ranking** from 異名同物 name collisions — the mechanism behind a documented carcinogen
  exposure (aristolochic acid) and a documented hepatic injury (pyrrolizidine alkaloids).
- **Conservation substitution priority** ranked by formula role, costing no animals to produce.
- **Interaction-rule mining** from 十八反/十九畏/*viruddha* — a pre-modern herb–drug interaction dataset.
- **TK policy with a working opt-out and a Nagoya-model benefit-sharing position**, plus an honest statement
  of the consent debt we have not discharged (`docs/SAFETY_AND_ETHICS.md` §4).
- Everything Apache-2.0 and offline-runnable, so a clinic, an NGO or a ministry can use it without a vendor.
- Where to look: `docs/SAFETY_AND_ETHICS.md`, slide 9.

---

## 5. "Check it in under a minute" — five commands

```bash
# 1. the corpus is real and audited
head -20 corpus/registry/sources.yaml

# 2. the workbench runs on any machine, offline
python app/serve.py            # → prints URL + a per-panel LIVE / DEMO FIXTURE banner

# 3. ten-plus falsifiable hypotheses across six discovery classes
python -m shennong.cli shi --n 12 --out /tmp/shi.json && python -m json.tool /tmp/shi.json | head -60

# 4. the central experiment, with the nulls
python -m shennong.cli report --out eval/report.json && python -m json.tool eval/report.json

# 5. the deck is exactly 10 slides and every number is real
python submission/build_slides_json.py --final
```

If command 5 fails, a a double-bracketed PENDING marker is still in the deck and we have not shipped — that check is
deliberately wired into the repository rather than left to a reviewer's memory.
