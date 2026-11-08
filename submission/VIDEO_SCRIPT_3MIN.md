# SHENNONG — 3-minute video (Track 02)

**Hard limit 3:00.** Screen-recorded, 1080p, no music under voice-over. Every number spoken is reproducible
from the repo; the provenance column names the file it comes from.

**Order mirrors the deck:** artefact-level findings first (slides 1–4), then how it works (5–9), then close.

| # | Time | Beat | Provenance |
|---|---|---|---|
| 1 | 0:00–0:20 | Cold open — the processing instruction | 肘後備急方 |
| 2 | 0:20–0:55 | **The finding that survived** — 歸經 | `eval/report.json` |
| 3 | 0:55–1:30 | **The arbiter overrules consensus** — 菖蒲 + the funnel | `artifacts/{tradition_first,consensus_vs_arbiter}.json` |
| 4 | 1:30–2:00 | **We caught a bug in ourselves** — 0.443 → 0.607 | `artifacts/routing_steering.json` |
| 5 | 2:00–2:30 | Architecture — three layers | `docs/EXPERTS.md` |
| 6 | 2:30–3:00 | Honest gaps + the ask | `docs/DIAGNOSTICS.md` |

> **LOCKED — verified against artefacts, do not edit.** Every number spoken below is read from a file, and
> each one was re-checked against that file after the last pipeline change. If a number here disagrees with
> `artifacts/`, the artefact wins and the script is wrong.
>
> | spoken | value | source file |
> |---|---|---|
> | funnel | 203 → 151 → 24 → 28 → 10 → 18 | `artifacts/tradition_first.json` |
> | physics checks failed | 78 of 203 | `artifacts/consensus_vs_arbiter.json` |
> | unanimous 5/5, still refuted | **6** (named: 菖蒲·蒸, 升麻·蒸, 附子·炮, 甘草·炮, 甘草·炙, 甘草·蒸) | `artifacts/consensus_vs_arbiter.json → unanimous_refutations_named` |
> | 菖蒲 + 蒸 → terpenoid retention | **median 54.2 %**, range 10–94 % | `artifacts/deterministic_outcomes.json` |
> | reference monoterpene (limonene) | 1.5 % — the *mechanism illustration*, not the card | `shennong/physics/simulate.py` |
> | Joback validation | 4.5 % mean error, 6/6 within 10 % | `shennong/physics/estimators.py → validate()` |
> | phytochemistry AUC | 0.443 → 0.607 after the fix | `artifacts/routing_steering.json` |
> | 歸經 | 7.48 % vs 3.80 % permutation mean, n = 2,059, p = 0.008 | `eval/report.json` |
> | quantum layer | Koopmans IP MAE 0.82 eV | `artifacts/qm_results.json` |
>
> **The one rule for the voice-over:** read the number on screen *before* saying the conclusion. If the card
> says 54 %, say 54 %. A number spoken from memory is how this project got burned twice.


## 0:00–0:20 — Cold open · the processing instruction

**On screen:** 本草綱目 page, one line highlighted in cinnabar: 「以水二升漬，絞取汁」.

> *"In 1972 a team in Beijing read one line from a fourth-century text — soak it in water and wring out the
> juice — and realised every previous attempt had boiled it, which destroys the compound. That was
> artemisinin. The information that won the Nobel Prize was a **processing instruction**, not a plant name,
> and nobody had translated it into chemistry."*

---

## 0:20–0:55 — The finding that survived · 歸經

**On screen:** the five pre-registered axes; 歸經 lights up; the three nulls grey out.

> *"So we asked a question that can actually be answered: does the classical theory predict chemistry? We
> pre-registered five axes, fixed the thresholds before seeing any result, and ran permutation tests with
> Holm correction. 歸經 — channel tropism — predicts target organ at **seventy-five in a thousand against a
> thirty-eight in a thousand permutation mean**; two thousand and fifty-nine pairs, **p equals nought point
> nought nought eight**. Four of the five axes we could test did **not** survive, and the two Ayurvedic tests
> could not run at all. One survived, it is the most mechanistic one, and the nulls are in the repo beside
> it."*

**Provenance:** `eval/report.json → drug_discovery.theory_predictivity`; thresholds in `docs/EVALUATION.md`.

---

## 0:55–1:30 — The money shot · the arbiter overrules consensus

**On screen:** 菖蒲 card — five green 5/5 chips on the left; retention bar on the right reading **54 % median,
range 10–94 %**. Then the funnel: 203 → 151 → 28 → 10 → 18.

> *"Then the half that is missing everywhere else: something to **kill** what we generate. The hypothesis is
> that a preparation **enriches** the medicinally relevant class — that is why anyone prescribes the step.
> Steaming 菖蒲 to enrich its terpenoids: our five tradition experts scored it five out of five. Then the
> physics layer asked one question — how volatile is a monoterpene at a hundred degrees in steam? The median
> terpenoid keeps fifty-four per cent, the range across this plant's terpenoids is ten to ninety-four, and the
> reference monoterpene keeps **one and a half per cent**. You cannot enrich a class you are actively
> stripping. The claim predicted the wrong direction, and the system said so with arithmetic before anyone
> bought a reagent."*

**On screen, then the funnel, spoken with the middle step included:**

> *"One hundred and fifty-one candidates fail the attestation gate. Twenty-four more fail the tradition's own
> theory frame — that is fifty-two, and twenty-eight pass both. Physics refutes ten of those. Eighteen survive.
> And across the whole set, seventy-eight of two hundred and three fail a physics check somewhere in the
> funnel — six of them despite unanimous five-out-of-five agreement: 菖蒲 and 蒸, 升麻 and 蒸, 附子 and 炮,
> and three 甘草 preparations. You can check all six by name in the repository."*

**On screen, small:** *Joback boiling points validated against known constants — mean 4.5 % error, 6/6 within
10 %.* **Provenance:** `shennong/physics/{estimators,simulate}.py`, `artifacts/{deterministic_outcomes,
tradition_first,consensus_vs_arbiter}.json`.

---

## 1:30–2:00 — The diagnostic caught our own bug

**On screen:** AUC table; phytochemistry highlighted at 0.443; arrow to 0.607 after the fix.

> *"We built a diagnostic that scores every expert on one question: does its confidence predict whether a claim
> actually survives physics? Utility is defined by physics, never by agreement. That diagnostic caught one of
> our own experts — phytochemistry was scoring **below chance**, point four four — measuring data sparsity
> instead of validity. We found the cause in our code: a hand-written bonus that rewarded sparse-chemotype
> plants, which are exactly the ones that fail physics. We removed it, the score moved to **point six one**,
> and we **retracted the finding** rather than featuring it."*

**On screen, one line:** *"the asset is the diagnostic; the bug is the evidence it works."*

**Provenance:** `shennong/experts/steering.py`, `docs/DIAGNOSTICS.md` §2.

---

## 2:00–2:30 — Architecture · why it is auditable

**On screen:** three-layer diagram — data pipeline ⟶ 12 routeable experts ⟶ fixed first-principles core
(15 laws: 5 physics, 5 chemistry, 5 biology).

> *"Three layers at different speeds. The data pipeline takes new corpora, licence-audited, one command.
> Twelve expert modules routed by content — two and a quarter experts per item on a mixed stream, so cost
> tracks the question. And underneath, a fixed core of physics, chemistry and biology that **can say no and
> never say yes**. Adding experts cannot move it: the funnel is identical with seven experts and with
> twelve."*

**On screen, small:** *Western literature is recorded as an observation and holds no decision weight — most of
the chemistry here is Western. The point is the order of evidence.*

---

## 2:30–3:00 — Honest gaps · and the ask

**On screen, plainly:**
`plant-materia resolution 48.7 %` · `quantum: fragments only` · `2 of 5 pre-registered axes untestable`

> *"What we cannot yet do: drug-name resolution is fourteen per cent accurate and bounds every downstream
> number; the quantum layer arbitrates fragments, not natural products; and two of our five axes could not be
> tested at all. Everything we could test is in the repo with its nulls. We are looking for a lab to run the
> first three assays — everything else is already open."*

---

## Production checklist

- [ ] Every number visible on screen at the moment it is spoken.
- [ ] 歸經 beat: show the **permutation mean** beside the hit rate, not the hit rate alone.
- [ ] 菖蒲 retention bar animates **down** — the point is the collapse.
- [ ] The 0.443 → 0.607 must be shown as a correction, with the word "retracted" spoken aloud.
- [ ] No claim of drug discovery; the output is a **filter**, not a cure.
- [ ] End card: repo URL + release tag + licence.
