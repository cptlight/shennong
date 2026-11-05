# CONTRIBUTING

SHENNONG is a research instrument over living traditional heritage, and the contribution rules reflect that.
The short version: **stay in your write scope, never fabricate a number, and never weaken a control.**

---

## 1. Set up

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
make setup            # verifies the environment, prints the source registry status
```

CPU-only is a supported and tested configuration — it is the configuration this project was built and
measured on. No GPU is required, and no GPU-only code path is allowed to become load-bearing.

```bash
make test             # pytest
make eval             # benchmarks + theory tests → eval/report.json
make workbench        # the Workbench at http://127.0.0.1:8765/
```

---

## 2. The five rules

### Rule 1 — Never fabricate a number

No invented citations, no estimated metrics presented as measurements, no illustrative loss curves.

- A number that comes from a recipe rather than a run must be labelled a **recipe number in the same
  sentence**.
- A placeholder is written with a double bracket, the word PENDING, a colon and the name of the metric, and is
  tracked. `submission/check_pending.py` fails if one
  survives into a shipped artefact.
- If a value cannot be computed, leave it `null` and render it as pending. This applies with special force to
  molecular structures: **never invent a SMILES string** to make a table look complete.

### Rule 2 — Never weaken a control to improve a headline

The negative controls (`docs/EVALUATION.md` §3) exist to make specific claims falsifiable. A change that
improves a headline metric while degrading a control is rejected without discussion. The learning gate
(`docs/CONTINUOUS_LEARNING.md` §2) enforces this mechanically; do not try to route around it.

### Rule 3 — Every source carries its provenance, or it is not used

Required for any new corpus entry:

```
title · author/date · URL · licence · licence_evidence (a URL) · tier · tradition · lang
```

- Licence unclear → `status: unverified` → **excluded from training**, cited only.
- NonCommercial licences are incompatible with an Apache-2.0 release. Do not add one; if you believe a
  special case exists, raise it in an issue first.
- `status: withdrawn` must be honoured by the next corpus build. Add the mechanism, not just the field.

### Rule 4 — Safety constraints are not negotiable

- No dosing, no self-treatment guidance, no preparation instructions, no synthesis routes for toxins or
  pathogens — in code, docs, tests, fixtures, commit messages or slide decks.
- Toxic materia medica may be *analysed*; the safety annotation must render on every view of it and must not be
  collapsible or filterable.
- No change may reduce the coverage of the dual-use screen without a corresponding measured justification in
  `docs/EVALUATION.md` §7.

### Rule 5 — Stay in your write scope

| Owner | Writes | Never writes |
|---|---|---|
| `lead` | `PROJECT_BRIEF.md`, `README.md`, `pyproject.toml`, `Makefile`, `LICENSE`, `docs/FIRST_PRINCIPLES.md`, `docs/ARCHITECTURE.md`, `scripts/`, `.gitignore`, **all git operations** | everything else |
| `data-curator` | `corpus/`, `data/` | `model/`, `shennong/`, `docs/` |
| `model-forge` | `tokenizer/`, `model/`, `training/`, `artifacts/` | `corpus/`, `shennong/`, `docs/` |
| `discovery-engine` | `shennong/`, `tests/`, `eval/` | `corpus/`, `model/`, `docs/` |
| `story-builder` | `docs/` (not FIRST_PRINCIPLES/ARCHITECTURE), `submission/`, `app/`, `assets/` | `corpus/`, `model/`, `shennong/` |

**Nobody but the Lead runs `git add`, `git commit` or `git push`.** If you need a change outside your scope,
message the owner with the exact file and change — do not edit it yourself.

---

## 3. Adding a corpus source

1. Verify the licence **and save the evidence URL** — the page that states the licence, not the text itself.
2. Add a registry entry to `corpus/registry/sources.yaml` with every required field.
3. Run the fetcher; record `sha256` of the downloaded file as the registry entry's `sha256`.
4. Run the cleaner; it enforces minimum length, NFC normalisation and script checks.
5. Confirm the dedupe report did not remove most of your source (a 90% dedupe rate means you added a
   parallel edition, not new material — that is a finding, not an error, but say so).
6. Re-run `make eval` and report the delta in `docs/EVALUATION.md` if it moves a headline number.

A source with no licence evidence is not a source. It is a liability with a URL.

---

## 4. Adding or changing an extractor

Extractors change every downstream number, so they carry the heaviest review burden.

- Add a gold-set example for every rule you change. If the gold set is small, grow it first.
- Report **extraction agreement across editions** — a rule that improves agreement on one edition while
  destroying it on another is a regression.
- Any change to the property-vector encoding (nature ordinals, flavour multi-hot, channel assignment) is a
  **breaking change**: it invalidates every published theory statistic. Bump the version, re-run the full
  evaluation, and expect to argue for it.

---

## 5. Adding a discovery class

A new class needs all five of these before it can merge:

1. a **module** in `shennong/discover/`, with a documented failure mode;
2. a **falsification-test template** — what would count as refuting a hypothesis in this class;
3. at least **one worked example** through the whole pipeline, ending in a dossier a specialist could read;
4. a **line in `docs/METHODOLOGY.md`** saying what the class is for and how it can go wrong;
5. a **row in the evaluation table** (`docs/EVALUATION.md`), even if the row is "not yet measurable".

Classes without a failure mode are not discovery classes; they are aspiration.

---

## 6. Code style

- Python 3.12, type hints on public functions, `from __future__ import annotations`.
- Prefer the standard library. Every dependency must justify itself on CPU cost and reproducibility; the
  Workbench in particular is **stdlib-only by contract** (a judge must be able to run it with no installs).
- No network calls at import time. No network calls in the Workbench. Ever.
- Tests: `pytest`, deterministic seeds, no network. A test that can flake is a broken test.
- Commit messages: imperative subject, then *why* in the body. Reference the artefact a change touches.

---

## 7. Changing the Workbench

- It must keep working with **zero artefacts present** — every panel degrades to a labelled empty state or a
  `DEMO FIXTURE`, never to a stack trace.
- It must **never silently mix** real and fixture data. Each panel states its own provenance; if you add a
  panel, add its badge.
- Keep it small. The budget is roughly ~100 KB total of unbuilt HTML/CSS/JS. No framework, no build step, no
  CDN, no webfonts.
- Accessibility is a requirement, not a polish pass: keyboard reachable, visible focus, native `<details>` for
  disclosure, `prefers-reduced-motion` respected, and a non-visual route to anything the graph can do.
- Run `python app/serve.py --strict` before you ship anything interface-related; if it refuses to start, you
  are shipping fixtures.

---

## 8. Pull request checklist

Copy this into the PR description.

```markdown
- [ ] Stays inside my write scope (or the owner approved the cross-scope change)
- [ ] No invented numbers; anything pending is a double-bracketed PENDING marker and listed in the PR body
- [ ] No control weakened (null model, 取象比類, refusal benchmarks) — deltas shown if touched
- [ ] Any new source has licence + licence_evidence URL, or is marked unverified
- [ ] Safety: no dosing / preparation / synthesis content anywhere in the diff
- [ ] `make test` green
- [ ] `make eval` run; deltas reported, including any regression
- [ ] `python submission/build_slides_json.py --final` green if submission/ touched
- [ ] `python submission/check_pending.py` green
- [ ] Docs updated: METHODOLOGY / EVALUATION / SAFETY as applicable
```

---

## 9. Reporting a problem with the science

If you think a test is wrong, a null is overstated, a control is miscalibrated, or a candidate is not novel:
**open an issue with the specific artefact.** Documentation drift and overstated claims are treated as bugs,
not as opinions.

The most valuable contribution to this project is a well-argued negative result. Please bring one.
