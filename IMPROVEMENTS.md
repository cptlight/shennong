# IMPROVEMENTS — audit of the "make the system stricter, not the model bigger" agenda

This is a response to a list of eleven architectural improvements. The short version:

> **Six of the eleven are already the architecture. Three are partially built. Two are not built and
> should be the next work. The framing — that value lives in the system around a small model, not in
> more parameters — is the design thesis of this repository, not a retrofit.**

Grading below is deliberately harsh: "implemented" means *there is code on disk and a test or an
artefact that exercises it*, not "we believe in it".

| # | Improvement | Status | Where |
|---|---|---|---|
| 1 | Move the "compiler" out of the neural net — deterministic cited lexicon + rule engine | ✅ **implemented** | `shennong/ontology.py`, `shennong/extract/lexicons.py`, `shennong/decode/`, `corpus/processed/lexicon_drugs.json` (827 entries) |
| 2 | Retrieval-augmented, span-grounded generation with a strict verifier | 🟡 **mostly** | `shennong/rag/` (BM25, span citations, refusal), renderer-level refusal check. **Missing: embedding-based semantic verifier** |
| 3 | Neuro-symbolic constraint layer | 🟡 **partial** | `shennong/chem.py` (SMILES parser, MW/HBD/HBA/TPSA/rings/rotBonds, Lipinski, Veber, PAINS-lite). **Missing: mass-balance checks, assay-feasibility schema, live novelty lookup** |
| 4 | Grammar-constrained structured output | ✅ **effectively** | Output is dataclass-defined JSON (`chain`, `scores`, `uncertainty`, `falsification`, `safety`), validated by the Workbench. **The small LM generates prose, not JSON** — the pipeline, not decoding, enforces the schema |
| 5 | Per-tradition LoRA adapters | ❌ **not built** | `training/flagship/` is the shared-base path; adapters are a documented next step |
| 6 | Active learning with expert review | 🟡 **partial** | `shennong/learn/active.py` (information-gain selection), `shennong/learn/loop.py` (eval-gated rounds). **Missing: the human review queue** |
| 7 | Calibrated novelty and confidence | 🟡 **partial** | Novelty is operationalised against a curated exclusion list + graph evidence, with an explicit "upper bound" caveat. **Missing: reliability diagrams, calibration against human judgments** |
| 8 | Pre-registration + falsification harness as first-class code | ✅ **implemented** | `docs/EVALUATION.md` (thresholds written before results, Holm–Bonferroni, one disclosed deviation), `shennong/eval/controls.py` (permutation nulls, shuffled-edge null, refusal benchmark), `eval/rounds/` |
| 9 | Ensembling + distillation | ❌ **not built** | — |
| 10 | Quantisation + CPU-first, offline deployment | ✅ **implemented** | f16 GGUF in `artifacts/`, `training/flagship/export_gguf.sh` for Q4_K_M, stdlib-only offline Workbench, `make` targets |
| 11 | Explicit "what this cannot do" contract | ✅ **implemented** | `safety.tier`, kill-criteria per hypothesis, "research use only" in schema, `docs/SAFETY_AND_ETHICS.md`, refusal-by-default |

## The three that matter most, and what we would actually do next

### 1. Embedding-based semantic verifier (the biggest real gap in #2)
We verify that a cited **span exists and contains the entity**. We do not verify that the span
**supports the claim**. That is the difference between a citation checker and a verifier.

Next step: a small distilled multilingual encoder (e.g. a 30–100 M sentence model), offline, scoring
`support(candidate_claim, retrieved_span)` with a threshold calibrated on ~300 human-labelled pairs
we would have to create first. Cost: ~100 MB and ~2 days of labelling. This is the single highest-
value addition to the stack and it does not touch the LM.

### 2. Live novelty lookup instead of a curated exclusion list (#3, #7)
Today novelty is "not in our curated list of ~180 known compounds/species + graph evidence" and is
explicitly an **upper bound** (`artifacts/drug_candidates.md` says so). The honest fix is a tool call
against PubChem/ChEMBL at generation time, plus a **structural** novelty measure rather than a name
match — we already have 23,176 SMILES, so Tanimoto-style distance to the nearest known compound is
implementable **offline, today**, and would replace a name-based proxy with a chemistry-based one.
That is the next engineering task if the project continues.

### 3. Calibration surfaces, not just scores (#7)
We report a composite with an uncertainty interval and a sensitivity analysis over the weights, and we
pre-registered a withdrawal threshold for the null model. What is missing is **reliability**: does a
hypothesis scored 0.8 succeed 80 % of the time? Nobody can answer that without a prospective test, so
the only honest position is the one in the report: *scores rank hypotheses, they are not probabilities.*
We should print that sentence next to every number, and eventually calibrate on expert ratings.

## Where we disagree — respectfully

**On ensembles and distillation (#9):** for this artefact the bottleneck is not model reliability, it
is *coverage of the evidence*. An ensemble of three 8.7 M models trained for 45 minutes on a CPU would
produce three similar mediocre models and one more thing to keep in sync. The 0.5 B flagship with a
real GPU is the better use of the same effort. Ensembling becomes interesting *after* the base model is
actually trained to compute-optimal.

**On grammar-constrained decoding (#4):** it is the right tool when a model emits final answers. Here
the LM does not — it is one component whose output feeds a JSON pipeline with a schema, validation and
a refusal gate. Adding GBNF decoding to an 8.7 M model would constrain a component that is already
constrained by construction. It becomes essential for the flagship path, where the model writes the
dossier fields directly.

**On per-tradition LoRA (#5):** correct in principle, but it presumes a base that has spare capacity.
At 0.19 tokens/param we are nowhere near the point where specialisation is the binding constraint —
data coverage and the join rate between the classical texts and modern taxa are (47 % of property rows,
43 % of use rows resolve to a binomial). Fixing the join moves more than any adapter at this scale.

## What we would do with another week, in order

1. **Inverse folding / chemotype expansion** — go from "this plant contains this class" to concrete
   candidate structures using the 23 k SMILES as the space.
2. **Semantic verifier** (above) — turn citation checking into claim checking.
3. **Structural novelty** (above) — replace the name-list proxy with a chemistry-based measure.
4. **Assay-feasibility schema** — every hypothesis must name endpoint, direction, control and a
   plausible sample size; the symbolic checker rejects output that cannot fill the form.
5. **Expert review queue + calibration labelling** — 300–1,000 pairs, then reliability diagrams.
6. **Train the 0.5 B flagship to compute-optimal** on a GPU (the recipe is in `training/flagship/`).

The one thing we would **not** do is make the model bigger before items 1–3 are done. That is the
agenda this document was asked to respond to, and it is correct.
