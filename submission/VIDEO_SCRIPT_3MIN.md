# SHENNONG — 3-minute video (Track 02)

**Hard limit 3:00.** Screen-recorded, 1080p, no music under voice-over. Every number spoken here is
reproducible from the repo; the file each one comes from is named in the right-hand column.

| | |
|---|---|
| **Target audience** | a pharmacologist and a computational judge, in that order |
| **What must land** | (1) the funnel, (2) the physics overruling consensus, (3) that we retracted our own finding |
| **What must not** | "AI for ancient medicine" framing; any claim we cannot show on screen |

---

## 0:00–0:20 — Cold open · the processing instruction

**On screen:** 本草綱目 page, one line highlighted in cinnabar: 「以水二升漬，絞取汁」.

> *"In 1972 a team in Beijing read one line from a fourth-century text — soak it in water and wring out the
> juice — and realised every previous attempt had boiled it, which destroys the compound. That was
> artemisinin. The information that won the Nobel Prize was a **processing instruction**, not a plant name,
> and nobody had translated it into chemistry."*

---

## 0:20–1:00 — The result · a filter, not a search engine

**On screen:** the funnel animates: 203 → 151 → 28 → 10 → 18.

> *"So we built the translation layer — and then the part that is missing from every other pipeline:
> something to **kill** what it produces. Two hundred and three processing instructions become chemical
> predictions. One hundred and fifty-one are discarded because the classical record does not attest them.
> Twenty-eight survive the record and the theory gates. Physics refutes ten of those. Eighteen are left, and
> those are the ones worth an assay."*

**Provenance:** `artifacts/tradition_first.json` — invariant across both the 7- and the 12-expert panel.

---

## 1:00–1:40 — The money shot · the arbiter overrules consensus

**On screen:** the 菖蒲 card. Five green 5/5 chips on the left; on the right a retention bar collapsing to
1.5 %.

> *"Here is the claim that matters. 'Steaming 菖蒲 should enrich its terpenoids.' Our five tradition experts
> scored it five out of five — well attested, theory-consistent, plausible process. Then the physics layer
> asked one question: how volatile is a monoterpene at a hundred degrees in steam? Ninety-eight point five
> per cent of it is gone. The claim is backwards, and the system said so with arithmetic — before anyone
> bought a reagent. Seventy-eight of our two hundred and three candidates die this way, six of them despite
> unanimous panel agreement."*

**On screen, small:** *Joback boiling points validated against known constants — mean 4.5 % error, 6/6
within 10 %.*
**Provenance:** `shennong/physics/{estimators,simulate}.py`, `artifacts/consensus_vs_arbiter.json`.

---

## 1:40–2:10 — The part most projects would hide · we were wrong

**On screen:** the AUC table, phytochemistry highlighted; then it moves 0.443 → 0.607 after the fix.

> *"We also measure our own experts. Each one is scored against the arbiter: does its confidence predict
> whether a claim actually survives physics? Our phytochemistry expert came out **below chance** — point four
> four. The tempting story was 'it senses data sparsity'. The real cause was worse: a hand-written bonus that
> rewarded plants with sparse chemistry, which are precisely the plants that fail physics. We removed the
> bonus, the score went to point six one, and we **retracted the finding** instead of featuring it. The tool
> that caught it is what we kept."*

**Provenance:** `shennong/experts/steering.py`, `artifacts/routing_steering.json`, `docs/DIAGNOSTICS.md` §2.

---

## 2:10–2:40 — Architecture · why it is auditable

**On screen:** three-layer diagram: data pipeline ⟶ 12 routeable experts ⟶ fixed first-principles core
(15 laws: 5 physics, 5 chemistry, 5 biology).

> *"Three layers that change at different speeds. The data pipeline takes new corpora — any licence-audited
> source, added with one command. Twelve expert modules, routed by content: two and a quarter experts per
> item on a mixed stream, so cost tracks the question. And underneath, a fixed core of physics, chemistry and
> biology that **can say no and never say yes**. Adding experts cannot move it — the funnel is identical with
> seven experts and with twelve."*

**On screen, small:** *Western literature is recorded as an observation and holds no decision weight — most of
the chemistry here is Western. The point is the order of evidence.*

---

## 2:40–3:00 — Honest gaps · and the ask

**On screen:** three lines, plainly:
`drug→taxon resolution 14.1 % · quantum: fragments only · 帰経 p=0.008, n=2,059`

> *"What we cannot yet do: drug-name resolution is fourteen per cent accurate, which limits every downstream
> number; the quantum layer arbitrates fragments, not natural products; and the entire corpus is Chinese,
> Sanskrit, Latin and English with nothing else. On the one thing we pre-registered and could test
> properly — whether the classical theory predicts chemistry — one axis survived at twice chance, p equals
> nought point nought nought eight, and three did not. That is in the repo with the nulls.
> We are looking for a lab to run the first three assays. Everything else is already open."*

---

## Production checklist

- [ ] Every number on screen at the moment it is spoken; no number spoken that is not visible.
- [ ] The 菖蒲 retention bar must animate **down**, not up — the whole point is the collapse.
- [ ] The 0.443 → 0.607 correction must be shown as a correction, with the word "retracted".
- [ ] No claim of drug discovery; the output is a **filter**, not a cure.
- [ ] End card: repo URL + release tag + licence.
