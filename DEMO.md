# Test it yourself — three ways, no gate

Everything below is **open source and open weights (Apache-2.0)**. There is no login, no API key, no GPU
requirement, and no network requirement once cloned.

---

## 1 · In a browser, right now

**https://cptlight.github.io/shennong/**

A self-contained static page (no Python, no server, no CDN). Seven tabs:

| tab | what you can check |
|---|---|
| The funnel | 203 → 151 → 24 → 28 → 10 → 18, and the law-impact table |
| The arbiter | the modelled retention for each prepared candidate, with the Joback validation and the QM layer |
| Does theory predict? | 歸經 ≈2× chance at **p = 0.008**, n = 2,059, with the three nulls beside it |
| Candidates | 60 candidates: SMILES, computed properties, **structural novelty**, verified span, kill criteria |
| Experts | each expert's AUC against the arbiter — including the one that was anti-predictive |
| Diagnostics | what the system says about itself |
| Weights | files, sizes, sha256, and the licence of every component |

**This page cannot show a number the repository does not contain** — it is generated from `artifacts/*.json`
by `scripts/build_demo.py`, and the build fails if a placeholder or an external CDN reference sneaks in.

---

## 2 · Locally, offline, CPU-only

```bash
git clone https://github.com/cptlight/shennong && cd shennong
make setup                     # CPU venv: torch 2.2.2, numpy<2, tokenizers, pytest…
make workbench                 # http://127.0.0.1:8000 — the interactive Workbench
make test                      # test suite
python scripts/verify_contracts.py    # enforces: <1 GB weights, ≤1 B params, no placeholders,
                                      # novelty non-degenerate, licence audit, domain mix
```

The Workbench is **stdlib-only** — no build step, no network, no CDN. It reads the same artefacts the
demo page does, plus live pipeline state.

---

## 3 · The weights, directly

| release | what | how |
|---|---|---|
| [v0.1.0](https://github.com/cptlight/shennong/releases/tag/v0.1.0) | `shennong-mini-f16.gguf` — **18,054,560 B** dense model, sha256 `a67ad442…4cdb60` | `llama-cli -m shennong-mini-f16.gguf -p "附子必須先炮製，因為" -n 80` |
| [v0.2.0](https://github.com/cptlight/shennong/releases/tag/v0.2.0) | `model.safetensors` — **47,086,544 B** sparse MoE (19.3 M total / 12.3 M active) | load with `model/shennong_moe.py` |

Every file has a **sha256** you can check, and `artifacts/tokenizer_parity.json` proves the GGUF tokenizer
is token-identical to the one the model was trained with (240/240 held-out chunks).

**What the mini model is, stated plainly in `model/MODEL_CARD.md`:** 8.72 M parameters trained on 1.64 M
tokens (≈0.9 % of compute-optimal). Bits-per-byte **2.526** against a unigram baseline of **3.076** — it beats
the "did it learn anything beyond token frequency" test — but it is a **pipeline demonstration, not a factual
oracle**, and it is not for clinical use.

---

## What to look for if you have five minutes

1. **The funnel closes arithmetically** — 203 − 151 − 24 = 28, then 28 − 10 = 18. Nothing is skipped.
2. **The funnel is invariant** — adding five experts moved zero counts.
3. **One expert is flagged anti-predictive** — we found it, fixed it, and retracted the finding.
4. **Every candidate has a verified span and a kill criterion.** No claim is emitted without both.
5. **The weak link is disclosed** — drug→taxon resolution is 14.1 %, and it bounds everything downstream.

## What it is not

Not medical advice. Not a dosing or preparation guide. Not a claim of drug discovery — the output is a
**filter**: 18 preparations worth an assay, each with the experiment that would kill it.
