# `data/` — the SHENNONG corpus pipeline

Everything that turns public-domain / openly-licensed sources into the artefacts under
`corpus/`. Every fetcher is **idempotent, resumable and rate-limited**; every writer is a pure
function of its inputs; all API responses are cached under `data/.cache/` (git-ignored).

```
data/
  _net.py             shared HTTP layer: retry, backoff, per-host throttle, disk cache
  manifest.py         the CURATED source manifest (id, title, author, year, tradition, lang,
                      tier, licence, licence_evidence, fetch target). This is the source of truth.
  discover.py         re-run candidate discovery (Gutenberg + archive.org) -> registry/candidates.json
  wikisource.py       MediaWiki client: recursive subpage walk + plaintext extract
  fetch_wikisource.py classical Chinese (zh.wikisource) + Sanskrit (sa.wikisource)
  fetch_gutenberg.py  Project Gutenberg (Tier 1 English foundational science)
  fetch_archive.py    Internet Archive `_djvu.txt` OCR (PD English/Latin editions)
  clean.py            raw -> training text (boilerplate, OCR noise, script gate, NFC, reflow)
  parse_bencao.py     本草 entry parser + property extraction (四氣五味, 歸經, 毒性, 三品)
  rules.py            classical rule tables: 十八反, 十九畏, 七情, 炮制 terms, vocabs
  script_fold.py      繁↔简 fold table for drug-name matching (大黄/大黃)
  build_corpus.py     cleaned -> corpus/processed/corpus.jsonl + stats.json (chunk + 13-gram dedupe)
  build_registry.py   -> corpus/registry/sources.yaml (chars + sha256 read off disk)
  build_structured.py -> properties/uses/formulas/processing/incompatibilities/relations_seven/
                         ayurveda_properties CSVs
  build_lexicon.py    drug name -> modern binomial (Wikidata P225) + plants.csv
  build_compounds.py  compound -> SMILES (Wikidata P233 / PubChem) + found-in taxon (P703)
  build_docs.py       -> corpus/DATA_CARD.md + the licence table in LICENSE_AUDIT.md
  build_join_report.py-> corpus/registry/join_report.json
  make_corpus.py      single entry point (see below)
```

## One command

```bash
python -m data.make_corpus            # full rebuild (network required, ~1–2 h)
python -m data.make_corpus --offline  # rebuild from corpus/raw/, no network
python -m data.make_corpus --stage fetch
python -m data.make_corpus --stage build --stage docs
```

Stages, in order: `fetch → clean → build → registry → docs → structured → lexicon → report`.
A failed stage does not abort the run; it is reported at the end so partial artefacts still
exist for downstream teams.

## Individual stages

```bash
python -m data.fetch_wikisource --lang zh     # ~50 Chinese works
python -m data.fetch_wikisource --lang sa     # Sanskrit Ayurveda (Devanagari)
python -m data.fetch_gutenberg                # 19 English foundational texts
python -m data.fetch_archive                  # 11 PD scanned editions
python -m data.clean                          # + --report for a per-source quality table
python -m data.build_corpus
python -m data.build_registry
python -m data.build_docs
python -m data.build_structured               # + --only properties --only uses ...
python -m data.build_lexicon                  # + --limit N for a quick test
python -m data.build_compounds
python -m data.build_join_report
python scripts/verify_contracts.py            # the inter-team contract gate
```

## Judgement calls a reviewer should know about

- **GRETIL is excluded.** Its TEI headers license the text **CC BY-NC-SA 4.0**; the
  NonCommercial clause would contaminate a public corpus. Sanskrit is sourced from
  `sa.wikisource.org` (CC BY-SA 4.0) instead. See `corpus/LICENSE_AUDIT.md`.
- **Wikisource transcriptions are CC BY-SA 4.0** even where the underlying work is PD-old, so
  the derived corpus carries a ShareAlike obligation. Stated in the DATA_CARD.
- **Properties are extracted, never inferred.** A drug only appears in `properties.csv` if the
  parsed text gives a 氣味 (or equivalent) field. 歸經 channels are only taken from explicit
  `歸…經` / `入…經` statements.
- **Unresolved drug names are left null, not guessed.** `join_status` records the decision;
  `corpus/registry/join_report.json` reports the counts.
- **十八反 / 十九畏 are shipped faithfully, not padded.** 16 canonical 相反 pairs (19 drugs
  named) + 11 相畏 relations. The classical names count drugs in the verse, not pairs.
