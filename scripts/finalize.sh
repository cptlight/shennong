#!/usr/bin/env bash
# Endgame: fill every pending number from real artefacts, gate the submission, commit and publish.
# Run only when eval/report.json has fixture:false and training/runs/*/metrics.json is completed:true.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
FAIL=0
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
gate() { if [ "$1" -ne 0 ]; then printf '\033[31mFAILED\033[0m %s\n' "$2"; FAIL=1; else printf '\033[32mok\033[0m %s\n' "$2"; fi; }

say "0. are the artefacts actually final?"
$PY - <<'PYEOF'
import json, pathlib, sys
ok = True
r = pathlib.Path("eval/report.json")
if r.exists():
    d = json.loads(r.read_text())
    print(f"  eval/report.json  fixture={d.get('fixture')}  generated={d.get('generated_at')}")
    ok &= not d.get("fixture", True)
else:
    print("  eval/report.json  MISSING"); ok = False
ms = sorted(pathlib.Path("training/runs").glob("*/metrics.json"))
done = [m for m in ms if json.loads(m.read_text()).get("completed")]
print(f"  training runs: {len(ms)} total, {len(done)} completed")
ok &= bool(done)
g = list(pathlib.Path("artifacts").glob("*.gguf"))
print(f"  gguf: {[ (x.name, x.stat().st_size) for x in g ]}")
ok &= bool(g)
sys.exit(0 if ok else 1)
PYEOF
gate $? "artefacts final"

say "0b. refresh structural novelty (shi regenerates the artefact and resets it)"
$PY scripts/structural_novelty.py || echo "WARN: structural novelty step failed"

say "1. fill the numbers from real artefacts"
$PY submission/sync_numbers.py; gate $? "sync_numbers"

say "2. ship gate — no placeholders anywhere"
$PY submission/check_pending.py; gate $? "check_pending"

say "3. contract verification in strict mode"
$PY scripts/verify_contracts.py --strict; gate $? "verify_contracts --strict"

say "4. export GGUF if a completed checkpoint exists and no gguf yet"
if ! ls artifacts/*.gguf >/dev/null 2>&1; then
  CK=$(ls -t training/runs/*/ckpt-best.pt 2>/dev/null | head -1)
  [ -n "$CK" ] && $PY model/export/to_hf.py --checkpoint "$CK" --tokenizer tokenizer/shennong-bpe \
      --out artifacts/shennong-mini-hf --dtype f32 && \
    $PY model/export/to_gguf.py --hf-dir artifacts/shennong-mini-hf \
      --out artifacts/shennong-mini-f16.gguf --outtype f16 --name shennong-mini --verify
  gate $? "gguf export"
fi

say "5. commit + push"
git add -A
git -c user.name=cptlight -c user.email=cptlight@users.noreply.github.com \
    commit -q -m "SHENNONG v1: real corpus, trained weights, discovery engine, evaluation, submission" || echo "nothing to commit"
git push -q origin main && echo "pushed"

say "SUMMARY"
if [ "$FAIL" -eq 0 ]; then printf '\033[32mALL GATES PASSED\033[0m\n'; else printf '\033[31mGATES FAILED — do not submit yet\033[0m\n'; fi
exit $FAIL
