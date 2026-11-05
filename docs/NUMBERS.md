# NUMBERS — the ledger of every number this project claims

Every quantitative claim in `docs/` and `submission/` resolves to **one** file. This document is that
mapping, plus the live list of values still owed by the pipeline. It is intentionally excluded from the
`[[PENDING]]` ship gate (`submission/check_pending.py`), because its job is to name what is missing.

**Rule:** a number not listed here does not go in the Devpost, the deck, the video or the docs. If it cannot be
traced, it is a mistake.

---

## 1. Source of truth per artefact

| Number | Produced by | Read from |
|---|---|---|
| Corpus sources (kept / excluded), characters, tiers, traditions, languages, licence split | `data-curator` | `corpus/registry/sources.yaml`, `corpus/DATA_CARD.md` |
| Token count, vocab size, held-out split | `data-curator` / `model-forge` | `corpus/DATA_CARD.md`, tokenizer report |
| Model parameters, steps, tokens seen, final train/val loss, ppl, bits/byte, wall clock | `model-forge` | `model/MODEL_CARD.md`, `training/runs/<id>/metrics.json` |
| Loss curve (points, train and val) | `model-forge` | `training/runs/<id>/metrics.json → loss_curve` |
| Benchmark table | `discovery-engine` | `eval/report.json → benchmarks` |
| Theory predictivity (AUC/ρ, n, p, corrected p) | `discovery-engine` | `eval/report.json → drug_discovery.theory_predictivity` |
| Negative controls (取象比類 ρ/p, null-model drop) | `discovery-engine` | `eval/report.json → negative_controls` |
| Ablations | `discovery-engine` | `eval/report.json → ablations` |
| Candidate count, resolved structures, mean novelty, Lipinski pass rate | `discovery-engine` | `artifacts/drug_candidates.json`, `eval/report.json → drug_discovery` |
| Refusal / grounding rates | `discovery-engine` | `eval/report.json → refusal_benchmark` |
| Hypothesis count and class spread | `discovery-engine` | `app/data/hypotheses.json` |
| Workbench payload size | `story-builder` | `wc -c app/static/*` — checkable with one command |

**Workbench provenance:** every panel reports which of these files it actually loaded, and whether that file is
real or a `DEMO FIXTURE`. `python app/serve.py` prints the same table at startup. If a panel says `FIXTURE`,
nothing on it may be quoted.

---

## 2. Values still owed (live `[[PENDING]]` list)

Each row names the placeholder exactly as it appears, the artefact that resolves it, and where it is used.

### Corpus — owed by `data-curator`

| Placeholder | Resolves from |
|---|---|
| `corpus.sources_ok` | `sources.yaml` count where `status: ok` |
| `corpus.excluded` | `sources.yaml` count where `status != ok` |
| `corpus.chars` | sum of `chars` over `status: ok` |
| `corpus.languages` | distinct `lang` over `status: ok` |
| `corpus.traditions` | distinct `tradition` over `status: ok` |
| `corpus.licence_dom` | count of `licence: Public Domain` over `status: ok` |
| `corpus.licence_ccby` | count of `licence: CC-BY-SA-4.0` over `status: ok` |
| `corpus.n_stages_commands` | number of `make` stages in the `Makefile` |

### Model — owed by `model-forge`

| Placeholder | Resolves from |
|---|---|
| `model.mini_params` | `model/MODEL_CARD.md` / `metrics.json → params` |
| `model.steps` | `metrics.json → steps` |
| `model.tokens` | `metrics.json → tokens_seen` |
| `model.final_train_loss` | `metrics.json → final_train_loss` |
| `model.final_val_loss` | `metrics.json → final_val_loss` |
| `model.val_ppl` | `metrics.json → val_ppl` |
| `model.bits_per_byte` | `metrics.json → bits_per_byte` |

### Evaluation — owed by `discovery-engine`

| Placeholder | Resolves from |
|---|---|
| `theory.tcm_nature_value` / `_p` / `_verdict` | `report.json → drug_discovery.theory_predictivity.tcm_nature` |
| `theory.tcm_channel_value` / `_p` / `_verdict` | `… .tcm_channel` |
| `theory.tcm_flavor_value` / `_p` / `_verdict` | `… .tcm_flavor` |
| `theory.ayurveda_virya_value` / `_p` / `_verdict` | `… .ayurveda_virya` |
| `theory.ayurveda_rasa_value` / `_p` / `_verdict` | `… .ayurveda_rasa` |
| `theory.headline_result_spoken` | one sentence written *from* the resolved values (video segment 9) |
| `eval.theory_summary` | one sentence written from the resolved values (slide 8) |
| `eval.theory_positive_count`, `eval.theory_n_tests` | count of tests passing the pre-registered threshold |
| `eval.n_tcm_nature`, `eval.n_tcm_channel`, `eval.n_tcm_flavor`, `eval.n_ayurveda_virya`, `eval.n_ayurveda_rasa` | `… .n` per test |
| `eval.quxiangbilei_rho`, `eval.quxiangbilei_p`, `eval.quxiangbilei_n` | `report.json → negative_controls.quxiangbilei` |
| `eval.null_model_drop` | `report.json → negative_controls.null_model.score_drop` |
| `eval.mean_candidate_novelty` | `report.json → drug_discovery.mean_novelty` |
| `eval.lipinski_pass_rate` | `report.json → drug_discovery.lipinski_pass_rate` |
| `eval.grounded_answer_rate`, `eval.citation_fidelity`, `eval.correct_refusal_rate`, `eval.over_refusal_rate`, `eval.policy_screen_recall`, `eval.policy_screen_precision` | `report.json → refusal_benchmark` |
| `ablation.no_theory`, `ablation.no_process`, `ablation.no_resolution`, `ablation.monolingual`, `ablation.weight_sweep` | `report.json → ablations` |
| `hypotheses.count` | `app/data/hypotheses.json → counts.total` |
| `candidates.count`, `candidates.resolved` | `artifacts/drug_candidates.json` |
| `limitations.theory_sentence` | written from the resolved theory values (video segment 10) |
| `app.bytes` | `wc -c app/static/*` |

---

## 3. Numbers that are already real and checkable now

These do not need any team input — they are properties of the repository, verifiable with the command shown.

| Claim | Value | Verify |
|---|---|---|
| Deck is exactly 10 slides, 3–5 bullets each, visual + speaker note on every slide | validated | `python submission/build_slides_json.py --final` |
| Workbench is stdlib-only, no build step, no network | true | `grep -n '^import\|^from' app/serve.py` |
| Workbench payload | `53 KB` JS + `33 KB` CSS + `12 KB` HTML | `wc -c app/static/*` |
| Workbench has six panels | candidates · hypotheses · graph · ask · corpus · methodology | `python app/serve.py` banner |
| Stdlib YAML reader matches PyYAML on the real registry | `39 rows × 9 fields, 0 mismatches` | `python - <<'PY'` diff as in `app/serve.py` docstring |
| Every SVG in `assets/` is well-formed XML | 5/5 | `python -c "import xml.etree.ElementTree as E,glob; [E.parse(f) for f in glob.glob('assets/*.svg')]"` |
| No fixture data can reach a slide accidentally | `app/serve.py --strict` refuses to start on fixtures | run it |
| Molecular weights in the candidate fixture are computed, not typed | e.g. `C32H45NO10 → 603.71` | `app/data/make_candidates.py → mw_from_formula` |

---

## 4. Numbers we deliberately do **not** claim

Recorded so that nobody reintroduces them later in good faith:

- **No loss curve** while `training/runs/*/metrics.json` is absent. The panel renders an empty state that says
  a loss curve cannot be approximated.
- **No SMILES** for a compound whose structure was not resolved. `null` and a `pending` badge, never a guess.
- **No aggregate score** (mean novelty, Lipinski pass rate) invented to fill a stat tile. `null` renders as `—`.
- **No benchmark number** in `eval/report.json` until the harness produces it; the Workbench shows a labelled
  fixture twin instead and chips every value.
- **No "permissive throughout"** claim about licences. The corpus contains CC BY-SA material (share-alike, not
  permissive) and one source was rejected for being NonCommercial.
- **No wet-lab validation** claim of any kind. Zero candidates have been tested.
