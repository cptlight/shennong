# CONTINUOUS LEARNING

How SHENNONG improves itself without becoming either a myth or a rubber stamp.

The honest version first: **there is no online learning loop running against users.** "Continuous learning"
here means a reproducible, eval-gated cycle that a human can run and audit, in which a change to the corpus,
the model, the extractors or the scorer is accepted only if it improves a published benchmark table. The gate
is code, not a promise.

---

## 1. What a "round" is

A **round** is one complete pass:

```
collect (采) → prepare (制) → combine (配) → deploy (使) → measure → gate → accept or reject
```

Each round is identified by `<date>-<n>` and is fully described by one file: `eval/report.json`, plus the run
configs it references. A round is **not** a commit — several commits may belong to one round, and a round may
be rejected outright and never merged.

```bash
make round ROUND=2026-11-05-1        # runs the whole cycle, writes eval/rounds/2026-11-05-1.json
```

A round record contains:

| Field | Meaning |
|---|---|
| `round_id` | `YYYY-MM-DD-n` |
| `parent` | the round it was compared against |
| `corpus` | sources, chars, per-tier and per-tradition counts, and **the diff** against the parent |
| `model` | run id, params, steps, loss curve reference |
| `extractors_version` | version tag of lexicons and process maps |
| `benchmarks` | the full table (see `docs/EVALUATION.md`) |
| `deltas` | per-metric change vs. parent, with the direction that counts as improvement |
| `decision` | `accepted` / `rejected` / `accepted-with-caveat` |
| `rationale` | one paragraph, human-written, naming the trade-off |

The `rationale` field is not optional and is not generated. A round that cannot be explained in a paragraph
has not been understood well enough to adopt.

---

## 2. The gate

A candidate round is **accepted** only if all of the following hold, evaluated mechanically by
`shennong/learn/gate.py`:

1. **No regression on the invariants.** `pytest` green; corpus validator green (every record traces to a
   `status: ok` source; every source has a licence and licence evidence).
2. **No regression on the negative controls.** The null-model score drop must stay ≥ 0.30, and 取象比類 must
   not become strongly predictive. A round that "improves" results by weakening a control is rejected
   without discussion — this is the failure mode that destroys projects of this kind.
3. **Theory tests do not degrade.** For each of T1–T5 (`docs/EVALUATION.md` §2), the value must not fall
   below its parent by more than the pre-registered tolerance (δ = 0.02 AUC / 0.05 ρ). A small decline in one
   test is allowed if another improves enough to compensate; the accounting is shown in `deltas`.
4. **The primary metric improves.** The primary metric is the composite of (a) theory-predictivity summary
   statistic, (b) candidate plausibility mean, (c) grounded-answer rate. A round must improve the composite
   by more than noise — estimated by re-running the parent's evaluation with a different permutation seed and
   taking the spread as the noise floor.
5. **Refusal behaviour does not degrade.** Over-refusal and under-refusal must both stay within tolerance.
   A round that improves grounding by refusing more is rejected.

**What the gate explicitly does not reward:** a bigger model, a longer corpus, or more candidates. Size is not
the metric. Every round is judged on what the measurements did, at whatever size.

---

## 3. The three loops

The gate is the same; what changes per round is what is being improved.

### Loop A — corpus growth (fastest, lowest risk)

Add sources → re-run 采 制 配 → measure. New text is the cheapest improvement available, and the licence audit
is the constraint, not the compute. Typical round: hours.

Rounds are expected to *hurt* short-term: a new tradition introduces contradictions with the old extraction,
and the initial delta is often negative until the extractors catch up. The gate rejects those rounds, which is
correct — but it means corpus rounds are usually paired with extractor work.

### Loop B — extractor and lexicon improvement (medium)

Better name resolution, better process-term mapping, better property extraction. Measured by:

- **resolution F1** against a growing manually-annotated gold set;
- **extraction agreement** across editions (a proxy for reliability);
- **downstream** effect on theory tests and candidate plausibility.

The extractor round is the highest-leverage loop, because a systematic extraction error corrupts every
downstream measurement in a way that is invisible in the aggregate.

### Loop C — model retraining (slowest, highest cost)

Retrain `shennong-mini` on the grown corpus, or fine-tune on extracted structures. On a CPU-only machine this
is the expensive loop and it is gated hardest: a retrain must beat the parent on the grounded-answer and
refusal benchmarks, not merely on loss. **Lower loss is not evidence of a better research instrument** — a
model can get better at fluent classical prose while getting worse at refusing. The gate uses the task
benchmarks, not the loss curve.

---

## 4. Self-improvement of the scorer: the part we are careful about

It is tempting to let the ranking function learn from its own outputs. We do not, and the reason is stated so
it can be argued with.

- **The scorer does not train on unvalidated hypotheses.** A hypothesis that has not been externally
  validated (by a domain expert, or eventually by an assay) is not a label. Training on it is how a system
  learns to reproduce its own priors and calls it learning.
- **What does change** is the *calibration* of the score axes: the mapping from raw evidence to 0–1 values is
  refit against expert ratings collected each round. Expert ratings are the only labels admitted.
- **Every calibration change is a round** and must pass the same gate, including the negative controls.
- **Dissent is recorded.** When an expert disagrees with the ranking, that disagreement is stored as a labelled
  example with the reason. The disagreement log is part of the artefact set, because a scorer that has never
  been contradicted has never been tested.

This is slower than self-training, and it is the only version we can defend.

---

## 5. What "learning" is not allowed to do

Hard constraints on any round, enforced by the gate and by review:

1. **It may not weaken a negative control** to improve a headline. Control regressions are an automatic reject.
2. **It may not add sources with unclear licences.** `UNVERIFIED` is terminal, not a pending state to be
   flipped by convenience.
3. **It may not remove a safety annotation**, or make one collapsible, or relegate one to a tooltip.
4. **It may not improve novelty scores by narrowing the prior-art search.** The novelty instrument's coverage
   is itself measured (a fixed probe set with known-answer pairs).
5. **It may not report a metric that a reader cannot recompute** from `eval/report.json`.
6. **It may not merge a round whose `rationale` is empty.**

---

## 6. Scheduling and cost

On this machine (CPU-only, i7-4790K):

| Loop | Wall clock | Frequency | Gate cost |
|---|---|---|---|
| A — corpus growth | minutes to hours | whenever a vetted source lands | cheap (no training) |
| B — extractors | hours | weekly | cheap (no training) |
| C — retrain | hours to days | rarely, and only with a clear hypothesis | expensive |

The asymmetry is deliberate: most improvement should come from Loop A and B, which is also the cheapest and
most auditable path. Reaching for a bigger model to fix an extraction problem is the classic mistake in this
kind of project, and the gate is designed so that it does not work.

---

## 7. Reproducing a round

```bash
make round ROUND=<id>              # full cycle + gate
make gate ROUND=<id> PARENT=<id>   # re-run just the gate (no training)
cat eval/rounds/<id>.json | jq .decision,.rationale
```

Every accepted round leaves the four artefacts a reviewer needs: the report, the diff against its parent, the
decision, and the paragraph explaining it. A reader who disagrees with a decision has everything required to
contest it — which is the only sense in which "continuous learning" is a virtue rather than a marketing word.
