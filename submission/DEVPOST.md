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

**The benchmark was broken in three ways, and we only found out late.** Each fix uncovered a worse problem
underneath it. First, the results were scored against a benchmark file that no longer existed in the repository —
only **13 of 200** questions matched by text. Second, the keys for the "use" family were the *tradition label*
rather than the recorded use, so a model answering "emetics" — correct — scored zero; that is why both arms
reported `use: 0/113`. Third, and worst: after fixing the keys, `use` was *still* 0/63 for **both** models. The
questions didn't match their own gold — *"What is 蕺菜 recorded to treat?"* carried the answer *"Recorded use:
emetics (Indian medicine)."* The file had been generated from an older training set and never rebuilt. We
regenerated it from current data (`scripts/build_benchmark.py`), re-ran both arms from scratch, and wrote the whole
diagnosis up in `docs/BENCHMARK.md`. **The corrected number is lower than the one we had published — +12.0 points
instead of +13.5 — and that is the one we ship.**

**A number we had published was measuring an impossible task.** We reported "drug-name → taxon resolution: 14.1 %"
as our weakest link. Reading the evaluator showed it held out every test surface and then asked the resolver to
guess it from character similarity — but `甘草` and `Licorice` share no characters, so no lexicon can pass. The real
measurements are in-lexicon accuracy **1.000** and **48.7 %** coverage of plant-derived mentions. Investigating the
rest revealed that **37.9 % of the classical pharmacopoeia is not botanical at all** — 23.5 % animal, 8.3 % mineral,
4.1 % manufactured objects, 2.0 % human-derived. `縛豬繩` is a rope used to tie pigs. `溺白垽` is urine sediment.
Counting those as resolution failures was the wrong denominator.

**A sparse MoE that lost.** We upcycled Qwen2.5-0.5B into a genuine 4-expert top-2 MoE (1,435,499,392 parameters,
expert weights actually trained, 999 MiB) and found it scored **31.7 % against 43.3 %** for the dense model. We
released it anyway, with the benchmark that shows it losing.

**Three GGUF format bugs to make that MoE loadable at all.** Zero-size shared-expert tensors crashed the quantiser
(it died at tensor 12 of 410, leaving a 159 MB partial file); the tied LM head left `output.weight` missing, which
llama.cpp's qwen2moe loader requires; and the loader then demanded *full-width* shared-expert tensors where we had
written narrow ones. All three were format problems — the trained weights never changed.

**A demo bug that would have been fatal.** The screening endpoint ignored its target parameter and silently returned
COX2 results for every query. A judge typing EGFR would have seen Cyclooxygenase-2. Found by testing the demo the
way a judge would, not by running the tests.

**And a deployment failure that taught us the most.** Twelve minutes before recording the demo, the Space went to
`BUILD_ERROR`. The cause was not our code: Hugging Face's builder was timing out fetching the `llama-cpp-python`
wheel from a GitHub release. More instructive was the second bug it exposed — the Dockerfile downloaded the model
with `curl` *without* `-f`, so a failed download silently wrote a GitHub error page over the GGUF. The build
"succeeded", the container started, and the failure only appeared when someone asked the model a question. We now
vendor the wheel into the Space and pull weights from the Hugging Face CDN with `-f` and a size assertion, so a
truncated download fails the build instead of producing a model-shaped error page.

## Accomplishments that we're proud of

- **Two track demos that actually run live**, on CPU, with no dead ends and no rehearsed answers — resolve a name,
  read a passage, screen a target, ask the model.
- **714,079 drug–indication pairs** extracted from 273,334 formulas across 1,082 CC0 classical works, in **52 seconds
  on a CPU**, with span-level provenance on every one.
- **78 of 203 recorded preparation claims refuted by first principles** — and **6 refuted despite unanimous textual
  agreement**. That is the claim a retrieval pipeline structurally cannot make: *ancient consensus is not evidence.*
- **Span-level provenance throughout**: every claim carries `source_id` plus character offsets, so it is checkable
  character by character rather than trusted.
- **We audited our own submission and published the corrections** — a benchmark defect, an unresolvable metric, and
  a lower score than the one we had already published. The numbers in the README now trace to artifacts, and the
  two we could not reproduce were corrected rather than kept.
- **A negative result we published rather than buried**: a genuine sparse MoE that lost to the dense baseline, with
  the benchmark that shows it losing.

## What we learned

**Ancient consensus is not evidence.** Six hypotheses that every text-based check endorsed — the ancient record,
the tradition, and the five-expert panel — were refuted by mass balance and heat stability. Building that check
mattered more than building a bigger model.

**Most "AI for traditional medicine" projects stop at retrieval.** The hard part is the names, and then the
verification. The model is the easy layer.

**The model is not the knowledge layer.** Asked *"what is Echinochloa colona used for in Indian medicine?"* our
fine-tune answers with a *Chinese* classical use — it confuses traditions, and it scores 0/63 on that family. That
single measurement shaped the architecture: uses come from extraction and retrieval, and the model is kept to
language and reasoning. Knowing where a 1.5 B model must not be trusted was most of the engineering.

**A benchmark you cannot reproduce from your own repository is worth nothing**, however good the number looks. Ours
looked 13.5 points better than it was. Now every headline figure traces to a file.

## What's next for SHENNONG 神农

**Close the Greek and Latin gap.** We hold 19 records' worth, so we do not claim to decode them. This is an
acquisition task - Perseus, PHI, Galen translations - not a modelling task, and it is the single highest-value
addition for Track 1.

**Read the scanned record: OCR and vision.** Most of the classical canon survives as page images, not text - woodblock
editions, manuscript scans, vertical Chinese with interlinear glosses. We currently consume transcribed editions, so
the pipeline stops exactly where most of the material lives. The next step is a vision path: page segmentation plus
OCR tuned for vertical CJK and dense commentary, then feeding the recognised text through the same extractor. The hard
part is not character accuracy but **span provenance** - an OCR'd passage must still resolve to a page region and a
character range, or the auditability guarantee that everything else rests on disappears. Digitisation is also the only
way to reach the folklore and ethnobotanical archives that were never typeset at all.

**Add non-English sources.** The corpus skews heavily Chinese (35 % of characters are zh-Hant); Sanskrit is present but
effectively unmodelled (13.46 bits/byte, worse than a unigram baseline), and Arabic, Persian and Tibetan coverage is
thin. This is acquisition plus tokenizer work - the tokenizer was trained before the Devanagari corpus arrived, which
is why Sanskrit scores so poorly. The join side is already ahead of the text side: the resolver holds 10,393
vernacular names across seven languages, so the cross-era links exist before the editions do.

**Grow the historical lexicon.** 48.7 % of plant materia medica resolves; the missing half are archaic names absent
from every open source we tried. We tested character-similarity fallback as a coverage fix: it recovered 2.9 % of
mentions and was wrong about half the time, so we did not ship it. This needs data, not cleverness.

**Scale the model: more experts, more capable releases.** The 4-expert sparse MoE was an 1,800-step specialisation
experiment, not a capacity result - and it lost to the dense model. The architecture supports more: 8 experts at the
same top-2 routing roughly doubles FFN capacity at the same per-token compute, for about 2.1 GB at Q4. The missing
piece is not parameters but **router supervision** - teaching the router which expert owns which discipline - and
enough data per discipline for specialisation to be measurable. We would rather publish the next expert count with
the benchmark attached than ship a bigger file and call it wiser.

**Physical validation.** Track 2 currently ends at a ranked, falsifiable shortlist. The next step is testing the top
candidates, especially the ones whose mechanism the classical text predicted and the physics did not refute.

**Then the loop closes:** mine the corpus -> link eras -> check the physics -> rank the candidates -> test in a lab ->
feed the result back into the corpus.

---

*Everything above is open: the corpus with span-level provenance, the weights, the screening pipeline, the negative
results, and the audits of our own errors. Permissive licences only.*

**Live:** https://cptlight-shennong.hf.space · **Code:** https://github.com/cptlight/shennong · **Weights:** https://huggingface.co/cptlight/shennong-1.5b-sft
