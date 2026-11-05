# ARCHITECTURE

## Design thesis

> **Knowledge in the index. Structure in the graph. Reasoning in a small model. Provenance everywhere.**

A one-billion-parameter ceiling forces a clean division of labour, and the clean division of labour is
what makes the system auditable. The model is not asked to *remember* the materia medica; it is asked
to *read* it, *translate registers*, and *propose falsifiable claims* whose evidence is resolved
elsewhere.

```
                         ┌───────────────────────────────────────────────┐
  public-domain texts ──▶ │  采 CǍI   ingest · clean · provenance         │
  (zh-Hant, sa, ar,     │           corpus.jsonl + registry/sources.yaml│
   fa, bo, ja, ko, en)   └───────────────────────┬───────────────────────┘
                                                  │
                         ┌───────────────────────▼───────────────────────┐
                         │  制 ZHÌ   normalise · resolve · decode        │
   POWO / WCVP ────────▶ │  drug-name → modern taxon; process → chemistry│
   Dr Duke / PubChem     │  lexicon_drugs.json · process_table.json      │
   TCMID-type CSVs       └───────────────────────┬───────────────────────┘
                                                  │
                         ┌───────────────────────▼───────────────────────┐
   ChEMBL / KEGG ──────▶ │  配 PÈI   combine into the knowledge graph    │
   STRING / GO / MeSH    │  plant–compound–target–pathway–indication     │
                         │  formula roles · incompatibility edges        │
                         └───────────────────────┬───────────────────────┘
                                                  │
                         ┌───────────────────────▼───────────────────────┐
                         │  使 SHǏ   deploy: hypotheses + falsification  │
                         │  6 discovery classes · scoring · dossiers      │
                         └───────────────────────┬───────────────────────┘
                                                  │
        ┌─────────────────┬───────────────────────▼────────────┐
        │  eval/report.json│  app/data/*.json  →  Workbench     │
        └─────────────────┴────────────────────────────────────┘
```

## Runtime components

| Component | Path | Role | Deps |
|---|---|---|---|
| Corpus builders | `data/`, `corpus/` | fetch, licence-audit, clean, dedupe, chunk | requests, bs4 |
| Tokenizer | `tokenizer/` | byte-level BPE over zh-Hant + sa + en | tokenizers |
| Language model | `model/`, `training/` | `shennong-mini` (from scratch), `shennong-0.5b` recipe | torch (CPU) |
| Package `shennong` | `shennong/` | ontology, extraction, decoding, KG, discovery, RAG, safety, learn, eval | numpy, stdlib |
| Workbench | `app/` | stdlib HTTP server, vanilla JS; reads `app/data/*.json` | stdlib only |
| Evaluation | `eval/` | benchmark harness, negative controls, ablations | pytest, numpy |

Import direction is strictly one-way: **`shennong/` must not import from `data/`, `training/` or
`app/`.** It reads only the processed artefacts on disk.

## Package layout (`shennong/`)

```
shennong/
  ontology.py     dataclasses + controlled vocabularies (Tier 0), incl. the 炮制→chemistry table
  config.py       paths, weights, thresholds; no global state
  kg/             build.py (corpus.jsonl + CSVs → graph), schema.py, queries.py, store.py
  extract/        lexicons.py, orthography.py (繁/简, long-s, IAST↔Devanagari), entities.py, relations.py
  decode/         drugs.py (name→taxon, A6), processes.py (process→chemistry, A2), rules.py (十八反/十九畏/viruddha)
  discover/       primitives.py, incompatibility.py, processing.py, name_collision.py,
                  formula_role.py, understudied.py, endangered.py, score.py, plan.py
  rag/            bm25.py, index.py, grounded.py, cite.py
  safety/         screen.py (dual-use, dosing, self-treatment), toxicology.py (Hg/As/Pb drugs as data)
  learn/          loop.py (eval-gated rounds), active.py (information-gain selection), rounds.py
  eval/           bench.py, controls.py, report.py
  cli.py          cai | zhi | pei | shi | ask | report
```

## Data flow at query time

```
"ask"   → BM25 retrieve over passages → span-cited context → small model composes answer
        → safety screen → if citations unresolved, refuse.
"shi"   → load KG → for each discovery module, enumerate candidate (drug, claim) pairs
        → mechanism bridge via compound-class → target-class edges
        → novelty = not already linked in the modern-evidence layer
        → score = f(novelty, plausibility, testability, evidence) with uncertainty
        → attach falsification plan + provenance chain
        → rank, dedupe near-duplicates, assign 君臣佐使 role label
        → emit JSON dossiers
```

## Failure modes we design around (explicitly)

| Failure | Mitigation |
|---|---|
| **Fabricated citations** | every claim carries `(source_id, char_start, char_end)`; the renderer verifies the span exists before printing it |
| **Confident nonsense** | small model + retrieval-only grounding; refusal when no span supports the claim |
| **Name-collision contamination** | resolution confidence is a first-class field; low-confidence edges are excluded from discovery, not averaged in |
| **Survivorship bias** | discovery reports *convergence count* and *tradition diversity*, never treats a single attestation as strong |
| **Scoring theatre** | the weight sensitivity is computed and printed; if the ranking is unstable under plausible weights, we say so |
| **Safety leakage** | the toxicology module has read access to Hg/As/Pb drug entries but the *emitter* refuses to produce dosing or preparation instructions; red-team tests in `tests/` |
| **Self-deception in the learning loop** | held-out gating, recorded rejections (`eval/rounds/`) |

## Reproducibility contract

- Every artefact has a `sha256` and the command that produced it.
- Every source has a licence and an evidence URL; `status: unverified` is excluded from training.
- One `make` target per stage; the entire pipeline runs CPU-only.
- Deterministic where the maths allows it: fixed seeds, fixed corpus hash, recorded torch version.
- `training/runs/<id>/metrics.json` is the single machine-readable record of a run — no number appears
  in the README, model card, slides or Devpost text that is not traceable to one of these files.
