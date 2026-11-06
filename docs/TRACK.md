# TRACK — the one choice, and why

**Declared track: 02 — Natural products and drug discovery.**

The four tracks are not equally served by this project. This document records the choice, the evidence that
justifies it, and — deliberately — what we give up by making it.

---

## The decision matrix

| track | what it asks for | what we actually have | fit |
|---|---|---|---|
| 01 · Traditional knowledge | NLP/AI to extract medicinal knowledge from historical texts; map plant names across eras; connect ancient knowledge to modern pharmacology | 106 sources / 45.6 M characters; entity resolution; the pre-registered 歸經 result (**2× chance, p = 0.008**, n = 2,059) | **strong secondary** |
| **02 · Natural products & drug discovery** | ML/cheminformatics to find plant-derived compounds for disease targets; **predictive models, knowledge graphs, and screening pipelines** | a **screening pipeline**: 203 hypotheses → 151 excluded → 28 pass both gates → 10 refuted by validated physics → **18 survive**; 60 candidates with SMILES, computed properties, target class and kill criteria; a physics arbiter (Joback 4.5 %, QM 0.82 eV) | **primary** |
| 03 · Biodiversity & sustainability | geospatial/ecological data; conservation risk; sustainable harvesting | conservation substitution ranked by formula load-bearingness (犀角 → 水牛角, 穿山甲 → 豬蹄甲) | **thin** — one artefact, no geospatial data |
| 04 · Digital health & phytotherapy | apps, decision support, recommendation engines for clinical/patient contexts | the Workbench (offline, CPU-only) + refusal policy + safety gate | **thin** — no clinical validation, no patient-facing claim |

### Why 02 wins

1. **The strongest results are drug-discovery statements.** "78 of 203 candidate preparations fail a physics
   check; of the 28 that clear both tradition gates, 10 are refuted; 18 survive" is a statement about
   compound viability under real preparation conditions. That is a screening result.
2. **The track text names exactly what we built** — "predictive models, knowledge graphs, and screening
   pipelines" — and the physics arbiter is the part that is genuinely hard to copy.
3. **Impact (40 % of the rubric) is largest here.** Excluding 151 unattested candidates and refuting 78
   enrichment claims is a measurable reduction in experimental search space; the biodiversity and digital
   health angles are real but unquantified in this repo.

### What we give up, stated plainly

- **Track 01 would score well on our corpus work** — the 歸經 experiment is a traditional-knowledge result and
  it is our most rigorous single finding. Choosing 02 means it becomes **supporting evidence** ("the tradition
  predicts chemistry, and here is where it fails"), not the headline. We accept that.
- **No geospatial, no biodiversity modelling** — Track 03 is out on the evidence.
- **No clinical or patient-facing claim** — Track 04 is out on ethics and evidence; the Workbench is a
  research tool, and the refusal policy exists precisely because clinical advice is out of scope.

---

## What the choice changes in the project

| area | change |
|---|---|
| Devpost | **Declared track: 02** at the top, with 01 and 04 named as depth |
| deck | slide 1 is the pre-experimental filter; slide 2 the arbiter; slide 3 the theory result as *support* |
| video | opens on the processing instruction, lands on the funnel and the refutation |
| model | fine-tuned on **Track-02 tasks**: preparation viability, candidate cards, incompatibility rules, hypothesis posture — see `training/finetune.py` |
| demo | the Ask console poses Track-02 questions; the Hypothesise tab is a *screening* posture, not a chat |

---

## The one-sentence version

> We are not building a chatbot that knows about herbs. We are building a **pre-experimental filter** for
> natural-product discovery: it takes a classical processing instruction, compiles it into a chemical
> hypothesis, and uses validated physics to tell you whether the hypothesis can survive the preparation —
> before anyone buys a reagent.

---

## The Track-02 fine-tune — measured

```bash
python scripts/build_sft_dataset.py     # 1,490 task examples from the project's own artefacts
python training/finetune.py --steps 250 # answer-only loss, prompt masked
```

| | |
|---|---|
| examples | 1,490 (1,400 train / 90 val) |
| tasks | property 1,357 · viability 60 · candidate 60 · incompatibility 13 |
| format | `<\|user\|>…<\|assistant\|>…<\|eos\|>` — the tokenizer's own chat tokens |
| objective | next-token, **prompt masked** (answer-only loss) |
| base val loss | **7.8974** |
| fine-tuned | **2.6136** at step 100 (**−5.28 nats**) |

**Two bugs were found and fixed before this number meant anything**, and both are worth recording because
each produced a *better-looking* result than the truth:

1. `token_to_id("</s>")` returns `None`; `or 0` turned it into `<|pad|>`, so every answer was trained to end
   in a pad token and generation collapsed to commas.
2. The trainer compared `logits[t]` with `labels[t]` instead of `labels[t+1]`. The model learned to **copy its
   input token**, scoring 0.07 CE while being unable to generate a single word.

### What the fine-tune actually bought

**Learned:** the Track-02 answer *shape* — the model now emits
`Nature 寒, flavours 甘, channels not recorded, toxicity 無毒, grade …` instead of `,,, and the the the`.

**Not learned:** the values. Given an unseen herb it produces a plausible structure with wrong entries, and on
long passage-conditioned prompts (the demo's retrieval path) it is **no better than the base model** — so the
demo keeps the base checkpoint and the fine-tuned one is the task interface.

That is the honest line: **this is format learning, not domain knowledge.** It makes the model usable as a
Track-02 interface; it does not make it an expert. Recorded in `artifacts/sft_result.json`.
