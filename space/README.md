---
title: SHENNONG 神农
emoji: 🌿
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Pre-experimental filter for natural-product discovery
---

# SHENNONG 神农 — live demo

A **pre-experimental filter** for natural-product discovery: it lifts a processing instruction out of the
classical Asian medical record, compiles it into a chemical hypothesis, and uses validated physics to decide
whether the hypothesis is physically possible — before any wet-lab work.

This Space runs the same `app/serve.py` as the repository, with the judge demo served at `/`.

## What you can do here

| | |
|---|---|
| **Ask it live** | type any question → BM25 retrieval over 45.6 M characters → the 19.3 M MoE generates over the retrieved passages → citations with `source_id:char_start-char_end` |
| **Propose a hypothesis** | the model proposes one falsifiable hypothesis over retrieved evidence, with kill criteria attached and labelled UNVALIDATED |
| **Funnel / arbiter / theory / candidates / experts** | every number read from `artifacts/*.json` |
| **Curriculum & self-observation** | the staged training order, and the per-layer probe asking whether the model represents its own groundedness |

## Honest status

- The **pipeline** is the strong part: 78 of 203 enrichment claims refuted by validated physics, 歸經 at 2×
  chance (p = 0.008, n = 2,059, three published nulls), span-level citations over the whole corpus.
- The **model weights** are not: 19.3 M parameters trained on ~5.5 M tokens (≈1.4 % of compute-optimal).
  It reads the register; it does not write reliable sentences. The demo shows the bare completion next to the
  grounded one precisely so this is visible rather than hidden.
- Not medical advice. No dosing, no preparation protocols for toxic materia medica, no synthesis routes.

Code and weights: **Apache-2.0**. Corpus data keeps its per-source licences (public domain + CC BY-SA-4.0;
GRETIL rejected because CC BY-NC-SA cannot ship in a public repository).

Source: https://github.com/cptlight/shennong
