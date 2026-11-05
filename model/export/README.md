# `model/export/` — checkpoint → HF → GGUF, with verification

Everything in this directory runs on CPU and needs no `transformers`, no `pip`, and no network
(for the mini model — the llama.cpp checkout used as a reference is already at `.tmp/llama.cpp`).

## Files

| file | purpose |
|---|---|
| `to_hf.py` | training checkpoint (`ckpt.pt`) → HuggingFace layout: `config.json`, `model.safetensors`, `tokenizer.json`; also provides `load_hf_model()` (the inverse) |
| `to_gguf.py` | HF layout → **GGUF f16/f32** + full verification (tensors, shapes, parameter count, per-value bit-exactness, vocab, special tokens, sha256 + `.sha256` sidecar) |
| `verify_tokenizer_parity.py` | re-implements llama.cpp's `gpt-2` pre-tokenizer + BPE from the GGUF vocab/merges and compares token IDs against the HF tokenizer |
| `export_gguf.sh` | the exact end-to-end command sequence, for both `shennong-mini` and the flagship `shennong-0.5b` recipe |
| `Modelfile` | Ollama template for `shennong-mini` |

## Why `to_gguf.py` exists instead of `convert_hf_to_gguf.py`

llama.cpp's `convert_hf_to_gguf.py` loads the tokenizer with
`from transformers import AutoTokenizer` (see `conversion/base.py::get_vocab_base` in the
checkout). This environment has **no `pip`, no `uv`, and no `transformers`**:

```console
$ .venv/bin/python -m pip --version
/Users/tom/Documents/ETHno/.venv/bin/python: No module named pip
$ .venv/bin/python -c "import transformers"
ModuleNotFoundError: No module named 'transformers'
```

Installing packages was out of scope, and shipping a fake GGUF was not an option. `to_gguf.py`
therefore re-implements the conversion using llama.cpp's **own** `gguf` writer package
(`gguf 0.19.0`, already in the venv) and the metadata keys / tensor names taken from
llama.cpp's `gguf-py/gguf/constants.py` (`MODEL_ARCH.LLAMA`, `TENSOR_NAMES`). The GGUF it emits
is a normal, self-contained GGUF; `llama.cpp` loads it like any other Llama-architecture file.

If `transformers` is available on another machine, the reference conversion is:

```bash
python .tmp/llama.cpp/convert_hf_to_gguf.py artifacts/shennong-mini-hf \
    --outtype f16 --outfile artifacts/shennong-mini-f16.gguf.f16  # compare tensor data
```

## Verification performed (all real, reproducible)

`to_gguf.py --verify` reads the file back with `gguf.GGUFReader` and checks:

1. tensor names and shapes match the HF model (reverse-dim convention handled);
2. total parameter count equals the model's exact count;
3. **every f16 tensor value is bit-exact against the HF safetensors** (`max_abs_diff == 0.0`);
4. `general.architecture=llama`, tokenizer model/pre, vocab size, pad/bos/eos ids;
5. writes `artifacts/<name>.gguf.sha256` as a sidecar (`sha256  filename`).

`verify_tokenizer_parity.py` then proves the GGUF's **token stream** equals the training
tokenizer's, by re-implementing llama.cpp's `LLAMA_VOCAB_PRE_TYPE_GPT2` regex + the byte↔unicode
alphabet + lowest-rank BPE merges. On a 45-chunk held-out sample (en/la/zh-Hant, 15 each) this
was **100.00 % exact**.

## Commands

```bash
# 1. checkpoint -> HF
.venv/bin/python model/export/to_hf.py \
  --checkpoint training/runs/shennong-mini-r1/ckpt-best.pt \
  --tokenizer tokenizer/shennong-bpe \
  --out artifacts/shennong-mini-hf --dtype f32

# 2. HF -> GGUF f16 + verify + sidecar hash
.venv/bin/python model/export/to_gguf.py \
  --hf-dir artifacts/shennong-mini-hf \
  --out artifacts/shennong-mini-f16.gguf \
  --outtype f16 --name shennong-mini --verify

# 3. tokenizer parity
.venv/bin/python model/export/verify_tokenizer_parity.py \
  --gguf artifacts/shennong-mini-f16.gguf \
  --tokenizer tokenizer/shennong-bpe/tokenizer.json \
  --out artifacts/tokenizer_parity.json
```

The flagship path (Qwen2.5-0.5B → CPT → LoRA → merge → **Q4_K_M**) is documented in
`export_gguf.sh` and `training/merge_quantize.py`. Quantisation needs llama.cpp's
`llama-quantize` binary; if it is not built, that script **prints the command and refuses to
claim a quantised file exists**.
