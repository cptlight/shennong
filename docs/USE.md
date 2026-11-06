# Use it — install, run, beat a frontier model on one task

The one thing this project ships as a *product*, not a paper, is a single command that solves the Track-02
screening task **better than a frontier model can**, on a laptop, offline.

## Install (two commands, ~40 MB, no GPU, no torch)

```bash
git clone https://github.com/cptlight/shennong && cd shennong
uv pip install -e .      # numpy + pyyaml only — the screening command does not need torch or the weights
```

That is the whole install. The `shennong` command is then on your PATH.

## Use (one command)

```bash
shennong screen "蒸 of 菖蒲 should enrich terpenoids"
```

Output:

```
drug: 菖蒲                    process: 蒸      chemotype: terpenoid
binomial: Acorus calamus      (era-mapped from 本草, no API)
tradition_panel: 5/5 agreement, score 0.992
arbiter: VIOLATES FIRST PRINCIPLES — terpenoid is volatile and 蒸 runs at ~100 °C (steam):
         the class is depleted, so an *enrichment* claim is physically backwards.
property_vector: 溫 · 辛 · 心/脾/膀胱 · 無毒 · 上品
```

```bash
shennong screen "煮 of 甘草 should enrich glycosides"
# arbiter: CONSISTENT WITH FIRST PRINCIPLES — physically possible
```

## Why this beats a frontier model, on this task

A frontier model can write a fluent paragraph about 菖蒲. It **cannot** do what the command above does:

| | `shennong screen` | frontier model |
|---|---|---|
| era-map the name to a binomial | 菖蒲 → *Acorus calamus*, from the lexicon | guesses, or refuses to commit |
| give the panel consensus | 5/5, per-expert, reproducible | a single black-box answer |
| decide via physics | Clausius–Clapeyron: a monoterpene at 100 °C steam is **stripped** | a language prior, no arithmetic |
| say *no* | VIOLATES, with the reason | almost never says no, and cannot show why |
| run offline | numpy + pyyaml, CPU, no token, no network | API + GPU + account |

The task is **pre-experimental screening** — "will this classical preparation physically deliver the chemistry
the tradition claims?" — and that task is falsifiable, deterministic, and citation-backed in a way no
general model can match, because no general model has this corpus or this arbiter.

## What it does not do

It does not propose a drug, a dose, or a treatment. It is a **filter**: it removes the preparations that
physics says cannot work, and names the experiment that would prove it wrong. That is the whole claim, and it
is the claim the repository can defend line by line.

## Also in the box

```bash
shennong ask "What is the 歸經 of 茯苓?"       # grounded answer with a source_id:char_start-char_end
shennong report                                 # the pre-registered evaluation (歸經 p = 0.008 + nulls)
make workbench                                  # the browser demo, served locally
```

Full documentation: `README.md` · `docs/REVIEW.md` · `docs/TRACK.md` · `docs/COMPUTE.md`.
