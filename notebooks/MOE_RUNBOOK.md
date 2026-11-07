# MOE RUNBOOK — train a real sparse MoE for Track 1 + Track 2, from scratch

One model, one run. `ibm-granite/granite-3.0-1b-a400m-instruct` is a **genuine sparse mixture of experts**
(32 experts/layer, top-8 router *inside* the network, 1.33 B total / 400 M active, Apache-2.0). Fine-tuning it
on our corpus teaches the whole model — both tracks — and the router learns the domain dispatch internally.

**Q4_K_M lands at ~822 MB**, so the <1 GB constraint still holds.

---

## Cell 0 — runtime

Runtime → **Change runtime type** → Hardware accelerator = **T4 GPU** → Save.
Then Runtime → **Disconnect and delete runtime** (guarantees a clean, matched package tree).

## Cell 1 — setup + preflight (~4 min)

```python
import subprocess, os

os.chdir("/content")   # step OUT first: rm-rf on the shell's own CWD gives
                       # "fatal: Unable to read current working directory"

def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, cwd="/content", executable="/bin/bash",
                       capture_output=True, text=True)
    print((r.stdout or "")[-900:], flush=True)
    if r.returncode:
        print((r.stderr or "")[-2000:], flush=True); raise SystemExit("FAILED: " + cmd)
    return r

sh("rm -rf shennong && git clone -q https://github.com/cptlight/shennong.git shennong")
os.chdir("/content/shennong")
sh("pwd && ls")

# NOTE: never --upgrade torch-adjacent packages in Colab. No torch, no torchvision.
sh('pip install -q "transformers==4.46.3" "peft==0.14.0" "protobuf>=5.28.0" accelerate')

sh('python -c "'
   'import torch; print(\'torch\', torch.__version__, \'| cuda\', torch.cuda.is_available(), \'| dev\', torch.cuda.device_count()); '
   'assert torch.cuda.is_available(), \'NO GPU\'; '
   'from transformers import GraniteMoeForCausalLM; from peft import LoraConfig; '
   'print(\'preflight imports OK\')"')
```

**You must see `cuda True`, `dev 1`, `preflight imports OK`.** If `cuda False` → the runtime has no GPU; no pip
command fixes that.

## Cell 2 — train the MoE (~1 h 15 m)

```python
sh("cd /content/shennong && python notebooks/train_granite_moe.py --epochs 1 --sample 40000")
```

The script preflights itself: it refuses to start without a GPU, without `GraniteMoeForCausalLM`, or if the
LoRA attaches to zero parameters. Expected opening lines:

```
device: Tesla T4
torch 2.x.x | cuda 12.x
base: ibm-granite/granite-3.0-1b-a400m-instruct
params: 1,330,...
LoRA trainable: ~10-20M
LoRA target modules matched: ['down_proj', 'gate_up_proj', 'k_proj', 'o_proj', 'q_proj', 'v_proj']
examples: 40,000 train / ...
```

If `target modules matched` is missing `gate_up_proj`, stop and report — the FFN LoRA is what gives the MoE its
per-expert capacity.

Ends with `saved -> training/runs/granite-moe/merged`.

## Cell 3 — convert to GGUF (~6 min)

```python
sh("git clone -q --depth 1 https://github.com/ggerganov/llama.cpp gguf || true")
sh("pip install -q -r gguf/requirements.txt")
sh("python gguf/convert_hf_to_gguf.py training/runs/granite-moe/merged "
   "--outfile granite-moe-f16.gguf --outtype f16")
sh("python gguf/llama-quantize granite-moe-f16.gguf granite-moe-Q4_K_M.gguf Q4_K_M")
sh("ls -lh granite-moe-Q4_K_M.gguf")
```

**Check: must be < 1 GB.** Expected ~822 MB. If `llama-quantize` is not built in that repo copy, use
`pip install llama-cpp-python` and `llama_cpp.llama_model_quantize(...)` — ask and I'll supply the cell.

## Cell 4 — upload

```python
from huggingface_hub import HfApi
api = HfApi(token="YOUR_HF_TOKEN")
api.upload_file(path_or_fileobj="/content/shennong/granite-moe-Q4_K_M.gguf",
                path_in_repo="granite-moe-Q4_K_M.gguf",
                repo_id="tomscot/shennong-1.5b-sft", repo_type="model")
print("uploaded")
```

---

## Then the benchmark (my side)

Three systems, same 200-question set (`artifacts/benchmark.jsonl`, already split Track 1 / Track 2):

| system | what it is |
|---|---|
| base granite MoE | floor, no fine-tune |
| **fine-tuned granite MoE** | **the candidate product** |
| dense 1.5 B fine-tune | current champion, 39.0 % vs 25.5 % baseline |

Winner by track becomes the shipped model. If the MoE loses, it's reported as a negative result and the dense
model stays — but the project will at least have a *genuine* MoE, not a dispatch layer.

## Why this and not the adapter layer

`scripts/build_expert_datasets.py` + `train_moe_experts.py` produce **LoRA adapters swapped by an external
router** — that is dispatch, not a mixture. Granite MoE has the router and the experts inside the Transformer,
so the "experts" are architectural. That is the claim the submission can defend.
