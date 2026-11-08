# Shennong — the 3-minute pitch

**Live:** https://tomscot-shennong.hf.space · **Code:** https://github.com/cptlight/shennong · **Weights:** https://huggingface.co/tomscot/shennong-1.5b-sft

---

## The one-line problem

Traditional medicine is a large, old, observational dataset that nobody can query — because **the names do not
survive the centuries** and **the claims are never checked against physics**.

The same plant is `甘草`, `Glycyrrhiza uralensis`, `Liquorice`, `Mulethi`, `감초`, `kanzō`. A 16th-century
therapeutic claim and a modern gene target never meet, because nothing links `甘草` to `PTGS2`.

We built the link, and then we checked the claims.

---

## The two problems, and what we built for each

### Problem 1 · Track 1 — read a passage, then follow it to modern pharmacology

> **What runs live:** open tab **1b · Track 1 — read a passage**. Paste any classical or ethnobotanical text
> (three examples are preloaded). The system returns every drug it recognises with a **character span and
> confidence**, its modern binomial, compound classes and gene targets; the therapeutic claims mapped onto a
> controlled vocabulary; and the preparation processes it detected.

Verified on a four-drug formula from a Taiwan-edition text:

```
in  甘草（炙）二两、人參一兩、白朮二兩、茯苓二兩，以水六升，煮取三升。治脾胃虛弱，氣短乏力。
out drugs      甘草 → Glycyrrhiza uralensis     flavonoid, phenylpropanoid   ABCB1, ABCB11
               白朮 → Atractylodes macrocephala alkaloid, flavonoid          ACHE, ADORA1
               茯苓 → Wolfiporia cocos          terpenoid                    (none recorded)
    claim      脾胃虛弱 → dyspepsia          (traditional form folded to simplified)
    process    煮 (decoction)
```

Extraction is **rule- and lexicon-based** — it cannot hallucinate a span. Every item points at a character range
in the text the judge pasted, so the claim can be checked by eye.

### Problem 1b · Track 1 — names do not survive the centuries

> **What runs live:** open tab **1 · Track 1 — resolve a plant name**.
> Click `丹參`. In ~1 second you get `Salvia miltiorrhiza`, its names in Chinese/Japanese/German/French/Korean,
> 8 recorded therapeutic uses, 4 compound classes, and 10 modern gene targets.

This is the whole chain the track asks for, in one query:

```
historical name (any era, any language)
   -> modern binomial           827 historical Chinese · 4,154 Indian plants · 10,393 vernacular names
   -> recorded therapeutic uses  8 per plant, attributed to a tradition
   -> compound classes           terpenoid / flavonoid / alkaloid / phenylpropanoid
   -> modern gene targets        ABCB1, AKR1C3, ALDH1A1, ALOX15, ...
   -> pharmacology               class -> molecular target -> disease
```

Nothing is retrieved at inference. This is a curated corpus with **888,303 facts** and span locators
(`source_id:char_start-char_end`) back to **CC0/public-domain sources only**. Traditional Chinese is normalised to
simplified; an unknown name returns **near matches, never a guess**.

### Problem 2 · Track 2 — which plant compounds are worth testing, on a CPU

> **What runs live:** open tab **2 · Track 2 — screen a target**.
> Type `EGFR`. In seconds you get 8 ranked plant-derived candidates, each with a Tanimoto similarity to a known
> ChEMBL active, its plant, its chemotype, and three independent verdicts.

A tiered, CPU-only screen over **23,176 plant compounds**:

| layer | method | what it answers |
|---|---|---|
| 1 | knowledge graph, multi-hop | is there a recorded plant→compound→target path? |
| 2 | ECFP4 Morgan r=2, 2048-bit Tanimoto vs ChEMBL actives | does it look like a real ligand? |
| 3 | Lipinski ADMET + preparation physics + novelty | is it drug-like, stable under the recorded preparation, and new? |

Measured live: `EGFR` → CHEMBL3608, 58 actives, top Tanimoto 0.667 · `HMGCR` → CHEMBL402, 120 actives, top
Tanimoto **1.000** (rediscovers a known active — a control that the pipeline works).

---

## The part nobody else has: first-principles refutation

A model can generate *"boil this to extract the active compound"*. We **check the physics**.

`78 of 203` recorded preparation claims are physically impossible: the compound decomposes at the prescribed
temperature, or it is not soluble in the prescribed solvent. Every one is published as a refutation with its
reasoning. **This is the trust mechanism** — the system is built to say "no" to its own corpus.

---

## The model underneath

| | |
|---|---|
| base | Qwen2.5-1.5B, fine-tuned on 88,082 domain examples |
| result | **39.0 % vs 25.5 %** base on 200 held-out domain questions (**+13.5 pts**) |
| artifact | 940 MB Q4_K_M GGUF, **runs on CPU**, no GPU needed |
| also released | a 4-expert sparse MoE (1.44 B, 999 MB) — **31.7 % vs 43.3 %, worse. Published anyway.** |

That last row is the pitch: **we benchmarked our own architecture and published the loss.** A judge can check
`artifacts/moe_vs_dense.json` and reproduce it.

---

## The 3-minute script

**[0:00] The hook.** "Ayurvedic, Chinese and European pharmacopoeias hold thousands of years of clinical
observation. Almost none of it is machine-readable, and the names don't survive translation. Here is 甘草 —"

**[0:20] Track 1, live.** Click `丹參` → *"one second later: the modern binomial, its name in five languages,
eight recorded uses, and ten modern gene targets. That is a 16th-century drug name connected to modern
pharmacology — live, on a CPU, from a laptop."*

**[0:55] Track 2, live.** Type `EGFR` → *"23,176 plant compounds screened against the known actives for EGFR.
Every row cites its similarity, its plant, its chemotype, and whether it survives the preparation. No GPU. No
cluster. No wet lab."*

**[1:30] The verifier.** *"Now the part I think matters most. 78 of 203 ancient preparation claims fail a
mass-balance and heat-stability check — the compound decomposes at the temperature the text prescribes. We
publish those refutations. The system's job is to be wrong out loud."*

**[2:05] The model.** *"Underneath is a 1.5 B model, 940 MB, CPU-only: 39 % versus 25.5 % for the base model on
200 held-out questions. We also trained a sparse mixture-of-experts. It scored 31.7 % — worse. That's published
too, with the benchmark file."*

**[2:35] The close.** *"Everything is open: the corpus, the weights, the screening pipeline, the negative
results. Permissive licences only. The contribution isn't a bigger model — it's a system that links eras and
then checks itself."*

---

## Q&A — the questions a judge will ask, and honest answers

**"Is this just RAG over a scraped corpus?"**
No. Retrieval is one layer; the other four are: a curated name lexicon, a fingerprint/ChEMBL screen, a physics
verifier, and a fine-tuned model that answers without retrieval. The demo's tab 3 queries the model **directly**
— no retrieval at inference — and it is scored at 39.0 % on 200 held-out questions.

**"How do I know your names are right?"**
Each resolution reports *how* it matched (historical lexicon / Indian synonym / Wikidata language). Coverage is
4,716 binomials, 827 historical Chinese names, 10,393 vernacular names. It returns near matches, never a guess,
and the coverage boundary is stated on the page.

**"Is the MoE better? You said it's a MoE."**
No — it is worse: 31.7 % against 43.3 % for the dense model on the same 60 questions. It is released as a
trained artifact with the benchmark that shows it losing. The dense model ships.

**"Where does the training data come from and is it licensed?"**
CC0/public domain/permissive only. Major sources are cited in `docs/CORPUS_PROVENANCE.md`. We explicitly
**excluded** sources with non-commercial licences (ctext.org, GRETIL) even though they were the easiest to get.

**"What would you do with more time?"**
Two things, both data not compute: (1) acquire **Greek and Latin** classical texts — currently only 19 records'
worth, so the "decode Latin and Greek" claim is not yet backed; (2) grow the historical Chinese lexicon beyond
827 entries, since famous drugs such as 人参 are missing.

**"Is this safe?"**
No dosing, no self-treatment, no synthesis routes. The system answers historical and pharmacological questions
and flags toxicity. It is a research tool.

---

## Why this wins on the rubric

| criterion | weight | evidence |
|---|---|---|
| **Impact** | 40 | Solves a real accessibility problem: any era/language → modern pharmacology, in one CPU query; 78/203 pseudo-scientific claims refuted |
| **Technical** | 20 | 5-layer system, 888,303 span-located facts, ECFP4+ChEMBL screening, physics verifier, 1.5 B fine-tune at +13.5 pts |
| **Creativity** | 20 | Name-drift resolution across eras; first-principles refutation of its own corpus; publishes its own MoE loss |
| **Pitch** | 20 | Two live demos, no dead ends, every number reproducible from the repo |

**The differentiator is not the model size. It is that the system can be caught being wrong — and we show you
where it already was.**
