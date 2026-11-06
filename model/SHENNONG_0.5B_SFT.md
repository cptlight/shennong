# SHENNONG-0.5B-SFT — the Track-02 fine-tune

A **494 M-parameter, sub-1 GB, Apache-2.0** model: Qwen2.5-0.5B fine-tuned on the SHENNONG corpus + Track-02
task pairs, response-masked, then quantized to Q4_K_M.

| | |
|---|---|
| base | `Qwen/Qwen2.5-0.5B` (Apache-2.0) |
| fine-tune | full fine-tuning, 3 epochs, 1,400 examples (property 1,357 · viability 60 · candidate 60 · incompatibility 13) |
| eval loss (answer-only) | **0.4029 → 0.2979 → 0.261** across epochs |
| format | `<\|user\|>…<\|assistant\|>…<\|eos\|>` — plain-text task convention |
| file | `shennong-0.5b-sft-Q4_K_M.gguf` |
| size | **397,807,328 bytes (~379 MiB)** |
| sha256 | `048209ac2e1690cb448e1be82bc4a7da969da67581a461b739fa9e0479115f30` |
| bits/weight | 6.35 (Qwen2.5-0.5B's d_model=896 forces q5/q6 fallback for 144/290 tensors) |

## What it does

It produces **coherent, structured Track-02 answers** where the 19 M model produced `,,, and the the the`:

```
<|user|>What is the recorded nature, flavour and channel tropism of 人參?<|assistant|>
Nature 溫, flavours 甘, channels not recorded, toxicity 無毒, grade —.<|eos|>
```

## What it does not do

It learned the **shape**, not the facts. On unseen herbs it emits a plausible structure with wrong values, and
the incompatibility task (only 13 examples) is weak. This is a task interface, not a domain oracle — the
retrieval layer and the physics arbiter are still what make the answers *true*, and they run on top of it.

## Run it

```bash
pip install llama-cpp-python
python -c "from llama_cpp import Llama; m=Llama(model_path='shennong-0.5b-sft-Q4_K_M.gguf', n_ctx=1024); print(m('<|user|>What is the 歸經 of 甘草?<|assistant|>', max_tokens=90)['choices'][0]['text'])"
```

Or via the repo: `make workbench` and point the Workbench at this GGUF.
