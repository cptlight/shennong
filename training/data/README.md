# SHENNONG instruction data (hand-written, task-shape demonstration)

**What this is.** Two small, hand-written JSONL files covering the five task shapes SHENNONG
needs for its downstream work. Written by the `model-forge` member of this team in November 2026
while the from-scratch pretraining run was executing. **Nothing here is scraped, and nothing here
is a capability claim.** ~50 examples demonstrate a *task shape*; they do not teach a 9 M- or
494 M-parameter model a skill.

| file | rows | task shapes |
|---|---|---|
| `instruction_drug_candidate.jsonl` | 22 | `drug_candidate` — classical drug entry + 性味歸經 (or rasa/vīrya/doṣa) + known constituents → chemotype → candidate molecule → mechanism hypothesis → assay → falsification → residual risk |
| `instruction_core.jsonl` | 33 | `entity_extraction` (10), `process_translation` (8), `hypothesis_critique` (8), `falsification` (7) |

Total: **55 hand-written examples**.

## Format

One JSON object per line:

```json
{"task": "drug_candidate", "tradition": "tcm",
 "messages": [{"role": "user", "content": "..."},
              {"role": "assistant", "content": "..."}]}
```

`training/sft_lora.py` wraps each row in the vocabulary's chat tokens
(`<|system|> … <|eos|><|user|> … <|eos|><|assistant|> … <|eos|>`) and computes loss **only** on
the assistant spans (everything before `<|assistant|>` is masked with `-100`).

## Editorial rules used when writing the responses

1. **Hypothesis, not evidence.** Every mechanistic sentence is a hypothesis with a named assay
   and a stated kill criterion. No response claims efficacy.
2. **Separation of voices.** What the classical text says is labelled as such and is not
   conflated with what modern evidence shows.
3. **No dosing, no self-treatment, no extraction/synthesis routes.** Classical quantities are
   quoted only as historical text and explicitly marked as *not* a prescription.
4. **Toxicity is stated, not softened.** 附子 (aconitine), 雷公藤-type toxicity, aloe
   anthraquinones, 何首烏 hepatotoxicity, thujone — these are presented as hazards and as the
   scientific object (e.g. "does processing reduce it?"), never as something to use.
5. **Theory claims are testable claims.** 四氣五味, 歸經, tridoṣa, vīrya are operationalised
   (endpoint, assay, pre-registration, permutation null) or explicitly called interpretive.
6. **Pan-assay interference is called out** for flavonoids, quinones, curcuminoids and tannins,
   because a natural-product hypothesis that ignores PAINS is not a hypothesis.

## What this data is *not*

- It is not sufficient for instruction-following. A model trained on 52 examples will imitate
  the *format* and nothing more.
- It is not expert-validated. These are the work of one team member reading the literature
  summarised in the responses; a pharmacognosist would find errors. The model card says so.
- It is not a prescription dataset and must not be presented as clinical content.

## Reproduce / inspect

```bash
.venv/bin/python - <<'PY'
import json, pathlib
for p in sorted(pathlib.Path("training/data").glob("*.jsonl")):
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(p, len(rows), sorted({r["task"] for r in rows}))
PY
```

## Two on-disk formats (same content, two consumers)

The same 55 hand-written examples are stored twice because two different trainers read them:

| file | format | consumer |
|---|---|---|
| `instruction_core.jsonl`, `instruction_drug_candidate.jsonl` | `{"task","tradition","messages":[{"role","content"},…]}` | `training/sft_lora.py` (our own tokenizer, assistant-token-masked loss) |
| `sft_instructions.jsonl` | `{"task","tradition","system","instruction","output"}` | `training/flagship/train_flagship.py` (Qwen chat template, `apply_chat_template`) |

`sft_instructions.jsonl` is generated from the other two (a one-line transformation, no new
content); it exists so the flagship script's default path works unchanged.
