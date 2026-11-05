# FAQ

The questions we actually got asked, including the uncomfortable ones. Answers are drawn from the artefacts,
not from aspiration.

---

### "Isn't this just another LLM fine-tune?"

No, and the difference is testable. Three things separate it:

1. **The corpus was derived, then sourced.** We wrote the axioms of the domain first and derived what data
   classes they require (`docs/FIRST_PRINCIPLES.md`). The source registry is a proof obligation, not a
   download list.
2. **The theory is the predictor, and it is on trial.** 四氣五味/歸經 and rasa/vīrya are encoded as a feature
   matrix and tested with permutation nulls (`docs/EVALUATION.md` §2). A fine-tune does not test its own prior.
3. **The output is a drug candidate with a development path**, not prose. Every candidate carries a classical
   line, a formula, a computed molecular weight, a mechanism, an assay and its residual risks.

The model is the *smallest* interesting part of the project. That is a deliberate design choice.

---

### "The model is tiny. Why would anyone use a small model for this?"

Because the job is **reading and grounding**, not open-ended reasoning, and because the constraint is the point:

- The task is retrieval plus structured extraction over a fixed, licensed corpus — a narrow domain where a
  small model with a domain vocabulary beats a large model with an English-centric one.
- On a CPU-only machine, a small model is the difference between "reproducible by a judge in an afternoon" and
  "please trust our cloud endpoint".
- A grounding-first architecture means the Ask surface quotes and cites spans rather than generating freetext,
  so capability ceiling matters less than faithfulness.

Where the small model is genuinely worse, we say so — it reads classical Chinese and Sanskrit far better than
it reasons about them.

---

### "Did the Asian theory actually predict anything?"

Read `docs/EVALUATION.md` §2.3, which reports the five pre-registered tests with AUC or ρ, n and permutation
p, plus the Holm-corrected values — including the tests that came back null. The Workbench renders three
verdicts only: *predicts above chance*, *trend, not significant*, *no predictive signal*.

We will not summarise a null as a win, and we will not hide a win behind hedging. The summary sentence lives
in `eval/report.json → drug_discovery.theory_predictivity` and is rendered verbatim in the interface.

---

### "You can't get drug candidates from text. Where's the wet-lab validation?"

Correct — we can't, and we don't claim to. The deliverable is a **ranked shortlist of testable proposals**,
each with:

- a named target and mechanistic chain,
- a molecular formula and computed molecular weight,
- a specific discriminating experiment with a positive control,
- and a stated condition under which the mechanism is falsified.

**Zero candidates in this project have been tested in a laboratory.** That is stated in
`docs/SAFETY_AND_ETHICS.md` §7 and on slide 10. What we have built is the cheapest possible path from 2,000
years of text to a shortlist that a lab could start on Monday, with the reasoning exposed so a
pharmacognosist can disagree with it.

---

### "Isn't it dangerous to tell people about these plants?"

The dangerous thing is the *current* situation, where the knowledge is unindexed and unanalysed while the
plants are sold online. Our position:

- **No dosing, no preparation, no self-treatment, ever.** The Ask surface refuses by policy, and the refusal
  is a visible, measured behaviour (`docs/EVALUATION.md` §7).
- **Toxic materia medica is analysed as toxicology, never recommended.** Mercury/arsenic/lead drugs appear as
  hazard rankings with the safety annotation rendered on every view.
- **The risk-reducing outputs are the point**: name-collision detection (the 木通/關木通 carcinogen case),
  adulteration ranking, and the 十八反/十九畏 interaction dataset.

A system that can say "these two taxa share a name and one of them causes urothelial cancer" is a safety
instrument. A system that refuses to look is not safe; it is just quiet.

---

### "How do you avoid biopiracy?"

Four mechanisms, all checkable in the repo (`docs/SAFETY_AND_ETHICS.md` §4–5):

1. **Structural attribution** — source, edition, author, locator are foreign keys on every span. A candidate
   that cannot be traced to a line of text is withdrawn.
2. **`UNVERIFIED` is terminal** — unclear licence means excluded from training and cited only.
3. **Nagoya-model benefit-sharing** stated as a precondition for any downstream development, plus a working
   opt-out so a community can withdraw a text and the next build honours it.
4. **Rejections are documented** — including a NonCommercial-licensed source we excluded because it would have
   poisoned an Apache-2.0 release.

**The debt we have not discharged:** public-domain status is not consent. We have no agreement with every
lineage whose text is in the corpus. We state that plainly rather than claiming a clean conscience.

---

### "Why are there Western herbal texts in the corpus at all?"

As a **labelled comparative control**, capped at ≤ 3% of tokens and marked `tradition: comparative-control` in
the registry. Its only function is to answer: *is a finding an artefact of any large botanical corpus?* If a
pattern appears in both the Asian canon and the Western herbals, it is probably a property of botanical
languages, not of Asian pharmacology.

It is not used as evidence for any hypothesis, and one hypothesis (H-01) explicitly says so in its provenance
list.

---

### "Where are the numbers?"

Every number is in a file:

| Number | Source file |
|---|---|
| Corpus counts, licences, tiers | `corpus/registry/sources.yaml`, `corpus/DATA_CARD.md` |
| Model size, steps, loss | `model/MODEL_CARD.md`, `training/runs/*/metrics.json` |
| Benchmarks, theory tests, nulls, ablations | `eval/report.json` |
| Candidates and their properties | `artifacts/drug_candidates.json` |
| Whatever the Workbench is showing | its own startup banner + per-panel `LIVE`/`FIXTURE` badge |

If the Workbench shows a `DEMO FIXTURE` badge, that panel is running on placeholder data for interface
development and **nothing on it is a result**. `python app/serve.py --strict` refuses to start in that state —
it is the mode we use for the final recording.

We also ship `submission/check_pending.py`, which fails if a a double-bracketed PENDING marker placeholder survives into a
shipped artefact. Documentation drift is a bug with a test.

---

### "Why is the Workbench not a web app?"

Because a judge, a clinic and a ministry should be able to run it. `python app/serve.py`, standard library
only, no build step, no CDN, no network, ~90 KB of HTML/CSS/JS, keyboard-navigable. It runs on the same CPU
that trained the model.

Local-first is also an ethics position: a research instrument over living traditional knowledge should not
require sending queries to someone's cloud.

---

### "What would make you withdraw the candidate list?"

Five pre-registered conditions, in `docs/EVALUATION.md` §9, written before the results:

1. Null model does not collapse the discovery scores (drop < 0.30).
2. 取象比類 shows a strong positive ρ — our extraction is reading resemblance language.
3. Theory tests are null *and* the monolingual ablation performs equally well — then reading originals bought
   nothing.
4. Candidate novelty collapses against a human-curated prior-art list.
5. A candidate cannot be traced to a specific line of text.

Any one of these is a live risk, not a hypothetical. That is why they are numbered and published.

---

### "Can I reuse the corpus / the model / the figure assets?"

- **Code and weights:** Apache-2.0 — yes, including commercially, with attribution.
- **Derived corpus:** carries a **CC BY-SA share-alike obligation** on the derived text; the underlying
  sources keep their own licences (`corpus/registry/sources.yaml` lists each).
- **Figures:** hand-written SVG in `assets/`, same licence as the code.
- **Model weights are not for clinical use.** Research only. That sentence is in `model/MODEL_CARD.md` in the
  same words.

---

### "How long did this take, and what would you do with another month?"

Built during EthnoHack 2026. With another month the order would be:

1. the cheapest falsification — processed-versus-raw 附子 by LC-MS, one method decides it;
2. cross-tradition prediction: fit on 本草綱目, predict a held-out class recorded only in Ayurvedic or Unani
   material. If the framework generalises across traditions, it is a discovery engine;
3. practitioner review with attribution and benefit-sharing agreed *before* any wet work.

Notice what is not on that list: a bigger model.
