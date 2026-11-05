# JUDGES.md — SHENNONG in five minutes

You have a lot of repos to review. Here is the shortest path to judging this one.

## What it is, in one sentence

We read the pre-modern **Asian** record of medicine, alchemy and science (本草綱目, 神農本草經, 傷寒論,
黃帝內經, Charaka Saṃhitā, Suśruta Saṃhitā, al-Qānūn, 天工開物, 齊民要術, 夢溪筆談, 雷公炮炙論 …) in the
**original languages**, used **Asian pharmacological theory as the predictive framework**, and emitted a
ranked shortlist of **new drug candidates** — each with a structure, a mechanism, and the experiment
that would prove or kill it.

## The four questions you are probably asking

**1. Is this a real AI contribution, or a prompt wrapper?**
There is a **from-scratch, open-weights language model** trained on this machine — multilingual
(Classical Chinese + Sanskrit + English), under 1 GB, with real training logs and a real loss curve.
See [`model/MODEL_CARD.md`](model/MODEL_CARD.md) and [`training/runs/`](training/runs/). The model is
not the product; the *discovery pipeline* is. The model is the part that reads the register of a 1596
pharmacopoeia.

**2. Where is the science?**
The central experiment is: **do Asian pharmacological frameworks predict modern chemistry and target
biology?** 四氣五味 (four natures, five flavours), 歸經 (channel tropism), Ayurvedic rasa/vīrya — these
are encoded as feature vectors and tested against molecular properties and target families, with
permutation-tested nulls. Result, n, and p are in [`eval/report.json`](eval/report.json) under
`drug_discovery.theory_predictivity`. **We committed in advance to publishing the answer whether or
not it flatters the framework** — see [`docs/FIRST_PRINCIPLES.md`](docs/FIRST_PRINCIPLES.md) §7.

**3. Is any of it reproducible by me?**
Yes, on a CPU with no GPU and no network at inference:
```bash
make setup && make corpus && make tokenizer && make train-mini && make export && make eval && make workbench
```
Or the whole thing as one assertion-passing script: [`scripts/smoke_e2e.sh`](scripts/smoke_e2e.sh).
Contracts between subsystems are machine-checked by
[`scripts/verify_contracts.py`](scripts/verify_contracts.py) and run in CI
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) — including the **< 1 GB** and **≤ 1 B
parameter** ceilings.

**4. What would I actually look at if I only look at three things?**
1. [`artifacts/drug_candidates.md`](artifacts/) — the candidate shortlist (the deliverable).
2. [`eval/report.json`](eval/report.json) — the theory-predictivity experiment and the benchmarks.
3. [`docs/FIRST_PRINCIPLES.md`](docs/FIRST_PRINCIPLES.md) — the derivation of the data from axioms, and
   the four ways this project could have been wrong.

## Where each judging criterion is addressed

| Criterion | Where |
|---|---|
| **Scientific relevance** | `docs/FIRST_PRINCIPLES.md` §1–3; the six discovery classes in `PROJECT_BRIEF.md` §2; `docs/METHODOLOGY.md` |
| **Novelty / creative data use** | Asian-theory-as-predictor (`eval/report.json`); alchemical & 炮制 process→chemistry decoding (`shennong/decode/processes.py`); bilingual classical modelling (`tokenizer/`) |
| **Technical implementation & reproducibility** | `Makefile` (one command per stage), `scripts/smoke_e2e.sh`, `scripts/verify_contracts.py`, CI, `training/runs/*/metrics.json` |
| **Data-science quality** | permutation-tested statistics, null model, ablations, calibration, explicit uncertainty — all in `eval/report.json` and `docs/EVALUATION.md` |
| **Scalability beyond the hackathon** | `docs/ROADMAP.md`; the pipeline is corpus-agnostic — new traditions, editions and assay data plug into 采→制→配→使 without retraining the model |
| **Benefit (conservation / drug discovery / public health)** | drug candidates; herb–drug interaction prediction (十八反/十九畏); adulteration safety (異名同物, the *Aristolochia* nephropathy case); CITES substitute discovery (瀕危代用品) |
| **Safety & ethics** | `shennong/safety/`, `tests/` red-team cases, `docs/SAFETY_AND_ETHICS.md` (incl. Nagoya Protocol / Traditional Knowledge policy) |

## What is real vs. what is a recipe

- `shennong-mini`: **actually trained** on this machine, CPU only. Logs, loss curve and GGUF are real;
  exact sizes and hashes are in `model/MODEL_CARD.md`.
- `shennong-0.5b`: a **fully executable recipe** (domain continued-pretraining → LoRA SFT → merge →
  Q4_K_M GGUF ≈ 350–400 MB). It is **not** claimed to have been run at that scale here. The model card
  says so in the same sentence as the numbers.
- Every benchmark number in the repo is produced by a command in this repo. No number is estimated.

## The honest limitations (please read these too)

`shennong-mini` is a small model on a modest corpus; it is not a factual oracle. Drug-name → taxon
resolution is the weakest link, and its F1 is reported *before* any discovery claim because everything
downstream depends on it. The candidates are **leads for experimental testing**, not drugs; nothing
here is medical advice and nothing has been tested in vitro or in vivo. The corpus skews Chinese
because that is where the largest public-domain original-language canon is — the DATA_CARD quantifies
the imbalance instead of hiding it.

<div align="center">

*「青蒿一握，以水二升漬，絞取汁，盡服之。」 — 葛洪《肘後備急方》*

*The Nobel Prize in Physiology or Medicine 2015 was awarded for reading that line correctly.*

</div>
