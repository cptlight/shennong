# EXPERTS — the twelve-domain panel and its router

## Why a panel and a router

A single model cannot be expert at taxonomy, extraction chemistry, ADME, gut-flora activation and
electronic structure at once. A panel can — provided it is **sparse**: running twelve experts on every
chunk is wasteful and noisy (an ADME question is meaningless for a mineral). The router activates only
what an item can use, exactly like the neural MoE routes FFN experts by a learned gate — except here the
gate is lexical/schema features, because the applicability conditions are known exactly.

## The twelve experts

| # | Expert | Question | Layer | Cost |
|---|---|---|---|---|
| 1 | `ethnobotany` | is the use independently attested across sources/traditions? | ancient record | cheap |
| 2 | `taxonomy` | is the binomial an accepted name with a family? | ancient record | cheap |
| 3 | `theory` | does 四氣/五味/歸經 (rasa/vīrya) frame it? | Asian theory | cheap |
| 4 | `operator` | does the 炮制 term physically act on this class? | Asian pharmacy | cheap |
| 5 | `extraction` | does the process medium extract this chemotype? (polarity) | Asian pharmacy | cheap |
| 6 | `phytochemistry` | is the class actually documented in this plant, how narrowly? | first principles | cheap |
| 7 | `chemotaxonomy` | does the plant family produce this chemistry at all? | first principles | cheap |
| 8 | `toxicology` | safety signal that makes this worth or risky to test? | first principles | cheap |
| 9 | `mechanics` | RDKit MMFF94 conformers: rigid or flexible, how much shape? | first principles | ~1 s |
| 10 | `quantum` | RHF/6-31G(d) electronic structure of the bond class | first principles | cached |
| 11 | `adme` | can it be absorbed and survive first pass? | first principles | cheap |
| 12 | `microbiome` | is it an inactive glycoside needing gut-flora hydrolysis? | first principles | cheap |

## Routing rules (`shennong/experts/router.py`)

| feature in the item | experts activated |
|---|---|
| always | ethnobotany |
| a binomial | taxonomy, chemotaxonomy, phytochemistry |
| a structure/chemotype | mechanics, quantum, adme |
| a 炮制 term | operator, extraction |
| toxicity marking | toxicology |
| classical property vector | theory |
| glycosidic class | microbiome |

## Measured sparsity (`artifacts/expert_routing.json`)

| stream | mean experts/item | fraction of full panel |
|---|---|---|
| rich structured items (203 cross-sections) | 9.15 | 76 % |
| **mixed realistic stream (389 items: 60 rich + 29 rule pairs + 300 raw chunks)** | **2.25** | **18.7 %** |

329 of the 389 items — plain corpus text — activate **one** expert (`ethnobotany`). Only 55 activate
nine. That is the nimbleness property: cost tracks what the item can actually be asked.

## Validation of the physical experts

- **mechanics**: benzene rigid (spread 0.00 kcal), limonene rigid (1.24), menthol flexible (8.06),
  berberine compact (Rg 4.24 Å) — matches known conformational behaviour.
- **quantum**: RHF Koopmans ionisation potentials vs experiment — **MAE 0.82 eV** (expected HF
  overestimate, disclosed rather than hidden). Hydrolysis ΔE ordering ester 49.5 < amide 65.7 <
  acetal 66.7 kJ/mol **independently reproduces the activation-energy priors** used by the kinetic
  model in `physics/simulate.py`.
