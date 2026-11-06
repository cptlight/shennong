# Test it — query the model, then check the numbers

## 0 · Live, hosted (no install)

The demo runs as a Hugging Face Space: **the page below with the model actually behind it**.

| | |
|---|---|
| **Hosted demo** | `https://huggingface.co/spaces/<your-org>/shennong` — deploy with `./scripts/deploy_space.sh <your-org>/shennong` (needs `HF_TOKEN`) |
| **Ask it live** | free-form question → BM25 over 45.6 M characters → the 19.3 M MoE generates over the retrieved passages → citations with `source_id:char_start-char_end` |
| **Propose a hypothesis** | the model proposes one falsifiable hypothesis over retrieved evidence, with **kill criteria** attached, labelled UNVALIDATED |

The Space clones this repository at build time, so a push to `main` is what updates it — there is no second
copy to drift.

---

The point of this project is not a page of claims. It is a **live pipeline** you can question. Here is how,
in order of how little setup it costs you.

---

## 1 · Query the 19.3 M model, live (one click, free Codespace)

A static page cannot run inference — there is no server and no browser-WASM build, and pretending otherwise
would be exactly the kind of demo that falls over in front of a judge. So the query path runs the real model
on a real CPU:

1. Open the repo in a Codespace → **Code ▸ Codespaces ▸ Create codespace on main**
2. In the terminal: `make workbench`
3. Open the forwarded port, then append **`/demo/`** — the page detects the live endpoint and enables the ask box

**Or entirely local** (the model is 47 MB, so this works on a laptop):

```bash
git clone https://github.com/cptlight/shennong && cd shennong
make setup && make workbench      # → http://127.0.0.1:8765/demo/
```

Every request runs **one code path** — no keyword dispatch, no table lookup, no canned answer:

```
question ──▶ bare model completion            (shown, because it is weak and hiding it would be rigging)
         ──▶ BM25 retrieves 5 passages        (45.6 M characters, 106 sources)
         ──▶ model continues over those 5      (the grounded completion)
         ──▶ passages returned as citations    (source id + character offsets)
```

Measured on this machine, CPU only: **first click after boot ≈ 4 s** (retrieve + generate), later ≈ 2.7 s.
The retrieved passages are the domain knowledge; the model is what sits on top of it.

**Safety is one narrow check:** dosing instructions, self-treatment, and synthesis/manufacture of toxins or
pathogens are refused. Everything else is answered — including questions whose answer is "the corpus does
not record this", which it says rather than inventing.

---

## 2 · Browse the evidence (no install at all)

**https://cptlight.github.io/shennong/** — a static page that reads `artifacts/*.json`. It cannot run the
model (see above), but every figure in it is generated from the repo, so it cannot show a number the
repository does not contain:

| tab | what to check |
|---|---|
| The funnel | 203 → 151 → 24 → 28 → 10 → 18, with the middle step included so the arithmetic closes |
| The arbiter | modelled retention per prepared candidate; Joback 4.5 % validation; QM 0.82 eV |
| Does theory predict? | 歸經 7.48 % vs 3.80 %, n = 2,059, p = 0.008, three nulls beside it |
| Candidates | 60 candidates with SMILES, structural novelty + nearest known compound, verified span, kill criteria |
| Experts | each expert's AUC against the arbiter, including the one we found was anti-predictive |
| Weights | both releases, sizes, sha256, per-component licence |

---

## 3 · Weights, directly (open, Apache-2.0, no gate)

| release | file | size | sha256 |
|---|---|---|---|
| [v0.1.0](https://github.com/cptlight/shennong/releases/tag/v0.1.0) | `shennong-mini-f16.gguf` | 18,054,560 B | `a67ad442…4cdb60` |
| [v0.2.0](https://github.com/cptlight/shennong/releases/tag/v0.2.0) | `model.safetensors` (19.3 M / 12.3 M active) | 47,086,544 B | `645374b4…` |

```bash
llama-cli -m shennong-mini-f16.gguf -p "附子必須先炮製，因為" -n 80
```

---

## What is genuinely strong, and what is not

**Strong, and checkable:** the retrieval over 45.6 M characters of classical Asian medicine with span-level
locators; the validated physics arbiter (Joback 4.5 % mean error, QM 0.82 eV) that refuted 78 of 203
enrichment claims; the pre-registered theory result; the 60 candidates with kill criteria; the self-diagnostic
that caught our own broken expert.

**Not strong, and stated in `model/MODEL_CARD.md`:** the model's *prose*. It is 8.7 M–19.3 M parameters
trained on ~1.6 M tokens (≈0.9 % of compute-optimal). It reads the register; it does not write reliable
sentences, and the demo shows the bare completion next to the grounded one precisely so you can see that.
The expertise is in the pipeline — retrieval, structured chemistry, and the physics arbiter — not in the
weights, and claiming otherwise would be the rigging this project is trying to avoid.

## Run the comparison yourself

```bash
python scripts/compare_models.py --with-remote     # needs your own OPENAI_API_KEY
```
Eight domain questions, the same code path for all, and the frontier column filled in with **your** key —
we ship no keys and no pre-recorded frontier answers.

## What it is not

No dosing. No preparation protocols for toxic materia medica. No synthesis routes. Not medical advice. The
output is a **filter**: 18 preparations worth an assay, each with the experiment that would kill it.
