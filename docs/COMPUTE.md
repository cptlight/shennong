# COMPUTE — the architecture thesis, measured

This project is **not** trying to out-write a frontier model. That comparison is lost before it starts, and
pretending otherwise would be the fastest way to fail a technical review.

What it does claim is narrower, measurable, and — for this domain — the more useful thing:

> **A sparse MoE buys total capacity without paying per-token compute. On hardware people already own, that
> decides how much domain knowledge a model can hold, and therefore whether it can run where the work
> actually happens.**

A rural clinic, a field researcher in Yunnan, a museum's collection server, a laptop in an archive with no
network: none of them can host a frontier model. A 38.7 MB model that runs on a CPU in ~1.6 s can.

---

## 1 · The measurement

Both models trained at **identical token budget (1,638,400 tokens)** on the same 2015 iMac, CPU only.

| | dense | **sparse MoE** | ratio |
|---|---|---|---|
| Total parameters (capacity) | 8,719,616 | **19,342,616** | **2.22×** |
| Active parameters per token | 8,719,616 | 12,264,728 | 1.41× |
| Forward FLOPs / token (2·active) | 17.4 M | 24.5 M | 1.41× |
| **Capacity per FLOP** | 0.50 params/FLOP | **0.79 params/FLOP** | **1.58×** |
| Held-out val loss | 6.3901 | **5.4828** | **−0.907 nats** |
| Weights, fp16 | 17.4 MB | **38.7 MB** | 2.22× |
| Architecture | 6L · d256 · FFN 768 | 6L · d256 · 4 experts, top-2 | |

**The number the claim rests on is 1.58×**: for every unit of per-token compute, the MoE holds 58 % more
parameters. The FFN is where knowledge lives; routing means four specialists cover Classical Chinese, Latin,
Sanskrit and English pharmaceutical text without every token paying for all four.

### The confound, stated rather than buried

The MoE run used **2 torch threads**; the dense run used **1**. The observed throughput difference
(769 vs 604 tok/s) could be entirely the second thread, so:

- **throughput and wall-clock are *suggestive, not causal*, and no claim rests on them**;
- the capacity-per-FLOP ratio and the val-loss delta do **not** depend on thread count — they are
  structural properties of the architecture;
- repeating at matched threads is on the list, and until it is done the throughput row stays labelled.

### The other confound

200 steps × 8,192 tokens is **≈0.9 % of compute-optimal** for either model size. This is a valid
**architecture ablation** (same tokens, same data, same seed) and a useless capability benchmark. Nothing
here says what these models know; it says what the architecture buys at fixed compute.

---

## 2 · Why CPU-first is the right constraint for *this* domain

The domain is classical Asian medicine: 106 sources, 45.6 M characters, distributed across Chinese,
Sanskrit, Latin and English, with strict per-source licensing. Three consequences:

1. **The data cannot be shipped to an API.** Several sources are CC BY-SA (share-alike) and the rest carry
   provenance obligations. Running the model locally is the only way to honour them.
2. **The users are not at a GPU.** Herbarium staff, university departments in the regions the corpus comes
   from, and independent researchers are the intended operators.
3. **Latency is not the bottleneck; provenance is.** A 1.6 s answer with a `source_id:char_start-char_end`
   is worth more than a 0.3 s answer with none.

So the architecture optimises for **capacity at a fixed deployable footprint**, not for throughput at a
fixed GPU count. That is a different objective function from a frontier lab's, and it is why a MoE is the
right shape: capacity scales with *total* parameters, cost scales with *active* ones.

---

## 3 · How the expertise is meant to grow without a GPU

Three levers, in increasing order of what they buy:

| lever | what it adds | cost | status |
|---|---|---|---|
| **retrieval** | all 45.6 M characters, exactly citable | ~0 — BM25 over the corpus | **shipped** |
| **experts** | new modalities (molecular mechanics, quantum chemistry, taxonomy, ADMET) | modular, each independently testable | **shipped** — 12, routed |
| **parameters** | fluency, generalisation, better phrasing | GPU training | the 19.3 M model is the demo, `make train-flagship` is the path |

The first two are already doing the work the pitch relies on: the physics arbiter refuted **78 of 203**
enrichment claims — that is, **78 of 203 fail a physics check somewhere** in the funnel, and **of the 28**
that clear both tradition gates **10** are refuted — and retrieval puts a checkable span behind every answer. The third is where the current
model is weak, and it is a training-budget problem, not an architecture problem.

**The modularity is the point.** Because experts are additive — a new expert is a module plus a routing
rule, documented in `README.md` — the domain expertise can grow with the corpus without retraining
everything. That is what "use the available compute to our advantage" means concretely: you add a
specialist, not a data centre.

---

## 4 · What this does and does not claim

**Claims, each backed by an artefact:**

- 1.58× capacity per FLOP at matched training compute (`artifacts/compute_budget.json`)
- −0.907 nats held-out loss at identical token budget, single seed
- 38.7 MB fp16, runs CPU-only, no GPU, no network (`make workbench`)
- the router recovered script structure without supervision — Jensen–Shannon distance **0.709** between
  Latin and Classical Chinese routing (`artifacts/moe_diagnostics.json`)
- 78 of 203 enrichment claims refuted by validated physics, 6 despite unanimous 5/5 panel agreement

**Does not claim:**

- that this model writes better than a frontier model — it does not, and the live demo shows the bare
  completion next to the grounded one for exactly that reason;
- that 0.91 nats transfers to a larger scale — one endpoint, one seed;
- that CPU inference substitutes for GPU *training* — training still wants a GPU; **serving** does not;
- that a 19.3 M model is a domain expert today. It is the architecture demonstration; the expertise lives
  in retrieval, the structured chemistry, and the physics arbiter until the parameter budget is raised.

---

## 5 · What "better than a frontier model for this subject" can honestly mean

There are two tasks, and the answer differs:

| task | who wins | why |
|---|---|---|
| **Write a fluent summary of 附子的 processing** | frontier model | more parameters, better prose — no contest |
| **Return the exact recorded line, its source, character offsets, and whether the claimed preparation is physically possible** | **this system** | a frontier model does not have this corpus, cannot cite spans it lacks, and has no deterministic physics layer to say *no* |

The second task is the one this project is for. It is also falsifiable: the judge can open the passage at
`source_id:char_start-char_end` and check.

So the honest pitch is not *"our model is smarter"*. It is: **for corpus-locked, provenance-bearing,
first-principles-arbitrated questions in classical Asian medicine, this stack returns things a frontier
model structurally cannot — and it does it on a laptop, offline, in 38.7 MB.**

---

See also: [`DIAGNOSTICS.md`](DIAGNOSTICS.md) · [`EXPERTS.md`](EXPERTS.md) · [`../model/MODEL_CARD.md`](../model/MODEL_CARD.md)
