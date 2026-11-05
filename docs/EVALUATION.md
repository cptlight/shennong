# EVALUATION

The measurements, the experimental design, and — most importantly — the conditions under which we would have
to admit we were wrong.

`eval/report.json` is the machine-readable source for every number in this document. `docs/METHODOLOGY.md`
explains what is being measured; this file explains why the measurement is credible.

---

## 1. Design principles

1. **Pre-registration.** The tests, the metrics and the pass/fail thresholds were written before the results
   were computed, in this file. Where we changed something after seeing data, it is marked *[post hoc]* and
   the original is still shown.
2. **Effect size, n and p, always.** A p-value alone is not a result. Every test reports an effect size
   (AUC or ρ), the n it was computed on, and the p-value.
3. **A permutation null for every statistic.** All tests are compared against the distribution obtained by
   shuffling the theory vector across drugs (10,000 draws, seed recorded in the report). This protects
   against the most likely failure of this project — that a smoothed, class-imbalanced dataset makes any
   plausible feature look predictive.
4. **Multiple comparisons are corrected and disclosed.** The number of tests is small and stated; the
   correction method and the uncorrected values are both reported.
5. **Negative results are first-class.** A null is reported at the same prominence as a positive, with the
   same apparatus. This is the entire point of working on a two-thousand-year-old framework.
6. **Nothing is reported that a reader cannot recompute** from `eval/report.json` plus the repository.

---

## 2. The central experiment: does Asian pharmacological theory predict modern chemistry?

This is the intellectual centre of SHENNONG. Everything else — the corpus, the model, the graph — exists to
make this one experiment possible.

### 2.1 The five pre-registered tests

| # | Theory vector | Prediction | Metric | n |
|---|---|---|---|---|
| T1 | **四氣** (four natures: 寒/涼/平/溫/熱) | hotter drugs → more lipophilic, more volatile, less thermolabile; colder drugs → the reverse | AUC (ordinal nature vs. polarity/volatility class) | [[PENDING: eval.n_tcm_nature]] |
| T2 | **歸經** (channel tropism) | channel assignment predicts target organ or receptor family above chance | **hit rate** vs permutation (§2.1a) | [[PENDING: eval.n_tcm_channel]] |
| T3 | **五味** (five flavours) | flavour profile predicts receptor/action class (e.g. 苦 → GPCR-rich; 辛 → ion-channel/TRP-rich) | AUC (multi-label macro) | [[PENDING: eval.n_tcm_flavor]] |
| T4 | **vīrya** (Ayurvedic hot/cold potency) | uṣṇa → higher logP, lower thermolability; śīta → the reverse | Spearman ρ | [[PENDING: eval.n_ayurveda_virya]] |
| T5 | **ṣaḍrasa** (six tastes) | taste profile predicts pharmacological action class | AUC (multi-class, macro) | [[PENDING: eval.n_ayurveda_rasa]] |

### 2.1a The one deviation from the pre-registered plan — disclosed

T2 (歸經) was pre-registered with **macro-AUC**. When the harness was built it became apparent that the
predictor is **set-valued** — a drug enters several channels, and the target is an organ class — so there is no
natural negative class and macro-AUC would have to be manufactured by an arbitrary one-vs-rest choice. The
statistic was therefore changed to a **hit rate against a permutation null**: "does the channel-predicted organ
contain the recorded indication organ more often than a shuffled assignment?" That is the direct statistic for a
set-valued predictor, and it is harder to game than a synthesised AUC.

This change was made **before** the real-corpus run, it is the only metric substitution in the set, and it is
recorded here rather than absorbed silently. If a reviewer prefers the pre-registered macro-AUC, the harness can
produce it, and we will report both.

### 2.2 How a test is constructed

1. **Unit of analysis.** One row per `(drug, taxon)` pair with a confident name resolution and a property
   vector. Drugs with unresolved names are dropped, and the drop count is reported — a test run on the easy
   half of the corpus must say so.
2. **Feature.** The encoded vector from `docs/METHODOLOGY.md` §3. Ordinal where the tradition is ordinal;
   multi-hot where the tradition is multi-valued.
3. **Target.** A measured molecular or target property from structured open data (ChEMBL, PubChem, Duke),
   not a model output. Targets are binarised into interpretable classes by a published rule, not fitted.
4. **Statistic.** AUC for classification (0.5 = chance), Spearman ρ for ordinal association (0 = no
   association).
5. **Null.** Shuffle the property vector across drugs 10,000 times, recompute, and place the observed value
   in that distribution. p = fraction of permuted values at least as extreme.
6. **Thresholds, pre-registered:** a test counts as *predictive* only if **AUC ≥ 0.60 or |ρ| ≥ 0.15** **and**
   permutation p < 0.05. Below that it is reported as *trend, not significant*, or *no predictive signal*.
   The Workbench renders exactly these three verdicts — no fourth, softer vocabulary.

### 2.3 Results

| Test | Metric | Value | n | p (permutation) | Verdict |
|---|---|---|---|---|---|
| T1 四氣 → polarity/thermolability | AUC | [[PENDING: theory.tcm_nature_value]] | [[PENDING: eval.n_tcm_nature]] | [[PENDING: theory.tcm_nature_p]] | [[PENDING: theory.tcm_nature_verdict]] |
| T2 歸經 → target organ / receptor family | AUC | [[PENDING: theory.tcm_channel_value]] | [[PENDING: eval.n_tcm_channel]] | [[PENDING: theory.tcm_channel_p]] | [[PENDING: theory.tcm_channel_verdict]] |
| T3 五味 → action class | AUC | [[PENDING: theory.tcm_flavor_value]] | [[PENDING: eval.n_tcm_flavor]] | [[PENDING: theory.tcm_flavor_p]] | [[PENDING: theory.tcm_flavor_verdict]] |
| T4 vīrya → logP / thermolability | ρ | [[PENDING: theory.ayurveda_virya_value]] | [[PENDING: eval.n_ayurveda_virya]] | [[PENDING: theory.ayurveda_virya_p]] | [[PENDING: theory.ayurveda_virya_verdict]] |
| T5 ṣaḍrasa → action class | AUC | [[PENDING: theory.ayurveda_rasa_value]] | [[PENDING: eval.n_ayurveda_rasa]] | [[PENDING: theory.ayurveda_rasa_p]] | [[PENDING: theory.ayurveda_rasa_verdict]] |

**Multiple comparisons:** five pre-registered tests. Holm–Bonferroni corrected p-values are reported alongside
the raw ones in `eval/report.json`; both are shown in the Workbench card metadata. We do not report the
uncorrected value as the headline when the corrected one fails.

**Summary:** [[PENDING: eval.theory_summary]]

### 2.4 How to read a null here

A null result on T1–T5 does **not** mean "the tradition is worthless". It means one of four things, and we are
obliged to distinguish which:

- **(a)** the theory genuinely does not predict the specific modern property we chose (a real finding);
- **(b)** the property we chose is the wrong operationalisation (e.g. 四氣 may map onto something other than
  logP — pharmacokinetic half-life is a plausible alternative);
- **(c)** the extracted vectors are noisy because editions disagree (we report extraction agreement as a
  covariate);
- **(d)** the name resolution is too lossy for the subset we could test (we report the drop count).

We say which of these we believe and why. A null with no diagnosis is not a result.

---

## 3. Negative controls

Controls are not decoration. Two of the tests below can embarrass the entire project, and they are published
regardless.

### 3.1 取象比類 — reasoning by resemblance

**Claim under test:** does morphological, colour or habitat resemblance to an organ predict the recorded
indication better than chance? This is a foundational TCM analogical principle, and it is exactly what a naive
text-mining system will "discover" if you do not test for it.

- Result: ρ = [[PENDING: eval.quxiangbilei_rho]], p = [[PENDING: eval.quxiangbilei_p]], n =
  [[PENDING: eval.quxiangbilei_n]]
- Interpretation rule, pre-registered: a **strong** positive ρ would mean our extraction is picking up
  organ-word co-occurrence rather than pharmacology, and would invalidate the ranked list. A null is the
  expected and desired outcome.

### 3.2 Null model — shuffled edges

**Claim under test:** the discovery scores are measuring the graph's biology, not the scoring function.

Shuffle the plant↔use edges, recompute all discovery scores, and measure the drop.

- Result: score drop = [[PENDING: eval.null_model_drop]]
- Interpretation rule, pre-registered: a drop below 0.30 means the scoring is insensitive to structure and the
  ranked list must not be trusted. This control runs on every evaluation, not once.

### 3.3 Ayurvedic ṣaḍrasa

Listed as a theory test (T5) **and** as a control: if the six tastes predict action class, that is a positive
theoretical result; if they do not, the Ayurvedic encoding is not carrying information beyond the TCM one.
Reported either way.

---

## 4. Candidate novelty

Novelty is the axis most easily gamed, so its method is published.

For each candidate compound:

1. **Identity lookup** against open chemistry data (ChEMBL, PubChem) by name and — where a structure exists —
   by canonical SMILES/InChIKey.
2. **Target-space lookup**: is there a recorded bioactivity against the proposed target class? If yes, the
   candidate is *not* novel for that target, whatever the literature says.
3. **Literature-space lookup**: has the plant→compound→indication chain been asserted as a whole anywhere? A
   novel molecule with a well-known chain is not novel; a known molecule with an unasserted chain may be.
4. **Score** = 1 − (weighted fraction of the chain already asserted), with the weights exposed in
   `eval/report.json`. Calibration anchors are included deliberately: **artemisinin 0.02** (the most famous
   corpus-derived drug — if the scorer called this novel, the scorer is broken) and **fennel/parthenolide 0.18**.

Aggregate: `drug_discovery.mean_novelty` = [[PENDING: eval.mean_candidate_novelty]] over
[[PENDING: candidates.count]] candidates.

**What novelty does not mean.** A novelty score of 0.6 does not mean "new drug". It means "we could not find
this specific chain asserted in the modern literature we can search". Absence of evidence, stated as such.

---

## 5. Candidate plausibility rubric

A published rubric, not a model's opinion. Each candidate is scored 0–1 on four criteria, and the four
sub-scores are shown, not just the total:

| Criterion | 1.0 | 0.5 | 0.0 |
|---|---|---|---|
| **Structural validity** | resolved structure, formula consistent, no valence errors | formula only, structure pending | neither |
| **Target plausibility** | named target with an assay and a literature precedent for the compound class | target class inferred by analogy only | no target |
| **Synthetic / isolation accessibility** | commercially available standard or one-step isolation from a documented source | multi-step isolation | no route |
| **Toxicity risk** | no known class liability | known class liability but manageable | severe liability (PAINS, heavy metal, known organ toxin) |

Aggregate: `drug_discovery.lipinski_pass_rate` = [[PENDING: eval.lipinski_pass_rate]] of candidates with
resolved structures pass all evaluable Lipinski rules. Candidates with unresolved structures are excluded from
the denominator and the exclusion count is reported — a pass rate that silently drops failures is a lie.

---

## 6. Ablations

What each component actually contributes. All rows use the same held-out split and the same seeds.

| Ablation | Question | Result |
|---|---|---|
| **No theory vector** (drop TCM/Ayurvedic features, keep graph) | does the theory add anything over plain graph topology? | [[PENDING: ablation.no_theory]] |
| **No process translation** (treat 炮制 as opaque strings) | does mapping process words to chemistry change the ranking? | [[PENDING: ablation.no_process]] |
| **No name resolution** (exact-string drug matching) | how much does resolution alone buy? | [[PENDING: ablation.no_resolution]] |
| **Monolingual model** (English translations only, if transcriptions exist) | what does reading originals buy? | [[PENDING: ablation.monolingual]] |
| **Weight sweep** (uniform / novelty-heavy / testability-heavy) | is the ranking robust to the exponents? | [[PENDING: ablation.weight_sweep]] |

The weight sweep is reported as a **rank correlation** between orderings, not as a preferred answer. If the top
five change materially under reasonable weights, the ranking is weight-dependent and says so.

---

## 7. Grounding and refusal benchmark

The Ask surface must answer from retrieved spans or refuse. This is measured, not asserted:

| Metric | Definition | Result |
|---|---|---|
| **Grounded-answer rate** | fraction of in-scope questions answered with ≥ 1 citation per sentence | [[PENDING: eval.grounded_answer_rate]] |
| **Citation fidelity** | fraction of citations whose quoted span actually supports the sentence | [[PENDING: eval.citation_fidelity]] |
| **Correct-refusal rate** | fraction of out-of-corpus questions refused rather than answered | [[PENDING: eval.correct_refusal_rate]] |
| **Over-refusal rate** | fraction of in-scope questions wrongly refused | [[PENDING: eval.over_refusal_rate]] |
| **Policy-screen recall** | fraction of dosing / dual-use probes blocked by the safety screen | [[PENDING: eval.policy_screen_recall]] |
| **Policy-screen precision** | fraction of blocked probes that genuinely required blocking | [[PENDING: eval.policy_screen_precision]] |

The probe set is versioned in the repo so the numbers are comparable across runs. Over-refusal is reported as
prominently as under-refusal: a system that refuses everything is useless, and one that refuses nothing is
dangerous.

---

## 8. Reproducing every number here

```bash
make eval                      # → eval/report.json  (benchmarks, theory tests, controls, ablations)
python submission/check_pending.py    # → fails if any [[PENDING: …]] survives into a shipped artefact
```

Every row in this document is a field in `eval/report.json`. If a number appears here and not there, it is a
bug in the documentation and should be reported as one.

---

## 9. What would make us wrong

Written before the results, so that the results cannot rewrite it:

1. **If the null model does not collapse** (score drop < 0.30), the ranking is artefact and we withdraw the
   candidate shortlist.
2. **If 取象比類 shows a strong positive ρ**, our extraction is reading resemblance language and the whole
   ranked list is suspect.
3. **If the theory tests are null and the monolingual ablation performs equally well**, then reading originals
   bought nothing and the project's central novelty claim is false. We would report that.
4. **If candidate novelty collapses when checked against a human-curated prior-art list**, the novelty axis is
   measuring search coverage rather than discovery, and the ranking must be recomputed without it.
5. **If a candidate cannot be traced to a specific line of text in the corpus**, attribution fails and the
   candidate is withdrawn under our own TK policy (`docs/SAFETY_AND_ETHICS.md` §4).

None of these is hypothetical. Each is a live risk, which is why they are numbered.
