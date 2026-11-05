#!/usr/bin/env bash
# =============================================================================
# Finalise a completed shennong-mini run into shippable artefacts.
#
#   1. baselines.json          trivial baselines (unigram / uniform / UTF-8) for the honesty test
#   2. eval.json + samples.md  pooled held-out CE/ppl/bpb, per-language diagnostic, memorisation,
#                              10 raw generations, inference tokens/s
#   3. HF dir -> GGUF f16      verified: tensor shapes, parameter count, bit-exact values, sha256
#   4. tokenizer parity         GGUF tokenizer == training tokenizer token-for-token
#   5. loss curve              artifacts/loss_curve.png + .svg from the real log
#   6. model card              every PENDING_* filled from the files above
#
# Usage:
#   bash training/finalize_run.sh [run_dir] [checkpoint_name]
#   e.g. bash training/finalize_run.sh training/runs/shennong-mini-r1 ckpt-best.pt
#
# Everything runs single-threaded (OMP/MKL pinned to 1) so it does not fight a live training
# run; total wall clock is ~10-12 min for the 8.7 M model.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PY:-.venv/bin/python}"
RUN="${1:-training/runs/shennong-mini-r1}"
CKPT="${2:-ckpt-best.pt}"
TOKENIZER="${TOKENIZER:-tokenizer/shennong-bpe}"
HF_DIR="${HF_DIR:-artifacts/shennong-mini-hf}"
GGUF="${GGUF:-artifacts/shennong-mini-f16.gguf}"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

echo "== run: $RUN   checkpoint: $CKPT =="
[[ -f "$RUN/$CKPT" ]] || { echo "ERROR: $RUN/$CKPT not found" >&2; exit 2; }

echo
echo "== 1/6 HF export (checkpoint -> config.json + model.safetensors + tokenizer.json) =="
nice -n 10 "$PY" -u model/export/to_hf.py --checkpoint "$RUN/$CKPT" \
  --tokenizer "$TOKENIZER" --out "$HF_DIR" --dtype f32

echo
echo "== 2/6 GGUF f16 + verify + sha256 sidecar  (PROTECT THIS: artefacts beat promises) =="
nice -n 10 "$PY" -u model/export/to_gguf.py --hf-dir "$HF_DIR" --out "$GGUF" \
  --outtype f16 --name shennong-mini --pre gpt-2 --verify

echo
echo "== 3/6 tokenizer parity (GGUF tokenizer == training tokenizer) =="
nice -n 10 "$PY" -u model/export/verify_tokenizer_parity.py --gguf "$GGUF" \
  --tokenizer "$TOKENIZER/tokenizer.json" --out artifacts/tokenizer_parity.json

echo
echo "== 4/6 baselines (unigram / uniform / UTF-8 bits per byte) =="
nice -n 10 "$PY" -u training/baselines.py --run "$RUN" --tokenizer "$TOKENIZER/tokenizer.json"

echo
echo "== 5/6 evaluation: pooled held-out CE/ppl/bpb, per-language diagnostic, memorisation, samples =="
nice -n 10 "$PY" -u training/eval_model.py --run "$RUN" --ckpt "$CKPT" \
  --tokenizer "$TOKENIZER/tokenizer.json" --per-lang 25 --max-windows 60 --threads 1 --out-dir artifacts

echo
echo "== 6/6 loss curve + model card fill-in =="
nice -n 10 "$PY" -u training/plot_curve.py --run "$RUN"
nice -n 10 "$PY" -u training/fill_model_card.py --run "$RUN" --gguf "$GGUF" --hf-dir "$HF_DIR"

echo
echo "== artefacts =="
ls -l "$GGUF" "$GGUF.sha256" artifacts/loss_curve.png artifacts/loss_curve.svg \
      artifacts/samples.md artifacts/tokenizer_parity.json 2>/dev/null || true
echo
echo "sha256: $(cat "$GGUF.sha256")"
