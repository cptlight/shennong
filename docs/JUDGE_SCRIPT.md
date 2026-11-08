# Judge run sheet — Shennong

**Live:** https://tomscot-shennong.hf.space · **Repo:** https://github.com/cptlight/shennong

Read this once before you present. It is ordered by what to do, not by what the system is.

---

## 0 · Five minutes before you start

The Space loads two GGUF models lazily. **The first request after idle takes ~60 s and HF's proxy may kill it.**
Never let a judge's first click be the first request.

```bash
# warm all four endpoints, in this order, from your terminal
curl -s -X POST https://tomscot-shennong.hf.space/api/query   -H 'Content-Type: application/json' -d '{"question":"What is 甘草 used for?"}' > /dev/null
curl -s -X POST https://tomscot-shennong.hf.space/api/extract -H 'Content-Type: application/json' -d '{"text":"甘草（炙）二两。治脾胃虛弱。"}' > /dev/null
curl -s -X POST https://tomscot-shennong.hf.space/api/screen  -H 'Content-Type: application/json' -d '{"target":"EGFR"}' > /dev/null
curl -s -X POST https://tomscot-shennong.hf.space/api/resolve -H 'Content-Type: application/json' -d '{"question":"丹參"}' > /dev/null
echo warm
```

Then **open three browser tabs in this order** so switching costs nothing:

1. `0 · The two problems` (landing)
2. `1b · Track 1 — read a passage`
3. `2 · Track 2 — screen a target`

**Have a recorded 90-second screen capture as backup.** If the venue wifi dies mid-demo, you play it and keep
talking. A judge who sees you handle a failure well scores you higher than one who sees a perfect demo.

---

## 1 · The 3-minute script

### 0:00 — Problem (15 s). No slides. Look at them.

> "Traditional medicine is the largest observational dataset humanity has — hundreds of thousands of recorded
> treatments, centuries of use. It has never been queryable, for two reasons: **the names don't survive the
> centuries**, and **nobody ever checked the claims against chemistry.** We built both."

### 0:15 — Track 1, live (40 s). Switch to tab **1b**. It has already run.

> "This is a formula from a classical Chinese text — 甘草, 白朮, 茯苓, boiled in water.
> The system reads it and returns every drug it recognises **with a character span and a confidence**, the modern
> botanical binomial, the compound classes, and the modern gene targets."

Point at the table, then at the claim row:

> "`脾胃虛弱` — a 16th-century way of saying poor digestion — mapped to **dyspepsia** in a controlled vocabulary.
> And note this: extraction is rule- and lexicon based, so it **cannot invent a span**. Every item points at a
> character range in the text I just pasted. You can check it by eye."

### 0:55 — Track 2, live (40 s). Switch to tab **2**. Type `EGFR`.

> "Same philosophy, different track. A plant compound library is cheap to compute and expensive to test. We screen
> 23,176 plant-derived compounds against a disease target on **a CPU, in seconds** — ECFP4 similarity to the known
> ChEMBL actives, then Lipinski ADMET, then preparation physics, then novelty.
> Every row cites the active it resembles and the plant it came from."

Point at `HMGCR` if you have time:

> "On HMGCR the top hit scores a Tanimoto of 1.000 — the pipeline rediscovers a known active. That's our control:
> the method works when the answer is known."

### 1:35 — The refutation (35 s). **This is your only real novelty. Slow down.**

> "Now the part I think matters more than either demo.
> We ran 203 recorded preparation claims through a mass-balance and heat-stability check. **78 are physically
> impossible** — the compound decomposes at the temperature the text prescribes.
> And here is the number that should worry you about every other system in this room:
> **six of those claims passed every textual gate** — the ancient record, the tradition, the theory. All agreed.
> Physics still said no."

Pause. Then:

> "A system that only reads texts cannot know that. Ours is built to argue with its own sources."

### 2:10 — Credibility, honestly (25 s). Tab **3**.

> "Underneath is a 1.5 B open model, 940 MB, CPU-only: **39.0 % against 25.5 %** for the base model on 200
> held-out questions.
> We also trained a real sparse mixture-of-experts — 4 experts, 1.44 B, expert weights actually trained, 999 MB.
> It scored **31.7 % versus 43.3 %**. Worse. It's released anyway, with the benchmark file.
> We publish what loses."

### 2:35 — Close (25 s).

> "Everything is open: the corpus with span-level provenance, the weights, the screening pipeline, the negative
> results. Permissive licences only — we excluded the easy non-commercial sources.
> The contribution isn't a bigger model. **It's a system that links eras and then checks itself.**"

**Stop talking.** Do not fill the silence.

---

## 2 · If they cut you to 60 seconds

> "Paste a 16th-century formula — you get its modern pharmacology: binomial, compound classes, gene targets,
> every claim traceable to a character span. Then we check the physics: **78 of 203 recorded preparation methods
> are chemically impossible, and 6 of them passed every text-based check.** The system's job is to argue with its
> own sources. Everything is open, 940 MB, runs on a CPU."

Then **open tab 1b and let it sit on screen**. Silence beats a rushed sentence.

---

## 3 · Q&A — the six they will ask

**"Isn't this just RAG over a scraped corpus?"**
> "Retrieval is one layer. The other four are: a curated name lexicon across 7 languages, a fingerprint/ChEMBL
> screen, a physics verifier, and a fine-tuned model that answers **with no retrieval at all** — tab 3 — scored at
> 39 % on 200 held-out questions."

**"How do I know the names are right?"**
> "Each resolution reports *how* it matched — historical lexicon, Indian synonym, or Wikidata language. Coverage is
> 4,716 binomials, 827 historical Chinese names, 10,393 vernacular names. It returns near matches, never a guess,
> and the coverage boundary is printed on the page."

**"Is your MoE better?"**
> "No. 31.7 against 43.3. It's released with the benchmark that shows it losing. The dense model ships."
> *(Say this immediately and without defensiveness — it buys you more credibility than any feature.)*

**"Where's the data from, and is it licensed?"**
> "CC0, public domain and permissive only. We **excluded** ctext.org and GRETIL even though they were the easiest
> to get, because their licences are non-commercial. Provenance is file-by-file in `docs/CORPUS_PROVENANCE.md`."

**"What's missing?"**
> "Two data gaps, not capability gaps. Greek and Latin classical texts — we hold 19 records' worth, so I won't
> claim we decode them. And the historical drug lexicon is 827 entries; famous drugs like 人參 are missing. Both
> are acquisition work, not modelling work."

**"Is this medically safe?"**
> "It refuses dosing, self-treatment and synthesis routes. It reports historical and pharmacological content and
> flags toxicity. It is a research tool, and it says so."

---

## 4 · Slides — five, and only five

1. **The two sentences** — the problem, no logo, no agenda
2. **`甘草 / Liquorice / Mulethi / 감초 → Glycyrrhiza uralensis → PTGS2`** — the name-drift chain as one image
3. **78 / 203** — huge. Subtitle: *"6 passed every textual check."*
4. **The two live demos** — two screenshots, two URLs
5. **The honest table** — 39.0 vs 25.5 · MoE 31.7 vs 43.3 (worse, released) · limits

No architecture diagram. No layers graphic. You will lose 40 seconds of a 3-minute pitch explaining a box you
could have just demonstrated.

---

## 5 · Three rules

1. **Demo, don't describe.** If you have 30 seconds left, open a tab instead of showing a bullet.
2. **Say the negative results before they ask.** It converts your weakest number into your strongest signal.
3. **Never claim Greek or Latin, and never claim the MoE is better.** Both are testable in one question, and being
   caught overclaiming costs more than the feature was ever worth.
