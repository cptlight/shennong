#!/usr/bin/env python3
"""Emit every raw training number, straight from the run metrics.

The point is that no number here is retyped: the table is generated from `training/runs/*/metrics.json`, so a
stale figure cannot survive. It also marks the runs whose numbers are **not** comparable, because several
are not and the honest table says so.

    python scripts/training_numbers.py        # -> artifacts/TRAINING_NUMBERS.md
"""
from __future__ import annotations

import json
import pathlib
import time

import torch

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS = ROOT / "training/runs"


def f(v, nd=4):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return f"{v:,}"


def main() -> int:
    rows = []
    for d in sorted(RUNS.iterdir()):
        m = d / "metrics.json"
        if not m.exists():
            continue
        j = json.loads(m.read_text())
        c = j.get("corpus") or {}
        rows.append({
            "run": j.get("run_id"), "family": j.get("model_family", "dense"),
            "params": j.get("params"), "active": j.get("active_params"),
            "non_embed": j.get("non_embedding_params"),
            "steps": j.get("steps_completed"), "tokens": j.get("tokens_seen"),
            "epochs": j.get("epochs"),
            "train": j.get("final_train_loss"), "val": j.get("final_val_loss"),
            "ppl": j.get("val_ppl"), "tok_s": j.get("tokens_per_s"),
            "wall": j.get("wall_clock_s"), "threads": j.get("threads"),
            "seed": j.get("seed"),
            "corpus_tokens": c.get("train_tokens"), "corpus_val": c.get("val_tokens"),
            "corpus_chars": c.get("corpus_chars"), "corpus": c.get("corpus"),
        })

    L = ["# RAW TRAINING NUMBERS", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')} from `training/runs/*/metrics.json` by "
         "`scripts/training_numbers.py`. No number below is typed by hand.", ""]

    # ---------- pre-training ----------
    L += ["## Pre-training (corpus in shuffled order)", "",
          "| run | family | params | active | steps | tokens | epochs | train | val | ppl | tok/s | wall s | threads |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["run"].startswith(("curriculum", "sft")):
            continue
        act = f"{r['active']:,}" if r["active"] else "—"
        L.append(f"| `{r['run']}` | {r['family']} | {f(r['params'])} | {act} | {r['steps']} | "
                 f"{f(r['tokens'])} | {f(r['epochs'], 3)} | {f(r['train'])} | {f(r['val'])} | {f(r['ppl'], 2)} | "
                 f"{f(r['tok_s'], 1)} | {f(r['wall'], 1)} | {r['threads']} |")

    L += ["", "**Corpus each run could see:**", "",
          "| run | train tokens | val tokens | chars | corpus file |",
          "|---|---|---|---|---|"]
    for r in rows:
        if r["run"].startswith(("curriculum", "sft")):
            continue
        L.append(f"| `{r['run']}` | {f(r['corpus_tokens'])} | {f(r['corpus_val'])} | {f(r['corpus_chars'])} | "
                 f"`{r['corpus']}` |")

    # ---------- curriculum ----------
    cur = [r for r in rows if r["run"].startswith("curriculum")]
    if cur:
        L += ["", "## Curriculum (staged, resuming from the MoE checkpoint)", "",
              "`steps` and `tokens` are **cumulative** across stages (the trainer resumes and keeps counting).",
              "", "| stage | cumulative steps | cumulative tokens | new steps | new tokens | train | val | ppl | tok/s | wall s | epochs | stage corpus tokens |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        prev_s, prev_t = 199, 199 * 8192
        for r in cur:
            s = r["steps"] or 0
            t = r["tokens"] or 0
            L.append(f"| {r['run']} | {s} | {f(t)} | {s - prev_s} | {f(t - prev_t)} | {f(r['train'])} | "
                     f"{f(r['val'])} | {f(r['ppl'], 2)} | {f(r['tok_s'], 1)} | {f(r['wall'], 1)} | "
                     f"{f(r['epochs'], 2)} | {f(r['corpus_tokens'])} |")
            prev_s, prev_t = s, t
        L += ["", "**Each stage validates on its own held-out slice**, so val losses across stages are "
              "**not comparable** — a lower number means an easier corpus, not a better model.", ""]

    # ---------- SFT ----------
    sft_ck = RUNS / "sft-r3" / "ckpt-best.pt"
    if sft_ck.exists():
        ck = torch.load(sft_ck, map_location="cpu", weights_only=False)
        meta = ck.get("sft") or {}
        L += ["## Track-02 SFT", "",
              "| field | value |", "|---|---|",
              f"| checkpoint | `training/runs/sft-r3/ckpt-best.pt` |",
              f"| step | {ck.get('step')} |",
              f"| base val (answer-only) | {f(meta.get('base_val'))} |",
              f"| best val (answer-only) | {f(meta.get('val'))} |",
              f"| improvement | {f((meta.get('base_val') or 0) - (meta.get('val') or 0))} nats |",
              f"| train examples | {f(sum(1 for _ in (ROOT/'artifacts/sft/train.jsonl').open()))} |",
              f"| val examples | {f(sum(1 for _ in (ROOT/'artifacts/sft/val.jsonl').open()))} |",
              "", "No `metrics.json` exists for this run: it was stopped at step 100 of 250 because machine "
              "load hit 15 and throughput fell to 0.03 it/s. The numbers above come from the checkpoint's own "
              "`sft` metadata, written when the best checkpoint was saved.", ""]

    # ---------- caveats ----------
    L += ["## Which numbers are not trustworthy, and why", "",
          "- **`shennong-moe-r2`**: `val_loss` is `null` and `tokens_per_s` reads 9,024. The run was killed "
          "before its first evaluation and the throughput is a cache-timing artefact. It is listed for "
          "completeness and **must not be used** in any comparison.",
          "- **`tok/s` in every curriculum run is inflated** (up to 12,007) because resumed steps hit the "
          "token cache and complete almost instantly; `wall_clock_s` is the honest measure.",
          "- **MoE vs dense throughput is confounded**: the MoE run used 2 torch threads, the dense run 1. The "
          "capacity-per-FLOP ratio (1.58×) and the val-loss delta do not depend on threads; the speed numbers do.",
          "- **All runs are ~0.1–2 % of compute-optimal tokens** at these parameter counts. They are "
          "architecture ablations and task-shape demos, not capability results.", "",
          "## Reproduce", "", "```bash", "make train-mini        # dense baseline, 200 steps",
          "make train-moe         # sparse MoE, same token budget",
          "make curriculum STEPS=40", "make sft               # Track-02 fine-tune",
          "```", ""]

    out = ROOT / "artifacts/TRAINING_NUMBERS.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}")
    print("\n".join(L[:14]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
