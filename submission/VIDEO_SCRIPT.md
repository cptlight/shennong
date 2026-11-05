# SHENNONG — 10:00 pitch video script

**Hard limit: 10 minutes (600 s).** Recorded screen-first, 1080p, no music under the voice-over except a
quiet bed at −26 dB. Every on-screen artefact named below exists in this repository; the timings are the edit
target, and each segment is written to be trimmable in the listed order (cut 1, then 2…) if we run long.

Spoken numbers marked `*(analysis pending)*` are read from the repository at record time — never approximated
on camera. No shot shows a fixture panel without its `DEMO FIXTURE` badge visible.

| # | In | Out | Dur | Segment |
|---|---|---|---|---|
| 1 | 00:00 | 00:38 | 0:38 | Cold open — the word that changed a drug |
| 2 | 00:38 | 01:22 | 0:44 | The gap |
| 3 | 01:22 | 02:12 | 0:50 | The thesis: theory is the method |
| 4 | 02:12 | 03:02 | 0:50 | Derivation, not collection |
| 5 | 03:02 | 04:02 | 1:00 | The corpus and the licence audit |
| 6 | 04:02 | 05:00 | 0:58 | The model, and the real curve |
| 7 | 05:00 | 06:00 | 1:00 | The pipeline, on the command line |
| 8 | 06:00 | 07:22 | 1:22 | The Workbench — one candidate end to end |
| 9 | 07:22 | 08:22 | 1:00 | Does the theory predict? |
| 10 | 08:22 | 09:14 | 0:52 | Honest limitations |
| 11 | 09:14 | 09:40 | 0:26 | Safety, TK, conservation |
| 12 | 09:40 | 10:00 | 0:20 | Roadmap, the ask, close |

**Total 600 s.**

---

## 1 · 00:00–00:38 — Cold open

**On screen:** A page of 本草綱目 in 繁體, slowly settling. One line highlights in cinnabar. Hard cut to
`assets/og-image.svg` — the seal mark and the name, SHENNONG 神农.

**VO:**
> In 1972, a pharmacologist read one word in a fourth-century Chinese handbook of emergency remedies.
> The instruction was to steep the herb in **cold** water. Not boiled. Cold.
> That word became artemisinin.
>
> Two thousand years of Asian pharmacology is sitting in public-domain archives. We are still reading the
> English summaries — which is the one layer where the knowledge was already lost.

**Artefact:** 本草綱目 (public-domain edition), then `assets/og-image.svg`.

---

## 2 · 00:38–01:22 — The gap

**On screen:** Split screen. Left: the Chinese originals — 神農本草經, 傷寒論, 雷公炮炙論 — as raw text scrolling.
Right: modern papers citing only translated summaries. A third column appears: "theory — 四氣五味 · 歸經 · 七情 ·
rasa / guṇa / vīrya".

**VO:**
> Here's the thing that's hard to see unless you work in this field. The Asian medical canon isn't folklore.
> It's a *predictive system*. "Cold, bitter, enters the Liver channel" is a claim about polarity, about
> compartment, about mechanism. Ayurveda makes the same kind of claim with *vīrya* and the six *rasa*.
>
> Those are hypotheses. They're just never been *evaluated* as hypotheses — because that means reading the
> untranslated originals at scale, and connecting them to modern structure and target data. Nobody had the
> model. So nobody ran the experiment.

**Artefact:** corpus excerpts (`corpus/processed/`), theory vector fields in `properties.csv`.

---

## 3 · 01:22–02:12 — The thesis

**On screen:** One drug name resolves into a property vector — chips: `熱 · 辛 · 歸心腎 · 升 · 下品` — then an
arrow labelled *prediction* to `MW · logP · target · thermolability`. Then a second arrow, labelled
*permutation null*, folding back on the first.

**VO:**
> Everyone else built a chatbot over this material — there are TCM assistants, curated herb–compound databases,
> virtual-screening pipelines. All good work. None of them asks the prior question.
>
> We treat Asian pharmacological theory as a **predictive prior** — a feature vector — and we put it on trial.
>
> Two questions, both falsifiable. Does the theory predict modern chemistry better than chance? And if it does —
> what drug candidates does that let us propose?
>
> The deliverable isn't an answer in a chat window. It's a ranked shortlist of **drug candidates**: a molecule,
> a mechanism, and the experiment that would kill it.

**Artefact:** theory chips in the Workbench Candidates view.

---

## 4 · 02:12–03:02 — Derivation, not collection

**On screen:** `docs/FIRST_PRINCIPLES.md` opens; axioms highlight; a tree unfolds into required data classes;
those become the tiers in `assets/corpus_tiers.svg`.

**VO:**
> We didn't start from a dataset dump. We wrote down the axioms of the field, derived what data classes those
> axioms *logically require*, and only then went sourcing.
>
> That matters because it turns the source registry into a proof obligation. Every tier exists because
> something demanded it. And the biology and chemistry substrate at tier one isn't "Western medicine" — it's
> the interpretive layer that lets us say what a classical claim actually *means*.
>
> The Western herbal tradition is in there too, at under three percent of tokens, labelled `comparative-control`
> — purely so we can test whether a finding is just an artefact of any large botanical corpus.

**Artefact:** `docs/FIRST_PRINCIPLES.md`, `assets/corpus_tiers.svg`, `corpus/registry/sources.yaml`.

---

## 5 · 03:02–04:02 — The corpus and the licence audit

**On screen:** Workbench → **Corpus** panel. Scroll the tier chart, the licence badges, the ledger table.
Cut to `corpus/registry/sources.yaml` in the editor; scroll to a `status: unverified` entry. Then a terminal:
`grep -c 'licence: Public Domain' corpus/registry/sources.yaml`.

**VO:**
> 106 sources. 45.6 million characters. Twenty-seven thousand records.
> 5 languages, from the first century to the twentieth.
>
> 神農本草經, 本草綱目, 傷寒論, 雷公炮炙論. Caraka, Suśruta, al-Qānūn. And the science corpus most people
> skip — 天工開物 on materials, 齊民要術 on fermentation, 夢溪筆談 on natural observation. That's where the
> process chemistry actually lives.
>
> Now — the part that took the longest and won't make a demo. Every source carries its licence *and the
> evidence for that licence*. 38 we kept. 1 we rejected.
>
> One of those rejections was a Sanskrit *rasaśāstra* text under a **NonCommercial** licence. It would have
> been easy to include. A NonCommercial dependency would have poisoned an Apache-2.0 release, so we excluded
> it and wrote down why. That's in the audit file, not in a footnote.

**Artefact:** Workbench Corpus panel (live), `corpus/registry/sources.yaml` (its `licence` /
`licence_evidence` fields are the audit), `LICENSE_AUDIT.md`.

---

## 6 · 04:02–05:00 — The model, and the real curve

**On screen:** Terminal: `cat training/runs/shennong-mini-r1/metrics.json | head -20`. Then the Workbench
**Methodology** panel with the loss curve drawing in. Zoom the axes so train and held-out lines are legible.
Cut to a terminal: `ls -l artifacts/*.gguf` and `sha256sum artifacts/shennong-mini-f16.gguf`.

**VO:**
> The model is `shennong-mini`: 8.72 million parameters, trained **from scratch on this laptop's CPU**. An
> Intel i7 — no GPU at all. Two hundred steps, 1.64 million tokens, and it took **forty-five minutes**.
>
> The vocabulary is 16,384 tokens, budgeted for Classical Chinese and Sanskrit, because the entire point is
> reading the originals rather than English summaries.
>
> This curve is the actual log — train loss 6.37, held-out 6.39, validation curve falling from 9.74 to 6.39.
> We could have shown you a nicer curve. It would have been fiction, and then you'd have no reason to believe
> any other number in this video.
>
> Now the part that is easy to oversell, so let me undersell it. 1.6 million tokens against 8.7 million
> parameters is 0.19 tokens per parameter — about **one percent of a compute-optimal budget**. This is a
> **pipeline proof, not a useful model**. Anyone who tells you a model this size is generally capable is
> selling something.
>
> What is genuinely unusual is the rest of it: the weights are **18 megabytes**, not gigabytes — one point
> eight percent of the one-gigabyte ceiling we were given — and they are published, with a hash you can check.
> The whole chain runs on a CPU, offline, and one person can reproduce it.

**Artefact:** `training/runs/shennong-mini-r1/metrics.json`, `artifacts/shennong-mini-f16.gguf` (18,054,560 B,
sha256 `a67ad442…4cdb60`), Workbench Methodology → loss chart.

---

## 7 · 05:00–06:00 — The pipeline, on the command line

**On screen:** Split: terminal left, growing JSON right. Commands typed at human speed, output streaming.

```bash
python -m shennong.cli cai  --corpus-dir corpus/processed     # collect
python -m shennong.cli zhi  --corpus-dir corpus/processed     # prepare
python -m shennong.cli pei  --out-kg app/data/kg.json         # combine
python -m shennong.cli shi  --n 12 --out app/data/hypotheses.json   # deploy
```

**VO:**
> Four stages, named for the four classical operations of Chinese pharmacy.
>
> **采 Cǎi** — collect. Fetch, normalise 繁 and 简, fold IAST against Devanagari, dedupe at the thirteen-gram
> level, extract entities.
>
> **制 Zhì** — prepare. This is 炮制 applied to text: resolve 異名 across eras and scripts into modern taxa, and
> translate process words — 炮, 煅, 淬, 九蒸九曬 — into modern extraction chemistry.
>
> **配 Pèi** — combine. Build the graph. And encode the incompatibility rules: 十八反, 十九畏, *viruddha* — a
> pre-modern drug-interaction dataset that nobody has systematically tested.
>
> One detail worth saying out loud. 十八反 does not contain eighteen pairs. The mnemonic counts drugs, not
> pairings: sixteen canonical antagonisms cover nineteen named drugs. We report both denominators, because
> padding the list to look round would mean inventing pairs.
>
> **使 Shǐ** — deploy. Rank. Attach a falsification plan to every single thing we emit. And run the theory
> experiment.
>
> Each stage is one command. Each artefact is hashed.

**Artefact:** `shennong/cli.py`, `app/data/{kg,hypotheses}.json`.

---

## 8 · 06:00–07:22 — The Workbench: one candidate, end to end

**On screen:** `python app/serve.py` → prints the provenance banner → browser opens the Workbench. Click
**Candidates**. The table is real output: 60 candidate molecules across 15 taxa, every classical line verified
against a byte offset. Expand the **前胡** row and scroll it slowly, in order.

**VO:**
> This is the screen that matters. `python app/serve.py` — standard library only, no build step, no network.
>
> Sixty candidate molecules across fifteen taxa. Every row is a classical lead turned into a molecule. Let's
> open one.
>
> **The line.** The 普濟方 formulary, 1406. The 前胡湯 entry: *“Qianhu decoction treats cough from lung heat.”*
> Verbatim, with a byte offset into the corpus, so you can go and read it yourself.
>
> **The theory.** 前胡 is cold, bitter, entering the Lung channel. So the prediction is specific: an action
> directed at the lung. And the recorded indication is a cough syndrome. The framework named the organ — that is
> what makes it a testable system rather than poetry.
>
> **The molecule.** Peucedanocoumarin I. C₂₁H₂₄O₇, molecular weight 388.42, logP 4.6, zero hydrogen-bond donors,
> seven acceptors, TPSA 64.6. Four of four Lipinski rules evaluated — it passes. Veber passes. Those numbers are
> computed from the resolved SMILES, not estimated.
>
> **The assay.** Calcium flux on TRPA1-expressing cells, then a recombinant line. Go/no-go: reproducible
> engagement in two orthogonal assays, plus selectivity over the nearest paralogue.
>
> **And the honest part.** Novelty is 0.88 — for every single candidate. The novelty estimator is not yet
> discriminating, so the rank order does not carry information today. We could sort the table by something that
> looks like a score. Instead we show the defect, and it is item one on our own improvements list.

**Artefact:** Workbench → Candidates → 前胡 expanded; `artifacts/drug_candidates.json` (60 candidates, all
structures resolved, all classical lines verified). Panel badge: **candidates = LIVE**.

---

## 9 · 07:22–08:22 — Does the theory predict?

**On screen:** Workbench → **Methodology**. Scroll to the five theory cards. Cut to a terminal computing the
permutation null: the same statistic recomputed a thousand times, histogram building, the observed value
marked as a vertical line.

**VO:**
> Here's the experiment the whole project hangs on.
>
> We take the property vectors — 四氣, 歸經, 五味, vīrya, ṣaḍrasa — and we ask whether they predict measured
> chemistry. Nature against polarity and thermolability. Channel tropism against target organ.
> Ayurvedic vīrya against logP. Every test gets an effect size, an n, a p-value, and a permutation null.
>
> *(analysis pending)*
>
> And the null model still runs underneath: shuffle the plant-to-use edges and the discovery scores collapse.
> If they didn't collapse, we'd be measuring our own pipeline instead of the biology.
>
> 取象比類 — reasoning by resemblance — gets the same treatment. It's a control, not an assumption, and it
> sits at the bottom of our ranked list where it belongs.

**Artefact:** Workbench Methodology → theory-predictivity cards; `eval/report.json`; `docs/EVALUATION.md`.
Numbers read on camera from `eval/report.json` — the same file a judge can open.

---

## 10 · 08:22–09:14 — Honest limitations

**On screen:** Nothing but type on parchment. No B-roll. This beat is deliberately plain.

**VO:**
> Now the part most pitches skip.
>
> **No candidate here has been validated in a wet lab.** Not one. We produce ranked leads with assays
> attached — we do not produce drugs.
>
> **The theory result is not a triumph by default.** *(analysis pending)* We report the
> tests we lost with the same prominence as the ones we won.
>
> **The model is small.** It's a research instrument, and it reads classical Chinese and Sanskrit far better
> than it reasons about them.
>
> **Our corpus has real gaps.** Tibetan and Southeast Asian material is thin because openly licensed editions
> are thin — not because the knowledge isn't there. And channel assignments disagree between editions; we
> inherited those disagreements rather than resolving them.
>
> **Attribution has limits.** These are living traditions. A catalogue entry is not a conversation, and we
> know the difference.
>
> One rule we enforce in the product, not the prose: **every hypothesis carries its own kill-criteria, and a
> hypothesis whose citation span fails to resolve is dropped, not softened.**

**Artefact:** `docs/SAFETY_AND_ETHICS.md` limitations section.

---

## 11 · 09:14–09:40 — Safety, TK, conservation

**On screen:** Ask panel. Type *"how do I prepare aconite at home"*. The cinnabar `policy-screen · dual_use`
refusal lands. Then cut to the CITES badge and the 異名同物 collision graph.

**VO:**
> The canon contains mercury, arsenic and lead drugs. We don't pretend otherwise — they're in the corpus as
> toxicology data. They never leave it as advice. Ask how to prepare one and this is what you get: a refusal,
> on policy, not on capability.
>
> And the corpus contains living heritage, not ore. Attribution is in the data model. Benefit-sharing is on
> the Nagoya model. A community can withdraw a text and the build honours it.
>
> One more output: conservation. Rank endangered ingredients by how load-bearing they are in their formula,
> and you get a substitution-priority list that costs no animals to produce.

**Artefact:** Workbench Ask (refusal), CITES tagging, `docs/SAFETY_AND_ETHICS.md`.

---

## 12 · 09:40–10:00 — Roadmap, ask, close

**On screen:** Three-horizon roadmap strip, then the three asks as pins, then the seal mark and the repo URL.
Hold on the URL for 3 seconds.

**VO:**
> Next: the cheapest falsification first — the processed-versus-raw comparison, where one LC-MS method decides
> it. Then cross-tradition prediction: fit on 本草綱目, predict a held-out class recorded only in Ayurvedic or
> Unani material. If the framework generalises across traditions, it's a discovery engine.
>
> What we need is a lab for the first three assays, practitioners for review, and compute to train the
> flagship properly.
>
> Everything else is already open — the corpus audit, the method, the candidates, the negative results, and
> this workbench. Apache-2.0, no gate, no network required.
>
> Shennong tasted a hundred herbs. We taught a model to read what he wrote down.

**Artefact:** `README.md`, `https://github.com/cptlight/shennong`.

---

## Production notes

- **No fixture on camera without its badge.** The Workbench prints `DEMO FIXTURE` on any panel running on
  `app/data/*` fixtures. Record the final video with real artefacts (`make app-data` + `make eval`); if any
  panel is still fixture, leave the badge visible and say so — do not crop it.
- **Numbers are read live.** Wherever the script says `*(analysis pending)*`, read it off the file during the take
  rather than memorising it. Prevents drift between video, deck and Devpost.
- **Terminal legibility:** 16 pt minimum, dark-on-parchment theme, cursor blink off, typing at ~55 wpm with
  commands pasted for the long ones.
- **Cut order if long:** trim segment 4 by 15 s, then segment 7 by 15 s, then segment 2 by 10 s. Never trim
  segment 10 — the honest-limitations beat is load-bearing.
- **Accessibility:** burned-in captions of the VO. Describe the on-screen artefact in the caption where the
  visual carries information the audio doesn't.
