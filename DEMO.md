# Test it — query the model, then check the numbers

## The demo

- **Static (browse every result):** https://cptlight.github.io/shennong/ — no install, reads `artifacts/*.json`.
- **Live (query the model):** `make workbench` then open `/demo/`.

The demo has **two judge-facing sections**:

**1 · Ask the model** — the fine-tuned 1.5 B directly — no retrieval, no injected passages — side-by-side
with the unfine-tuned baseline, same prompt, same decode, exact prompts shown, and **12 clickable domain
questions** across both tracks (🌿 Traditional knowledge, 🧪 Natural products).

**2 · Screen a target (Track 02)** — type a disease target (e.g. `COX2`, `tubulin`, `EGFR`) and the
three-layer pipeline runs live: knowledge-graph plant→compound→target links, ECFP4 similarity of 23,176 plant
compounds to the target's known ChEMBL actives, then Lipinski ADMET + preparation physics + structural
novelty, fused into a ranked shortlist. `shennong/screen.py` (`make screen-ml TARGET=COX2`).

## The model (open weights, Apache-2.0)

| model | params | HF | GGUF |
|---|---|---|---|
| **SHENNONG 1.5 B** (shipped) | 1,543,714,304 | [`tomscot/shennong-1.5b-sft`](https://huggingface.co/tomscot/shennong-1.5b-sft) | [v1.17.0](https://github.com/cptlight/shennong/releases/tag/v1.17.0) · 940 MB Q4_K_M |
| SHENNONG 0.5 B (intermediate) | 494 M | [`tomscot/shennong-0.5b-sft`](https://huggingface.co/tomscot/shennong-0.5b-sft) | [v1.16.0](https://github.com/cptlight/shennong/releases/tag/v1.16.0) · 379 MB Q4_K_M |

## The benchmark (200 held-out domain questions, direct generation)

**ours 49.0 % vs unfine-tuned 37.0 % = +12.0 pts.** Contains-match of the gold key fact, no retrieval,
identical decode. Full raw answers in `artifacts/benchmark_results.json`; reproduce with
`python scripts/run_benchmark.py`.

## Install and run

```bash
pip install llama-cpp-python
python -c "from llama_cpp import Llama; m=Llama(model_path='shennong-1.5b-sft-Q4_K_M.gguf', n_ctx=1024); print(m('<|user|>What is the modern botanical binomial of 丹參?<|assistant|>', max_tokens=40)['choices'][0]['text'])"
```

Or clone the repo and `make workbench` for the full live demo with the side-by-side comparison.

## Honest scope

The fine-tuned 1.5 B answers domain questions coherently and beats the unfine-tuned baseline by 13.5 points,
but it is **not an oracle** — on long-tail facts it will produce a plausible structure with a wrong value.
The retrieval layer and the physics arbiter, which run on top, are what make answers *checkable and true*.

## The pipeline (the part a frontier model cannot match)

`shennong screen "<claim>"` — era-map the name → 5-expert consensus → first-principles physics verdict:

```bash
shennong screen "蒸 of 菖蒲 should enrich terpenoids"
# arbiter: VIOLATES FIRST PRINCIPLES — terpenoid is volatile at 100 °C steam; the class is depleted
```

78 of 203 enrichment claims are refuted by validated physics; 6 despite unanimous 5/5 panel agreement.
