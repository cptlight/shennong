# SAFETY AND ETHICS

Safety here is not a disclaimer bolted to a README. It is a set of constraints that shaped the corpus, the
data model, the refusal paths and the ranking. This document states the constraints, the mechanisms that
enforce them, and the limitations we have not solved.

Read alongside `docs/METHODOLOGY.md` (how outputs are produced) and `docs/EVALUATION.md` (how the refusal
behaviour is measured).

---

## 1. Medical safety

**SHENNONG is a research instrument. It is not a medical device, and it does not provide medical advice.**

Concretely, and enforced in code rather than in prose:

| Prohibited output | Enforcement |
|---|---|
| Dosing, dose ranges, dose adjustment | `shennong/safety/` policy screen; refusal precedes any retrieval |
| Self-treatment or "should I take" guidance | same screen; refusal text names the reason |
| Diagnosis or differential diagnosis | out of scope by design; no diagnostic output path exists |
| Preparation or administration instructions | refused for all drugs, and additionally hard-gated for toxic classes |
| Contraindication *advice* | we report what a source asserts; we never convert it into advice for a person |

Every interface surface carries a persistent `research use only — not medical advice` statement. The Ask panel
shows a dual-use notice before the input field, not after the answer.

**Why refusal and not a warning.** A warning next to a plausible-sounding answer is not a safety mechanism,
because the answer is what gets read. The system refuses, and a refusal is displayed as a result — styled
distinctly, with the reason given (`no-match`, `low-coverage`, `medical`, `dual_use`). Refusing is not an
error state; it is the expected behaviour on out-of-scope input, and `docs/EVALUATION.md` §7 measures both
over- and under-refusal.

---

## 2. Toxic materia medica — analysing without recommending

The Asian canon includes genuinely dangerous drugs: 丹 (mercurial elixirs), 輕粉 (calomel), 雄黃 (realgar,
arsenic sulphide), 砒霜 (arsenic trioxide), 鉛丹 (lead tetroxide), and the Ayurvedic *bhasma* class of
incinerated metal preparations. A corpus that pretends otherwise is not a faithful corpus.

**Our position: they are in the data, and they are never in the output as advice.**

- They enter the corpus as **data about historical practice** and are treated as **toxicology evidence**, not
  as therapeutic candidates.
- When a hypothesis or candidate touches one, a hard safety annotation is attached at the data level
  (`safety.severity = "high"`, with explicit flags) and **rendered on every view** — it cannot be collapsed,
  filtered away, or hidden behind an interaction.
- The output for these is a **hazard ranking**: which preparations are dangerous, by what mechanism, with what
  speciation, at what exposure class. That is a public-health deliverable.
- No preparation method, no dosage, no administration route and no synthesis path for any of them appears
  anywhere in this repository. There is a dual-use screen in front of the generative surface specifically for
  this class, and its recall is measured.

**The honest line:** studying a poison is not the same as prescribing it, and refusing to study poisons leaves
the people who use them unprotected. We study them; we never help with them.

---

## 3. Dual-use screening

Two independent screens run before any text is generated:

1. **Medical-intent screen** — personal-use, dosing, "is it safe to take", symptom-specific self-treatment.
2. **Dual-use screen** — preparation/isolation/synthesis of toxic materials, weaponisation, deliberate harm.

The screens are pattern-based and deliberately narrow. The design trade-off is explicit: a broad screen would
refuse legitimate research questions ("how was 附子 processed classically?" is a *history* question and must
be answered), while a narrow screen lets some borderline inputs through. We accepted over-permissiveness on
historical/comparative questions and measured the resulting false-negative rate rather than guessing it
(`docs/EVALUATION.md` §7, `policy_screen_recall`).

The Ask surface never generates text from a blocked query — the block happens before retrieval, so no partial
answer can leak through a fallback path.

---

## 4. Traditional Knowledge — the Nagoya Protocol position

**Classical Asian medical texts are living heritage, not a free ore body.** They are read, recited, taught and
practised today by communities who did not consent to their knowledge being mined into a startup's dataset.
We take four positions, and each has a mechanism behind it.

### 4.1 Attribution

Attribution is **structural, not polite**. The data model carries `source → edition → author (where known) →
locator (chapter/section)` on every span, and a candidate that cannot be traced back to a specific line of text
is **withdrawn** by our own policy. You cannot cite a candidate in SHENNONG without also citing the text and
the tradition it came from. Attribution in a footnote would satisfy nobody; attribution as a foreign key is
what makes it enforceable.

### 4.2 Benefit-sharing

We adopt the **Nagoya Protocol** model of access and benefit-sharing as the default expectation for any
downstream development:

- **Prior agreement**: any commercial or clinical development arising from a candidate is expected to involve
  source-country and practitioner-community participation and a benefit-sharing arrangement agreed *before*
  exploitation, not negotiated afterwards.
- **No patent-first posture.** The corpus audit, the method and the candidate shortlist are published openly
  so that no single party can appropriate the productive layer before communities are at the table.
- **Fair return**: where a candidate advances, we expect the arrangement to include capacity building and
  research participation in the source region, not only a royalty.
- **Honest limitation**: we are a hackathon project with no legal standing to negotiate benefit-sharing. What
  we can do is state the condition, publish it, and refuse to advance a candidate whose provenance cannot be
  attributed. That is the part we control.

### 4.3 Non-extractive framing

- We publish the **negative results** as prominently as the positive ones (`docs/EVALUATION.md` §2.3). A
  project that only reports wins is extracting credibility from a tradition that cannot answer back.
- We publish the **licence audit including rejections** (`LICENSE_AUDIT.md`, and the `licence_evidence` field of every entry in `corpus/registry/sources.yaml`).
  We excluded a source we could
  have used because its NonCommercial clause conflicted with the licence we ship under.
- We do not present ourselves as correcting or completing the tradition. We present a *test* of one reading of
  it, with numbers, that a specialist is free to reject.

### 4.4 Opt-out

The registry carries `status`, and the corpus build honours it. A text may be marked **withdrawn** by a
tradition, community, or rights-holder; the next corpus build excludes it, and dependent artefacts are
rebuilt. The mechanism exists because "we didn't know how to remove it" is not an acceptable answer in a
project whose entire input is other people's heritage.

**What our opt-out does not claim:** we have not obtained prior informed consent from every lineage whose
text is in the public domain. Public-domain status is a legal fact, not an ethical acquittal. This is stated
plainly rather than papered over, and it is the single largest open ethical debt in the project.

---

## 5. Biopiracy avoidance

Four concrete rules, each checkable in the registry:

1. **Provenance before prose.** No source enters the corpus without title, author/date, URL, licence,
   licence evidence, tier, tradition and language. A source with no traceable provenance is not used.
2. **`UNVERIFIED` means excluded.** If a licence cannot be evidenced, the source is marked `UNVERIFIED`,
   **excluded from training**, and cited only. It never contributes text to the model.
3. **No redistribution of restricted material.** Public-domain text is reproduced; share-alike material is
   attributed and its obligations preserved; proprietary or inaccessible material is referenced, never
   redistributed.
4. **No "new" use claim without prior art.** A candidate's novelty claim is checked against modern literature
   and chemistry data before it is published (`docs/EVALUATION.md` §4). Claiming novelty for a known
   traditional use is both bad science and a form of appropriation.

---

## 6. Conservation

Conservation is a **direct output** of the project, not a gesture.

Traditional pharmacopoeias record substitutes for scarce materials, and CITES-listed species appear in the
canon. SHENONG tags every ingredient against CITES status and ranks substitution urgency by **how
load-bearing the ingredient is in its formula** — the 君臣佐使 role, where 君 (emperor) ingredients are
structurally essential and 佐/使 can often be replaced.

Worked cases in the current set:

- **犀角 → 水牛角** (rhino horn → water buffalo horn): an official pharmacopoeial substitution, ranked by
  how often 犀角 sits in the 君 position. A conservation priority list built from text.
- **穿山甲 → 豬蹄甲** (pangolin scale → pig toenail): the classical processing column is the argument. The
  material is typically **煅** (calcined) before use; calcination destroys keratin structure and leaves a
  largely material-agnostic mineral residue. The tradition argues for its own replacement, if you read the
  processing column rather than the ingredient name.

**Framing discipline.** These statements are **technically framed and culturally careful**. We are quantifying
a substitution argument that researchers in the source countries have themselves made. We are not asserting
that a traditional indication is worthless, and no output contains procurement, trade or sourcing guidance of
any kind.

---

## 7. Limitations we have not solved

Listed because a safety document that claims completeness is not credible.

1. **Prior informed consent is partial.** Public-domain status does not equal community consent. We have an
   opt-out mechanism and an attribution model; we do not have agreements with every lineage. This is the
   biggest debt.
2. **Attribution granularity.** Many classical texts are compilations with layers of commentary over
   centuries; naming "the author" can be a fiction. We record author *as the edition states it* and mark
   uncertain authorship rather than inventing a name.
3. **Translation dependence.** Some material is read through 19th/early-20th-century translations. Those
   translators had their own frameworks, and their word choices can pre-encode interpretation. We prefer
   originals wherever the script is supported, but this is not universally possible.
4. **Hazard analysis is not risk assessment.** We rank toxicity divergence; we do not perform
   exposure-adjusted risk assessment, and our hazard rankings must not be read as clinical guidance.
5. **The dual-use screen is pattern-based.** It will miss novel phrasings. Its recall is measured, not
   assumed, and the measurement is published.
6. **No wet-lab validation.** No candidate in this project has been tested in a laboratory. The output is a
   ranked list of testable proposals with assays attached, and nothing more.
7. **Model limitations are safety-relevant.** A small bilingual model can produce fluent, wrong classical
   readings. This is why the Ask surface is extractive-with-citations and refuses rather than generates: the
   grounding constraint is a safety mechanism as much as a scientific one.

---

## 8. Data and licence posture

- **Code and model weights:** Apache-2.0.
- **Corpus:** per-source licences preserved in `corpus/registry/`; the derived corpus carries a
  **CC BY-SA share-alike obligation**. Public-domain text is reproduced; share-alike material is attributed
  and its obligations respected; restricted material is referenced only.
- **Rejected material:** one GRETIL *rasaśāstra* source under **CC BY-NC-SA-4.0** was rejected because the
  NonCommercial clause is incompatible with a public Apache-2.0 release. It is recorded as a documented
  rejection in `LICENSE_AUDIT.md`; no text from it is used.
- **Weights intended use:** computational ethnopharmacology research. Not clinical use. Not for medical
  decision-making. Stated in `model/MODEL_CARD.md` in the same words.
