# Submission checklist — does SHENNONG meet the EthnoHack requirements?

A line-by-line audit against the hackathon's requirements, so nothing is claimed that cannot be pointed at.
Each row names the file or command that proves it. Verdicts: **✓ met · △ partial · ✗ missing**.

---

## 1 · "Build a working prototype … addressing one of the four tracks"

**Track 02 — Natural products and drug discovery** (declared in `submission/DEVPOST.md`; rationale in
`docs/TRACK.md`).

| requirement | where | verdict |
|---|---|---|
| working prototype | the judge demo — 10 tabs, live Ask + Hypothesise (`docs/demo/`, `app/serve.py --demo-root`) | **✓** locally · △ not yet hosted publicly |
| computational pipeline | two-pipeline: hypothesis generation → deterministic physical outcome (`shennong/experts/`, `shennong/physics/`) | **✓** |
| model | 19.3 M sparse MoE, open weights (`training/runs/`, `v0.1.0`/`v0.2.0` releases) | **✓** |
| analysis / digital tool | screening filter + extraction report + Workbench | **✓** |

It is, concretely, a **cheminformatics screening pipeline** (a listed category) with a knowledge-graph
component and an NLP front end.

## 2 · "Demonstrate how data, computation, AI or digital technologies generate useful insights"

| insight | evidence |
|---|---|
| a classical preparation can be refuted before the lab | **78 of 203** enrichment claims fail physics; 6 despite unanimous 5/5 panel (`artifacts/consensus_vs_arbiter.json`) |
| classical theory predicts chemistry, weakly but significantly | 歸經 7.48 % vs 3.80 % permutation, n = 2,059, **p = 0.008** (`eval/report.json`) |
| 2,000-year-old names map to modern binomials | 827/1,027 names mapped (`artifacts/extraction_report.json`) |

Verdict: **✓**

## 3 · "A clearly defined problem"

**The problem, in one sentence:**

> A traditional preparation is a chemical hypothesis in disguise — *"steam this, to enrich its terpenoids"* —
> and drug discovery has no way to test that hypothesis before spending laboratory time on it, so most
> ethnopharmacology work starts from a preparation that physics already says cannot work.

Verdict: **✓** (stated in `submission/DEVPOST.md` "The result"; now also here). The problem is *testable*:
any claim can be falsified with Clausius–Clapeyron, Arrhenius and mass conservation.

## 4 · "A computational or data-driven approach"

**✓** — retrieval over a 45.6 M-character corpus, a 12-expert MoE, a validated physics arbiter (Joback 4.5 %
mean error, QM 0.82 eV), and a pre-registered permutation test with Holm correction. Nothing here is a
prompt wrapped around an API.

## 5 · "A working prototype or demonstrable result"

| path | status |
|---|---|
| GitHub Pages — browse all results | **✓ live** (`https://cptlight.github.io/shennong/`) |
| local Workbench — query the model | **✓ live** (`make workbench` → `/demo/`) |
| Codespace — one click | **✓** (`.devcontainer/`) |
| Hugging Face Space — permanent public host | **△ ready, not deployed** (`space/`, needs `HF_TOKEN`) |

Verdict: **△ — the prototype works, but the interactive demo has no permanent public URL.** This is the one
genuine gap and it is a credential, not a code, gap: `export HF_TOKEN=… && ./scripts/deploy_space.sh
<you>/shennong` closes it.

## 6 · "Evidence supporting your approach"

**✓** — the physics is validated before it is trusted (Joback 6/6 within 10 %, QM MAE 0.82 eV), the theory
test is pre-registered with nulls disclosed, and every answer carries a `source_id:char_start-char_end`.
`scripts/audit_script_numbers.py` fails CI if any pitch number drifts from the artefacts.

## 7 · "Clear documentation"

**✓** — `README.md`, `docs/{REVIEW,TRACK,ARCHITECTURE,COMPUTE,CURRICULUM,DIAGNOSTICS,EVALUATION,NOVELTY,
DATA_SOURCES,EXPERTS}.md`, `CONTRIBUTING.md`, `DEMO.md`, `model/MODEL_CARD.md`, `corpus/DATA_CARD.md`.

## 8 · "Potential real-world relevance"

**✓** — quantified: **151 of 203** candidate preparations excluded at the record gate (search-space
reduction), **78** refuted by physics (experiments that do not get funded). The honest scope: this is a
*pre-experimental filter*, not a drug, and that framing is stated in the Devpost.

---

## Bottom line

| | |
|---|---|
| met fully | 6 of 8 requirements |
| partial | 1 (working prototype — works, not permanently hosted) |
| missing | 0 (Track 03/04 are not chosen tracks; the chosen track is 02 with 01 as depth) |

**The single action that closes the last gap:** deploy the Space (one command, needs a Hugging Face token).
Everything else is in the repository and points at an artefact.
