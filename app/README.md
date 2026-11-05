# app/ — the SHENNONG Workbench

A local-first research cockpit. Standard library only. No build step, no CDN, no network, no GPU.

```bash
python app/serve.py
```

It prints its own URL and a provenance banner, then serves:

```
  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
   SHENNONG 神农  ·  Workbench v0.2.0
  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
   candidates  FIXTURE  12 candidates          app/data/drug_candidates.json
   hypotheses  FIXTURE  13 ranked              app/data/hypotheses.json
   kg          FIXTURE  118 nodes / 94 edges   app/data/kg.json
   passages    FIXTURE  68 passages            app/data/passages.json
   corpus      REAL     38 kept / 1 excluded   corpus/registry/sources.yaml
   eval        FIXTURE  DEMO FIXTURE twin      app/data/eval_fixture.json
   metrics     FIXTURE  absent — no fabricated curve
   ⚠ 6/7 panels are showing DEMO FIXTURE data.

   → open  http://127.0.0.1:8765/
```

That banner is the most important output of the program. It tells you, before you look at anything, which
panels are showing **real pipeline artefacts** and which are showing the **demo fixture** shipped in
`app/data/` so the interface could be built before the pipeline existed.

```bash
python app/serve.py --strict   # refuse to start if any panel would show fixture data
python app/serve.py --port 9000 --open
python app/serve.py --help
```

`--strict` is the mode we record the video in. If it starts, every number on screen came out of the pipeline.

---

## The six panels

| Panel | What it is for | Reads |
|---|---|---|
| **Candidates** | The terminal artefact. Ranked drug candidates: classical line → theory vector → molecule (formula, computed MW, structure if resolved) → mechanism → development path → residual risk. Sortable, filterable, expandable. | `artifacts/drug_candidates.json`, fallback `app/data/` |
| **Hypotheses** | The working layer. Ranked, provenance-cited hypotheses across the six discovery classes, each with a falsification plan and an uncertainty note. Re-sortable by any single score axis. | `app/data/hypotheses.json` |
| **Knowledge graph** | 配 Pèi. Taxa, drug names, processes, compounds, targets, indications, formulae, sources. Click a node to filter the hypotheses. | `app/data/kg.json` |
| **Ask** | Grounded Q&A. Answers extractively with a citation per sentence, or refuses. Dual-use screen in front. | `shennong.rag` if importable, else local BM25 over `app/data/passages.json` |
| **Corpus** | 采 Cǎi. Tiers, licences, traditions, languages, the full source ledger. | `corpus/registry/sources.yaml` |
| **Methodology** | 采→制→配→使, the training loss curve, the **theory-predictivity experiment**, the null model, benchmarks, and the reproduction commands. | `eval/report.json`, `training/runs/*/metrics.json` |

Every panel carries a `LIVE DATA` or `DEMO FIXTURE` badge, individually. Panels never mix the two silently.

---

## Keyboard and accessibility

- `Tab` / `Shift+Tab` reaches everything; arrow keys move between tabs (`Home`/`End` jump to the ends).
- Every card's dossier is a native `<details>` element — no custom disclosure widget, so it works with
  screen readers and without JavaScript enhancements.
- The knowledge graph is decorative-but-interactive: **the search box above it is the accessible route to
  every node**, and results are a plain focusable list.
- Score bars carry `role="img"` with the numeric value in the label, so a bar is never the only encoding.
- `prefers-reduced-motion` disables all transitions.
- Contrast: body ink on parchment ≈ 15:1, cinnabar accent ≥ 5.3:1, verdigris ≥ 6.5:1.
- Payload: **98 KB total** (`app/static/` = 101,107 bytes across HTML, CSS, JS and one SVG favicon). No
  framework, no bundler, no webfont.

---

## How the server decides what is real

Each artefact is resolved **independently**, most-authoritative first, and the result is reported:

| Panel | Real source | Fallback |
|---|---|---|
| candidates | `artifacts/drug_candidates.json` | `app/data/drug_candidates.json` (fixture) |
| hypotheses | `app/data/hypotheses.json` | same file, fixture-flagged |
| graph | `app/data/kg.json` | same file, fixture-flagged |
| passages | `app/data/passages.json` | same file, fixture-flagged |
| corpus | `corpus/registry/sources.yaml` | `app/data/corpus.json` (fixture) |
| eval | `eval/report.json` | `app/data/eval_fixture.json` (fixture) |
| training | `training/runs/*/metrics.json` (newest) | **nothing** — the panel shows an empty state |

Two deliberate non-fallbacks:

- **No loss curve is ever invented.** If no `metrics.json` exists, the chart is empty and says why. A loss
  curve is the one artefact that cannot be approximated.
- **No aggregate score is filled in.** If `eval/report.json` reports `mean_novelty: null`, the panel shows
  `—` rather than a number derived from a different source.

### The stdlib YAML reader

`corpus/registry/sources.yaml` is read by a ~70-line hand-written parser (`parse_sources_yaml`) rather than
PyYAML, because the Workbench must run with no installs. It handles the documented registry shape — a
top-level list of flat mappings with scalar values — and returns `None` on anything it does not understand,
which triggers the fixture fallback rather than a crash.

It was diffed against `yaml.safe_load` on the real registry: **39 rows × 9 fields, 0 mismatches**. If the
registry schema grows nested structures, this parser must grow with it, and the diff should be re-run.

### Ask: grounding before generation

`/api/ask` tries `shennong.rag.answer(question, k=5)` if the package is importable. If it is not (or if it
raises), the server falls back to a local implementation and **says so in the response** (`mode:
"local-bm25-extractive"` with a `mode_note`). The fallback:

1. runs the safety screen first, and refuses before retrieving anything;
2. scores passages with BM25 — CJK is tokenised as unigrams **plus bigrams**, IAST diacritics are folded,
   so 繁體 queries work without a segmenter;
3. boosts the source whose title the question names, so "what does 雷公炮炙論 say" surfaces that text;
4. computes **IDF-weighted coverage** across the top passages, and refuses if it is below 0.22;
5. drops citations scoring below 35% of the top hit, so a passage sharing one common word cannot pad the
   answer;
6. quotes spans, joins them with `[n]` markers, and adds no claim the text does not contain.

Refusal reasons are enumerated and rendered distinctly: `no-match`, `low-coverage`, `medical`, `dual_use`,
`empty-index`, `empty-query`. A refusal is styled as a result, not an error.

---

## Adding a panel

1. `app/static/index.html`: add a tab button and a `<section class="panel" id="panel-<name>" role="tabpanel">`.
2. `app/static/app.js`: add the name to `TABS`, and a `load<Thing>()` that fetches and renders.
3. If it needs new data: add a route in `serve.py` and a loader that returns
   `dict(..., fixture: bool, source: str)`.
4. **Add its badge.** Every panel states its own provenance — a panel without one is a bug.
5. Add a row to the startup banner in `build_report()` so a judge sees it before the UI does.

Budget: keep the whole of `app/static` under ~150 KB. No framework, no build step, no CDN, no webfonts, no
network calls.

---

## Layout

```
app/
├── serve.py                 # the whole server: routes, loaders, BM25, safety screens, CLI
├── static/
│   ├── index.html           # six panels, all scaffolding; entities rendered into
│   ├── app.css              # one stylesheet, design tokens at the top
│   ├── app.js               # renderers, graph, ask, filters — no dependencies
│   └── favicon.svg          # the seal mark, redrawn to survive 16–32 px
└── data/
    ├── make_fixtures.py     # generates hypotheses.json, kg.json, passages.json, corpus.json
    ├── make_candidates.py   # generates drug_candidates.json, eval_fixture.json
    ├── hypotheses.json      # ← `cli shi --out app/data/hypotheses.json` overwrites this
    ├── kg.json              # ← `cli pei --out-kg app/data/kg.json`
    ├── passages.json        # ← `cli cai --out-passages app/data/passages.json`
    ├── drug_candidates.json # ← `cli shi --candidates --out …` / artifacts/
    ├── corpus.json          # fixture twin of the registry
    └── eval_fixture.json    # fixture twin of eval/report.json
```

`make app-data` populates the three pipeline files; `python app/data/make_fixtures.py` regenerates the
fixtures if you delete them. Both generators are deterministic (fixed seeds), so the demo is stable
across machines.

---

## Tests

The Workbench is exercised without a browser, which keeps the checks runnable in CI:

```bash
curl -s localhost:8765/api/health                     # {"ok": true, ...}
curl -s localhost:8765/api/meta | python -m json.tool # per-panel fixture/live status
curl -s -X POST localhost:8765/api/ask \
     -H 'Content-Type: application/json' \
     -d '{"question":"what did 雷公炮炙論 say about 附子?"}'   # grounded answer + citations
curl -s -X POST localhost:8765/api/ask \
     -H 'Content-Type: application/json' \
     -d '{"question":"how do I prepare aconite at home"}'    # → refused, dual_use
```

The server is written so that **no request can take it down**: every route is wrapped, a missing artefact
degrades to a labelled empty state, and a malformed request returns 400/404 rather than a traceback.

---

## Why local-first

Three reasons, in order of importance:

1. **The corpus is living heritage.** A research instrument over traditional knowledge should not require
   sending queries to someone else's cloud.
2. **A judge must be able to run it.** One command, no installs, no API key, no network at demo time.
3. **Honesty is easier to verify locally.** The provenance banner is generated from the files on disk. You
   can check it with `ls`.
