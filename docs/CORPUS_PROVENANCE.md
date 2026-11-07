# CORPUS PROVENANCE LOG

Every source in this repository is recorded here with its **licence**, whether it is **ingested** or
**excluded**, and why. The rule this project holds: *a corpus that cannot be redistributed cannot be shipped*.
A NonCommercial source mixed into a redistributable repo is the one indefensible choice.

**Licence decision: permissive only.** The repository ships under **Apache-2.0** (code + weights). Sources
under CC0, Public Domain Mark, or CC BY are ingested. CC BY-SA (share-alike) sources are kept in a separate
`derived-sa/` layer, never merged into the training index — a model trained on share-alike data inherits a
share-alike cloud over its weights, which would undermine the "open weights, Apache-2.0" claim.

---

## Ingested — permissive / public domain

| source | what | licence | status |
|---|---|---|---|
| **jicheng.tw** (中醫笈成) | **1,304 classical TCM works, 131.7 M characters**, punctuated, with author/dynasty/year/base-edition metadata | **CC0 1.0** | ✅ ingested — `corpus/processed/jicheng.jsonl.xz` |
| Our own corpus (106 sources) | Classical Chinese, Sanskrit, Latin, English medical + scientific texts | per-source (PD + CC BY-SA) | ✅ ingested — `corpus/processed/corpus.jsonl.gz` |
| **IMPPAT** | Indian medicinal plants → phytochemicals → gene targets → therapeutic uses (Ayurveda/Siddha/Unani) | CC BY | ✅ ingested — `corpus/processed/structured/imppat_*.csv` |
| **Wikidata** | multilingual plant names (de/fr/ko/zh/ja) via SPARQL | CC0 | ✅ ingested — `corpus/processed/structured/wikidata_names.csv` |
| **ChEMBL** | compound → target bioactivity (planned, for the screening layer) | CC BY-SA | ⏳ planned — `derived-sa/` only |

## Planned — recommended ingestion order

1. **Kanripo Archive.org mirror** (PD Mark 1.0) — broad classical base (四庫全書, 道藏, 大正藏) for a
   meaningful attestation gate beyond the medical canon. *Use the Archive.org PD mirror, not the GitHub
   CC BY-SA repos*, so it stays permissive. Kept in a separate index.
2. **Tao-Shanghan-Corpus** (Zenodo, CC0 editorial / CC BY 4.0 structured) — 681 clause records, 2,958 aligned
   commentaries, 616 variants, 4,255 graph nodes. Clause-aligned and provenance-aware: the **validation set
   for the span gate**, and the structural template for the larger ingest.
3. **Bencao Dian** — classical quotation spans only (public domain); the site's translations and graph are
   CC BY-SA and are **not** ingested.

## Excluded — and why

| source | licence | decision |
|---|---|---|
| **ctext.org** | CC BY-**NC**-SA | **excluded** — NonCommercial, incompatible with a redistributable corpus. Recorded as a research reference only. |
| **GRETIL** | CC BY-**NC**-SA | **excluded** — same NonCommercial problem (already rejected in `corpus/registry/sources.yaml`). |
| HuggingFace `classical-tcm-canon`, `tcm-materia-medica` | commercial | **excluded** — not corpus sources. |
| TCM-Pretrain-Data-ShizhenGPT | unclear / web-scraped | **excluded** — unverifiable provenance is indefensible in a submission. |
| **SARIT** (Sanskrit) | CC BY-SA | **separate layer** — kept in `derived-sa/` only, to make the ṣaḍrasa/vīrya axis linkable without contaminating the permissive index. |
| Kommission E (German), French pharmacopoeias | not openly redistributable | **excluded** — no open bulk data; German/French coverage comes via Wikidata names instead. |
| OASIS / KIOM (Korean) | registration-gated | **excluded** for bulk use; Korean names come via Wikidata. |

---

## What jicheng changes

- The corpus goes from **106 sources / 45.6 M characters** to **1,304 works / 131.7 M characters** on the
  classical-medicine side alone — a **~3× increase** with the cleanest possible licence.
- The **attestation gate** becomes meaningful: "not attested" no longer means "not in our modest corpus" but
  "not attested across the largest CC0 medical corpus available."
- The **operator lexicon** (827 entries) can be re-extracted against `炮制` sections across 1,304 works,
  with every new entry carrying `source: jicheng.tw` and `license: CC0`.

Reproduce: `python scripts/ingest_jicheng.py --jc /tmp/jc_data` (after `git clone --depth 1
https://gitlab.com/jicheng/jc.data.git /tmp/jc_data`).
