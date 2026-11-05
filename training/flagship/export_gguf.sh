#!/usr/bin/env bash
# =============================================================================
# SHENNONG-0.5b flagship — HF dir -> GGUF f16 -> Q4_K_M (< 1 GB) -> sha256.
#
# ⚠️  NOT RUN IN THIS REPOSITORY, and no flagship artefact is claimed.
#     The build machine is CPU-only (i7-4790K, no CUDA/MPS); flagship training needs a GPU.
#     Every size/time number here is an ESTIMATE with its assumption written next to it.
#
# Input comes from the flagship trainer (training/flagship/train_flagship.py):
#     artifacts/shennong-0.5b/final/        HF-format model (config.json + *.safetensors
#                                           + tokenizer.json) written by model.save_pretrained
# (If instead you merged a LoRA adapter with training/merge_quantize.py, point HF_DIR there.)
#
# Size arithmetic, so the Q4 requirement is explicit:
#     Qwen2.5-0.5B = 494,032,768 params
#     f16  : 494M × 2 B            ≈ 988 MB  → already at/over the 1 GB limit  (intermediate)
#     Q4_K_M: 494M × ~4.8–5.3 bits ≈ 297–327 MB of weights + vocab metadata
#                                   ≈ 350–400 MB  → under 1 GB   (ESTIMATE)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PY="${PY:-.venv/bin/python}"
HF_DIR="${HF_DIR:-artifacts/shennong-0.5b/final}"
F16="${F16:-artifacts/shennong-0.5b-f16.gguf}"
Q4="${Q4:-artifacts/shennong-0.5b-q4_k_m.gguf}"

if [[ ! -f "$HF_DIR/config.json" ]]; then
  echo "ERROR: no HF model dir at $HF_DIR" >&2
  echo "       train first:  python training/flagship/train_flagship.py --stage both" >&2
  echo "       (or merge a LoRA: python training/merge_quantize.py --base ... --lora ... --out $HF_DIR)" >&2
  exit 2
fi

mkdir -p artifacts

# -----------------------------------------------------------------------------
# 1. HF -> GGUF f16, verified by reading it back (works WITHOUT `transformers`).
#    The Qwen2.5 tokenizer is a byte-level BPE, so the tokenizer is converted from
#    tokenizer.json; `--pre qwen2` selects llama.cpp's Qwen2 pre-tokenizer regex.
# -----------------------------------------------------------------------------
"$PY" model/export/to_gguf.py \
  --hf-dir "$HF_DIR" \
  --out "$F16" \
  --outtype f16 \
  --name shennong-0.5b \
  --pre qwen2 \
  --verify

# Reference conversion with llama.cpp's own script (needs `transformers`, which this
# environment does not have). Tensor data should be identical to the file above.
# "$PY" .tmp/llama.cpp/convert_hf_to_gguf.py "$HF_DIR" --outtype f16 --outfile "$F16"

# -----------------------------------------------------------------------------
# 2. Quantise to Q4_K_M. The f16 file is ~988 MB — over the limit — so this is
#    mandatory, not optional.
# -----------------------------------------------------------------------------
QUANTIZE_BIN="${QUANTIZE_BIN:-.tmp/llama.cpp/build/bin/llama-quantize}"
if [[ ! -x "$QUANTIZE_BIN" ]]; then
  cat >&2 <<'MSG'
ERROR: llama-quantize not found. NO quantised file was produced and NONE is claimed.
Build llama.cpp (needs cmake + a C++ toolchain; a few minutes, mostly idle CPU):
  cmake -B .tmp/llama.cpp/build -DCMAKE_BUILD_TYPE=Release .tmp/llama.cpp
  cmake --build .tmp/llama.cpp/build --config Release -j4 --target llama-quantize
Then re-run this script.
MSG
  exit 3
fi

"$QUANTIZE_BIN" "$F16" "$Q4" Q4_K_M
shasum -a 256 "$Q4" | awk '{print $1"  '"$(basename "$Q4")"'"}' > "$Q4.sha256"

# -----------------------------------------------------------------------------
# 3. Real size + hash, checked against the < 1 GB constraint
# -----------------------------------------------------------------------------
BYTES=$(wc -c < "$Q4" | tr -d ' ')
echo
echo "shennong-0.5b Q4_K_M: ${BYTES} bytes"
"$PY" - "$BYTES" <<'PY'
import sys
b = int(sys.argv[1])
print(f"  = {b/1e6:.1f} MB (limit 1000 MB → {'OK' if b < 1_000_000_000 else 'OVER LIMIT'})")
print("  ESTIMATE basis: 494,032,768 params × ~4.8–5.3 bits/weight (Q4_K_M) "
      "+ 151,936-token vocab metadata ≈ 350–400 MB. Not measured on this machine.")
PY
cat "$Q4.sha256"

# -----------------------------------------------------------------------------
# 4. Ollama: point model/export/Modelfile FROM at $Q4, then
#      ollama create shennong-0.5b -f model/export/Modelfile
# -----------------------------------------------------------------------------
echo "done."
