---
title: SHENNONG 神农
emoji: 🌿
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: 1.5B model for TCM + natural products
---

# SHENNONG 神农 — live demo

A **1.5 B-parameter, Apache-2.0, fine-tuned model** for classical Asian medicine and natural products.

**Ask anything about the two tracks.** Answers are **direct generation from the fine-tuned weights** — no
retrieval, no injected passages, no lookup. Every question runs side-by-side against an **unfine-tuned**
baseline with the same prompt and decode, so you can see exactly what fine-tuning bought.

| | |
|---|---|
| 🌿 Traditional knowledge | name mapping across eras, 性味歸經, therapeutic uses, 十八反, 七情 relations |
| 🧪 Natural products | preparation viability (physics verdicts), compound classes, candidate leads |

**Benchmark:** 49.0 % vs 37.0 % (+12.0 pts) over an unfine-tuned baseline on 200 held-out, question-aligned domain questions.

Model: [`tomscot/shennong-1.5b-sft`](https://huggingface.co/tomscot/shennong-1.5b-sft) · repo:
https://github.com/cptlight/shennong
