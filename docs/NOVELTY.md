# NOVELTY — what is actually new, and how to say it without lying

This document exists because "we used AI on ancient medicine" is not a product, it is a category. This
is the subtractive analysis: what we are **not** claiming, what is genuinely ours, what the closest
prior work is, and the exact sentence to say to a judge.

---

## 1. Subtract first: what we are NOT claiming

Every one of these is already done by someone, and pretending otherwise would be the fastest way to
lose a technical judge:

- **❌ A knowledge graph of TCM.** Done to death. TCMSP, SymMap, ETCM, HERB, TCMID all provide
  herb–compound–target edges, most with more curation than we can match in a week.
- **❌ An LLM that answers questions about Chinese medicine.** ShenNong-TCM, HuatuoGPT, BianCang and
  a dozen others exist, with training sets and benchmarks. *(Note: there is a 2023 model called
  "ShenNong-TCM" — different project, different goal, and we should say so explicitly rather than
  let a judge discover the name clash. See §5.)*
- **❌ Named-entity / relation extraction over 本草 texts.** A real research literature exists; we are
  not the first to extract "herb → treats → disease" from classical Chinese.
- **❌ Virtual screening / drug-likeness filtering.** Lipinski, Veber, PAINS: textbook.
- **❌ "AI discovers ancient remedy."** The genre of press release we are explicitly avoiding.

If we had built any of those, we would have built a commodity. So we did not.

## 2. The four things that are genuinely new

### N1 — We test the theory itself as a predictive framework (the bold claim)

Every TCM/ML paper **uses** 四氣五味 · 歸經 · 君臣佐使 or rasa/guṇa/vīrya as **features**. We could not
find one that asks the prior question and reports the answer with a null distribution:

> **Does the classical property system predict measured molecular chemistry and target biology better
> than chance — and how much better?**

We encode the classical theory as a feature vector, regress it against *measured* properties
(molecular polarity, volatility, thermolability, logP, target family, organ-level action), and report
**AUC / Spearman ρ with a permutation-test p-value and n**, for each framework separately.

Why this is novel and why it is the product: it is the only claim here that can be **wrong in an
interesting way**. If 歸經 predicts receptor family at AUC 0.72, we have validated a 2,000-year-old
predictive system as a *usable prior for drug discovery* — that is a genuine finding, not a demo.
If it lands at 0.51, we have published a real negative result about a framework that a billion people
use — also a finding, and one nobody in this competition will have.

**And it is pre-registered.** The thresholds and the null construction are written down in
`docs/EVALUATION.md` before the numbers exist. We cannot tune it into a positive.

### N2 — Process language is compiled into a chemistry operator (the useful claim)

Classical pharmacy does not just say *what* to use; it says **how to prepare it** — 炮, 煅, 煨, 淬, 蒸,
炒, 醋炙, 蜜炙, 酒炙, 發酵, 水飛, 昇/飛/伏, and on the Indian side *śodhana*, *māraṇa*, *bhasma*.
That vocabulary is an **instruction set for physical chemistry** that modern NLP treats as noise.

We compile it into an explicit operator table — each process term mapped to what it does to a
molecule (hydrolysis, decarboxylation, oxidation, volatilisation, esterification, complexation,
salt formation, thermal decomposition) — and then use it **generatively**:

- For a given drug, *predict which constituents a preparation destroys, enriches or conjugates.*
- Flag drugs where the traditional step is **load-bearing** (Aconitum: 炮制 hydrolyses diester
  diterpene alkaloids to far less toxic monoesters — remove the step and you have a poison, not a
  medicine) versus where the step is **plausibly ritual** (an honest negative we are willing to print).
- Explain *why* the classical protocol had to be that protocol, in chemical terms.

The famous artemisinin story (葛洪's 絞取汁 = cold maceration, not decoction, because artemisinin is
thermolabile) is **one anecdote**. We are turning that anecdote into a systematic operator with
provenance. *That* is the generalisation nobody has built.

### N3 — Numbered rules become a finite, mechanistically-bridged hypothesis set

十八反 (18 antagonisms) and 十九畏 (19 mutual fears) — plus Ayurvedic *viruddha* — are a **closed list of
~40 interaction claims** compressed by a pre-modern tradition. They are almost never tested as a set;
pharmacology papers study individual pairs. We:

1. enumerate them with citations to the text,
2. bridge each pair to a plausible **modern mechanism** (CYP450 inhibition/induction, P-gp transport,
   chelation, precipitation, shared toxic constituents, additive cardiotoxicity),
3. attach a cheap **assay** that would confirm or kill it.

A closed, bridged, assay-annotated interaction hypothesis set is a **shippable artifact** — and in a
world where herb–drug interactions are an actual clinical problem, it is the most immediately useful
thing we make.

### N4 — The whole stack is auditable, and that is a design constraint, not a slogan

- **< 1 GB, open weights, CPU-runnable** → the people who hold this knowledge (clinics in Yunnan,
  Kerala, Tehran, Lhasa) can run it offline; a 70 B hosted API cannot be audited or deployed there.
- **Span-level provenance**: every claim resolves to `(source_id, char_start, char_end)` in a real
  text, and the renderer **refuses** when it cannot resolve. A hypothesis whose evidence will not
  resolve is dropped, not softened.
- **Knowledge in the index, structure in the graph, reasoning in the model** — so the corpus is
  enumerable and the licence is auditable (including the sources we *rejected*: GRETIL was excluded
  because CC BY-**NC**-SA is incompatible with a public repository).
- **Refusal is a feature**: on a question with no supporting span, the system must say so.

The existing TCM-LLM line is uniformly "bigger model, better benchmark, closed weights". We go the
other way deliberately, and can defend why.

## 3. Why this is different — against the actual prior art

| | TCMSP / SymMap / ETCM / HERB | ShenNong-TCM / HuatuoGPT | NLP-on-herbals papers | General LLMs | **SHENNONG** |
|---|---|---|---|---|---|
| Herb–compound–target graph | ✅ curated | ⚠️ indirect | ❌ | ❌ | ✅ derived (+provenance) |
| Reads **untranslated** classical text | ❌ | ⚠️ partly | ✅ | ❌ | ✅ + Sanskrit/Latin |
| **Process language → chemistry** | ❌ | ❌ | ❌ | ❌ | ✅ **the operator** |
| **Theory tested as a predictive prior** | ❌ (only used as feature) | ❌ | ❌ | ❌ | ✅ **the experiment** |
| Rules as a bridged testable set | ❌ | ❌ | ❌ | ❌ | ✅ 十八反/十九畏/viruddha |
| Emits **falsifiable** hypotheses w/ kill-criteria | ❌ | ❌ | ❌ | ❌ | ✅ |
| Span-level citation, refuses when ungrounded | ❌ | ❌ | ⚠️ | ❌ | ✅ |
| Open weights, < 1 GB, CPU | ❌ | ❌ | n/a | ❌ | ✅ |
| Licence audit incl. rejections | ❌ | ❌ | ❌ | n/a | ✅ |

The gap is a single missing thing: everybody has data, everybody has a chatbot — **nobody has the
translation layer, and nobody has tested whether the theory it encodes actually predicts anything.**

## 4. How to sell it (three lengths)

**One sentence (30 s).**
> Everyone else built a chatbot over ancient Asian medicine. We built the missing translation layer —
> and then we tested whether the classical theory actually predicts modern chemistry, because that is
> what turns 2,000 years of text into drug candidates.

**Two minutes.**
1. **The stake:** the record is real but encoded in a language science never decoded — process words,
   numbered rules, formula roles, drug names that drifted. The bottleneck has never been data volume,
   it is *translation*.
2. **The build:** 38 M characters of licensed public-domain canon in the original languages
   (本草綱目, 神農本草經, 雷公炮炙論, 傷寒論, Avicenna's 1593 Latin *Canon*, Suśruta) → a <1 GB open model
   that reads the register → a graph with span-level provenance → candidates.
3. **The experiment that makes it science:** does 四氣五味/歸經 predict molecular properties above
   chance? Pre-registered, permutation-tested, published either way.
4. **The artifact:** N drug candidates, each with structure, computed drug-likeness, mechanism, and
   the assay that would kill it. Plus a bridged herb–drug interaction set that a clinic could use
   tomorrow.
5. **The honesty:** the resolution F1 is reported *before* any discovery claim, because a graph built
   on bad name resolution is built on sand; the limitations section is longer than the brag section.

**The demo moment (what the judges should see, in this order).**
> A line from 傷寒論 (220 CE) → the classical property vector → the process step it prescribes →
> the molecule and its computed properties → the modern target → **and the single experiment that
> would prove us right.**

That chain, one screen, in that order, is the whole product.

## 5. The name clash, handled

A 2023 model named **ShenNong-TCM** exists (Chinese TCM LLM + dataset). We use **SHENNONG** as the
*project* name because 神農 is the mythic founder of the discipline and our thesis is "taste the herbs
again, systematically". We must state the distinction in one line in the README and Devpost:
*different project, different goal — they built a TCM assistant; we built a discovery engine and a
theory test, and we are not affiliated.* Saying it first is stronger than being asked.

## 6. What follows for the build (product consequences)

From the above, five decisions follow and everything else is optional:

1. **Lead with the theory test and the candidates.** The knowledge graph and the Workbench are
   *instruments*, not the product. `eval/report.json`'s theory block and `artifacts/drug_candidates.md`
   are the headline artefacts.
2. **The process-operator table must be complete and cited**, because N2 is the most useful novelty
   and it is the one a pharmacognosist can immediately check against their own knowledge.
3. **Enumerate the rule set completely** (all 18 + 19 + viruddha pairs) — completeness is itself the
   contribution; a partial list is just an anecdote.
4. **Publish the nulls** — including 取象比類 and ṣaḍrasa — because in a field with this much hype,
   a pre-registered negative is the strongest possible signal of integrity.
5. **Cut anything that only looks impressive.** More benchmarks we did not pre-register, more
   dashboards, more model parameters: all of it dilutes the two claims that are actually ours.
