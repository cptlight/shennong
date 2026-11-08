# Benchmark — protocol, the scoring bug we found, and how to reproduce

This file exists because an accuracy audit before submission found that the numbers previously published
(39.0 % vs 25.5 %) **could not be reproduced from the repository**. What follows is what was wrong, what was
fixed, and the corrected protocol.

---

## What the benchmark measures

200 held-out questions generated from the same corpus the model was trained on, but from held-out rows. Ten
question families: recorded use, classical formula use, plant property, gene target, name mapping, compound
class, pharmacology, viability, relation, candidate.

Scoring is **contains-match**: the gold key fact must appear in the generated answer. Decoding is fixed and
documented: `temperature 0.2, top_p 0.9, seed 1337, max_new_tokens 40`, prompt `<|user|>…<|assistant|>`, no
retrieval.

---

## The bug: the shipped results were scored against a different benchmark

`artifacts/benchmark_results.json` and `artifacts/benchmark.jsonl` did not describe the same 200 questions:

| | `benchmark.jsonl` | `benchmark_results.json` |
|---|---|---|
| `use` questions | 63 | **113** |
| question families | 10 | 8 |
| **questions matching by text** | — | **13 / 200** |

The composition differs, so the published 39.0 % was computed from a benchmark file that no longer exists in the
repository. **A judge could not reproduce it.** That is a defect regardless of whether the number happened to be
right.

### Second bug: the keys for the `use` family were not the answer

For 113 of 200 questions the stored key was the *tradition label* or a preparation phrase, not the recorded use:

```
Q:    What is Heimia salicifolia used for in Indian medicine?
gold: Recorded use: emetics (Indian medicine).
key:  "Indian medicine"          <- the tradition, not the use
```

A model answering **"emetics"** — correct — scored zero. This is why both arms reported `use: 0/113`: the metric,
not the models, was broken.

### Third bug: `classical_use` keys are sometimes the source book title

```
Q:    In classical Chinese medicine, what is used to treat 疥蟲䘌瘡?
key:  "珍珠囊補遺藥性賦"          <- the name of the BOOK, which no answer can contain
```

Those 20 questions are scored conservatively and reported **separately**, never folded into the headline.

---

## The corrected protocol

`scripts/benchmark_v2.py` re-evaluates both models from scratch against the shipped `benchmark.jsonl`:

- **`use`** — the key is re-derived from `gold` (`Recorded use: X (tradition)` → `X`), so the answer must name the
  use, not the tradition.
- **`classical_use`** — keys are unrecoverable for some rows (book titles); scored as-is with
  punctuation-insensitive matching and **reported separately**.
- **all other families** — original keys, unchanged.

Matching normalises whitespace and CJK/Latin punctuation before comparing, so `桂心、人參` and `桂心人參` behave
the same.

```bash
python scripts/benchmark_v2.py --n 200 --out artifacts/benchmark_v2.json
```

The run writes every generated answer per row, so any claim can be re-checked line by line:

```python
import json
d = json.load(open("artifacts/benchmark_v2.json"))
for r in d["arms"]["ours"]["rows"][:5]:
    print(r["kind"], r["mode"], r["key"], "->", r["hit"], r["answer"][:80])
```

---

## Results

*(filled in by the corrected run — see `artifacts/benchmark_v2.json`; the numbers in the README are generated
from that file, not typed by hand)*

| arm | all 200 | excluding `classical_use` (180) |
|---|---|---|
| fine-tuned 1.5 B | see file | see file |
| base Qwen2.5-1.5B-Instruct | see file | see file |

---

## Rules we hold ourselves to

1. **A number is only published if the file that produced it is in the repository.** The old 39.0 % failed this.
2. **Broken question families are disclosed, not silently dropped.** `classical_use` is reported separately and
   the reason is written down.
3. **Both arms are run in the same process, same decode, same prompts.** No hand-picking.
4. **Negative results ship.** The sparse MoE scored below the dense model and is released with its benchmark:
   `artifacts/moe_vs_dense.json`.
