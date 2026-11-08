# Resolution — what the 14.1 % meant, and what the real numbers are

This file replaces a published number that was not measuring what it claimed.

## The old metric measured an impossible task

`shennong/eval/harness.py` scored drug-name→taxon resolution at **14.1 % (n=368)**. The implementation:

```python
train = {surface: v for surface, v in items if not held_out(surface)}
test  = [(surface, v) for surface, v in items if held_out(surface)]
...
prediction = train.get(surface, (None, 0.0))[0]     # surface is BY DEFINITION not in train
```

Every test surface is held out of the training half, so the exact lookup **always misses**, and the code falls
back to character-bigram Jaccard ≥ 0.6. But two names for one plant share no characters — `甘草` vs `Licorice`,
`丹參` vs `Salvia miltiorrhiza`. No lexicon-based resolver can score above chance on that task.

**It measured "guess an unseen name from string shape", not resolution.** Reported as "accuracy", it looked like
the weakest link in the system. It was a benchmark bug.

## What is measured now

`python scripts/audit_resolution.py` → `artifacts/resolution_audit.json`

### 1 · In-lexicon accuracy — **1.000**

For a surface that is in the lexicon, the resolver returns its stored binomial. Anything below 1.0 would be a
bug, not a limitation.

### 2 · Corpus coverage — the number that matters

Of the **14,390** drug mentions across the structured tables:

| | mentions | share |
|---|---|---|
| **resolved** | **6,193** | **43.0 %** |
| not resolved | 8,197 | 57.0 % |

But that denominator is wrong. The classical pharmacopoeia is **not a plant list**:

| substance class | mentions | share | can resolve to a binomial? |
|---|---|---|---|
| plant | 6,805 | 47.3 % | yes |
| animal | 3,381 | 23.5 % | **no** — fur, shell, horn, bone |
| plant part | 2,139 | 14.9 % | only if the parent plant is known |
| mineral | 1,189 | 8.3 % | **no** — cinnabar, alum, furnace earth |
| object | 588 | 4.1 % | **no** — a rope, an undershirt, a sleeping mat |
| human-derived | 288 | 2.0 % | **no** — hair, urine sediment, urine crystal |

**37.9 % of the corpus can never resolve to a botanical binomial, because it is not botanical.**
Real entries from our corpus: `縛豬繩` (a rope used to tie pigs), `亂髮` (human hair), `溺白垽` (urine sediment),
`秋石` (urine crystal), `伏龍肝` (furnace earth), `汗衫` (an undershirt), `死人枕席` (a dead man's sleeping mat).

On the material that could resolve:

> **plant-derived coverage = 48.7 %** (4,357 of 8,944 mentions)

That is the honest headline: **we resolve about half of the botanical materia medica, and the other half are
archaic names absent from every open lexicon we could find.**

### 3 · Unseen-name generalisation — **~0, and that is correct**

A lexicon resolver cannot map a surface it has never seen. Reported separately and labelled, never folded into
the headline. Closing this needs a **larger historical lexicon** — data acquisition, not a better string metric.

## Why fuzzy matching was rejected

Character-similarity fallback was tested as a coverage fix: it recovered **2.9 %** of mentions and roughly half of
its candidate links were wrong (`蚯蚓泥`, clay mixed with earthworm, matched to `蚯蚓`, earthworm). A resolver that
mis-maps one name in eight is worse than one that reports "unknown", because every downstream layer inherits the
error. It was not shipped.

## What this changes in the pitch

Weakest link, before:

> "Drug-name → taxon resolution is 14.1 % accurate (n = 368). Every downstream layer inherits that error."

Weakest link, now:

> "About half the botanical materia medica resolves; the other half are archaic names no open lexicon holds.
> And a third of what looks like a plant list isn't botanical at all — 24 % animal, 8 % mineral, 4 % manufactured
> objects, 2 % human-derived. We report both rather than diluting the denominator."

The second is defensible, checkable, and it says something a domain judge did not already know.

## Reproduce

```bash
python scripts/audit_resolution.py
python -c "from shennong.eval.harness import resolution_benchmark; from shennong.extract.lexicons import build_lexicons; print(resolution_benchmark(build_lexicons()))"
```
