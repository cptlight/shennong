# Devpost form answers — SHENNONG 神农

Copy each section below into the corresponding Devpost field.

---

## Inspiration

Shennong, the mythical Chinese figure who tasted a hundred herbs to learn their effects, produced centuries of recorded observation. That record is unusable today for two reasons that have nothing to do with data volume.

**The names don't survive.** One plant is `甘草`, `감초`, `Glycyrrhiza uralensis` — and is also called Liquorice and Mulethi, names our lexicon does not yet hold. A 16th-century drug name and a modern gene target never meet, so a classical therapeutic use can't be connected to anything modern.

**Nobody ever checked the chemistry.** A preparation instruction is a chemical protocol written in a language no one validated against thermodynamics.

The binding constraint on discovering drugs from this corpus was never data. It was **translation**, and then **verification**. We built both.

---

## What it does

**Track 1 · Read a passage.** Paste any classical Chinese or ethnobotanical text. The system returns every drug it recognises with a **character span and confidence**, its modern botanical binomial, compound classes and gene targets; the therapeutic claims mapped onto a controlled vocabulary; and the preparation processes detected. Extraction is rule- and lexicon-based, so **it cannot hallucinate a span** — every item points at a character range in the text you pasted.

**Track 1 · Resolve a name.** Type any name from any era or language — `丹參`, `단삼`, `Salvia miltiorrhiza`, `Artemisia annua` — and follow it through the binomial to recorded uses, compound classes and gene targets in about a second on a CPU.

**Track 1 · At corpus scale.** We ran the same extractor over **273,334 formulas from 1,082 classical works**: **744,997 drug mentions**, **662 distinct drugs** (625 binomials), **714,079 drug–indication pairs** over 77,441 indications — in **52 seconds on a CPU**.

**Track 2 · Screen a target.** Type a disease target — `EGFR`, `COX2`, `HMGCR`. A tiered CPU-only screen over **23,176 plant compounds** ranks candidates by ECFP4 similarity to known ChEMBL actives, then filters on Lipinski ADMET, preparation physics and structural novelty. On HMGCR the top hit scores a Tanimoto of 1.000: the pipeline rediscovers a known active, which is our control that the method works.

**And the part we're proudest of.** We ran 203 recorded preparation claims through a mass-balance and heat-stability check. **78 are physically impossible** — the compound decomposes at the temperature the text prescribes. And **six of those had unanimous support from every text-based check** — the ancient record, the tradition and the theory all agreed. Physics still said no.

A system that only reads texts cannot know that. Ours is built to argue with its own sources.

---

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

**The benchmark was broken, and we found out late.** The published score was computed against a benchmark file that no longer existed in the repository — only 13 of 200 questions matched by text. Fixing the keys revealed something worse: the questions didn't match their own gold. *"What is 蕺菜 recorded to treat?"* carried the answer *"Recorded use: emetics (Indian medicine)."* The file had been generated from an older training set and never rebuilt. We regenerated it from current data, re-ran both arms from scratch, and documented the whole diagnosis in `docs/BENCHMARK.md`.

**A number we published was measuring an impossible task.** We had reported "drug-name → taxon resolution: 14.1 %" as our weakest link. Reading the evaluator showed it held out every test surface and then asked the resolver to guess it from character similarity — but `甘草` and `Licorice` share no characters, so no lexicon can pass. The real measurements: in-lexicon accuracy **1.000**, and **48.7 %** of plant-derived mentions resolve.

**And the reason the rest don't.** Investigating the unresolved names showed that **37.9 % of the classical pharmacopoeia isn't botanical at all** — 23.5 % animal (fur, shell, horn), 8.3 % mineral (cinnabar, alum, furnace earth), 4.1 % manufactured objects, 2.0 % human-derived. `縛豬繩` is a rope used to tie pigs. `溺白垽` is urine sediment. `汗衫` is an undershirt. None can resolve to a plant, and counting them as failures was the wrong denominator.

**Three separate GGUF format bugs** to make our sparse MoE loadable: zero-size shared-expert tensors crashed the quantiser, the tied LM head left `output.weight` missing, then the loader demanded full-width shared-expert tensors. All three were format problems; the trained weights never changed.

**A demo bug that would have been fatal.** The screening endpoint ignored its target parameter and silently returned COX2 results for every query. A judge typing EGFR would have seen Cyclooxygenase-2.

---

## Accomplishments that we're proud of

- **Two track demos that actually run live**, on CPU, with no dead ends and no rehearsed answers.
- **714,079 drug–indication pairs** extracted from 1,082 CC0 classical works in 52 seconds, with span-level provenance on every one.
- **78 of 203** recorded preparation claims refuted by first principles — and **6 refuted despite unanimous textual agreement**. That is the claim no retrieval pipeline can make: *ancient consensus is not evidence.*
- **A negative result we published rather than buried.** We trained a genuine 4-expert top-2 sparse MoE (1.44 B, expert weights actually trained, 999 MiB) — it scored **31.7 % vs 43.3 %**, worse than dense. It was released anyway, with the benchmark that shows it losing.
- **We found and published a defect in our own submission** two days before the deadline, rather than shipping a number we couldn't reproduce.

---

## What we learned

**Ancient consensus is not evidence.** Six hypotheses that every text-based check endorsed were refuted by physics. Building that check mattered more than building a bigger model.

**Most "AI for traditional medicine" projects stop at retrieval.** The hard part is the names, and then the verification.

**A benchmark you cannot reproduce from your own repository is worth nothing**, however good the number looks. Every headline figure in our README now traces to an artifact in the repository, and the two we could not reproduce were corrected rather than kept.

**The model is not the knowledge layer.** Asked *"what is Echinochloa colona used for in Indian medicine?"* our fine-tune answers with a *Chinese* classical use — it confuses traditions. That's why uses come from extraction and retrieval, and the model handles language and reasoning. Knowing where a 1.5 B model should and shouldn't be trusted is most of the engineering.

---

## What's next for SHENNONG 神农

**Close the Greek and Latin gap.** We hold 19 records' worth, so we don't claim to decode them. This is acquisition work — Perseus, PHI, Galen translations — not modelling work, and it's the single highest-value addition for Track 1.

**Grow the historical lexicon.** 48.7 % of plant materia medica resolves; the missing half are archaic names absent from every open source we tried. We tested character-similarity fallback as a fix: it recovered 2.9 % of mentions and was wrong about half the time, so we didn't ship it. This needs data, not cleverness.

**Physical validation.** Track 2 currently ends at a ranked, falsifiable shortlist. The next step is testing the top candidates — especially the ones whose mechanism the classical text actually predicted.

**Then the loop closes:** mine the corpus → link eras → check the physics → rank the candidates → test in a lab → feed the result back into the corpus.

---

*Everything above is open: the corpus with span-level provenance, the weights, the screening pipeline, the negative results, and the audits of our own errors. Permissive licences only.*

**Live:** https://tomscot-shennong.hf.space · **Code:** https://github.com/cptlight/shennong · **Weights:** https://huggingface.co/tomscot/shennong-1.5b-sft
