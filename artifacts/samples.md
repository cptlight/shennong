# SHENNONG-mini — raw generated samples

Run: `shennong-mini-r1` · checkpoint `ckpt-best.pt` (step 199, best val 6.3901) · 8,719,616 parameters · CPU only

These are **raw, unedited** continuations from the from-scratch model, sampled at temperature 0.8, top-k 50, top-p 0.95. A ~9 M-parameter model trained on 1.64 M tokens for ~45 min of CPU compute is a pipeline demonstration, not a knowledge base: expect locally plausible character statistics and unreliable facts. Nothing here is cherry-picked or post-edited.

**Inference throughput:** 13.1 tokens/s for a 128-token generation on this machine (single stream, CPU, fp32, 1 thread).

## English prompts

| # | prompt | continuation |
|---|---|---|
| 1 | `The processing of Aconitum in classical Chinese pharmacy is intended to` | it is in the used in the the fact, and a an case of the same have the other of the same may a very some of the be is in the two the same has an be in the this have the these as-. The a _B.
The very two is the this is of the a in _[a; and which is, and the drug of the case. |
| 2 | `Glycyrrhiza uralensis is described in the Bencao Gangmu as` | the same, for a more is in the same of the large have the most has the the other, a large a water and the one of the a the most one of the in the be be may a very same same it is the the this as the a not with the the an not of a for the its this in _Tat--._ of the the used as the |
| 3 | `A falsifiable hypothesis connecting 炮制 (processing) to modern extraction chemistry:` | O. The other in the one.
=[.
Aicuming the same is the an very said are by the the a an hus. In the one are a that the small, the an in the been the not more be in the same that is a a a be to the a an case, but to its be to the also-d, which the which in |
| 4 | `Salvia miltiorrhiza contains tanshinones, which` | is been not for the more, and one of the same in the the leaves and the water, and one in the same to its very leaves of the a made the _c--m-by (e, in the the same of a the the the a of the the it- is to the all of the small in the large to the other in the its it in a or |
| 5 | `The eighteen antagonisms (十八反) matter to pharmacology because` | have the the _ (S, and the the its same the also the _Daes, but by the first, when that the very the a the in a an a a _Cing to the the a water of the the the the been two the be in the form to the be.
. It is not the first to some be be same it by the the very other in |

## Classical Chinese (中文) prompts

| # | prompt | continuation |
|---|---|---|
| 1 | `甘草味甘，性平，歸` | ，或。以主此》而氣，生云。治以
【氣味。
【附方S1T1
_Cp, and _Pus.
The the a part as the all of the be in the an be be are is the most it in the a a so as the is are used is very very same is the body of the the the |
| 2 | `凡藥炮製之法，` | 非主一，其不用生，此于有人、若其則得，如人中。若大也，以治有则而，以其寒者，其主云，，以而血也。如之，或生为则食者，如治多作作也。主生其下，有者，以有。取、如其 |
| 3 | `神農本草經曰：上品` | ，而亦而其之，用，有非有，其而、亦而食，，是非不，可入、則亦能，得，水、亦不則生者，及以而中，用，以非其此者，其人，今。及治之中，乃而多人之，以如不而者，以則则 |
| 4 | `凡藥有十八反，其間` | 血者，以能，以皆之。
【
【】
【
以
【】
【∶
【治∶
【
\x（一两（一两）
（各一两）
【
（炒）
（各

\x（三分）
【丸（一两，用）甘草（半两）上为末。
\x（去皮） |
| 5 | `傷寒論太陽病，脈浮` | 生∶大，治入大。故即用，用，不其白、主《生云也。以大用、治治其，但下之︰治一之，除其即有以又則而则有。其食如︰但作下为治。又其︰以生之而以病，而病、治，有寒，故 |

## Held-out memorisation check

Mean longest verbatim run shared with the true continuation: **1.4 tokens out of 60 generated**, from verbatim 40-token *training* prefixes (5 samples, temperature 0.7, top-k 40). At this size/token budget the model recombines local phrasing rather than reproducing passages; this is weak-memorisation evidence, not a guarantee.

