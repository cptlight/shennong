# SHENNONG 神农

### Shennong tasted a hundred herbs. We are teaching a 400 MB model to do it again — and to tell us what he hid between the lines.

**EthnoHack 2026** · Track **01 — Traditional Knowledge Mining** (primary) · with depth in **02 — Natural
Products for Drug Discovery** and **04 — Digital Health & Phytotherapy**

> **A note on the name, said first.** There is a 2023 model called **ShenNong-TCM** (a Chinese TCM LLM with
> an associated dataset). We are a **different project with a different goal**: they built a TCM assistant;
> we built a discovery engine and a pre-registered test of whether classical theory predicts modern
> chemistry. We are **not affiliated**, and we are not claiming their work. We keep the name SHENNONG
> because 神農 is the mythic founder of this discipline and our thesis is *"taste the herbs again,
> systematically"*. If you searched the name and found them first: you are right to check, and this is the
> answer.

---

## Inspiration

In 1972 a pharmacologist in Beijing read a line in a fourth-century handbook of emergency remedies —
*青蒿一握，以水二升漬，絞取汁，盡服之*, "one handful of sweet wormwood, steeped in two sheng of water, wrung
out, and the juice drunk entire" — and noticed that the instruction was **cold** water. The compound that
followed was artemisinin. The lesson was not "ancient texts are wise". The lesson was that a **preparation
detail nobody had translated into modern terms** turned out to be the difference between a dead end and a drug.

That is the gap we are trying to close, and it is still open.

Two thousand years of Asian medical writing — 神農本草經, 本草綱目, Charaka, Suśruta, al-Qānūn — sit alongside
the *other* Asian record: 天工開物 on technology and materials, 齊民要術 on fermentation and food processing,
夢溪筆談 on natural observation. Between them they describe thousands of plants, hundreds of preparations, and
several complete theoretical systems for predicting what a drug does: **四氣五味** (four natures and five
flavours), **歸經** (channel and organ tropism), **升降浮沉** (directional action), **七情** (the seven
relations of combination), **君臣佐使** (formula roles), and in Ayurveda **rasa / guṇa / vīrya / vipāka /
prabhāva** with **tridoṣa**.

Those systems are not vague poetry. They are **predictions**: "cold, bitter, enters the Liver channel" is a
claim about polarity, about compartment, about mechanism. Yet they have almost never been evaluated as
predictors, because the evaluation requires reading the untranslated originals at scale and connecting them
to modern structure and target data. Most computational work on this literature reads modern English summaries
— which is precisely the layer where the encoded knowledge has already been laundered away.

So the question we set ourselves was narrow and testable: **does Asian pharmacological theory actually predict
modern chemistry, and if it does, what drug candidates does that let us propose?**

---

## How this is different

"AI meets ancient medicine" is a category, not a contribution. We are not building a knowledge graph
(TCMSP, SymMap, ETCM and HERB did that properly), not an LLM that answers questions about Chinese medicine
(ShenNong-TCM, HuatuoGPT, BianCang), and not another virtual-screening filter. Three rows are the whole
argument — the full nine-row comparison and the subtractive analysis are in `docs/NOVELTY.md`:

| | The curated TCM databases (TCMSP, SymMap, ETCM, HERB) | The TCM chatbot line (ShenNong-TCM, HuatuoGPT, BianCang) | **SHENNONG** |
|---|---|---|---|
| **Process language → chemistry** | ❌ | ❌ | ✅ a compiled operator table: 炮/煅/淬/九蒸九曬 → hydrolysis, oxidation, volatilisation, complexation |
| **Theory tested as a predictive prior** | ❌ used as a feature, never evaluated | ❌ | ✅ **the experiment**: AUC/ρ + permutation p + n, pre-registered |
| **Closed rule set bridged to mechanisms** | ❌ | ❌ | ✅ 十八反 / 十九畏 / *viruddha* enumerated, mechanistically bridged, assay-annotated |

Everyone else has data, or a chatbot. **Nobody has the translation layer, and nobody has tested whether
the theory it encodes actually predicts anything.** That is what turns two thousand years of text into drug
candidates, and it is the only reason this project should exist.

---

## What it does

SHENNONG is an open, **< 1 GB**, **≤ 1 B-parameter** bilingual classical model plus a discovery engine. It does
five things, in order of importance.

**1. It tests the theory itself — the claim that makes this science.** This is the product, not a supporting
analysis. Every TCM/ML paper *uses* 四氣五味 · 歸經 · 君臣佐使 or rasa/guṇa/vīrya as features. We could not find one
that asks the prior question and reports the answer with a null distribution: **does the classical property system
predict measured molecular chemistry and target biology better than chance, and how much better?** We encode the
theory as a feature vector and regress it against *measured* properties — polarity, volatility, thermolability,
logP, target family, organ-level action — reporting **AUC or Spearman ρ with a permutation-test p-value and n**
for each framework separately.
This is the only claim here that can be **wrong in an interesting way**. If 歸經 predicts receptor family at a
useful AUC, we have validated a two-thousand-year-old system as a usable prior for drug discovery. If it lands at
0.51, we have published a real negative result about a framework a billion people use — also a finding, and one
nobody else in this competition will have. **And it is pre-registered:** the thresholds and the permutation
construction were written down in `docs/EVALUATION.md` before the numbers existed, so we cannot tune it into a
positive.

**2. It emits drug candidates.** Each candidate is a complete chain: a line of classical text → the property
vector it implies → a molecule with formula and computed properties → a proposed mechanism → a development path
with the assay that would advance or kill it → its residual risks. Where a structure is unresolved we leave it
**null** and say so. We do not invent SMILES, and we do not round "one of four Lipinski rules evaluated" up to
"Lipinski-compliant".

**3. It enumerates the complete interaction rule set.** 十八反 (18 antagonisms) and 十九畏 (19 mutual fears), plus
Ayurvedic *viruddha* — a closed list of roughly forty interaction claims compressed by a pre-modern tradition and
almost never tested as a set. We enumerate every pair with a citation to the text, bridge each to a plausible
modern mechanism (CYP450 induction or inhibition, P-gp transport, chelation, precipitation, shared toxic
constituents, additive cardiotoxicity), and attach the cheap assay that would confirm or kill it.
**Completeness is the contribution** — a count without a denominator is an anecdote. [[PENDING: rules.eighteen_fan]]
of 18 and [[PENDING: rules.nineteen_wei]] of 19 pairs are enumerated, bridged and assay-annotated.

**4. It compiles process language into a chemistry operator.** Classical pharmacy does not only say *what* to use;
it says *how to prepare it* — 炮, 煅, 煨, 淬, 蒸, 炒, 醋炙, 蜜炙, 酒炙, 發酵, 水飛, 昇/飛/伏; on the Indian side
*śodhana*, *māraṇa*, *bhasma*. That vocabulary is an instruction set for physical chemistry that modern NLP treats
as noise. We compile it into an explicit operator table — each term mapped to hydrolysis, decarboxylation,
oxidation, volatilisation, esterification, complexation, salt formation or thermal decomposition — and use it
generatively: for a given drug, predict which constituents a preparation destroys, enriches or conjugates.
We also report the split we are least sure about: which steps are **load-bearing** (附子: 炮制 hydrolyses diester
diterpene alkaloids to far less toxic monoesters — omit the step and you have a poison, not a medicine) and which
are **plausibly ritual**. The artemisinin story — 葛洪's 絞取汁 is a cold maceration because artemisinin is
thermolabile — is one anecdote. The operator is the generalisation.

**5. It reads the untranslated originals, and it refuses.** The model is trained on Classical Chinese (繁體 and
简体), Sanskrit (Devanagari and IAST), Arabic and Persian, Tibetan, Japanese and Korean in public-domain editions,
alongside a first-principles substrate of anatomy, physiology, biochemistry, pharmacology, toxicology and
natural-product chemistry. The bilingual vocabulary budget is not decoration: it is what keeps the encoded layer
alive through tokenisation. On top sits a graph with span-level provenance and a question-answering surface that
answers only from retrieved spans, with a citation on every sentence, and **refuses when coverage is weak** rather
than generating something plausible. It also refuses — by policy, not by inability — questions asking for dosing,
self-treatment, or the preparation of toxic substances. Asian materia medica genuinely contains mercury, arsenic
and lead drugs (丹, 輕粉, 雄黃, *bhasma*). They are in our corpus as **data to analyse**; they are never in our
output as advice.

### Two rules we hold ourselves to

> **Every hypothesis carries its own kill-criteria — and a hypothesis whose citation span fails to resolve is
> dropped, not softened.** (This is enforced in the product: the Workbench verifies that each quoted classical
> span actually names the drug it is attributed to, strikes through and flags any that do not, and counts the
> failures on its summary panel. It caught eight of our own before we shipped.)

> **We publish the negative results, including two pre-registered controls that could have embarrassed the entire
> framework.** 取象比類 — reasoning by resemblance, a foundational TCM principle — is treated as a hypothesis, not
> an assumption, and sits at the bottom of our ranked list where it belongs.

### The four operations

The pipeline is named for the operations of Chinese pharmacy, and every stage is one command:

| Stage | | What happens | Artefact |
|---|---|---|---|
| 采 **Cǎi** | collect | licence-audited acquisition, normalisation (繁/简, IAST↔Devanagari), 13-gram dedupe, entity extraction | `corpus.jsonl`, `sources.yaml` |
| 制 **Zhì** | prepare | drug-name resolution across eras and scripts → modern taxa; process vocabulary → the chemistry operator | `lexicon_drugs.json`, `processing.csv` |
| 配 **Pèi** | combine | knowledge graph: taxon ↔ compound ↔ target ↔ indication, formula composition with 君臣佐使 roles, 十八反 / 十九畏 / *viruddha* edges | `kg.json`, `properties.csv` |
| 使 **Shǐ** | deploy | ranking, falsification plans, uncertainty, **drug candidates**, and the theory-predictivity experiment | `drug_candidates.json`, `eval/report.json` |

---

## The candidate screen

The Workbench is a local-first research cockpit: `python app/serve.py`, standard library only, no build step, no
network, keyboard-navigable, ~90 KB of HTML/CSS/JS in total.

The screen we would put in front of a judge first is **Candidates**. Each row is a classical lead turned into a
molecule:

- the **classical line** it descends from, quoted in the original script with a translation and a locator
  (*神農本草經*, 下品 · 大黃);
- the **theory vector** that justifies it — for 大黄: 寒 · 苦 · 歸脾/胃/大腸 · 降 · 下品;
- the **molecule**: molecular formula, and molecular weight **computed from that formula** by arithmetic rather
  than estimated;
- **computed drug-likeness** where it can be computed, and an explicit "pending structure resolution" where it
  cannot — one of four Lipinski rules evaluated is reported as one of four, not rounded up to "Lipinski-compliant";
- the **mechanism** and the pathway;
- the **development path**: which assay, which model, what would make it a real lead;
- the **residual risk** and any safety flag.

Three further panels support it: a **hypothesis explorer** across six discovery classes (配伍禁忌, 炮制,
异名同物, 君臣佐使, 未研究本草, 濒危代用品) with a falsification plan on every dossier; a **knowledge-graph
explorer** over the assembled KG; and a **corpus provenance** panel where every source carries its licence,
tier, tradition and language, and where anything whose licence is not verifiable is marked `UNVERIFIED` and
excluded from training.

The Workbench states, on every panel, whether the data behind it is a real artefact or a demo fixture. That
sounds like a small thing. It is the reason we trust the rest of the screens.

---

## How we built it

**Derivation before collection.** We did not start from a dataset dump. We wrote down the axioms of
ethnopharmacology and Asian pharmacology, derived what data classes those axioms logically require, and only
then went sourcing. The source registry is therefore a *proof obligation*: every tier exists because an axiom
demanded it, and every entry carries title, author, date, URL, licence, licence evidence, tier, tradition and
language.

**Corpus and licences.** The public-domain reality of this domain is unforgiving: many modern English
translations of Asian classics are still in copyright. The routes that work are zh.wikisource and ctext for
Chinese originals, Sanskrit Documents and GRETIL for Sanskrit, and archive.org for nineteenth- and
early-twentieth-century translations. Everything is audited. One GRETIL *rasaśāstra* source carried a
**CC BY-NC-SA** licence; the NonCommercial clause is incompatible with a public, Apache-2.0 repository, so we
**rejected it**, excluded it from training, and recorded the rejection in the licence audit
(`LICENSE_AUDIT.md`; the machine-readable evidence is the `licence` and `licence_evidence` fields of every
entry in `corpus/registry/sources.yaml`). That is a more
useful statement than "our licences are clean".

The corpus currently holds **[[PENDING: corpus.sources_ok]]** sources and **[[PENDING: corpus.chars]]**
characters across **[[PENDING: corpus.traditions]]** traditions and
**[[PENDING: corpus.languages]]** languages; **[[PENDING: corpus.excluded]]** sources were excluded. Trained
text is **[[PENDING: corpus.licence_dom]]** and **[[PENDING: corpus.licence_ccby]]** — no NonCommercial
material is used.

**The model.** `shennong-mini` is a Llama-style transformer trained from scratch on this machine — an Intel
i7-4790K with **no GPU** — in PyTorch 2.2.2 on CPU. It has **8,719,616 parameters** (4,525,312 of them
non-embedding) with a 16,384-token vocabulary, `d_model` 256, 6 layers, 4 heads (1 KV head), `d_ff` 768 and a
512-token context. Round `shennong-mini-r1` is **900 steps × 8,192 tokens = 7.37 M tokens seen**, against a
training split of 16.7 M available tokens across 23,652 documents. The loss curve in the Workbench is the logged
curve from `training/runs/<id>/metrics.json` — not a render, and not an illustration.

**And we will say the uncomfortable part plainly:** at roughly **0.85 tokens per parameter**, this round is
*deliberately undertrained*. It is a real run with real logs on a CPU-only machine inside a hackathon week, not a
converged model — and the model card says so in those words. We report it this way because a project whose entire
credibility rests on not flattering its own results cannot start by flattering its own loss curve. The flagship
`shennong-0.5b` is a fully executable recipe plus a quantisation path; where we quote a number for it we label it
a recipe number in the same sentence.

**The discovery engine.** Drug-name resolution is the hard part and the load-bearing part: 異名同物 and
同名異物 mean one name can denote different plants in different centuries and dialects, which is a documented
public-health problem rather than a curiosity. The 2003 Chinese ban on 關木通 (*Aristolochia manshuriensis*)
as a substitute for 木通 followed exactly this failure mode: the classical text already warns that the two look
alike and behave differently, in a marginal note. We build the collision graph explicitly, rank colliding taxa
by toxicity divergence, and surface the ranking.

**Evaluation.** The theory-predictivity experiment is the scientific centre of the project, so it is reported
with the same apparatus a reviewer would demand: effect size, n, p, and a permutation null in which the theory
vectors are shuffled across drugs. A **null model** that shuffles plant↔use edges is retained to confirm that
discovery scores collapse when structure is destroyed — if they do not, the scoring is measuring the pipeline
rather than the biology.

---

## Challenges

**The vocabulary problem is the domain problem.** Classical Chinese drug names are ambiguous at the character
level, Sanskrit transliterations into Chinese are systematic but lossy, and Arabic materia medica inherits Greek
and Indian names on top. A tokeniser that treats a name as one token loses the ability to generalise; one that
treats it as characters loses the ability to disambiguate. Budgeting vocabulary for CJK and Devanagari while
staying under a 1 GB file was a genuine design constraint, not a tuning exercise.

**CPU-only means choosing what to be honest about.** We had no GPU. That decision was made for us, and it forced
an editorial discipline we would keep anyway: the from-scratch mini model is really trained and really logged;
the flagship is a recipe unless a run exists; and a number is labelled a recipe number in the sentence that
quotes it.

**Encoding theory as a testable feature without flattening it.** "Cold, bitter, enters the Liver channel" is
rich. Turning it into a vector that a permutation test can evaluate requires committing to a mapping, and every
mapping is arguable. We published ours (`docs/METHODOLOGY.md`), including where we expect it to fail — the
commentarial tradition disagrees between editions about channel assignments, and we inherited those
disagreements rather than resolving them.

**Our own interface caught a bug we would otherwise have shipped.** Every candidate carries a quoted classical
span. The Workbench verifies that the span actually mentions the drug it is attributed to. When the real artefact
arrived, **all ten** spans failed that check — the locators pointed at the wrong character offsets, so a candidate
derived from 大黄 was quoting the entry for 甘草. The interface refused to present them as evidence: it struck the
quotes through, labelled them `provenance: unmatched`, and put a count of provenance failures on the summary
panel. We could have hidden that. Attribution that cannot be checked is worse than no attribution, so the failure
is visible in the product rather than in a bug tracker.
**Not inventing the boring things.** Structure data is the temptation. It is trivially easy to hand a plausible
SMILES to a model and have a table look complete. We left unresolved structures null and rendered them as
"pending". The table is less complete and much more useful.

**Safety is a design constraint, not a disclaimer.** Building a system whose corpus contains aconite, mercury
and arsenic forced concrete engineering: a dual-use screen in front of the Ask surface, a hard rule that no
preparation or dosing guidance is ever emitted, and a distinction the output has to make in the text — between
**analysing** a toxic preparation and **prescribing** one.

---

## Accomplishments

- A **complete pipeline** from licence-audited Asian originals to ranked drug candidates, reproducible with one
  command per stage, **[[PENDING: corpus.n_stages_commands]]** commands from a clean clone on CPU.
- **[[PENDING: candidates.count]]** drug candidates, each with a classical line, a theory justification, a
  mechanism, a development path and a falsification-adjacent assay, of which
  **[[PENDING: candidates.resolved]]** have fully resolved structures and computed molecular descriptors.
- **[[PENDING: eval.theory_positive_count]]** of **[[PENDING: eval.theory_n_tests]]** theory-predictivity tests
  reach significance against a permutation null, including **[[PENDING: eval.headline_test]]** — the honest
  number, including the tests that came back null.
- **[[PENDING: hypotheses.count]]** ranked, provenance-cited, falsifiable hypotheses across all six discovery
  classes, including the 取象比類 control that is published at the bottom of the list where it belongs.
- **[[PENDING: rules.eighteen_fan]]/18** 十八反 and **[[PENDING: rules.nineteen_wei]]/19** 十九畏 pairs enumerated
  with textual citations, bridged to a modern mechanism and annotated with an assay — a closed, checkable
  interaction hypothesis set rather than a list of anecdotes.
- The licence audit itself: **[[PENDING: corpus.sources_ok]]** sources accepted, **[[PENDING: corpus.excluded]]**
  rejected and documented, zero sources with an unclear licence entering training.
- A workbench that runs on any machine with Python and no network: **98 KB of HTML/CSS/JS**,
  zero dependencies, keyboard-navigable, honest about which panels are fixture and which are measured.

---

## What we learned

**The negative result is the product.** We expected the nature/flavour vectors to be weakly predictive at best.
Reporting that with a permutation null and an effect size is more valuable — to this field, and to a judge — than
another leaderboard-shaped claim. A system that can be wrong in public is the only kind worth building on this
corpus.

**Preparation instructions are the compressed knowledge.** The processing vocabulary (炮, 煅, 淬, 九蒸九曬,
*putrefaction*, *bhasma*) is where the corpus is most specific and least translated. "Roast until it splits,
peel it, cut it hot, then boil it in honey water" is a hydrolysis protocol with an endpoint, written fifteen
centuries before anybody described ester hydrolysis. That is the encoded layer we were looking for, and it
turned out to be in the verb, not in the noun.

**Name collisions are the most immediately useful output.** Nothing in this project helps a patient faster than
a ranked list saying: these two taxa share a name, they are not interchangeable, and the difference is
carcinogenic.

**Ethics is architecture.** The refusal paths, the dual-use screen, the UNVERIFIED licence status and the
`research use only` banner are not features bolted on at the end. They are the reason the output is usable by a
researcher rather than dangerous to a reader.

---

## What's next

1. **Wet-lab validation of the top candidates**, starting with the cheapest falsification: the processed-versus-raw
   comparison for 附子, where the mechanism is known and the experiment is a single LC-MS method.
2. **Extend the corpus** to the remaining science and agricultural texts (農政全書, 廣群芳譜, 救荒本草's full
   plant list) and to the Tibetan and Southeast Asian material where openly licensed editions can be found.
3. **Widen the theory test** from univariate predictivity to a held-out benchmark: fit on 本草綱目 and predict a
   held-out class of drugs recorded only in the Ayurvedic or Unani material. Cross-tradition prediction is the
   strongest possible evidence that the framework generalises.
4. **Practitioner review** of the dossiers, with attribution and a benefit-sharing arrangement agreed before any
   wet-lab collaboration. We are not willing to mine this material and walk away.
5. **Continuous, eval-gated improvement**: the loop only accepts a new model if it improves the published
   benchmark table, and the gate is in code (`docs/CONTINUOUS_LEARNING.md`).

---

## Built with

Python 3.12 · PyTorch 2.2.2 (CPU) · HuggingFace `tokenizers` · numpy · PyYAML · pytest · matplotlib · the
`http.server` standard library and hand-written vanilla JavaScript, HTML and CSS (no framework, no build step,
no CDN) · hand-authored SVG for every figure. Corpus sources are public-domain editions from zh.wikisource,
Sanskrit Documents, GRETIL and archive.org, plus open structured data from ChEMBL, PubChem, Dr Duke's
Phytochemical and Ethnobotanical Databases, and POWO/WCVP.

---

## Links

- **Repository:** https://github.com/cptlight/shennong
- **Model weights:** in this repository's **Releases** (GGUF, Apache-2.0, no gate)
- **Workbench:** `python app/serve.py` — local, offline, standard library only
- **Replicate everything:** `make setup && make corpus && make tokenizer && make train-mini && make eval &&
  make app-data && make workbench`

---

## Safety, ethics and Traditional Knowledge

**Medical safety.** SHENNONG is a research instrument. It provides no diagnosis, no dosing, no self-treatment
guidance and no preparation methods for use, and it actively refuses such questions. Every panel carries a
`research use only — not medical advice` statement. No synthesis or preparation route for any toxin or pathogen
appears anywhere in the codebase, documentation or output; the dual-use screen is a hard gate in front of the
generative surface, not a filter applied afterwards.

**Handling toxic materia medica honestly.** The Asian canon includes mercury, arsenic and lead drugs, and
pretending otherwise would be bad history and worse science. They enter the corpus as **toxicology data** and
they appear in the output only as hazard analyses and ranked risk profiles. Where a hypothesis concerns a toxic
drug, the safety annotation is rendered on every view of it — it cannot be collapsed or hidden.

**Traditional Knowledge.** Classical Asian texts are **living heritage**, not a free ore body. Our position, in
short and in full in `docs/SAFETY_AND_ETHICS.md`:

- **Attribution** to the tradition, the text, the edition and where possible the named author is preserved in
  the data model, not just in prose. A candidate that cannot be traced back to its line of text is not emitted.
- **Benefit-sharing** on the Nagoya Protocol model: any downstream development is expected to include
  source-country and practitioner-community participation and agreement, arranged *before* commercial
  exploitation rather than after.
- **Non-extractive framing.** We publish the method, the corpus audit and the derived candidates openly, and we
  publish the *negative* results too. The goal is to leave the field with more than we took from it.
- **An opt-out mechanism.** A tradition or community that does not want a text used can withdraw it; the registry
  records status and the corpus build honours it.
- **Conservation is a direct output**, not a gesture. Text-attested substitutes for CITES-listed materials
  (犀角 → 水牛角, 穿山甲 → 豬蹄甲) are ranked by how load-bearing the ingredient is in the formula it appears in
  — a conservation priority list built from text that costs no animals to produce.

**Licensing.** Code and model weights are **Apache-2.0**. Corpus data retains its per-source licence with a
**CC BY-SA share-alike obligation** on the derived corpus; nothing restricted is redistributed, and
NonCommercial source material is rejected and documented rather than quietly included.
