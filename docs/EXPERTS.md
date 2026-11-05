# EXPERTS — the multi-domain panel

Five experts, five tables, no shared evidence. See `shennong/experts/`.

## Why independence is the design

If two experts shared a source, their agreement would be circular. They do not: `ethnobotany` reads
corpus attestation counts, `phytochemistry` reads the compound table, `operator` reads the 炮制
ontology, `theory` reads the classical property vectors, `toxicology` reads toxicity markings and
structural alerts. Agreement between them is therefore evidence that *transferred across data types* —
which is what an interpolation is.

## Fusion rules (`shennong/experts/base.py`)

- a domain **supports** a claim at score ≥ 0.45;
- **agreement** = number of *distinct* domains supporting it;
- consensus = mean(score) × (1 + 0.06·(agreement−1)), capped at 1.0 — so agreement informs but never
  manufactures a score, and a strong 3-domain claim can outrank a weak 5-domain one;
- **disagreements are reported**, not averaged away;
- the verdict vocabulary has five values and no softer ones:

| agreement | verdict |
|---|---|
| 5 | five-domain interpolation — every expert agrees |
| 4 | four-domain interpolation |
| 3 | three-domain support — a genuine interpolation, worth an assay |
| 2 | two-domain support — hypothesis, not yet a finding |
| 1 | **single-domain assertion — NOT an interpolation** |
| 0 | no supporting domain — rejected |

## Observed distribution on the 203 cross-sections

5/5: 28 · 4/5: 59 · 3/5: 41 · 2/5: 75.

## Self-adjustment

`shennong/research/loop.py` acts on the diagnosis, not the threshold: it acquires evidence for the
blocking domain and re-runs. Round 1 upgraded 108 hypotheses (mean agreement 3.20 → 3.69); round 2
found nothing new and was **rejected and recorded**. See `artifacts/RESEARCH_LOG.md`.
