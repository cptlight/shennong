# SHENNONG — release notes

## What is in this release

**`shennong-mini` — an 8.7 M parameter classical-Asian-medicine language model, trained from scratch on
CPU, released as open weights under Apache-2.0.**

| | |
|---|---|
| Parameters | 8,719,616 (4,525,312 non-embedding) |
| Architecture | Llama-style decoder: RMSNorm, RoPE, SwiGLU, GQA, tied embeddings |
| Config | d_model 256 · 6 layers · 4 heads / 1 KV head · d_ff 768 · context 512 · vocab 16,384 |
| Training | from scratch, single CPU core, on a licence-audited Asian-medicine + foundational-science corpus |
| Tokenizer | byte-level BPE over Classical Chinese (zh-Hant), Latin, English; en 3.6 / la 2.2 / zh-Hant 1.3 chars/token |
| Weights | `shennong-mini-f16.gguf` — f16 GGUF, < 1 GB by three orders of magnitude |
| Licence | Apache-2.0 (weights and code) |

**This is a deliberately small, deliberately undertrained model.** It is a demonstration that the whole
pipeline — corpus → tokenizer → from-scratch training → GGUF → discovery engine — runs reproducibly on
a laptop CPU with no GPU. It is **not** a factual oracle, and it is **not** for clinical use. The model
card states the exact tokens seen and the ratio to compute-optimal.

## Files

```
artifacts/shennong-mini-f16.gguf        the weights (f16 GGUF)
artifacts/shennong-mini-f16.gguf.sha256 sha256 of the above
artifacts/loss_curve.png / .svg         the real training curve
artifacts/tokenizer_parity.json         proof the GGUF tokenizer == the training tokenizer
artifacts/drug_candidates.json / .md    the candidate shortlist
model/MODEL_CARD.md                     intended use, metrics, limitations
corpus/DATA_CARD.md                     corpus composition, licences, join coverage
eval/report.json                        benchmarks, the theory experiment, negative controls
```

## Run it

```bash
# the model, with llama.cpp (any build, CPU is fine)
llama-cli -m artifacts/shennong-mini-f16.gguf -p "附子必須先炮製，因為" -n 80

# the discovery engine (no GPU, no network)
python -m shennong.cli shi --n 12
python -m shennong.cli ask "Why is 附子 processed before use?"

# the Workbench
python app/serve.py
```

## What this release is NOT

- **Not a clinical tool, not medical advice, not a dosing reference.** The corpus includes
  mercury/arsenic/lead preparations and highly toxic plants (Aconitum, Aristolochia). Those are
  treated as **toxicology data to be analysed**, never as recommendations. The safety layer and the
  red-team tests enforce this.
- **Not a claim of drug discovery.** `drug_candidates.*` are ranked **leads with falsification
  criteria** — hypotheses for experimental testing.
- **Not a benchmark winner.** 8.7 M parameters on 16.7 M tokens of corpus is a pipeline proof. The
  flagship path (`training/flagship/`, Qwen2.5-0.5B + domain CPT + SFT → Q4_K_M GGUF ≈ 350 MB) is
  provided as an executable recipe and is **not** claimed to have been run at that scale here.

## Licences

Code and weights: **Apache-2.0**. Corpus data: per-source licences in `corpus/registry/`
(30 public-domain sources + 8 CC BY-SA-4.0 sources, with the ShareAlike obligation documented).
One candidate source (GRETIL, CC BY-**NC**-SA) was **rejected and excluded** because the NC clause is
incompatible with a public repository — see `corpus/LICENSE_AUDIT.md`.

## Verify it yourself

```bash
python scripts/verify_contracts.py --strict   # contracts, < 1 GB ceiling, no placeholders
bash scripts/smoke_e2e.sh                     # the full pipeline, end to end
python -m pytest                              # test suite
```
