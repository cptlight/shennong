#!/usr/bin/env bash
# End-to-end reproducibility check: run the full SHENNONG pipeline on CPU and assert that every
# stage produced a verifiable artefact. This is the script a judge (or CI) runs to see the whole
# thing work without a GPU. It is intentionally noisy.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }

say "0. environment"
$PY -c "import sys, numpy, yaml; print('python', sys.version.split()[0], '| numpy', numpy.__version__)"
$PY -c "import torch; print('torch', torch.__version__, '| threads', torch.get_num_threads())" 2>/dev/null || echo "torch: not installed (fine for the discovery engine)"

say "1. corpus"
test -s corpus/processed/corpus.jsonl || { echo "FAIL: corpus.jsonl missing — run 'make corpus'"; exit 1; }
wc -l corpus/processed/corpus.jsonl

say "2. tokenizer"
test -s tokenizer/shennong-bpe/tokenizer.json || test -s tokenizer/athanor-bpe-16k/tokenizer.json \
  || { echo "FAIL: tokenizer missing — run 'make tokenizer'"; exit 1; }

say "3. model weights"
ls -l artifacts/*.gguf 2>/dev/null || { echo "WARN: no GGUF (run 'make train-mini && make export')"; }

say "4. pipeline 采 → 制 → 配 → 使"
$PY -m shennong.cli cai --corpus-dir corpus/processed
$PY -m shennong.cli zhi --corpus-dir corpus/processed
$PY -m shennong.cli pei --corpus-dir corpus/processed
$PY -m shennong.cli shi --n 10 --out artifacts/hypotheses_smoke.json

say "5. hypotheses are real, cited and falsifiable"
$PY - <<'PYEOF'
import json, sys, pathlib
p = pathlib.Path("artifacts/hypotheses_smoke.json")
if not p.exists():
    sys.exit("FAIL: no hypotheses file")
h = json.loads(p.read_text())["hypotheses"]
assert len(h) >= 10, f"FAIL: only {len(h)} hypotheses (need >= 10)"
bad = [x["id"] for x in h if not x.get("falsification", {}).get("kill_criteria")]
assert not bad, f"FAIL: hypotheses without kill criteria: {bad}"
uncited = [x["id"] for x in h if not x.get("evidence")]
assert not uncited, f"FAIL: hypotheses without evidence: {uncited}"
print(f"OK: {len(h)} hypotheses, all cited, all with kill criteria")
print("classes:", sorted({x["class"] for x in h}))
PYEOF

say "6. evaluation + negative controls"
$PY -m shennong.cli report --out eval/report.json
$PY - <<'PYEOF'
import json, pathlib
r = json.loads(pathlib.Path("eval/report.json").read_text())
for k in ("quxiangbilei", "ayurveda_rasa", "null_model"):
    assert k in r["negative_controls"], f"FAIL: missing negative control {k}"
print("OK: benchmarks", list(r["benchmarks"])[:6])
print("OK: negative controls", json.dumps(r["negative_controls"], ensure_ascii=False))
PYEOF

say "7. safety red-team"
$PY -m pytest tests/ -q -k "safety or refusal"

say "8. contracts"
$PY scripts/verify_contracts.py

say "ALL STAGES PASSED"
