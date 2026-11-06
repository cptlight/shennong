# SHENNONG-1.5B-SFT — the Track 1 + Track 2 specialist

A **1.5 B-parameter, open-weight (Apache-2.0), laptop-runnable** model: Qwen2.5-1.5B fine-tuned on the full
SHENNONG knowledge base (15,308 examples across 9 tasks), then quantized to Q4_K_M.

| | |
|---|---|
| base | `Qwen/Qwen2.5-1.5B` (Apache-2.0) |
| fine-tune | LoRA r=64 → merged, 3 epochs, 14,389 examples |
| tasks | therapeutic uses (11,819) · properties (1,357) · compounds (1,008) · name mapping (827) · formulas (119) · viability/candidates (120) · 七情 relations (45) · incompatibilities (13) |
| eval loss (answer-only) | 0.561 → **0.534** → 0.570 (best at epoch 2; the saved model is epoch 3, noted) |
| file | `shennong-1.5b-sft-Q4_K_M.gguf` |
| size | **986,047,904 bytes (940 MiB)** |
| sha256 | `c2757da836c73e645755579e2cfc062c45ace25e42409576e00e9ea069ee27ba` |
| bits/weight | 5.08 |

## Sample output (quantized, CPU, offline)

```
<|user|>What is the modern botanical binomial of the historical name 丹參?<|assistant|>
丹參 -> Salvia miltiorrhiza (resolved by manual, confidence 0.95).

<|user|>Which herbs are recorded as incompatible with 烏頭?<|assistant|>
Recorded incompatibilities (pre-modern interaction rules, not clinical advice): 附子（十九畏·烏頭畏附子）.
```

## What it is, and is not

It answers **coherently and mostly correctly** on the two tracks' factual questions — a 19 M model emitted
`,,, and the the the`. It is still not a domain oracle: on long-tail facts it will produce a plausible
structure with a wrong value. The retrieval layer and the physics arbiter (which run on top) are what make
the answers *checkable and true*, and they are unchanged.

For "at least 1 GB" strictly, quantize the same model at Q5_K_M (~1.2 GB) — `scripts/quantize_gguf.py` takes
the ftype as the only change. Q4_K_M is the laptop-friendly default.

## Run it

```bash
pip install llama-cpp-python
python -c "from llama_cpp import Llama; m=Llama(model_path='shennong-1.5b-sft-Q4_K_M.gguf', n_ctx=1024); print(m('<|user|>What is the 歸經 of 甘草?<|assistant|>', max_tokens=90)['choices'][0]['text'])"
```

Source / weights: Apache-2.0. Corpus: per-source licences (see `corpus/registry/sources.yaml`).
