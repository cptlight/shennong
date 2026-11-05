# Tradition-first staging: ancient record → Asian medicine → Western medicine

2026-11-05T11:39:37-0800

**The ordering is the argument.** The usual computational approach starts from a Western
compound–target database, then looks for a plant, then cites a traditional use as colour.
That makes the tradition a marketing layer. Here the order is inverted and enforced as gates:

```
STAGE 1  ANCIENT RECORD       attested in the classical corpus?          GATE
STAGE 2  ASIAN THEORY         四氣/五味/歸經 (rasa/vīrya) frame it?      GATE
STAGE 3  ASIAN PHARMACY       炮制 / formula layer support it?           score
STAGE 4  MODERN CORROBORATION measured chemistry / bioactivity agrees?   score, CANNOT rescue
```

**A claim failing either gate is out regardless of how strong the modern evidence is.** Modern
data may strengthen a tradition-grounded hypothesis; it may never substitute for one.

## Results over 203 candidates

- **survive everything (tradition-grounded + physically consistent):** 18
- excluded at the ancient-record gate: 151
- excluded at the Asian-theory gate: 24
- **excluded by first principles — physically impossible as stated:** 10

> **What stage 4 actually is, in this run.** The two stage-4 experts draw on the
> Wikidata-derived compound table and our own 毒 markings — **not** measured ChEMBL bioactivity
> or Open Targets genetics. So "modern-corroborated" here means *structure/class evidence*,
> not *assayed evidence*. Because both signals are cheap and correlated, the
> "awaiting corroboration" class is empty in this run; it will populate once ChEMBL can
> disagree with the tradition rather than echo it.

## The strongest class

| Hypothesis | Score | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|---|---|---|---|---|---|
| 炙 of 甘草 (Glycyrrhiza uralensis) should measurably change its flavonoid conte | 0.922 | 1.00 | 1.00 | 0.85 | 0.85 |
| 煮 of 巴豆 (Croton tiglium) should measurably change its alkaloid content | 0.919 | 0.99 | 1.00 | 0.85 | 0.85 |
| 研 of 巴豆 (Croton tiglium) should measurably change its alkaloid content | 0.919 | 0.99 | 1.00 | 0.85 | 0.85 |
| 焙 of 附子 (Aconitum carmichaelii) should measurably change its terpenoid conte | 0.914 | 1.00 | 1.00 | 0.80 | 0.85 |
| 焙 of 知母 (Anemarrhena asphodeloides) should measurably change its terpenoid c | 0.914 | 1.00 | 1.00 | 0.80 | 0.85 |
| 蒸 of 菖蒲 (Acorus calamus) should measurably change its alkaloid content | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 蒸 of 升麻 (Actaea cimicifuga) should measurably change its alkaloid content | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 炮 of 附子 (Aconitum carmichaelii) should measurably change its alkaloid conten | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 焙 of 附子 (Aconitum carmichaelii) should measurably change its alkaloid conten | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 炮 of 甘草 (Glycyrrhiza uralensis) should measurably change its flavonoid conte | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 炮 of 甘草 (Glycyrrhiza uralensis) should measurably change its steroid content | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 炙 of 甘草 (Glycyrrhiza uralensis) should measurably change its steroid content | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 蒸 of 甘草 (Glycyrrhiza uralensis) should measurably change its flavonoid conte | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 蒸 of 甘草 (Glycyrrhiza uralensis) should measurably change its steroid content | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 焙 of 知母 (Anemarrhena asphodeloides) should measurably change its alkaloid co | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 焙 of 知母 (Anemarrhena asphodeloides) should measurably change its steroid con | 0.898 | 1.00 | 1.00 | 0.70 | 0.85 |
| 研 of 巴豆 (Croton tiglium) should measurably change its terpenoid content | 0.895 | 0.99 | 1.00 | 0.70 | 0.85 |
| 焙 of 知母 (Anemarrhena asphodeloides) should measurably change its phenylpropa | 0.880 | 1.00 | 1.00 | 0.70 | 0.80 |

## Tradition-grounded leads awaiting modern corroboration

These pass both gates on the tradition's own terms — the class a pharmacognosist would want
before any Western assay is run.

| Hypothesis | Score |
|---|---|

## What was excluded, and why that matters

**151** candidates were excluded because the classical record does not attest them,
and **24** because the Asian theory layer does not frame them. Under a
Western-first pipeline those would have been *priorities*; here they are non-hypotheses.
That is the difference the ordering makes.
