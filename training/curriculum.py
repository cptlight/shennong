#!/usr/bin/env python3
"""Curriculum training: foundations → Asian classics → regional → patterns → pharmacology → grounding.

Why staged instead of shuffled
------------------------------
Training a domain expert is not the same as training a general model. A general model can see the corpus in
random order because its job is next-token statistics. A model meant to *reason from first principles about
traditional medicine* has a dependency order:

    1 FOUNDATIONS      physics, chemistry, biology, botany, anatomy, philosophy of science
    2 ASIAN CLASSICS   the primary canon — 本草綱目, 神農本草經, 黃帝內經 … in the original scripts
    3 REGIONAL         Ayurvedic, Unani, Korean, acupuncture — the neighbouring traditions
    4 ALCHEMY/PROCESS  the operations: 炮製, distillation, calcination, fermentation
    5 PATTERNS         the structured record rendered as text: compound → plant → use → property → rule
    6 PHARMACOLOGY     discovery methods: pharmacognosy, screening, the experimental method
    7 GROUNDING        (question, retrieved evidence, answer) pairs — citation discipline
    8 SELF-OBSERVATION probes on hidden states: "am I grounded, or am I confabulating?"

Stages 1–6 are plain next-token training on increasingly specific data. Stage 7 teaches the citation habit.
Stage 8 is a different kind of training — a probe that reads the model's own activations and predicts whether
an answer is grounded (see `training/self_observe.py`).

The stages are built from the registry's own metadata (`tradition`, `lang`, `tier`), not hand-picked files,
so the curriculum is auditable and regenerates when the corpus grows.

    python training/curriculum.py --steps-per-stage 40 --out runs/curriculum-r1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import subprocess
import sys
import time

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CUR = ROOT / "training" / "curriculum"

# (stage_id, name, what it selects, why it comes here)
STAGES = [
    ("0_foundations", "FOUNDATIONS",
     {"tradition": ["foundational"]},
     "physics/chemistry/biology/botany/anatomy — the first-principles substrate every later claim is checked against"),
    ("1_asian_classics", "ASIAN CLASSICS",
     {"tradition": ["tcm"], "tier": [2], "lang": ["zh-Hant", "zh-Hans"]},
     "the primary canon in the original scripts, before any secondary retelling"),
    ("2_regional", "REGIONAL TRADITIONS",
     {"tradition": ["ayurveda", "unani", "korean", "acupuncture"]},
     "the neighbouring systems, so the model can compare rather than memorise one"),
    ("3_alchemy_process", "ALCHEMY & PROCESS",
     {"tradition": ["alchemy"]},
     "the operations that make a preparation work — 炮製, distillation, calcination"),
    ("4_patterns", "PATTERNS",
     {"synthetic": "patterns"},
     "the structured record as text: compound → plant → use → property → incompatibility"),
    ("5_pharmacology", "PHARMACOLOGY & METHOD",
     {"keywords": ["pharmacognosy", "pharmacology", "materia medica", "principles"]},
     "how a discovery is actually made — the method, not more facts"),
    ("6_grounding", "GROUNDING",
     {"synthetic": "grounding"},
     "citation discipline: answer only over retrieved spans, say so when the span is absent"),
]


def _reg_sources() -> list[dict]:
    reg = yaml.safe_load(open(ROOT / "corpus/registry/sources.yaml", encoding="utf-8"))
    src = reg["sources"] if isinstance(reg, dict) and "sources" in reg else reg
    if isinstance(src, dict):
        src = list(src.values())
    return src


def _records() -> list[dict]:
    out = []
    with open(ROOT / "corpus/processed/corpus.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def _synthetic(stage: str) -> list[str]:
    """Render structured tables as text, so the model sees the pattern, not a lookup table."""
    import csv

    docs: list[str] = []
    if stage == "patterns":
        base = ROOT / "corpus/processed/structured"
        props = list(csv.DictReader(open(base / "properties.csv", encoding="utf-8")))
        for r in props[:20000]:
            docs.append(f"{r.get('drug_name')} — 性 {r.get('nature')}; 味 {r.get('flavors')}; "
                        f"歸經 {r.get('channels')}; 毒性 {r.get('toxicity')}; 品級 {r.get('grade')}")
        incompat = list(csv.DictReader(open(base / "incompatibilities.csv", encoding="utf-8")))
        for r in incompat[:5000]:
            docs.append(f"{r.get('drug_a')} 與 {r.get('drug_b')} 不相合（{r.get('classical_label')}）")
        uses = list(csv.DictReader(open(base / "uses.csv", encoding="utf-8")))
        for r in uses[:20000]:
            docs.append(f"{r.get('drug_name')} 用於 {r.get('use_term')}")
    elif stage == "grounding":
        qa = ROOT / "artifacts" / "grounding_pairs.jsonl"
        if qa.exists():
            docs = [json.loads(line)["text"] for line in qa.open(encoding="utf-8") if line.strip()]
    return docs


def build_stages(min_chars_per_stage: int = 200_000) -> dict:
    recs = _records()
    reg = _reg_sources()
    by_id = {s.get("id"): s for s in reg}
    CUR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for sid, name, sel, why in STAGES:
        docs: list[str] = []
        if "synthetic" in sel:
            docs = _synthetic(sel["synthetic"])
        elif "keywords" in sel:
            kw = sel["keywords"]
            for r in recs:
                blob = f"{r.get('title','')} {r.get('title_en','')}".lower()
                if any(k in blob for k in kw) and (r.get("tier") or 9) <= 2:
                    docs.append(r["text"])
        else:
            for r in recs:
                meta = by_id.get(r.get("source_id"), {})
                ok = True
                for key, wanted in sel.items():
                    got = r.get(key, meta.get(key))
                    if key == "tradition":
                        if got not in wanted:
                            ok = False
                    elif key == "tier":
                        if (got if got is not None else 9) not in wanted:
                            ok = False
                    elif key == "lang":
                        if got not in wanted:
                            ok = False
                if ok:
                    docs.append(r["text"])

        chars = sum(len(d) for d in docs)
        if chars < min_chars_per_stage and docs:
            # repeat the stage content rather than silently training on almost nothing
            factor = max(1, min_chars_per_stage // max(chars, 1))
            docs = docs * factor
            chars = sum(len(d) for d in docs)

        random.Random(1337).shuffle(docs)
        split = max(1, int(len(docs) * 0.02))
        path = CUR / f"{sid}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for i, d in enumerate(docs):
                fh.write(json.dumps({"id": f"{sid}-{i}", "source_id": sid, "text": d,
                                     "split": "val" if i < split else "train",
                                     "tradition": sel, "lang": "mixed", "tier": 0},
                                    ensure_ascii=False) + "\n")
        manifest[sid] = {"name": name, "why": why, "docs": len(docs), "chars": chars,
                         "path": str(path.relative_to(ROOT))}
        print(f"  {sid:<18} {len(docs):>7,} docs  {chars/1e6:>6.2f} M chars  — {name}")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps-per-stage", type=int, default=40)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--threads", type=int, default=5)
    ap.add_argument("--config", default="model/configs/shennong-moe-cpu.json")
    ap.add_argument("--init", default="training/runs/shennong-moe-r1/ckpt-best.pt")
    ap.add_argument("--out", default="training/runs/curriculum-r1")
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()

    print("building stages from registry metadata")
    manifest = build_stages()
    CUR_MANIFEST = CUR / "manifest.json"
    CUR_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.build_only:
        print(f"\nwrote {CUR_MANIFEST}")
        return 0

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    history = []
    prev = args.init
    lr = args.lr
    for i, (sid, name, _sel, why) in enumerate(STAGES):
        stage_path = CUR / f"{sid}.jsonl"
        if not stage_path.exists() or manifest.get(sid, {}).get("docs", 0) == 0:
            print(f"  {sid}: no data, skipped")
            continue
        run_name = f"curriculum-{sid}"
        # --steps is a TOTAL target, not an increment. Resuming from step 199 with --steps 40 makes the
        # trainer believe it is already finished and exit immediately (it did, silently, on the first
        # attempt). So each stage's target is previous_step + steps_per_stage.
        prev_step = 0
        if prev and (ROOT / prev).exists():
            try:
                import torch as _torch
                prev_step = int(_torch.load(str(ROOT / prev), map_location="cpu",
                                            weights_only=False).get("step") or 0)
            except Exception:  # noqa: BLE001
                prev_step = 0
        target_steps = prev_step + args.steps_per_stage
        cmd = [sys.executable, str(ROOT / "training/train_pretrain.py"),
               "--config", args.config, "--corpus", str(stage_path),
               "--run-name", run_name, "--steps", str(target_steps),
               "--lr", f"{lr:.2e}", "--warmup", "5", "--threads", str(args.threads),
               "--eval-steps", str(max(10, args.steps_per_stage // 2)),
               "--ckpt-steps", str(max(10, args.steps_per_stage // 2)),
               "--log-steps", "10"]
        if prev and (ROOT / prev).exists():
            cmd += ["--resume", str(ROOT / prev)]
        print(f"\n=== stage {i} · {name} · {args.steps_per_stage} steps · lr {lr:.1e}")
        print(f"    why: {why}")
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        tail = (proc.stdout or "").strip().splitlines()[-4:]
        for line in tail:
            print("   ", line)
        if proc.returncode != 0:
            print((proc.stderr or "")[-800:])
            break
        metrics_path = ROOT / "training/runs" / run_name / "metrics.json"
        m = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
        history.append({"stage": sid, "name": name, "why": why,
                        "steps": args.steps_per_stage, "total_steps": target_steps,
                        "resumed_from_step": prev_step,
                        "lr": lr, "val_loss": m.get("final_val_loss"),
                        "train_loss": m.get("final_train_loss"),
                        "params": m.get("params"), "active_params": m.get("active_params"),
                        "wall_s": round(time.time() - t0, 1),
                        "docs": manifest.get(sid, {}).get("docs")})
        prev = f"training/runs/{run_name}/ckpt-best.pt"
        lr = max(8e-5, lr * 0.82)      # anneal across stages

    payload = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "order": [s[0] for s in STAGES],
               "rationale": ("staged curriculum: first principles before tradition, tradition before "
                             "regional comparison, operations before patterns, method before grounding"),
               "stages": history,
               "final_checkpoint": prev}
    (ROOT / "artifacts/curriculum.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote artifacts/curriculum.json ({len(history)} stages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
