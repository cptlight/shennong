# Devpost form answers — SHENNONG 神农

Copy each section below into the corresponding Devpost field.

---

## Inspiration

Shennong, the mythical Chinese figure who tasted a hundred herbs to learn their effects, produced centuries of recorded observation. That record is unusable today for two reasons that have nothing to do with data volume.

**The names don't survive.** The same plant is `甘草`, `Glycyrrhiza uralensis`, `Liquorice`, `Mulethi`, `감초`. A 16th-century drug name and a modern gene target never meet, so a classical therapeutic use can't be connected to anything modern.

**Nobody ever checked the chemistry.** A preparation instruction — *"boil for three hours, wring out the juice"* — is a chemical protocol written in a language no one validated against thermodynamics.

The binding constraint on discovering drugs from this corpus was never data. It was **translation**, and then **verification**. We built both.

---

## What it does

**Track 1 · Read a passage.** Paste any classical Chinese or ethnobotanical text. The system returns every drug it recognises with a **character span and confidence**, its modern botanical binomial, compound classes and gene targets; the therapeutic claims mapped onto a controlled vocabulary; and the preparation processes detected. Extraction is rule- and lexicon-based, so **it cannot hallucinate a span** — every item points at a character range in the text you pasted.

**Track 1 · Resolve a name.** Type any name from any era or language — `丹參`, `단삼`, `Salvia miltiorrhiza`, `Artemisia annua` — and follow it through the binomial to recorded uses, compound classes and gene targets in about a second on a CPU.

**Track 1 · At corpus scale.** We ran the same extractor over **273,334 formulas from 1,082 classical works**: **744,997 drug mentions**, **662 distinct drugs** (625 binomials), **714,079 drug–indication pairs** over 77,441 indications — in **52 seconds on a CPU**.

**Track 2 · Screen a target.** Type a disease target — `EGFR`, `COX2`, `HMGCR`. A tiered CPU-only screen over **23,176 plant compounds** ranks candidates by ECFP4 similarity to known ChEMBL actives, then filters on Lipinski ADMET, preparation physics and structural novelty. On HMGCR the top hit scores a Tanimoto of 1.000: the pipeline rediscovers a known active, which is our control that the method works.

**And the part we're proudest of.** We ran 203 recorded preparation claims through a mass-balance and heat-stability check. **78 are physically impossible** — the compound decomposes at the temperature the text prescribes. And **six of those passed every textual gate**: the ancient record, the tradition, and the theory all agreed. Physics still said no.

A system that only reads texts cannot know that. Ours is built to argue with its own sources.

---

## How we built it

- **Corpus** — 29,042 records / 177.3 M characters: 106 sources plus 1,304 CC0 jicheng.tw classical works. **Permissive licences only** (CC0 / public domain / CC BY). We excluded ctext.org and GRETIL — the easiest sources to get — because their licences are non-commercial. Provenance is file-by-file in `docs/CORPUS_PROVENANCE.md`.
- **Extraction** — a character-trie longest-match scan producing span-faithful observations with verbatim quotes and confidences. Rule-based by choice: auditable, and incapable of inventing a span.
- **Knowledge layer** — 888,303 facts, each carrying `source_id` + `char_start`/`char_end`.
- **Model** — Qwen2.5-1.5B fine-tuned with LoRA (r=64) on 88,082 domain examples; merged, quantised to Q4_K_M: **940 MiB, runs on CPU**. **49.0 % vs 37.0 %** for the un-finetuned base on 200 held-out questions.
- **Screening** — RDKit ECFP4 (Morgan r=2, 2048-bit) Tanimoto against precomputed ChEMBL actives, plus Lipinski, preparation physics and novelty, fused into one falsifiable score.
- **Demo** — a Hugging Face Space with 14 tabs, 4 running live inference on CPU, plus a static result browser.

---

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

**A benchmark you cannot reproduce from your own repository is worth nothing**, however good the number looks. Every headline figure in our README is now generated from an artifact, not typed by hand.

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
