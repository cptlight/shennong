# SHENNONG v0.2.0 — sparse MoE weights

**`shennong-moe` — an 19.3 M-parameter sparse mixture-of-experts model (12.3 M active per token), trained
from scratch on CPU, released as open weights under Apache-2.0.**

| | |
|---|---|
| Parameters | **19,342,616 total / 12,264,728 active** (4 SwiGLU experts, top-2 routing) |
| Architecture | Llama-style trunk (RMSNorm · RoPE · GQA · SwiGLU) + MoE FFN per block; Switch-style load-balancing aux loss |
| Training | from scratch, CPU only, **1,638,400 tokens**, 200 steps |
| Held-out | val loss **5.4828** vs dense **6.3901** at the same token budget (−0.91 nats) |
| Speed | **769 tok/s** vs dense 604 tok/s; 35.5 min vs 45.2 min |
| Weights | `model.safetensors` — **47,086,544 bytes**, sha256 `645374b4e7c04b09…` |
| Licence | Apache-2.0 |

**Routing result.** Across languages sampled from the real corpus, the mean gate weight per expert
gives pairwise Jensen–Shannon distances: **la↔zh-Hant 0.709, en↔zh-Hant 0.605**, la↔sa 0.462,
sa↔zh-Hant 0.332, en↔sa 0.330, en↔la 0.179. Classical Chinese routes nearly disjointly from Latin and
English without supervision — the traditions are separable in representation space. No dead experts
(usage 0.29 / 0.04 / 0.23 / 0.44).

**Caveat.** Single seed; the MoE trained on the frozen 45.6 M-char corpus and the dense comparison on the
38.24 M-char snapshot, so this is strong evidence rather than a clean paired ablation.

**Format note.** MoE weights ship as **safetensors**. A GGUF conversion requires llama.cpp's MoE expert
tensor layout (`ffn_*_exps`), which our converter does not yet emit — stated here rather than promised.

## Files
```
shennong-moe-hf/model.safetensors       47,086,544 B  (f16)
shennong-moe-hf/model.safetensors.sha256
shennong-moe-hf/config.json             HF-style config incl. num_experts / num_experts_per_tok
shennong-moe-hf/tokenizer.json
moe_diagnostics.json                    dense-vs-MoE table, routing JS distances, load balance
```
