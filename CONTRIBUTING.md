# Contributing

Everything here is **Apache-2.0** — code and weights. Fork it, change it, ship it. The only thing we ask is
that you keep the two things this project is actually for: **provenance** and **falsifiability**.

---

## The four things worth extending

### 1 · Add a corpus source

New sources go through `corpus/registry/sources.yaml` and `scripts/ingest.py`, which has a **non-overridable
licence gate**. A source that cannot legally be redistributed is rejected, not "noted and used anyway" —
GRETIL was rejected for exactly this reason (CC BY-**NC**-SA cannot ship in a public repo).

```yaml
- id: pg_my_new_text
  title: 新本草
  title_en: New Materia Medica
  year: 1700
  lang: zh-Hant
  tradition: tcm
  tier: 2
  licence: public-domain
  url: https://example.org/text.txt
```

Then `make corpus`. **Do not** add a source whose licence you have not read. If you are unsure, open an issue
rather than a pull request.

### 2 · Add an expert

An expert is a function with a contract, not a prompt:

```python
def my_expert(world, item) -> Proposal:
    score = ...            # 0..1
    return Proposal(domain="my_domain", score=score, evidence=[...], reasoning="...")
```

Register it in `shennong/experts/experts.py` (or `advanced.py` / `extra.py`), assign it a stage in
`shennong/experts/stages.py`, and it is routable immediately — `docs/EXPERTS.md` documents the contract and
the routing rules. **A gate is judged by its designated expert**, not by "any expert in that stage"; adding a
weak expert to a gate stage must not be able to move a gate.

The expert is then measured automatically: `make selfobserve`/`python -m shennong.experts.steering` scores it
by whether its confidence **predicts the physics arbiter's verdict** — never by whether it makes claims pass.

### 3 · Retrain

```bash
make train-mini                 # dense baseline
make train-flagship             # 0.5 B target (GPU)
make curriculum STEPS=40        # staged: foundations → canon → regional → patterns → method → grounding
make selfobserve                # probe: does the model represent its own groundedness?
```

`training/curriculum.py` builds its stages from the registry metadata, so new sources land in the right stage
automatically. **If you change the weights, re-run `make novelty`, `make compute` and the contract checks
before opening a PR.**

### 4 · Improve the demo

The page is generated — never edit `docs/demo/index.html` by hand:

```bash
make demo        # rebuilds docs/demo/{index.html,data.json,browser_corpus.json}
```

It reads `artifacts/*.json`. If you add an artefact, add it to `build_data()` in `scripts/build_demo.py` so
the page can show it.

---

## Deploying the live demo

The Space clones this repository, so **a push to `main` is what updates it** — there is no second copy to
drift.

```bash
export HF_TOKEN=hf_...                     # write token
./scripts/deploy_space.sh your-user/shennong
```

Locally: `make workbench` then open `/demo/`. In a codespace: same command, use the forwarded port.

---

## The rules this project holds itself to

1. **Never lower a threshold to make a number pass.** If a result dies, publish that it died — the
   `docs/` tree contains several negative results for this reason (0/172 processing rules surviving FDR,
   the curriculum losing to the base model, the self-observation probe at chance).
2. **Western literature never votes.** It is an observation, not an arbiter. Physics arbitrates.
3. **No fixture presented as live.** The Workbench prints which panels are fixtures; `--strict` refuses.
4. **A claim without a span is not emitted.** If retrieval finds nothing, the answer is "the corpus does not
   record this".
5. **Every artefact is regenerable.** If you cannot rebuild it from a command in the Makefile, it is not
   evidence.

## Practical notes

- **CPU-only is supported and tested.** No CUDA required; the whole pipeline runs on a laptop.
- **Chinese, Sanskrit and Latin text is UTF-8 throughout.** Do not normalise away 繁體.
- **Large files** belong in releases, not the repo: checkpoints are attached to releases, and
  `corpus/processed/corpus.jsonl.gz` is committed compressed.
- **Tests**: `make test` and `python scripts/verify_contracts.py` (18–28 contract checks). A PR that fails
  either is not mergeable.
