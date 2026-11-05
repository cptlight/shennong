"""Plot the training curve from a real run's `log.jsonl` / `metrics.json`.

Reads `training/runs/<run_id>/metrics.json` (contract §10.6) and writes
`artifacts/loss_curve.png` + `artifacts/loss_curve.svg`.

The annotation (params, tokens seen, wall clock, val loss) is read from the same files, so the
figure can never disagree with the run log.

Usage
-----
    python training/plot_curve.py                       # newest run in training/runs/
    python training/plot_curve.py --run training/runs/shennong-mini-r1
    python training/plot_curve.py --out-dir artifacts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def newest_run() -> Path:
    runs = [d for d in (ROOT / "training" / "runs").iterdir()
            if d.is_dir() and (d / "metrics.json").exists()]
    if not runs:
        raise SystemExit("no run with metrics.json found in training/runs/")
    return max(runs, key=lambda d: (d / "metrics.json").stat().st_mtime)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="", help="training/runs/<run_id> (default: newest)")
    ap.add_argument("--out-dir", default="artifacts")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run_dir = Path(args.run) if args.run else newest_run()
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    curve = metrics.get("loss_curve") or []
    if not curve:
        raise SystemExit(f"{run_dir}/metrics.json has no loss_curve")

    steps = [e["step"] for e in curve]
    train = [e.get("loss") for e in curve]
    val = [(e["step"], e["val_loss"]) for e in curve if e.get("val_loss") is not None]

    params = metrics.get("params") or 0
    tokens = metrics.get("tokens_seen") or 0
    wall_min = (metrics.get("wall_clock_s") or 0) / 60.0
    final_val = metrics.get("final_val_loss")
    best_val = metrics.get("best_val_loss")
    ppl = metrics.get("val_ppl")
    bpb = metrics.get("bits_per_byte")

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=170)
    ax.plot(steps, train, color="#b4532a", lw=1.5, label="train loss")
    if val:
        ax.plot([p[0] for p in val], [p[1] for p in val], color="#2f6f5e", lw=1.9,
                marker="o", ms=3.2, label="held-out val loss")
    ax.set_xlabel("optimiser step")
    ax.set_ylabel("cross-entropy (nats / token)")
    title = args.title or (
        f"SHENNONG-mini — {params / 1e6:.1f}M params, {tokens / 1e6:.1f}M tokens seen, "
        f"CPU only ({wall_min:.0f} min)")
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, loc="upper right")

    bits = [f"{params / 1e6:.2f}M params", f"{tokens / 1e6:.2f}M tokens",
            f"{wall_min:.0f} min wall clock"]
    if final_val is not None:
        bits.append(f"val {final_val:.3f} nats")
    if ppl:
        bits.append(f"val ppl {ppl:.1f}")
    if bpb:
        bits.append(f"val {bpb:.3f} bits/byte")
    ax.text(0.01, 0.02, " · ".join(bits), transform=ax.transAxes, fontsize=7.3,
            color="#444444", va="bottom")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ("png", "svg"):
        path = out_dir / f"loss_curve.{ext}"
        fig.savefig(path)
        print(f"wrote {path}  ({path.stat().st_size:,} bytes)")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
