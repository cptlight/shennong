# RAW TRAINING NUMBERS

Generated 2026-11-06 05:37 from `training/runs/*/metrics.json` by `scripts/training_numbers.py`. No number below is typed by hand.

## Pre-training (corpus in shuffled order)

| run | family | params | active | steps | tokens | epochs | train | val | ppl | tok/s | wall s | threads |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `shennong-mini-r1` | dense | 8,719,616 | — | 200 | 1,638,400 | 0.098 | 6.3662 | 6.3901 | 605.31 | 604.3 | 2711.0 | 1 |
| `shennong-moe-r1` | moe | 19,342,616 | 12,264,728 | 200 | 1,638,400 | 0.055 | 4.1944 | 5.4828 | 240.52 | 768.7 | 2131.3 | 2 |
| `shennong-moe-r2` | moe | 19,342,616 | 12,264,728 | 221 | 1,810,432 | 0.061 | 5.4259 | — | — | 9024.9 | 200.6 | 5 |

**Corpus each run could see:**

| run | train tokens | val tokens | chars | corpus file |
|---|---|---|---|---|
| `shennong-mini-r1` | 16,687,735 | 339,639 | 38,242,644 | `/Users/tom/Documents/ETHno/corpus/processed/corpus.jsonl` |
| `shennong-moe-r1` | 29,819,163 | 619,492 | 45,604,249 | `/Users/tom/Documents/ETHno/corpus/processed/corpus.jsonl` |
| `shennong-moe-r2` | 29,819,163 | 619,492 | 45,604,249 | `/Users/tom/Documents/ETHno/corpus/processed/corpus.jsonl` |

## Curriculum (staged, resuming from the MoE checkpoint)

`steps` and `tokens` are **cumulative** across stages (the trainer resumes and keeps counting).

| stage | cumulative steps | cumulative tokens | new steps | new tokens | train | val | ppl | tok/s | wall s | epochs | stage corpus tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| curriculum-0_foundations | 239 | 1,957,888 | 40 | 327,680 | 6.8342 | 6.8320 | 927.06 | 2408.9 | 812.8 | 0.45 | 4,313,424 |
| curriculum-1_asian_classics | 278 | 2,277,376 | 39 | 319,488 | 6.6191 | 6.7936 | 892.09 | 6687.3 | 340.6 | 0.21 | 10,925,624 |
| curriculum-2_regional | 317 | 2,596,864 | 39 | 319,488 | 2.9955 | 2.7051 | 14.96 | 7344.5 | 353.6 | 0.20 | 12,709,339 |
| curriculum-3_alchemy_process | 356 | 2,916,352 | 39 | 319,488 | 6.6589 | 6.6512 | 773.72 | 8741.4 | 333.6 | 2.25 | 1,296,744 |
| curriculum-4_patterns | 395 | 3,235,840 | 39 | 319,488 | 6.4409 | 6.4043 | 604.41 | 1505.1 | 2149.9 | 23.48 | 137,810 |
| curriculum-5_pharmacology | 434 | 3,555,328 | 39 | 319,488 | 6.8273 | 6.8272 | 922.60 | 2554.7 | 1391.7 | 0.64 | 5,565,954 |
| curriculum-6_grounding | 473 | 3,874,816 | 39 | 319,488 | 6.2285 | 6.2270 | 506.23 | 12007.0 | 322.7 | 69.57 | 55,697 |

**Each stage validates on its own held-out slice**, so val losses across stages are **not comparable** — a lower number means an easier corpus, not a better model.

## Track-02 SFT

| field | value |
|---|---|
| checkpoint | `training/runs/sft-r3/ckpt-best.pt` |
| step | 100 |
| base val (answer-only) | 7.8974 |
| best val (answer-only) | 2.6136 |
| improvement | 5.2839 nats |
| train examples | 1,400 |
| val examples | 90 |

No `metrics.json` exists for this run: it was stopped at step 100 of 250 because machine load hit 15 and throughput fell to 0.03 it/s. The numbers above come from the checkpoint's own `sft` metadata, written when the best checkpoint was saved.

## Which numbers are not trustworthy, and why

- **`shennong-moe-r2`**: `val_loss` is `null` and `tokens_per_s` reads 9,024. The run was killed before its first evaluation and the throughput is a cache-timing artefact. It is listed for completeness and **must not be used** in any comparison.
- **`tok/s` in every curriculum run is inflated** (up to 12,007) because resumed steps hit the token cache and complete almost instantly; `wall_clock_s` is the honest measure.
- **MoE vs dense throughput is confounded**: the MoE run used 2 torch threads, the dense run 1. The capacity-per-FLOP ratio (1.58×) and the val-loss delta do not depend on threads; the speed numbers do.
- **All runs are ~0.1–2 % of compute-optimal tokens** at these parameter counts. They are architecture ablations and task-shape demos, not capability results.

## Reproduce

```bash
make train-mini        # dense baseline, 200 steps
make train-moe         # sparse MoE, same token budget
make curriculum STEPS=40
make sft               # Track-02 fine-tune
```
