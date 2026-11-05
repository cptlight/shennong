# FIRST PRINCIPLES — deriving the data before collecting it

> This document is the intellectual spine of SHENNONG. It is written so that a pharmacognosist, a
> data scientist and a historian can each check our reasoning, and so that every data class in
> `corpus/registry/` can be traced back to an axiom that *requires* it.
>
> **Claim:** you cannot design a good ethnopharmacology model by starting from whatever datasets you
> can download. You have to start from what a medical tradition *is*, derive what must therefore be
> recorded, and only then go looking.

---

## 1. The problem, stated precisely

A classical Asian medical text is a **lossy, culturally-compressed recording of clinical and
pharmacological observations**, written under constraints that are alien to modern science: no
chemistry, no germ theory, no statistics, and a strong incentive to encode knowledge esoterically.
The information is real. The encoding is not ours.

SHENNONG's job is a **translation problem between two ontologies**:

```
classical Asian medical text        ⇄        modern biology + chemistry
(qualities, processes, roles,                (molecules, targets, pathways,
 sequences, ciphers, case records)            doses, pharmacokinetics)
```

Everything we build — the corpus, the tokenizer, the model, the graph, the hypothesis engine — is
instrumentation for that translation. And the output that matters is not a chat answer. It is a
**falsifiable claim** that did not exist in the literature before.

Why this is worth doing at all: the translation has been done **once, manually, catastrophically
successfully**, and it is worth being precise about that example because it validates the entire
methodology.

> **The artemisinin lesson.** In 1969 Tu Youyou was sent to find an antimalarial from the Chinese
> materia medica. 青蒿 (*Artemisia annua*) was a known candidate, but aqueous decoctions kept failing.
> The decisive step was reading Ge Hong's *Zhouhou Beiji Fang* (葛洪《肘後備急方》, c. 340 CE):
> **「青蒿一握，以水二升漬，絞取汁，盡服之」** — *one handful of qinghao, soak in two sheng of water,
> wring out the juice, drink it all.* Not a decoction. A **cold maceration**. Artemisinin is
> thermolabile; boiling destroys it. **The pharmacologically decisive information was encoded in a
> processing instruction, not in an indication.** The 2015 Nobel Prize in Physiology or Medicine
> followed.
>
> The same pattern recurs: 砒霜 (arsenic trioxide) from 砒石 for acute promyelocytic leukaemia;
> ephedrine from 麻黃 in 麻黃湯; huperzine A from 蛇足石杉 (千層塔); indirubin from 青黛 in 當歸龍薈丸;
> berberine from 黃連. In every case the drug was already described — what was missing was the
> **mechanistic and procedural translation**.

That is the hypothesis SHENNONG operationalises: **a large fraction of classical Asian medical
knowledge is pharmacologically valid but has never been mechanistically tested, because the
translation layer was never built.** A domain-exclusive classical-language model plus a first-principles
graph is that translation layer.

---

## 2. Axioms

We take these as irreducible. Each is defensible; each is stated so that it can be attacked.

**A1 — Molecular causation.** A biological effect of a medicinal substance requires one or more
molecules to reach a biological target (receptor, enzyme, channel, transporter, nucleic acid,
membrane, immune cell) at a sufficient local concentration for a sufficient time. *Nothing acts
"because it is cold-natured."* Corollary: traditional qualitative categories are **summaries of
unknown molecular facts**, and are only heuristically predictive.

**A2 — Preparation determines the molecule set.** The set of molecules that reaches the target is a
function of species, plant part, harvest, and — critically — **processing and preparation**
(solvent, heat, time, pH, fermentation, mineral form). Two preparations of the same plant are
different drugs. Corollary: process language is *the* highest-value, most-neglected layer of the
classical record.

**A3 — Traditional use is a noisy observation.** A recorded use is an observation of an effect,
corrupted by: indication language drift, humoral reinterpretation, copying errors, placebo,
confounding by co-administered drugs, and survival bias in what got copied. Corollary: use records
must be treated as **noisy labels with provenance**, never as ground truth, and their value rises
with *independent convergence* (same taxon, same indication, different tradition/era/region).

**A4 — Cultural selection is a weak prior for efficacy.** Knowledge that is repeatedly re-recorded
across centuries and independently across traditions has survived a selection process. Selection
pressure is imperfect (prestige, commerce, religion all matter) but non-zero. Corollary: convergence
across ≥2 independent traditions is a **measurable, computable prior** — and it is testable, not
assumed.

**A5 — Relatedness predicts chemistry.** Phylogenetically close taxa share biosynthetic pathways
(chemotaxonomy). Corollary: a use attested for *X* is a candidate prior for sister taxon *Y* — which
is how you find substitute species and under-studied leads.

**A6 — Names are not identities.** A drug name is a pointer into a historically unstable namespace.
The same name denotes different taxa across eras/regions; the same taxon has many names. Corollary:
**name resolution is a first-class scientific operation**, and its failures are a documented
public-health hazard (aristolochic-acid nephropathy from 關木通/廣防己 substitution).

**A7 — Dosage is a property of preparation, not of plant.** "Toxic plant" and "medicine" are the same
species at different process states (Aconitum is the canonical case: 炮制 hydrolyses diester diterpene
alkaloids to far less toxic monoesters). Corollary: safety claims attach to **(drug, process)** pairs.

**A8 — Rule systems are compressions.** 十八反/十九畏, viruddha, 君臣佐使 are pre-modern attempts to
compress many observations into compact rules. A compression can be **wrong, right-for-the-wrong-reason,
or right and mechanistically explicable** — and only testing distinguishes them. Corollary: numbered
incompatibility rules are not folklore to be repeated; they are **a finite list of testable
interaction hypotheses**.

**A9 — Everything must be traceable.** A claim about a 1596 text must be checkable against that text.
Corollary: **no provenance, no hypothesis.** This axiom is what makes the system science rather than
divination.

---

## 3. What the axioms logically require (the derivation that produces our corpus)

Each row is a **proof obligation**: if we accept the axiom, this data class is not optional.

| # | Requirement | Derived from | Corpus tier |
|---|---|---|---|
| R1 | Anatomy, physiology, histology, organ systems | A1 (targets are biological objects) | 1 |
| R2 | Biochemistry, molecular biology, genetics, cell biology | A1 | 1 |
| R3 | Pharmacology: receptors, enzymes, ADME, CYP450, transporters, dose–response | A1, A7 | 1 |
| R4 | Toxicology, incl. heavy metals and organ toxicity | A7, A8 | 1 |
| R5 | Organic chemistry, natural-product chemistry, phytochemistry (compound classes, polarity, volatility, thermolability) | A1, A2 | 1, 5 |
| R6 | Botany: morphology, taxonomy, phylogeny, plant physiology | A5 | 1, 5 |
| R7 | **Classical Asian materia medica corpora in original languages** | A2, A3, A6, A9 | 2 |
| R8 | **Process/protocol vocabulary** (炮制, rasaśāstra procedures, alchemical operations) | A2, A7 | 2, 3 |
| R9 | **Formula composition + role structure** (君臣佐使) | A2, A8 | 2 |
| R10 | **Numbered rule systems** (十八反, 十九畏, viruddha) | A8 | 2, 3 |
| R11 | **Historical lexicography** — drug-name → taxon, across eras, scripts, dialects | A6 | 2, 5 |
| R12 | **Provenance metadata**: source, edition, date, region, tradition | A9, A3 | all |
| R13 | **Cross-tradition independent corpora** (TCM × Ayurveda × Unani × Tibetan × Kampō) | A4, A5 | 2 |
| R14 | **Structured compound–target–pathway ground truth** | A1, A9 | 5 |
| R15 | **Modern clinical/literature evidence** to compute "already known" (novelty) | A3 | 5 |

Two things follow immediately and they are the reasons this project is not a dataset dump:

1. **The corpus must be multilingual and must contain the originals.** If we only train on English
   summaries (A7 violation: translation is itself a lossy preparation), we lose exactly the layer
   where the value is — process words, contrastive drug names, rule lists.
2. **The corpus must be balanced toward rules and processes, not just indications.** A model trained
   only on "X treats Y" learns a lookup table. A model trained on *how X was prepared, combined,
   feared and forbidden* learns the part of the record that has never been mechanised.

### 3.1 The nine-class encoding taxonomy (what "hidden" actually means)

We classify every piece of recoverable-but-untranslated knowledge so the engine can target it.

| Code | Hidden knowledge type | Example | Discovery class |
|---|---|---|---|
| **E1** | Process → chemistry | 青蒿 cold maceration vs. decoction; 煅 calcination; 醋炙 esterification | `processing` |
| **E2** | Rule → interaction | 十八反: 甘草 × 甘遂; 烏頭 × 半夏/瓜蔞/貝母 | `incompatibility` |
| **E3** | Role → synergy/PK | 使 "courier" herbs; Ayurvedic **yogavāhi** (piperine with curcumin) | `formula_role` |
| **E4** | Name → identity | 關木通 vs 川木通; 防己 confusion → aristolochic acid nephropathy | `name_collision` |
| **E5** | Cipher → substance | 龍血, 紫河車, 鉛丹, 曾青, 五石散 — allegorical or obsolete drug names | `name_collision`, `processing` |
| **E6** | Silence → opportunity | a well-attested use with **no** modern mechanistic study | `understudied` |
| **E7** | Substitution → conservation | text-attested substitutes for endangered species | `endangered` |
| **E8** | Sequence → protocol | dose timing, "take on empty stomach", 先煎/後下 (decoct-first / add-later) | `processing` |
| **E9** | Failure → boundary | explicit warnings, contraindications, "not to be taken long" | `safety` layer |

E8 deserves emphasis: **先煎 / 後下 / 包煎 / 烊化** (decoct first / add late / wrap-boil / melt) are
explicit pharmacokinetic instructions — volatile oils (薄荷, 砂仁) are added late precisely because
they are volatile. This is folk-process-engineering that maps cleanly onto physical chemistry, and it
is almost entirely absent from modern NLP work on TCM.

---

## 4. Why the model must be small (< 1 GB) — a design argument, not a compromise

The user's constraint is also the correct architecture. Three separate arguments converge:

1. **Division of labour.** Knowledge belongs in the **index** (retrieval) and the **graph** (structure),
   not in the weights. Weights should hold *language and reasoning style*: how to read a 1596 entry,
   how to move between qualitative and mechanistic registers, how to phrase a falsifiable hypothesis.
   That is a small-model capability. Forcing facts into a tiny model is how you get confident
   fabrication.
2. **Auditability.** A domain model must be *inspectable*: which sources taught it this? A 20 M-parameter
   model trained on a corpus we can enumerate, plus a retrieval layer that cites spans, gives us
   provenance on **both** the linguistic and factual side. You cannot do that with a 70 B black box.
3. **Deployability where the knowledge is.** The people who hold this knowledge — clinics in Yunnan,
   Kerala, Tehran, Lhasa; under-resourced research groups — do not have GPUs. A ~400 MB quantised model
   that runs on a laptop, offline, is a *different product* from a hosted API.

So: **knowledge in the index, structure in the graph, reasoning in a small model, provenance
everywhere.** Parameter count is a design decision, not a limitation.

---

## 5. The skills (capabilities) the system must acquire — and how each is measured

Deriving data is half the job; the other half is the capability stack. Each capability has an owner
module and a **measurable** target. Capabilities marked ▣ are needed to keep improving the methodology
itself — they are the meta-level (§6).

| # | Capability | Module | Measure |
|---|---|---|---|
| S1 | Classical Chinese / Sanskrit tokenisation & modelling | `tokenizer/`, `model/` | chars-per-token per script; per-language bits-per-byte |
| S2 | Entity extraction over historical orthography | `shennong/extract/` | P/R/F1 on a hand-labelled gold set (≥100 spans) |
| S3 | Drug-name → modern taxon resolution (A6) | `shennong/decode/` | accuracy on a gold synonym set; calibration of `confidence` |
| S4 | Process-term → chemistry translation (A2) | `shennong/decode/` | expert spot-check of the process table; coverage of corpus process tokens |
| S5 | Relation extraction (drug, part, prep, indication, role) | `shennong/extract/` | F1 on gold tuples |
| S6 | Evidence grading & provenance | `shennong/kg/` | % of claims with resolvable span citation (target 100%) |
| S7 | Knowledge-graph construction & querying | `shennong/kg/` | graph stats; query correctness tests |
| S8 | Mechanism bridging (compound class → target class) | `shennong/discover/` | precision@10 of proposed bridges vs. literature |
| S9 | Hypothesis generation (§2 classes) | `shennong/discover/` | n hypotheses, class balance, citation coverage |
| S10 | Novelty computation vs. modern literature | `shennong/discover/` | agreement with a manual novelty audit |
| S11 | Falsification-plan generation | `shennong/discover/` | expert rating of feasibility/specificity |
| S12 | Grounded QA with refusal (A9) | `shennong/rag/` | answer accuracy; **refusal rate on unanswerable** |
| S13 | Safety / dual-use screening | `shennong/safety/` | block-rate on a red-team set; false-positive rate |
| S14 ▣ | Self-critique of its own hypotheses | `shennong/learn/` | fraction of self-critiques that identify a real flaw |
| S15 ▣ | Active learning: pick the most informative next document | `shennong/learn/` | information gain on held-out eval |
| S16 ▣ | Eval-gated methodology improvement | `shennong/learn/` | accepted changes only when a named held-out metric improves |

---

## 6. How the methodology improves itself (the continuous-learning loop)

The instruction is not "train once". It is: *identify the skills needed to keep improving the method.*
We implement **one honest round** of a gated loop rather than claiming an autonomous scientist:

```
        ┌─────────────────────────────────────────────────────────────┐
        │  1. RUN: cai → zhi → pei → shi, and the eval harness        │
        │  2. DIAGNOSE: which capability failed, on which items?      │
        │     (retrieval miss / resolution error / weak bridge /      │
        │      unfalsifiable plan / safety false positive)            │
        │  3. PROPOSE: a change in *methodology* (lexicon entry,      │
        │     process mapping, scoring weight, prompt, extraction      │
        │     rule) — not a tweet of the output                       │
        │  4. GATE: re-run on HELD-OUT eval. Accept only if the       │
        │     named metric improves and no other metric regresses     │
        │     beyond its confidence interval.                          │
        │  5. RECORD: eval/rounds/round-NNN.json with before/after,   │
        │     diff, and the reason. Rejected proposals are recorded    │
        │     too — the failures are the most honest artefact.         │
        └─────────────────────────────────────────────────────────────┘
```

Two rules keep this from becoming self-deception:

- **Held-out or it didn't happen.** The eval set is never used to design the change that is then
  "validated" on it. Changes are proposed from diagnostics on the *dev* split.
- **Rejections are published.** A loop that only ever accepts its own ideas is a random-walk with
  good PR. `eval/rounds/` will show refused changes.

The same loop, in principle, is what lets the system grow when new editions, new traditions or new
assay data arrive: the method (how to decode) improves, independently of the facts (what is decoded).

---

## 7. What would falsify this project

We commit to these in advance, because a project that cannot fail is not science.

1. **No signal in the negative controls.** If 取象比类 and ṣaḍrasa track pharmacology no better than
   chance, that is a *result*, not a failure — but if **every** structural encoding we test (process,
   role, rule) also shows no signal, then the premise that classical encoding carries recoverable
   information is dead and we should say so.
2. **Name resolution is unfixable at acceptable precision.** If drug-name → taxon resolution cannot
   beat ~60% F1 even with lexicon + POWO + context, the graph is built on sand and every downstream
   hypothesis is contaminated. We report resolution F1 first, before any discovery claim, for exactly
   this reason.
3. **Hypotheses are not novel.** If our top-ranked hypotheses are already in the modern literature at
   a high rate, the system is a slow search engine. Measured directly (§5 S10).
4. **The small model cannot read the originals.** If per-language bits-per-byte on classical Chinese
   is close to a unigram baseline, the model has not learned the register, and the "bilingual" claim
   must be withdrawn.

---

## 8. The one-sentence version

> Classical Asian medicine is a large, noisy, esoterically-encoded corpus of pharmacological
> observations; the binding constraint on discovering new drugs from it has never been data volume but
> **translation** — and translation is exactly what a small, domain-exclusive, classical-language model
> plus a first-principles knowledge graph can do at scale, provided every claim stays traceable to a
> span in a real text and every hypothesis arrives with the experiment that would kill it.
