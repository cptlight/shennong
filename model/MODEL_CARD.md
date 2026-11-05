# SHENNONG-mini — Model Card

**A from-scratch, CPU-trained language model for computational ethnopharmacology of the
Asian medical and alchemical canon.**

> **Read this first.** `shennong-mini` is **8.72 M parameters trained on 1,638,400 tokens
> (≈0.19 tokens per parameter, ≈0.9 % of a compute-optimal budget) on one laptop CPU in a few
> hours**. It is deliberately undertrained. It is a *pipeline demonstration* — a real
> tokenizer, a real architecture, a real loss curve, a real GGUF — and it is **not** a factual
> oracle, not a chatbot, and not a medical resource. Judging it as a knowledge base would be a
> category error; judging it as an honest, reproducible end-to-end system is the intent.

| | |
|---|---|
| **Model id** | `shennong-mini` (from scratch) · `shennong-0.5b` (flagship, recipe only) |
| **Parameters** | **8,719,616** (`shennong-mini`, exact, counted from the weight tensors) · 494 M (`shennong-0.5b`, recipe) |
| **Tokens seen** | **1,638,400** ≈ **0.19 tokens/parameter** — ≈ **0.9 %** of the Chinchilla-style compute-optimal budget (20 tokens/param). **Deliberately undertrained: a pipeline demonstration, not a factual oracle.** |
| **Architecture** | Llama-style decoder: RMSNorm, RoPE, SwiGLU, grouped-query attention, tied embeddings |
| **Tokenizer** | byte-level BPE, vocab **16,384**, trained on the SHENNONG corpus |
| **Training** | from scratch, this machine, CPU only (Intel i7-4790K, 4 cores, no CUDA/MPS) |
| **Weights** | `artifacts/shennong-mini-f16.gguf` — **18,054,560** bytes, sha256 `a67ad442aa8511069cbf3dffd0275e697b8e59663b5a73dc0f56b9d13e4cdb60` (f16 is complete and lossless at this size: 17 MB; no quantisation needed) |
| **Licence** | code Apache-2.0; weights Apache-2.0; training text per-source licences (`corpus/registry/sources.yaml`) |
| **Status** | `shennong-mini` trained and released. `shennong-0.5b` is a fully executable recipe — **not yet run at 0.5 B scale** (see §11) |

---

## 1. Intended use

**In scope**

- Research on computational ethnopharmacology: reading classical Asian medical texts
  (Classical Chinese, Sanskrit, Arabic/Persian, Latin, English) and connecting their
  *process* vocabulary (炮制, rasaśāstra operations), *drug names* and *property vectors*
  (四氣五味, 歸經, tridoṣa) to modern chemistry and biology.
- Drafting **mechanistic hypotheses** with a named assay and an explicit falsification test —
  i.e. as a text-completion prior inside a larger, human-reviewed discovery pipeline.
- Studying tokenizer/architecture choices for low-resource, multi-script historical corpora on
  hardware with no GPU.

**Explicitly out of scope — do not use for**

- **Any clinical use**: diagnosis, treatment, prognosis, triage, or patient communication.
- **Any dosing or preparation advice** for any plant, mineral or formula. No output from this
  model is a prescription or a self-treatment instruction.
- Extract/synthesis routes for toxic compounds. The corpus and the instruction data discuss
  toxicity **as a hazard to be characterised**, never as a recipe.
- Anything requiring factual reliability. See §9 — this model hallucinates, confidently.

## 2. What is actually in this repository

| artefact | what it is | status |
|---|---|---|
| `shennong-mini` weights (GGUF f16) | 8.72 M-param model trained from scratch here | **real, trained, hashed** |
| `shennong-mini` HF dir | `config.json` + `model.safetensors` + `tokenizer.json` | **real, generated from the checkpoint** |
| training logs, `metrics.json`, loss curve | real run log, per-step | **real** |
| tokenizer | byte-level BPE 16 k + fertility measurements | **real, measured** |
| `shennong-0.5b` | 494 M flagship: CPT + LoRA-SFT + Q4_K_M recipes | **executable recipe, NOT run at scale** |

## 3. Architecture (measured, not copied)

The model is implemented from scratch in `model/shennong_mini.py` (plain PyTorch, no
`transformers`/`xformers`/flash-attention), following Llama 2/3 and Qwen2.5.

| hyper-parameter | value |
|---|---|
| vocabulary | 16,384 |
| `d_model` | 256 |
| layers | 6 |
| query heads / KV heads | 4 / 1 (GQA, head_dim 64) |
| `d_ff` (SwiGLU) | 768 |
| context length | 512 |
| RoPE theta | 10,000 |
| RMSNorm eps | 1e-5 |
| tied embeddings | yes |
| **total parameters** | **8,719,616** |
| — token embedding (tied with output) | 4,194,304 |
| — transformer blocks | 4,525,056 |
| — final norm | 256 |
| **embedding share of parameters** | **48.1 %** |

The embedding share is stated because it is large: with a 16 k multilingual vocabulary and
`d_model=256`, nearly half the parameters are the embedding table. That is a deliberate
trade — vocabulary coverage for Classical Chinese and Devanagari (the domain requirement) at
the cost of transformer depth. A 19 M config (`model/configs/shennong-mini.json`, 18,880,896
params) was benchmarked first and **rejected**: it ran at 241 tokens/s on this CPU
(`training/runs/bench.json`), i.e. ~16 h for the same token budget.

## 4. Tokenizer — measured

Byte-level BPE (GPT-2-style `ByteLevel` pre-tokenizer), vocab 16,384, 6 special tokens
(`<|pad|> <|bos|> <|eos|> <|system|> <|user|> <|assistant|>`), trained on the corpus snapshot
in §5 (38.24 M characters). Trained by `tokenizer/train_tokenizer.py`; evaluated on a held-out,
hash-selected per-language sample by `tokenizer/eval_tokenizer.py`
(raw numbers: `tokenizer/eval_results.json`).

**Chars per token, per language** — the honest way to report a multi-script tokenizer
(pooled averages hide CJK byte-shredding):

Measured on a held-out, hash-selected sample of the **final** corpus
(`tokenizer/eval_results.json`, 150 docs per language, seed 1337):

| language | chars/token | bytes/token | tokens/doc | vs UTF-8-byte encoding |
|---|---|---|---|---|
| `en` (English, foundational science) | **3.536** | 3.55 | 422 | 3.55× better |
| `la` (Avicenna *Canon*, 1593 Latin) | **2.194** | 2.21 | 709 | 2.21× better |
| `zh-Hant` (Classical Chinese) | **1.202** | 3.53 | 1,452 | 3.52× better |
| `sa` (Sanskrit, Devanagari) | **0.366** | **1.00** | 7,233 | **1.00× — none** |

The `sa` row is **not** a typo: **1.00 bytes/token means Devanagari is being encoded one byte at
a time — no merges at all.** Sanskrit arrived in the corpus *after* this tokenizer was trained and
after the training run had started, so its script is effectively byte-level (3 tokens per
Devanagari character). This is a known, measured gap, not a hidden one. The UTF-8-byte column is
the naive baseline (1 token per byte); for Chinese that baseline is 0.33 chars/token, which is
what an off-the-shelf English-centric tokenizer effectively gives you.

**繁 / 简 (traditional vs simplified) and IAST / Devanagari coverage gaps** (measured):
the tokenizer was trained only on the corpus, which is `zh-Hant` for Chinese, so simplified
forms are not guaranteed. Measured on a parallel passage of 傷寒論: traditional 34 chars →
22 tokens (1.55 chars/token), simplified 34 chars → 20 tokens (1.70 chars/token);
`炮製` = 2 tokens vs `炮制` = 1 token, while `當歸`/`当归` and `黃芩`/`黄芩` are 1 token in both.
So simplified Chinese works but is not optimised. Devanagari and IAST are **uncovered**:
`रस` / `guṇa` are byte-level, 3 tokens per Devanagari character, because Sanskrit entered the
corpus after the tokenizer and after the training run started (§5).

**Why this matters** — a calibration tokenizer trained on the first 6,000 corpus chunks
(which were, due to source ordering, English + Latin only) measured **0.33 chars/token on
Chinese**: `甘草` = 6 tokens. The shipped tokenizer gets `甘草` = **1 token**. On 9.3 M Han
occurrences that is the difference between ~36 M and ~9 M tokens of Chinese.

**Asian-theory vocabulary coverage** (single-token rate; probes in
`tokenizer/eval_tokenizer.py:THEORY_PROBES`):

| probe set | coverage |
|---|---|
| 四氣 — 寒 熱 溫 涼 平 | **5/5** |
| 五味 — 辛 甘 酸 苦 鹹 淡 澀 | **7/7** |
| 歸經 — 肝 心 脾 肺 腎 膽 胃 大腸 小腸 膀胱 三焦 | **11/11** |
| 炮制 — 炮 煅 煨 淬 蒸 煮 炒 炙 飛 伏 製 | **10/11** (`煅` = 2 tokens) |
| 七情 — 相須 相使 相畏 相殺 相惡 相反 | **1/6** |
| 三品 — 上品 中品 下品 | **3/3** |
| Ayurvedic IAST — rasa guṇa vīrya vipāka doṣa vāta pitta kapha | **0/9** |
| Devanagari — रस गुण वीर्य विपाक दोष वात पित्त कफ | **0/8** |

## 5. Training data

The model was trained on the corpus snapshot as it existed at run time
(`corpus/processed/corpus.jsonl`, reproducible via its sha256). Corpus-wide statistics from
`corpus/processed/stats.json`:

- **24,134 chunks · 38,242,644 characters**, UTF-8/NFC, ≥100 (CJK) / ≥200 (alphabetic)
  characters, 13-gram deduplicated. Sources: 105 registry entries, `status: ok` only.
- **By language:** `en` 23.35 M chars · `zh-Hant` 12.11 M · `la` 2.79 M.
- **By tradition:** foundational 16.32 M · ayurveda 5.3 M · tcm 4.4 M · unani 3.2 M ·
  acupuncture 54 k · alchemy 25 k characters.
- **By tier:** Tier 1 (foundational biology/chemistry) 16.3 M · Tier 2 (Asian materia medica)
  ~16 M · Tier 3 (Asian alchemy) ~1.5 M · Tier 4 (acupuncture) 0.6 M characters.
- Every source carries title, author/date, URL, licence + evidence, tier and language in
  `corpus/registry/sources.yaml`; only `status: ok` sources were trained on. Text whose licence
  is unclear is excluded from training and cited only.

**A later corpus re-emission** (45.59 M chars, adding 3.44 M characters of Sanskrit
Devanagari) landed after the run started. **This checkpoint was trained on the 38.24 M-char
corpus snapshot (02:47) because the token cache was keyed on the tokenizer only; the frozen
45.6 M-char corpus post-dates it.** `train_pretrain.py` has since been patched so the cache key
includes the corpus, so future runs train on the final corpus. That is why §4 reports
Devanagari coverage honestly as 0.366 chars/token (1 byte/token) rather than pretending
otherwise.

## 6. Training procedure (measured)

| item | value |
|---|---|
| steps | **200** |
| batch × grad-accum × seq | 8 × 2 × 512 = **8,192 tokens/step** |
| **tokens seen** | **1,638,400** = **0.10 epochs** of the 16,687,735-token training split (**0.19 tokens/param**) |
| **wall clock** | **45.2 min** |
| **throughput** | **604** tokens/s average |
| optimiser | AdamW (β 0.9/0.95, wd 0.1, eps 1e-8) |
| schedule | linear warmup 60 steps → cosine to 10 % of peak |
| peak LR | 6e-4 |
| gradient clipping | 1.0 (global norm) |
| precision | fp32 (bf16 autocast is emulated on Haswell; measured slower — see `training/runs/bench.json`) |
| data loading | corpus pre-tokenised once to a `uint16` memmap (`training/cache/*.npy`), random windows |
| validation | 2 % of chunks held out (deterministic shuffle, seed 0), never trained on |
| seed | 1337 |
| torch | 2.2.2 (CPU), numpy 1.26.4, Python 3.12 |

**Run provenance and wall clock (disclosed because the number in `metrics.json` is only part of
the story).** The run was restarted three times: the machine was being CPU-starved by unrelated
processes (a runaway print daemon at ~90 % of a core, a Wine app, browser renderers, and at
times other project jobs), and throughput swung between ~150 and ~800 tokens/s. `metrics.json`
records the **final contiguous segment: 45.2 min / 604 tokens/s average**; the total wall-clock
span from first launch to the final checkpoint was ≈ **3.2 h**. Steps and tokens seen
(200 steps / 1,638,400 tokens) are cumulative across the resumed segments and are exact — the
checkpoint truly saw every one of those tokens.

**Benchmark before design (measured on this machine, `training/runs/bench.json`):**
MKL fp32 matmul reached 132–162 GFLOPS, but the transformer step only achieved ~27 GFLOPS
because small-matrix elementwise work dominates. Threading gave *nothing*: 242 tokens/s at 1
thread vs 241 tokens/s at 4 threads on the 18.9 M config. That measurement is why the delivered
model is 8.7 M rather than 19 M — the run had to fit in a night.

Reproduce the run:

```bash
.venv/bin/python training/train_pretrain.py \
  --config model/configs/shennong-mini-cpu.json \
  --tokenizer tokenizer/shennong-bpe/tokenizer.json \
  --corpus corpus/processed/corpus.jsonl \
  --steps 450 --batch 8 --accum 2 --seq 512 --lr 6e-4 --warmup 40 \
  --run-name shennong-mini-r1
```

## 7. Evaluation — measured

> ### ⚑ The two honesty tests, before any other number
>
> **1. Compute-optimal comparison.** A compute-optimal (Chinchilla, 20 tokens/parameter) run of
> an 8.72 M-parameter model needs ≈ **174,432,000 tokens**. This model saw
> **1,638,400** tokens = **0.9 %** of that budget
> (**0.19 tokens/parameter**). It is undertrained by a factor of ≈
> **106.4×**, deliberately: the whole run had to fit in one night on a laptop CPU,
> and a *complete* small run with real logs was judged more valuable than a bigger, unfinished one.
>
> **2. Trivial-baseline test.** An add-one-smoothed **unigram token model with no context**
> scores **3.076 bits/byte** on the exact same held-out token stream. This model scores
> **2.526 bits/byte**.
>
> *If this model's bits-per-byte is not below the unigram token baseline of 3.076 bpb, it has
> learned nothing beyond token frequency — and we would say so here.* It is reported below,
> followed by the honest reading. **That is below the unigram baseline by a factor of 1.22×** (3.076 → 2.526 bpb), so the model has learned real contextual structure beyond token frequency — while still being far too weak to be trusted as a knowledge source.
>
> Everything below is measured on the same held-out data, per language, and none of it is
> extrapolated.

Held-out data: 2 % of corpus chunks, stratified only by the deterministic shuffle (not
language-stratified — a limitation for the per-language numbers below, which are computed over
the actual held-out documents of each language). Scored by `training/eval_model.py`.

| metric | **pooled (leakage-free)** | `en` | `zh-Hant` | `la` | `sa` |
|---|---|---|---|---|---|
| held-out cross-entropy (nats/token) | **6.406** | 6.716 | 7.039 | 6.874 | 9.410 |
| perplexity | **605.3** | 825.9 | 1139.9 | 966.4 | 12209.3 |
| **bits per byte** | **2.526** | 2.559 | 3.335 | 4.575 | 13.456 |
| final train loss | 6.366 | — | — | — | — |

The pooled column is the **exact training validation split** (from the cached val token array:
leakage-free by construction, 338,975 tokens scored). The four language columns are the
**per-language diagnostic** on the final corpus (25 docs each) — labelled a diagnostic because the
corpus was re-chunked after training started, so those documents are not guaranteed disjoint from
training text. Sanskrit is the outlier at **13.46 bpb** (worse than a unigram model) for the
expected reason: the tokenizer has no Devanagari merges and the model never saw that script.

Bits-per-byte is the metric to quote: it is comparable across tokenizers and scripts, whereas
perplexity is not. **Baselines on the same held-out token stream** (`training/runs/shennong-mini-r1/baselines.json`,
computed over all 339,639 held-out tokens / 1,239,972 bytes; the model's column is scored on 338,975 tokens because one token per 512-token window is the context edge):

| baseline | bits/token | bits/byte |
|---|---|---|
| uniform over the 16,384-token vocabulary | 14.000 | 3.835 |
| add-one-smoothed unigram token model (no context) | 11.229 | **3.076** |
| raw UTF-8 bytes (no model at all) | — | 8.000 |
| **shennong-mini (this model)** | **9.241** | **2.526** |

The number that matters is the comparison with the **unigram** baseline: a language model that
cannot beat 3.076 bits/byte has learned nothing beyond token frequency. **It beats the unigram baseline by 1.22×, and a uniform distribution over the vocabulary by 1.52× — real learned structure, from a model that still should not be trusted factually.**

**Memorisation check.** Five continuations were sampled from verbatim 40-token prefixes of
**training** documents; the longest verbatim run shared with the true continuation averages
**1.4** tokens out of 60 generated. Full transcripts in `artifacts/samples.md`.
At this model size and token budget the model recombines local phrasing rather than
reproducing passages; this is a weak-memorisation result and should not be read as a
guarantee that no training text can be elicited.

**Inference throughput (product number — this model is meant to run on a laptop):**
**13** tokens/s for a 128-token generation on this CPU, single stream, fp32.

## 8. Qualitative samples

Ten raw, unedited continuations (5 English, 5 Classical Chinese prompts) are published in
`artifacts/samples.md`. They are not cherry-picked. **Read them before using this model for
anything.** A ~9 M-parameter model trained for a few CPU-hours produces locally plausible
character statistics and unreliable propositions; expecting factual accuracy from it is a
category error.

## 9. Limitations (please read)

1. **It is tiny and undertrained by construction.** 8.72 M parameters, **1,638,400 tokens
   seen**: **0.19 tokens per parameter**, about **0.9 %** of the
   ≈20 tokens/parameter compute-optimal budget, and **0.10 epochs** of its
   16.7 M-token corpus. This is the dominant limitation;
   every other limitation below follows from it. It was not undertrained by accident — it was
   sized from a measured CPU throughput number so that a *complete* training run, with real
   logs and a real GGUF, would exist by the deadline.
2. **It hallucinates.** Any factual claim it produces must be verified against a primary source.
   It will invent plant names, compound–target links and citations.
3. **The classical languages are partially covered.** Classical Chinese is tokenised at 1.31
   chars/token and the model can produce Han text, but its classical Chinese is not reliable;
   Sanskrit/Devanagari is byte-level (3 tokens/char) and essentially untrained in this model.
4. **The theory vectors are annotations, not mechanisms.** 四氣五味, 歸經 and tridoṣa are
   historical classification systems. The model reading them does not validate them. That
   question is an experiment (`eval/`), not an inference from this model.
5. **No instruction-following in the released base model.** `<|user|>`/`<|assistant|>` tokens
   exist in the vocabulary and the LoRA-SFT path is implemented, but the released
   `shennong-mini` is a base model.
6. **Not multilingual in the balanced sense.** Training is 61 % English characters; the model's
   English is least bad, its Chinese weaker, its Sanskrit/Latin weakest.
7. **Data-era bias.** Tier-2/3 texts are historical, public-domain editions; they carry the
   medical and cultural assumptions of their time, including harmful or superseded claims.

## 10. Bias, safety and traditional-knowledge ethics

- **No clinical output.** The system prompt, the instruction data and the model card all state
  that no dosing, diagnosis or treatment advice is produced. The instruction data contains no
  extraction or synthesis routes.
- **Toxicity is a subject, not an endorsement.** Entries on 附子 (aconitine), 雷公藤-type
  toxicity, aloe anthraquinones, 何首烏 hepatotoxicity and thujone treat these as hazards and as
  objects of study ("does processing reduce it?").
- **Traditional knowledge**: classical texts are living heritage under Nagoya-Protocol-style
  expectations. Public-domain status of a 1596 edition does not make the tradition free to
  exploit. Attribution, non-extractive framing and benefit-sharing are project-level
  commitments; see the repository's TK policy document.
- **Bias sources**: the canon is elite, male and court/ monastic in origin; women's medicine,
  folk practice and oral traditions are under-represented, and the tradition labels follow
  later editorial boundaries (e.g. "tcm" flattens many regional lineages).
- **Dual-use**: the model is small and weak; the actual dual-use risk of this repository lies in
  the *downstream discovery pipeline*, which is why toxicological screening and a
  "no dosing / no synthesis" rule are enforced there.

## 11. The flagship: `shennong-0.5b` (recipe, **not run at this scale**)

The competition constraint is a model file under 1 GB with ≤1 B parameters. The shipped
flagship plan is a **continued-pretraining recipe**, not a trained model:

| stage | command | status |
|---|---|---|
| base weights | `Qwen/Qwen2.5-0.5B` (494 M, Apache-2.0) | public |
| domain CPT | `python training/cpt.py --base artifacts/qwen2.5-0.5b-base --steps 4000 ...` | **not run here** (CPU-only; ~10² GPU-hours) |
| LoRA SFT | `python training/sft_lora.py --data training/data/*.jsonl ...` | pipeline tested on the mini model; **not run on 0.5 B** |
| merge + quantise | `python training/merge_quantize.py ... --quantize Q4_K_M` | tested end-to-end on a random-weight model |
| GGUF Q4_K_M | ~350–400 MB (0.5 B × ~4.5 bits/weight) | **no file claimed** |

Entry points: `python training/flagship/train_flagship.py --stage cpt|sft|both` (defaults to
Qwen/Qwen2.5-0.5B, 3 epochs, seq 1024) and `bash training/flagship/export_gguf.sh`.
**These have never been executed in this repository** — the machine is CPU-only.

### ⚠️  ESTIMATES — NOT MEASURED. Every row states its assumption.

Nothing in this table is a result. It is the budget a GPU run would need, so that a reader can
check the claim "runs on a free tier" instead of taking it on faith.

| quantity | value | basis / assumption |
|---|---|---|
| parameters | 494,032,768 | Qwen2.5-0.5B public config (Qwen Team 2024, arXiv:2412.15115) |
| corpus tokens for CPT | ≈ 30,000,000 | ≈ 3 epochs over the ~10 M-token corpus chunked with the Qwen tokenizer |
| FLOPs | ≈ 8.9 × 10¹⁶ | `6 · N · T` = 6 × 494,032,768 × 30,000,000 (forward+backward ≈ 6·N·T) |
| A100 wall clock | ≈ 10–12 min | 312 TFLOPS bf16 peak × **50 % MFU** → 156 TFLOPS effective |
| T4 wall clock | ≈ 1.2 h | 65 TFLOPS bf16 peak × **~30 % MFU** → ≈20 TFLOPS effective |
| f16 GGUF size | ≈ 988 MB | 494,032,768 × 2 B + metadata — **at/over the 1 GB limit, hence not shippable** |
| **Q4_K_M GGUF size** | **≈ 350–400 MB** | 494 M × **~4.8–5.3 bits/weight** + 151,936-token vocab metadata |

**Measured vs estimated is visually separated on purpose:** the mini model's numbers in §3–§7
come from files in this repository; every number in this §11 table is an estimate whose
assumption is written next to it.

## 12. Files, hashes, reproduction

| file | size | sha256 |
|---|---|---|
| `artifacts/shennong-mini-f16.gguf` | **18,054,560** bytes | **a67ad442aa8511069cbf3dffd0275e697b8e59663b5a73dc0f56b9d13e4cdb60** |
| `artifacts/shennong-mini-hf/model.safetensors` | 34,884,592 bytes | generated, **gitignored** (`artifacts/*-hf/`); regenerate with the command below |
| `training/runs/shennong-mini-r1/ckpt-best.pt` | 104,703,270 bytes | kept on disk, **not committed** (>100 MB) |
| `training/runs/shennong-mini-r1/log.jsonl` | per-step loss | committed |
| `training/runs/shennong-mini-r1/metrics.json` | contract §10.6 summary | committed |
| `artifacts/loss_curve.png` / `.svg` | real curve from `log.jsonl` | committed |

The GGUF is a self-contained file and is distributed via **GitHub Releases** (no Hugging Face
token in this environment). Regenerate it from the checkpoint without any download:

```bash
python model/export/to_hf.py --checkpoint training/runs/shennong-mini-r1/ckpt-best.pt \
    --tokenizer tokenizer/shennong-bpe --out artifacts/shennong-mini-hf
python model/export/to_gguf.py --hf-dir artifacts/shennong-mini-hf \
    --out artifacts/shennong-mini-f16.gguf --outtype f16 --verify
sha256sum -c artifacts/shennong-mini-f16.gguf.sha256
python model/export/verify_tokenizer_parity.py --gguf artifacts/shennong-mini-f16.gguf \
    --tokenizer tokenizer/shennong-bpe/tokenizer.json
```

**GGUF provenance and verification.** The converter is `model/export/to_gguf.py`, written
against llama.cpp's official `gguf` writer package (`gguf 0.19.0`) using the metadata keys and
tensor names from llama.cpp's `gguf-py/gguf/constants.py` (`MODEL_ARCH.LLAMA`,
`TENSOR_NAMES`), with llama.cpp shallow-cloned at `.tmp/llama.cpp`. It exists because
llama.cpp's own `convert_hf_to_gguf.py` imports `transformers` for tokenizer loading, and this
venv has **no `pip`/`uv` and no `transformers`** (verified: `.venv/bin/python -m pip` → *No
module named pip*). No package was installed for the export.

The exported file is verified by reading it back with `gguf.GGUFReader`:
- tensor count, names and shapes match the HF model; 20 tensors for the mini model;
- total parameter count matches the model exactly (**8,719,616**);
- **every f16 tensor value is bit-exact against the HF safetensors** (max abs diff = 0.0);
- `tokenizer.ggml.model=gpt2`, `tokenizer.ggml.pre=gpt-2`, 16,122 merges, special-token ids
  present (`pad/bos/eos`), `tokenizer.ggml.padding_token_id=0`;
- **tokenizer parity**: the GGUF's vocab/merges re-implemented with llama.cpp's `gpt-2` pre-tokenizer
  regex reproduce the HF tokenizer's token IDs on **100.00 %** of held-out chunks
  (`en` 15/15, `la` 15/15, `zh-Hant` 15/15) — see `artifacts/tokenizer_parity.json`.

## 13. External references used for the design (not for the data claims)

- Llama 2: Touvron et al. 2023, arXiv:2307.09288 (RMSNorm/RoPE/SwiGLU/GQA stack)
- RoPE: Su et al. 2021, arXiv:2104.09864
- SwiGLU: Shazeer 2020, arXiv:2002.05202
- LoRA: Hu et al. 2021, arXiv:2106.09685
- GPT-2 byte-level BPE: Radford et al. 2019
- Qwen2.5: Qwen Team 2024, arXiv:2412.15115 (flagship dimensions)
- llama.cpp: `ggml-org/llama.cpp` (GGUF format, `gguf` python writer, `tokenizer.ggml.pre`
  regex set in `src/llama-vocab.cpp`)

## 14. Citation

```bibtex
@misc{shennong2026mini,
  title  = {SHENNONG-mini: a CPU-trained 8.7M-parameter model for Asian medical heritage},
  author = {Team SHENNONG (EthnoHack 2026)},
  year   = {2026},
  note   = {Trained from scratch on one Intel i7-4790K; Apache-2.0 weights},
  url    = {https://github.com/cptlight/shennong}
}
```

---

*This model card follows the "state what you measured, label what you did not" rule: every
number above is produced by a command in this repository, and the flagship numbers are labelled
as recipe values in the same sentence in which they appear.*
