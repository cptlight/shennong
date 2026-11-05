#!/usr/bin/env bash
# =============================================================================
# SHENNONG — GGUF export, end to end.
#
# Two paths:
#   A. shennong-mini  (trained from scratch on this machine)  -> f16 GGUF, ~17 MB
#   B. shennong-0.5b  (flagship: Qwen2.5-0.5B -> CPT -> LoRA merge) -> Q4_K_M, ~350-400 MB
#
# Path A is what this repository ships under artifacts/. Path B is a fully executable
# recipe; it is NOT claimed to have been run at 0.5 B scale on this CPU (see MODEL_CARD.md).
#
# Everything below is a real command that was executed for path A; path B is labelled.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PY="${PY:-.venv/bin/python}"
TOKENIZER="${TOKENIZER:-tokenizer/shennong-bpe}"
CHECKPOINT="${1:-training/runs/shennong-mini-r1/ckpt-best.pt}"
HF_DIR="artifacts/shennong-mini-hf"
GGUF="artifacts/shennong-mini-f16.gguf"

mkdir -p artifacts

# -----------------------------------------------------------------------------
# 0. llama.cpp (needed for convert_hf_to_gguf.py and llama-quantize)
#    The pinned checkout is shallow-cloned, never committed (.tmp/ is gitignored).
# -----------------------------------------------------------------------------
if [[ ! -d .tmp/llama.cpp ]]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp .tmp/llama.cpp
fi
LLAMA_CPP_COMMIT="$(git -C .tmp/llama.cpp rev-parse HEAD)"
echo "llama.cpp @ ${LLAMA_CPP_COMMIT}"

# -----------------------------------------------------------------------------
# PATH A — shennong-mini: checkpoint -> HF -> GGUF f16 -> verified
# -----------------------------------------------------------------------------

# 1. training checkpoint -> HuggingFace layout (config.json + model.safetensors + tokenizer)
"$PY" model/export/to_hf.py \
  --checkpoint "$CHECKPOINT" \
  --tokenizer "$TOKENIZER" \
  --out "$HF_DIR" \
  --dtype f32

# 2. HF layout -> GGUF f16, then read it back and verify every tensor + sha256
"$PY" model/export/to_gguf.py \
  --hf-dir "$HF_DIR" \
  --out "$GGUF" \
  --outtype f16 \
  --name shennong-mini \
  --verify
# -> writes artifacts/shennong-mini-f16.gguf.sha256 as a sidecar

# 3. tokenizer parity: does the GGUF reproduce the training tokenizer's IDs?
"$PY" model/export/verify_tokenizer_parity.py \
  --gguf "$GGUF" \
  --tokenizer "$TOKENIZER/tokenizer.json" \
  --out artifacts/tokenizer_parity.json

# 4. (optional) reference conversion with llama.cpp's own script. Requires `transformers`
#    for tokenizer loading (NOT installed here; the venv has no pip/uv — see MODEL_CARD.md).
#    Converted output should be byte-identical in tensor data to step 2.
# "$PY" .tmp/llama.cpp/convert_hf_to_gguf.py "$HF_DIR" --outtype f16 --outfile /tmp/ref-f16.gguf

# 5. (optional) lossless quantisation of the mini model with llama.cpp. Needs a built binary:
#    cmake -B .tmp/llama.cpp/build -DCMAKE_BUILD_TYPE=Release .tmp/llama.cpp
#    cmake --build .tmp/llama.cpp/build --config Release -j4 --target llama-quantize
QUANTIZE_BIN="${QUANTIZE_BIN:-.tmp/llama.cpp/build/bin/llama-quantize}"
if [[ -x "$QUANTIZE_BIN" ]]; then
  "$QUANTIZE_BIN" "$GGUF" artifacts/shennong-mini-q8_0.gguf Q8_0
  "$QUANTIZE_BIN" "$GGUF" artifacts/shennong-mini-q4_k_m.gguf Q4_K_M
  ls -l artifacts/shennong-mini-q8_0.gguf artifacts/shennong-mini-q4_k_m.gguf
else
  echo "NOTE: $QUANTIZE_BIN not built — no quantised mini file is produced or claimed."
  echo "      Commands: llama-quantize $GGUF artifacts/shennong-mini-q4_k_m.gguf Q4_K_M"
fi

# -----------------------------------------------------------------------------
# PATH B — shennong-0.5b flagship. RECIPE ONLY on this CPU (labelled, not run here).
# -----------------------------------------------------------------------------
#
# Size arithmetic, so nobody is surprised:
#   0.5 B params * 2 bytes (f16)            = ~988 MB  (+ metadata) -> OVER 1 GB
#   0.5 B at Q4_K_M (4.5 bits/weight avg)   = ~350-400 MB            -> under 1 GB  ✔
#   So the flagship *must* ship Q4_K_M. The f16 file exists only as an intermediate.
#
# 1. Base weights (public, Apache-2.0):
#      huggingface-cli download Qwen/Qwen2.5-0.5B --local-dir artifacts/qwen2.5-0.5b-base
#
# 2. Continued pretraining on the SHENNONG corpus (GPU recommended; see training/cpt.py):
#      python training/cpt.py \
#        --base artifacts/qwen2.5-0.5b-base \
#        --config model/configs/shennong-0.5b.json \
#        --corpus corpus/processed/corpus.jsonl \
#        --tokenizer artifacts/qwen2.5-0.5b-base/tokenizer.json \
#        --steps 4000 --batch 8 --accum 8 --seq 1024 --lr 5e-5 \
#        --run-name shennong-0.5b-cpt
#
# 3. LoRA SFT (task shape: propose a drug candidate; see training/data/):
#      python training/sft_lora.py \
#        --base artifacts/qwen2.5-0.5b-base \
#        --config model/configs/shennong-0.5b.json \
#        --data training/data/instruction_drug_candidate.jsonl \
#        --out training/runs/shennong-0.5b-lora --steps 600 --lr 1e-4
#
# 4. Merge LoRA -> HF dir -> GGUF -> Q4_K_M (this is what ships):
#      python training/merge_quantize.py \
#        --base training/runs/shennong-0.5b-cpt/ckpt-best.pt \
#        --lora training/runs/shennong-0.5b-lora/lora_adapter.pt \
#        --out artifacts/shennong-0.5b-hf \
#        --tokenizer artifacts/qwen2.5-0.5b-base \
#        --quantize Q4_K_M \
#        --gguf-out artifacts/shennong-0.5b-q4_k_m.gguf
#
#    Then verify it loads and hash it:
#      sha256sum artifacts/shennong-0.5b-q4_k_m.gguf > artifacts/shennong-0.5b-q4_k_m.gguf.sha256
#
# 5. Ollama (local, laptop):   ollama create shennong-0.5b -f model/export/Modelfile
echo "done."
