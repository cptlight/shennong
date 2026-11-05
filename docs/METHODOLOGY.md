# METHODOLOGY

How SHENNONG turns a shelf of classical Asian texts into ranked drug candidates — and where the method is
weak. This document is written so that a reviewer can reproduce the reasoning, disagree with a specific
decision, and find the line of code or data file responsible for it.

Companion documents: `docs/FIRST_PRINCIPLES.md` (the axiom derivation), `docs/ARCHITECTURE.md` (module
layout), `docs/EVALUATION.md` (the measurements), `docs/SAFETY_AND_ETHICS.md` (the constraints).

---

## 0. The claim, stated precisely

> Pre-modern Asian medical writing encodes pharmacological knowledge inside a **theory of drug action**
> (四氣五味, 歸經, 升降浮沉, 七情, 君臣佐使; rasa / guṇa / vīrya / vipāka / tridoṣa). That theory is a
> **predictive framework**, not decoration. If it predicts modern molecular and target properties above
> chance, it is a discovery method that does not require a Western starting point. If it does not, that is a
> finding about the framework, and it will be reported with the same apparatus.

Two artefacts follow: **ranked drug candidates** (the deliverable) and **theory-predictivity statistics**
(the evidence that the method works). Neither is allowed to be asserted; both are measured.

---

## 1. Derivation before collection (why the corpus looks the way it does)

We did not begin with a list of nice texts. We began with the domain's axioms and derived the data classes
those axioms require. The full derivation is in `docs/FIRST_PRINCIPLES.md`; the consequence for this document
is that **every tier in the registry exists because an axiom demanded it**, and a tier with an empty
justification is a bug.

The shape of the argument:

1. **Axiom: pharmacological knowledge is relational.** A plant is not a drug; a *plant + part + preparation +
   dose-form* is a drug. Therefore the atomic unit is not a species but a **(taxon, part, process)** triple.
   → requires a `Preparation` and `Process` entity, and forces the processing texts (雷公炮炙論, 炮炙大法) into
   tier 2 rather than treating them as commentary.
2. **Axiom: names drift, referents may not.** A drug name is a pointer into a taxonomy that changed over
   1,500 years, across scripts. Therefore drug-name resolution is not preprocessing — it is a first-class
   discovery class (异名同物).
3. **Axiom: effect is claimed at the level of the whole preparation.** The tradition reasons about *formulae*
   with assigned roles, not isolated compounds. Therefore formula composition and 君臣佐使 roles are data,
   not metadata.
4. **Axiom: the tradition predicts interactions.** 十八反, 十九畏 and *viruddha* are explicit negative
   interaction claims. Therefore incompatibility is an edge type in the graph.
5. **Axiom: claims are only checkable against measured structure.** Therefore the biological ground-truth
   tier (ChEMBL, PubChem, Duke, POWO) is not "extra data" — without it, nothing is falsifiable.

The reverse direction matters too: **what the axioms did not require, we did not acquire.** The Western
herbal tradition is present only as a ≤ 3% labelled `comparative-control` slice, because its only job is to
answer "is this finding an artefact of any large botanical corpus?".

---

## 2. The four operations

### 2.1 采 Cǎi — collect

| Step | What it does | Failure mode it prevents |
|---|---|---|
| Licence-audited acquisition | one registry entry per source: title, author, date, URL, licence, **licence evidence URL**, tier, tradition, language, sha256 | silently ingesting copyrighted translations |
| Script normalisation | NFKC; 繁↔简 folding; IAST↔Devanagari; Arabic transliteration | one drug recorded as four different strings |
| Hygiene | ≥ 100 chars/record for CJK, ≥ 200 for alphabetic; UTF-8; drop page furniture | OCR noise dominating the token distribution |
| Dedupe | 13-gram hash across sources | parallel editions inflating a plant's apparent frequency |

Output: `corpus/processed/corpus.jsonl`, `corpus/registry/sources.yaml`.

**Reproduction:** `python -m shennong.cli cai --corpus-dir corpus/processed`

> **A bias we can see in our own provenance panel.** Bucketing the registry by `year` shows that a large share
> of the corpus is **nineteenth- and early-twentieth-century editions and translations** of much older texts —
> that is simply where public-domain access lives. This matters for interpretation: a 19th-century translator's
> word choices can pre-encode an interpretation, and an edition's channel assignments may differ from an earlier
> recension. The corpus panel in the Workbench displays this distribution rather than hiding it, and
> `docs/EVALUATION.md` §2.4 treats extraction disagreement between editions as a covariate rather than noise.
> Preferring originals in 繁體 and Devanagari over translations is the mitigation; it is not a complete fix.

### 2.2 制 Zhì — prepare

Two distinct jobs share this stage, and keeping them distinct matters:

**(a) Name resolution.** For each historical drug name we emit every plausible modern taxon with a
confidence and a method tag:

```json
{"historical": [{"name": "木通", "lang": "zh-Hant", "readings": ["Akebia quinata", "Aristolochia manshuriensis"],
  "modern": "Akebia quinata", "confidence": 0.71, "method": "lexicon", "era": "pre-1900"}]}
```

Method tags are `manual` > `lexicon` > `fuzzy`, and the confidence is used downstream: a collision with two
high-confidence readings *and* divergent chemistry is promoted to the 异名同物 discovery class rather than
being silently resolved.

**(b) Process translation.** A 炮制 term is mapped to a modern operation with parameters where the text gives
them:

| Classical term | Modern operation | Parameters the edition supplies |
|---|---|---|
| 炮 | dry roast until the drug splits | endpoint: visible fracture |
| 煅 | high-temperature calcination | endpoint: ash / no organic structure |
| 淬 | quench hot metal into a liquid | liquid identity (vinegar, urine, water) |
| 蒸 / 九蒸九曬 | repeated steam–sun cycles | cycle count (nine), co-medium (black bean) |
| 蜜炙 / 酒炒 | co-firing with honey / wine | medium, "until yellow" |
| 麴 | fermentation with a starter culture | time, temperature, inoculum |

Output: `corpus/processed/lexicon_drugs.json`, `corpus/processed/structured/processing.csv`

**Reproduction:** `python -m shennong.cli zhi --corpus-dir corpus/processed`

### 2.3 配 Pèi — combine

The knowledge graph is a typed multigraph. Node types: `taxon` (plant/animal/mineral), `drug` (a *named
used form*, which is what the texts actually talk about), `process`, `compound`, `target`, `indication`,
`formula`, `source`, `concept` (e.g. 取象比類, ṣaḍrasa).

Two design decisions are worth stating because they are arguable:

1. **`taxon` and `drug` are separate node types.** 木通 is a drug name; it resolves to two taxa. Collapsing
   them destroys the single most useful structure in this corpus.
2. **Formula roles are edges, not attributes.** `(formula:四逆湯 —jun→ drug:附子)` lets a query ask "which
   ingredients are load-bearing across the whole corpus?" rather than "what role does this herb have in this
   one formula?".

Incompatibility edges are typed by rule system (`incompatible_18fan`, `incompatible_19wei`,
`incompatible_viruddha`) and carry the asserting source, because the rules are claims, not facts.

Output: `artifacts/kg.json` (via `--out-kg`), `corpus/processed/structured/*.csv`

**Reproduction:** `python -m shennong.cli pei --out-kg app/data/kg.json`

### 2.4 使 Shǐ — deploy

Three products: ranked hypotheses (the working layer), **drug candidates** (the terminal artefact), and the
evaluation report.

---

## 3. Encoding the theory as a feature vector

This is the step that makes the whole project testable, so it is specified rather than hand-waved.

**TCM vector** (`properties.csv`):
`nature ∈ {寒, 熱, 溫, 涼, 平}` · `flavors ⊆ {辛, 甘, 酸, 苦, 鹹, 淡, 澀}` ·
`channels ⊆ {肺, 心, 肝, 脾, 胃, 腎, 膽, 大腸, 小腸, 膀胱, 心包, 三焦}` ·
`direction ∈ {升, 降, 浮, 沉}` · `grade ∈ {上品, 中品, 下品}` · `toxicity ∈ {有毒, 無毒}`

**Ayurvedic vector** (`ayurveda_properties.csv`):
`rasa ⊆ {madhura, amla, lavaṇa, kaṭuka, tikta, kaṣāya}` · `guṇa` (from the twenty) ·
`vīrya ∈ {uṣṇa, śīta}` · `vipāka ∈ {madhura, amla, kaṭuka}` · `prabhāva` · `doṣa_effect ⊆ {vāta, pitta, kapha}`

**Encoding decisions and their consequences:**

| Decision | Why | What it costs |
|---|---|---|
| Nature and vīrya encoded as **ordinal** (cold < cool < neutral < warm < hot) | the tradition itself treats the axis as a scale, and ordinal encoding lets us test monotonic relationships to thermolability | collapses the distinction between 溫 and 熱, which some editions make |
| Flavours and channels encoded as **multi-hot** | a drug genuinely has several; forcing one loses information | a drug with five flavours contributes to five regressions; penalised by the permutation null but it does dilute effect size |
| Grade encoded as **ordinal with 下品 = highest toxicity prior** | 下品 means "poisonous, not to be taken long-term", a hazard class | conflates acute toxicity with chronic |
| `direction` included as **categorical, not tested** | 升/降/浮/沉 has no obvious modern correlate; we do not pretend otherwise | one fewer test, and we say so in `docs/EVALUATION.md` |

**Where the tradition disagrees with itself, we inherit the disagreement.** Channel assignments differ
between editions. Rather than resolving to a canonical value, the extractor emits distributions and the
aggregation is reported in `eval/report.json` as a sensitivity (single-assignment vs majority-vote vs
distribution-weighted). Hiding this would have produced a cleaner and less true result.

---

## 4. Ranking hypotheses — the composite score

```
composite = novelty^a × plausibility^b × testability^c × evidence^d      (default: a = b = c = d = 1)
```

A **geometric product**, not an arithmetic mean, because these axes are conjunctive: a hypothesis that is wildly
novel but untestable should score near zero, and an arithmetic mean would let it score well. The default is the
plain product specified in the brief; the exponents are a configuration value, and the run records the ones it
actually used (`eval/report.json`, and `uncertainty.exponents` per candidate).

**Consequence to keep in mind:** because it is a product, the absolute value is small and scale-dependent — a
strong candidate can read `0.03`. **Composite numbers are only comparable within one run.** The interface shows
the four axes separately for exactly this reason, and lets a judge re-sort by a single axis.

Each axis is defined by explicit, checkable criteria rather than a model's opinion:

| Axis | Scored from | Scale |
|---|---|---|
| **novelty** | distance between the proposed chain and the nearest modern literature assertion, using the KG plus curated prior-art lists | 0–1 |
| **plausibility** | does a molecular mechanism connect chemotype to target to indication, with a named target? an empty mechanism box caps this at ~0.4 by construction | 0–1 |
| **testability** | is there a named, cheap, discriminating experiment; is there a *positive control*; can it produce a negative result? | 0–1 |
| **evidence** | grade of the source chain: multi-tradition agreement, edition count, corroboration in structured data | 0–1 |

**The exponents are a design choice, so they are exposed.** `docs/EVALUATION.md` reports a sensitivity sweep:
we recompute the ranking under the uniform product (the default), under a novelty-heavy setting
(a=0.5, b=c=d=0.5/3) and under a testability-heavy setting, and report the rank correlation between orderings.
If the top 5 are stable across the sweep, the ranking is robust; if not, we say which hypotheses are
exponent-dependent.

**The axes are also shown separately in the interface.** The Workbench lets a judge re-sort by a single axis,
because "ranked by novelty" and "ranked by composite" answer different questions and the product should not
hide that.

---

## 5. From lead to drug candidate (§11.4)

The terminal artefact is not a hypothesis, it is a candidate. The transformation is explicit and every step
either has data behind it or is rendered empty:

```
classical lead  →  chemotype  →  molecule(s)  →  novelty vs modern chemistry
                                              →  mechanism + theory justification
                                              →  development path (assay)
                                              →  residual risk
```

1. **Lead.** A `(drug, part, processing, formula role, property vector, source span)` tuple.
2. **Chemotype.** The compound classes the corpus and structured data attribute to that drug. If nothing is
   attributed, the candidate is marked `weyanjiu`-class and the mechanism box stays empty — an empty box is
   a statement about the literature, not a placeholder to be filled.
3. **Molecule.** A named compound with a molecular **formula**. Molecular weight is **computed from the
   formula** by arithmetic (`sum over elements of count × atomic mass`), which makes it checkable by hand.
   SMILES is populated **only** where a structure is resolved; otherwise it is `null` and the interface says
   `pending`. We do not hand a plausible string to a table to make it look complete.
4. **Drug-likeness.** Evaluated rule by rule. One of four Lipinski rules computable is reported as
   "1 of 4 evaluated", never rounded up to "Lipinski-compliant". logP, HBD, HBA, TPSA and rotatable bonds
   require a structure and are left `null` until one exists.
5. **Novelty.** See `docs/EVALUATION.md` §4. The output is a score plus the explicit basis sentence and the
   prior art it was compared against.
6. **Mechanism + theory justification.** Two separate fields on purpose: *what the molecule would do* and
   *why the classical property vector predicted it*. Conflating them is how projects like this start
   believing their own press.
7. **Development path.** Ordered steps, each tagged with a kind (`in-silico`, `in-vitro`, `in-vivo`,
   `analytical`, `formulation`, `clinical-*`). The first step must be the cheapest discriminating experiment.
8. **Residual risk.** Named liabilities: toxicity class, PAINS/assay interference, solubility, interaction,
   supply-chain. Distinct from the safety annotation, which is a *policy* artefact (see
   `docs/SAFETY_AND_ETHICS.md`).

---

## 6. The falsification gate

Every emitted hypothesis carries a `falsification_plan` that must satisfy four structural requirements, or
the hypothesis is not emitted:

1. **A named readout** — a measurement, not a direction ("urinary cortisol:cortisone ratio", not
   "improved metabolism").
2. **A discriminating arm** — the experiment must be able to produce a result that *kills* the specific
   mechanism claimed, not merely a null overall effect.
3. **A positive control** — something known to work under the same conditions, so a null result is
   interpretable.
4. **A stated retraction condition** — the sentence "if X, the mechanism is falsified", written before the
   experiment is run.

A hypothesis whose mechanism box is empty is emitted as a **screening hypothesis** with a funnel design, and
its plausibility score is capped. This is deliberate: an honest screening proposal is more valuable than a
decorative mechanism.

---

## 7. Uncertainty

Three distinct kinds, reported separately because collapsing them is how uncertainty gets hidden:

1. **Statistical** — reported as p and CI wherever a test is run (`docs/EVALUATION.md`).
2. **Epistemic / source** — every hypothesis states what would change our mind. Example from the ranked set:
   "the historical record does not tell us how much glycyrrhizin a decoction contained; root quality varies
   by an order of magnitude."
3. **Structural / modelling** — the things the pipeline cannot see: what was in the bottle, whether a 16th-c
   commentary reflects 1st-c practice, and whether a translation we relied on is faithful. These are listed in
   `docs/SAFETY_AND_ETHICS.md` §Limitations and in each dossier's `uncertainty` field.

A hypothesis is allowed to be uncertain; it is not allowed to be silent about it.

---

## 8. What is deterministic and what is not

Reproducibility claims are only meaningful with this section.

| Component | Determinism |
|---|---|
| Fetch → clean → dedupe → split | **deterministic** given the registry; content-addressed by sha256; split is a hash-based 98/2 held-out, not a random draw |
| Tokeniser training | deterministic given corpus + seed (`seed: 1337` recorded in the run config) |
| Model training | seeds fixed; CPU BLAS reductions are order-stable *on the same machine*; documented as machine-dependent |
| Entity extraction / name resolution | **deterministic** (lexicon + rules); confidence values are from fixed tables |
| Graph assembly | **deterministic** |
| Discovery / ranking | **deterministic**; the permutation null uses a fixed seed and a recorded draw count |
| Theory-predictivity statistics | **deterministic** given the permutation seed; the seed is in the report |

The honest caveat: **floating-point training is reproducible on the same hardware and library versions, not
universally.** The recorded `torch_version` and run config exist so a reviewer can see exactly what would
have to match.

---

## 9. One-node audit

To check the method end to end without reading the whole repo, follow one drug:

```bash
grep -n '附子' corpus/registry/sources.yaml                        # which editions contain it
grep -n '附子' corpus/processed/corpus.jsonl | head                # the spans, with provenance
python -m shennong.cli shi --class paozhi --out /tmp/shi.json      # the hypotheses
grep -n 'Benzoylaconine' /tmp/shi.json                             # the candidate chain
grep -rn 'Aconitum' corpus/processed/lexicon_drugs.json            # the name resolution + confidence
```

Everything the Workbench displays is derivable from those files. If it is not in a file, it is not a claim.
