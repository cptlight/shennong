"""Fill the `PENDING_*` slots in `model/MODEL_CARD.md` from measured artefacts.

The model card is **generated from the files the training/eval/export pipeline produced**, so a
number can never drift from the run that produced it. Every substitution below reads a real file:

    training/runs/<run>/metrics.json        steps, tokens_seen, wall clock, losses, loss_curve
    training/runs/<run>/eval.json           pooled held-out CE/ppl/bpb, per-language, memorisation,
                                            inference tokens/s, samples
    training/runs/<run>/baselines.json      unigram / uniform / UTF-8 bits-per-byte baselines
    artifacts/shennong-mini-f16.gguf(.sha256)  size + hash of the shipped weights
    artifacts/shennong-mini-hf/model.safetensors  bytes
    tokenizer/eval_results.json             per-language chars/token (optionally incl. sa)

Usage
-----
    python training/fill_model_card.py --run training/runs/shennong-mini-r1
    # dry run (show what would change, write nothing):
    python training/fill_model_card.py --run training/runs/shennong-mini-r1 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARD = ROOT / "model" / "MODEL_CARD.md"
CHINCHILLA_TOKENS_PER_PARAM = 20.0


def jload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def fmt_int(v: float) -> str:
    return f"{int(round(v)):,}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="training/runs/shennong-mini-r1")
    ap.add_argument("--gguf", default="artifacts/shennong-mini-f16.gguf")
    ap.add_argument("--hf-dir", default="artifacts/shennong-mini-hf")
    ap.add_argument("--tokenizer-eval", default="tokenizer/eval_results.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    run_dir = ROOT / args.run
    metrics = jload(run_dir / "metrics.json")
    ev = jload(run_dir / "eval.json")
    baselines = jload(run_dir / "baselines.json")
    tok_eval = jload(ROOT / args.tokenizer_eval)

    if not metrics:
        raise SystemExit(f"no metrics.json in {run_dir} — has the run finished at least one log step?")
    if not ev:
        raise SystemExit(f"no eval.json in {run_dir} — run training/eval_model.py first")

    gguf_path = ROOT / args.gguf
    sha_sidecar = Path(str(gguf_path) + ".sha256")
    gguf_bytes = gguf_path.stat().st_size if gguf_path.exists() else None
    gguf_sha = None
    if sha_sidecar.exists():
        gguf_sha = sha_sidecar.read_text().split()[0]
    elif (run_dir / "eval.json").exists():
        pass
    ckpt_path = run_dir / "ckpt-best.pt"
    if not ckpt_path.exists():
        ckpt_path = run_dir / "ckpt.pt"
    ckpt_bytes = ckpt_path.stat().st_size if ckpt_path.exists() else None
    hf_safetensors = ROOT / args.hf_dir / "model.safetensors"
    hf_bytes = hf_safetensors.stat().st_size if hf_safetensors.exists() else None

    params = int(metrics.get("params") or ev.get("params") or 0)
    steps = int(metrics.get("steps_completed") or 0)
    tokens = int(metrics.get("tokens_seen") or 0)
    wall_s = float(metrics.get("wall_clock_s") or 0.0)
    tok_per_s = float(metrics.get("tokens_per_s") or 0.0)
    epochs = float(metrics.get("epochs") or 0.0)
    train_loss = metrics.get("final_train_loss")

    tok_per_param = tokens / params if params else 0.0
    optimal_tokens = CHINCHILLA_TOKENS_PER_PARAM * params
    pct_optimal = 100.0 * tokens / optimal_tokens if optimal_tokens else 0.0
    shortfall = optimal_tokens / tokens if tokens else 0.0

    pooled = ev.get("held_out_pooled") or {}
    diag = ev.get("per_language_diagnostic") or {}
    bpb = pooled.get("bits_per_byte")
    uni_bpb = baselines.get("baselines", {}).get("unigram_token_model", {}).get("bits_per_byte")

    if bpb is not None and uni_bpb is not None:
        if bpb < uni_bpb:
            margin = uni_bpb / bpb
            outcome = (f"**That is below the unigram baseline by a factor of {margin:.2f}×** "
                       f"({uni_bpb:.3f} → {bpb:.3f} bpb), so the model has learned real contextual "
                       f"structure beyond token frequency — while still being far too weak to be "
                       f"trusted as a knowledge source.")
        else:
            outcome = (f"**That is NOT below the unigram baseline ({uni_bpb:.3f} bpb).** Honest "
                       f"reading: at this token budget the model has learned little beyond token "
                       f"frequency. It is a pipeline demonstration (real tokenizer, real "
                       f"architecture, real logs, real GGUF) and **no capability claim of any kind "
                       f"may be made from it**. This is exactly the outcome the project committed "
                       f"to reporting if it occurred.")
        commentary = (f"It beats the unigram baseline by {uni_bpb / bpb:.2f}×, and a uniform "
                      f"distribution over the vocabulary by "
                      f"{baselines['baselines']['uniform_over_vocab']['bits_per_byte'] / bpb:.2f}×."
                      if bpb < uni_bpb else
                      f"It does **not** beat the unigram baseline — see the honesty block above.")
        fill = {"PENDING_BPB": f"{bpb:.3f}", "PENDING_BPT": f"{pooled.get('mean_nats_per_token', 0) / 0.693147:.3f}",
                "PENDING_BASELINE_OUTCOME": outcome, "PENDING_BPB_COMMENTARY": commentary}
    else:
        raise SystemExit("eval.json is missing pooled bits_per_byte")

    # per-language table (diagnostic)
    def lang_row(code: str, key_ce: str, key_ppl: str, key_bpb: str):
        d = diag.get(code) or {}
        return {key_ce: (f"{d['mean_nats_per_token']:.3f}" if d else "—"),
                key_ppl: (f"{d['perplexity']:.1f}" if d.get("perplexity") else "—"),
                key_bpb: (f"{d['bits_per_byte']:.3f}" if d else "—")}

    fill = {
        **fill,
        "PENDING_STEPS": str(steps),
        "PENDING_TOKENS": fmt_int(tokens),
        "PENDING_EPOCHS": f"{epochs:.2f}",
        "PENDING_TOK_RATIO": f"{tok_per_param:.2f}",
        "PENDING_PCT_OPTIMAL": f"{pct_optimal:.1f} %",
        "PENDING_SHORTFALL": f"{shortfall:.1f}×",
        "PENDING_WALL": f"{wall_s / 60:.1f} min" if wall_s < 7200 else f"{wall_s / 3600:.1f} h",
        "PENDING_TOK_S": f"{tok_per_s:.0f}",
        "PENDING_CE": f"{pooled.get('mean_nats_per_token', 0):.3f}",
        "PENDING_PPL": (f"{pooled['perplexity']:.1f}" if pooled.get("perplexity") else "—"),
        "PENDING_TRAIN_LOSS": f"{train_loss:.3f}" if train_loss is not None else "—",
        "PENDING_MEMORISATION": (f"{ev['memorisation']['mean_longest_verbatim_run_tokens']:.1f}"
                                 if ev.get("memorisation", {}).get("mean_longest_verbatim_run_tokens")
                                 is not None else "—"),
        "PENDING_INFERENCE": (f"{ev['inference']['tokens_per_s']:.0f}"
                              if ev.get("inference") else "—"),
        "PENDING_GGUF_BYTES": fmt_int(gguf_bytes) if gguf_bytes else "—",
        "PENDING_GGUF_SHA": gguf_sha or "—",
        "PENDING_HF_BYTES": fmt_int(hf_bytes) if hf_bytes else "—",
        "PENDING_CKPT_BYTES": fmt_int(ckpt_bytes) if ckpt_bytes else "—",
    }
    fill.update(lang_row("en", "PENDING_CE_EN", "PENDING_PPL_EN", "PENDING_BPB_EN"))
    fill.update(lang_row("zh-Hant", "PENDING_CE_ZH", "PENDING_PPL_ZH", "PENDING_BPB_ZH"))
    fill.update(lang_row("la", "PENDING_CE_LA", "PENDING_PPL_LA", "PENDING_BPB_LA"))

    # Sanskrit chars/token from the tokenizer evaluation (only if it was measured)
    sa = (tok_eval.get("per_language") or {}).get("sa")
    fill["PENDING_SA_C_T"] = f"{sa['chars_per_token']:.3f}" if sa else "3 tokens/char (byte-level, not covered)"

    s = CARD.read_text(encoding="utf-8")
    applied, missing = {}, []
    for key, val in fill.items():
        if key in s:
            s = s.replace(key, str(val))
            applied[key] = val
        else:
            missing.append(key)

    unresolved = sorted(set(re.findall(r"PENDING_[A-Z_]+", s)))
    print(f"applied {len(applied)} substitutions")
    for k, v in sorted(applied.items()):
        print(f"  {k:28s} = {str(v)[:120]}")
    if unresolved:
        print("STILL UNRESOLVED:", unresolved)
    if args.dry_run:
        print("(dry run: nothing written)")
        return 0 if not unresolved else 1
    CARD.write_text(s, encoding="utf-8")
    (run_dir / "model_card_fill.json").write_text(
        json.dumps({"applied": applied, "unresolved": unresolved,
                    "sources": {"metrics": str(run_dir / "metrics.json"),
                                "eval": str(run_dir / "eval.json"),
                                "baselines": str(run_dir / "baselines.json"),
                                "gguf": args.gguf}},
                   indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CARD}")
    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
