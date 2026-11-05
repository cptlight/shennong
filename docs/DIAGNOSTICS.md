# DIAGNOSTICS — what the system says about itself

Two things in this project are not claims about the corpus; they are measurements of the system. They are
the most novel artefacts here, and they are also the ones that can be wrong in a way that flatters us, so
each is reported with the check that could embarrass it.

---

## 1. The funnel is panel-size invariant

The headline funnel was computed twice: once with the **7-expert** panel, once with the **12-expert**
panel after molecular mechanics, quantum chemistry, taxonomy, chemotaxonomy, extraction, ADME and
microbiome were added.

| Stage | 7 experts | 12 experts |
|---|---|---|
| candidates | 203 | 203 |
| excluded at the ancient-record gate | **151** | **151** |
| excluded at the Asian-theory gate | 24 | 24 |
| pass both gates | **28** | **28** |
| refuted by first-principles physics | **10** | **10** |
| survive everything | **18** | **18** |

**Identical.** Adding five experts did not move a single count, because the gates are structural and the
arbiter is physics. That is the property worth quoting: the result does not depend on how many experts
you bolt on.

The numbers to lead with are therefore, in this order: **203 → 151 excluded at the record gate → 28 pass
both gates → 10 refuted by arithmetic → 18 survive.**

*(A bug was found and fixed in the process: adding `taxonomy` to stage 1 briefly let a merely *resolvable*
plant name satisfy the attestation gate, collapsing 151 → 0. Gates are now judged by their **designated**
expert, not by "any expert assigned to that stage". Recorded here because the reviewer should know the
number was checked, not just produced.)*

---

## 2. The expert self-diagnostic — and the bug it caught

Each expert's score is tested for whether it **predicts the arbiter's verdict**: AUC of the expert score
against the binary outcome *"survived first-principles arbitration"*. Utility is defined by physics, not
by agreement — an expert that merely makes claims pass is worthless.

### Measured on 60 staged claims (18 survived = 30 % base rate)

| Expert | AUC | Reading |
|---|---|---|
| theory | 0.893 | informative |
| ethnobotany | 0.889 | informative |
| toxicology | 0.838 | informative |
| mechanics | 0.707 | informative |
| **phytochemistry** | **0.607** | **informative (after fix — see below)** |
| quantum | 0.578 | informative, weak |
| microbiome | 0.535 | no information |
| taxonomy · operator · chemotaxonomy | 0.500 | no information (constant scores on this subset) |
| extraction | 0.300 | **anti-predictive — needs the same check** |
| adme | 0.282 | **anti-predictive — needs the same check** |

### The finding that was a bug

The first run showed `phytochemistry` at **AUC 0.443 — below chance**. The apparent conclusion was that
the expert was measuring data sparsity rather than validity. That conclusion was *partly* right and
*partly* a coding artefact:

- the expert added **+0.15 for a "narrow" chemotype** (≤2 compound classes), on the theory that a narrow
  chemistry gives a sharper prediction;
- sparse-chemotype plants are disproportionately the ones that fail physical checks;
- so the bonus was rewarding the plants most likely to be refuted.

Recomputing **with the bonus removed** moved the AUC from **0.443 → 0.607**. The prior was removed (the
code comments say why), and the measurement now reports `phytochemistry` as informative.

**The diagnostic is the asset, not the original finding.** A single line of prior was silently costing
0.16 AUC, and nothing else in the system would have revealed it.

### Same check, not yet applied

`extraction` (0.300) and `adme` (0.282) are below chance and are candidates for the identical treatment —
each has a hand-written scoring rule that could be mis-signed. **They have not been re-coded**, so they are
reported as suspect rather than fixed, and they are now down-weighted by the router's exploration floor.

---

## 3. Routing: sparse at item level, denser at question level

| stream | mean experts/item | fraction of the 12-expert panel |
|---|---|---|
| rich structured items (203 cross-sections) | 9.15 | 76 % |
| **mixed realistic stream (389 items)** | **2.25** | **18.7 %** |
| **natural-language questions (12)** | **6.17** | **51.4 %** |

Plain corpus text activates **one** expert (`ethnobotany`). Questions activate more, because a question
that names a plant legitimately needs taxonomy, chemotaxonomy and phytochemistry as well as the record
check — 12 named questions produced activation counts from 5 to 9 and **12 distinct panellings**. The
question-level claim is the interesting one for the Workbench, and it is measured, not asserted.

---

## 4. Which laws actually fired

| check | evaluated | turned into a rejection |
|---|---|---|
| `process_physics` (P2/P3/C2 — energy, phase partitioning, Arrhenius) | 203 | **78** |
| `mass_conservation` (P1/C1) | 203 | **0** |

**78 of 203 candidates are rejected by the physics alone.** The mass-conservation law never fired, and the
honest reason is that the generated claim text says *"should measurably change"*, not *"should enrich"* —
so the absolute-enrichment branch is never reached. The law is operationalised but not yet triggered by
our own phrasing; either the claim template should use the stronger word where it applies, or the law
should be retired from the "load-bearing" list. Stating this is better than claiming fifteen working laws.

---

## 5. Structural novelty — fixed, and now guarded

| | |
|---|---|
| distinct novelty values | **42** across 60 candidates |
| range | **0.000 – 0.750** |
| mean | 0.2825 |
| method | `1 − max Tanimoto` (ECFP-style, radius 2) against 23,172 structures, excluding own compound and own source plant |

An earlier version scored **every candidate 0.88** from a curated-name prior, which made the rank order
meaningless. It regressed once when `shi` regenerated the artefact, so a **contract-level guard now fails
the build** if novelty is degenerate (`scripts/verify_contracts.py` → `artifacts.novelty`), and
`make novelty` / `scripts/finalize.sh` refresh it after any regeneration.

---

## Honest limits of this whole document

- n = 60 for the AUC table, 30 % base rate: wide error bars, and high AUCs for `theory`/`ethnobotany` may
  reflect **data completeness** (items with full property vectors are complete everywhere) rather than
  causal informativeness.
- The routing prior is **global**, not per-context. Per-context specialisation needs 3-fold cross-fitting
  and far more claims before its weights mean anything.
- Two experts are below chance and unre-coded; one law never fires. Both are stated, not hidden.
