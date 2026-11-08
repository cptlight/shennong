# Devpost submission text

Copy the sections below into the Devpost form. Adjust the demo URLs if the Space is renamed.

---

## Project name

**Shennong — a knowledge system that argues with its own sources**

## Elevator pitch (200 chars)

> Traditional medicine is the largest observational dataset humanity has and it has never been queryable. We built
> the link from ancient names to modern pharmacology — and the check that refutes 78 of its own claims.

## Inspiration

Shennong is the mythical Chinese figure who tasted a hundred herbs to learn their effects. That method —
empirical, patient, self-experimental — produced centuries of recorded observation. But the record is unusable to
modern science for two reasons that have nothing to do with data volume:

1. **The names do not survive.** One plant is `甘草`, `감초`, `Glycyrrhiza uralensis` — and is also called
   Liquorice and Mulethi, names our lexicon does not yet hold.
   A 16th-century drug name and a modern gene target never meet.
2. **Nobody ever checked.** A preparation instruction is a chemistry protocol written in a language no one
   validated against thermodynamics.

The binding constraint on discovering drugs from this corpus was never data. It was **translation** — and then
**verification**.

## What it does

**Track 1 · Read a passage.** Paste any classical Chinese or ethnobotanical text. The system returns every drug
it recognises with a character span and a confidence, its modern botanical binomial, its compound classes and its
modern gene targets; the therapeutic claims mapped onto a controlled vocabulary; and the preparation processes it
detected. Extraction is rule- and lexicon based, so it **cannot hallucinate a span** — every item points at a
character range in the text you pasted.

**Track 1 · At corpus scale.** The same extractor was run over **273,334 formulas from 1,082 classical
works** — **744,997 drug mentions**, **714,079 drug–indication pairs** over 77,441 indications, in **52 seconds on a CPU**.
167,679 formulas (61.3%) contain a recognised drug. That is the difference between a demo and a corpus.

**Track 1 · Resolve a name.** Type any name from any era or language — `丹參`, `단삼`, `Salvia miltiorrhiza`,
`Artemisia annua` — and follow it through the binomial to eight recorded uses, four compound classes and ten gene
targets, in about a second on a CPU. Coverage: 827 historical Chinese names, 2,175 Indian plants with synonyms
(4,109 with recorded uses), 10,393 vernacular names across seven languages.

**Track 2 · Screen a target.** Type a disease target — `EGFR`, `COX2`, `HMGCR`. A tiered CPU-only screen over
23,176 plant compounds ranks candidates by ECFP4 similarity to known ChEMBL actives, then filters on Lipinski
ADMET, preparation physics and structural novelty. On HMGCR the top hit scores a Tanimoto of 1.000: the pipeline
rediscovers a known active, which is our control that the method works.

**The part we are proudest of.** We ran 203 recorded preparation claims through a mass-balance and heat-stability
check. **78 are physically impossible** — the compound decomposes at the temperature the text prescribes.
And **six of those passed every textual gate**: the ancient record, the tradition and the theory all agreed.
Physics still said no.

A system that only reads texts cannot know that. Ours is built to argue with its own sources.

## How we built it

**The design thesis: do not ask a 1.5 B model to do chemistry.** We split the system into five layers, each doing the
thing it is measurably good at, and each output checkable by the layer above it.

**1 · Corpus — the licence gate comes first, in code.**
106 sources plus 1,304 CC0 works from jicheng.tw: **29,042 records, 177.3 M characters**. `scripts/ingest.py`
refuses any document without a licence and a URL proving it, so an unusable source cannot enter the pipeline by
accident. Permissive only — CC0, public domain, CC BY. We **excluded ctext.org and GRETIL**, the two easiest corpora
to obtain, because both are non-commercial: shipping them would have made the "open weights" claim false. Every
source, including the rejected ones and why, is recorded in `docs/CORPUS_PROVENANCE.md`.

**2 · Extraction — rule-based on purpose, not for lack of a model.**
A character trie does longest-match scanning over the drug lexicon and emits observations carrying `char_start`,
`char_end`, the verbatim quote and a confidence. We could have asked the LLM to extract. We didn't, because a span
you cannot point at is not evidence: an LLM extractor can produce a fluent sentence citing a passage that does not
say it. The trie **cannot invent a span**, and every claim downstream inherits that guarantee. It ran over
**273,334 formulas in 52 seconds**, producing 744,997 drug mentions and 714,079 drug–indication pairs.

**3 · Knowledge layer — provenance as a schema, not a promise.**
**888,303 facts**, each carrying `source_id` plus `char_start`/`char_end`. Not "the corpus says X" — *this*
character range of *this* edition says X. That is what makes the graph auditable instead of merely authoritative.

**4 · The arbiter — the one layer that is not text.**
This is the part that could not live inside the model. `shennong/physics/` models what a preparation actually does to
a molecule: Clausius–Clapeyron volatilisation, Arrhenius hydrolysis with bond-class activation energies, thermal
degradation above the boiling point. It was **validated before it was trusted** — Joback group-contribution boiling
points against known constants, mean error **4.5 %**, 6/6 within 10 %. It returns a retention fraction with a
sensitivity range and overrules the text panel when they disagree: **78 of 203** recorded preparation claims fail it,
including 6 the panel had scored unanimously.

**5 · The model — language and reasoning, deliberately not knowledge.**
Qwen2.5-1.5B, LoRA r=64 on 88,082 domain examples, merged and quantised to Q4_K_M: **940 MiB, runs on CPU**.
On 200 held-out questions it scores **49.0 % against 37.0 %** for its un-finetuned base (**+12.0 pts**). We also
measured what it is *bad* at: asked "what is this Indian plant used for?" it answers with a Chinese classical use
(0/63 on the use family). So uses are served by extraction and retrieval; the model handles language and reasoning.
Knowing where the model must not be trusted was most of the engineering.

**6 · Screening — cheminformatics where it can be exact.**
**23,176 plant compounds** with real SMILES, fingerprinted with ECFP4 (Morgan r=2, 2048-bit) and ranked by Tanimoto
similarity against precomputed ChEMBL actives, then filtered by Lipinski ADMET, preparation physics and structural
novelty, fused into one falsifiable score. On HMGCR the top hit scores **Tanimoto 1.000** — the pipeline rediscovers
a known active, which is our control that the method works.

**7 · Deployment — CPU-only end to end.**
A Hugging Face Space (Docker, 2 vCPU) runs llama.cpp over the Q4 GGUF with no GPU and no torch. **14 tabs, 4 running
live inference.** The build pulls weights from the Hugging Face CDN with `-f` and a size assertion, after an earlier
build silently wrote a GitHub error page over the model file — a failure that only surfaced at query time.

**Why this shape.** Every component was chosen because it is *verifiable* at what it does: spans you can point at,
chemistry you can recompute, a benchmark you can re-run. The model is the one part we cannot fully audit, so it is
kept to the job it does well — phrasing and reasoning over evidence that the other layers supply.

## Challenges we ran into

- **The benchmark was broken, and we found out late.** The published score was computed against a benchmark file
  that no longer existed in the repository — only 13 of 200 questions matched by text. Worse, the keys for the
  113 "use" questions were the *tradition label* rather than the recorded use, so a correct answer like
  "emetics" scored zero. We rebuilt the scorer from scratch (`scripts/benchmark_v2.py`), documented the defect
  (`docs/BENCHMARK.md`) and re-ran both arms. Publishing the audit is more valuable than the number it produced.
- **A sparse MoE that lost.** We upcycled Qwen2.5-0.5B into a genuine 4-expert top-2 MoE (1.44 B, expert weights
  actually trained, 999 MiB), then found it scored **below** the dense model. We released it anyway, with the
  benchmark that shows it losing.
- **Three separate GGUF format bugs** to make the MoE loadable at all: zero-size shared-expert tensors crashed
  the quantiser, the tied LM head left `output.weight` missing, and the loader then demanded full-width
  shared-expert tensors. All three were format problems; the trained weights never changed.
- **A demo bug that would have been fatal.** The screening endpoint ignored its target parameter and silently
  returned COX2 results for every query. A judge typing EGFR would have seen Cyclooxygenase-2.

## Accomplishments we're proud of

- Two track demos that **actually run live**, on CPU, with no dead ends and no rehearsed answers.
- **78 of 203** recorded preparation claims refuted by first principles — and **6 refuted despite unanimous
  textual agreement**.
- Span-level provenance throughout: every claim is checkable character by character.
- A negative result we published rather than buried.

## What we learned

- Ancient consensus is not evidence. Six hypotheses that every text-based check endorsed were refuted by physics.
  Building that check mattered more than building a bigger model.
- Most "AI for traditional medicine" projects stop at retrieval. The hard part is the **names**, and then the
  **verification**.
- A benchmark you cannot reproduce from your own repository is worth nothing, however good the number looks.

## What's next

- **Greek and Latin classical texts.** We hold 19 records' worth, so we do not claim to decode them. This is an
  acquisition task, not a modelling task, and it is the single highest-value addition for Track 1.
- **Grow the historical Chinese drug lexicon** beyond 827 entries — famous drugs such as 人參 are missing.
- **Physical validation** of the top screening candidates.

## Built with

`python` · `pytorch` · `transformers` · `peft` · `llama.cpp` · `gguf` · `rdkit` · `numpy` · `scikit-learn` ·
`opencc` · `huggingface-spaces` · `docker` · `chembl` · `imppat` · `wikidata` · `jicheng.tw (CC0)` ·
`qwen2.5-1.5b` · `qlora`

## Links

- **Live demo**: https://tomscot-shennong.hf.space
- **Code**: https://github.com/cptlight/shennong
- **Weights**: https://huggingface.co/tomscot/shennong-1.5b-sft
- **Judge run sheet**: `docs/JUDGE_SCRIPT.md`
- **Benchmark integrity note**: `docs/BENCHMARK.md`

## One honest sentence for the judges

> We are not claiming a bigger model. We are claiming a system that links eras, checks itself against physics, and
> publishes where it was wrong — including a benchmark defect we found in our own submission two days before the
> deadline.
