# SHENNONG — one command per stage. CPU-only. Reproducible from a clean clone.
PY ?= .venv/bin/python
UV ?= uv

.DEFAULT_GOAL := help

help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup:  ## create the CPU venv and install everything
	$(UV) venv --python 3.12 .venv
	$(UV) pip install --python .venv/bin/python "torch==2.2.2" "numpy<2" pyyaml requests tokenizers \
		tqdm regex matplotlib pytest safetensors gguf beautifulsoup4 lxml
	@echo "OK — venv at .venv"

corpus:  ## fetch + licence-audit + clean the Asian-medicine corpus → corpus/processed/corpus.jsonl
	$(PY) data/build_corpus.py --out corpus/processed

tokenizer:  ## train the multilingual (zh-Hant / sa / en) BPE
	$(PY) tokenizer/train_tokenizer.py --corpus corpus/processed/corpus.jsonl --vocab 24000

train-mini:  ## train shennong-mini from scratch on CPU (real run, real logs)
	$(PY) training/train_pretrain.py --config model/configs/shennong-mini-cpu.json

novelty:  ## recompute structural novelty (must run after any `shi` regeneration)
	$(PY) scripts/structural_novelty.py

export:  ## export GGUF (< 1 GB) + sha256
	$(PY) training/merge_quantize.py --export-gguf

eval:  ## run the evaluation harness → eval/report.json
	$(PY) -m shennong.cli report --out eval/report.json

app-data:  ## materialise the Workbench data files from the pipeline
	$(PY) -m shennong.cli cai --corpus-dir corpus/processed --out-passages app/data/passages.json
	$(PY) -m shennong.cli pei --corpus-dir corpus/processed --out-kg app/data/kg.json
	$(PY) -m shennong.cli shi --n 12 --out app/data/hypotheses.json

demo:  ## rebuild the static judge demo -> docs/demo/
	$(PY) scripts/build_demo.py

workbench:  ## serve the local Workbench (stdlib only)
	$(PY) app/serve.py

train-flagship:  ## FREE GPU (Colab/Kaggle): domain CPT + SFT of Qwen2.5-0.5B -> <1 GB GGUF
	$(PY) training/flagship/train_flagship.py --stage both
	bash training/flagship/export_gguf.sh

test:  ## unit + behavioural tests
	$(PY) -m pytest

all: corpus tokenizer train-mini export eval app-data  ## full pipeline

clean:  ## remove caches (keeps corpus and checkpoints)
	find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rm -rf .pytest_cache

.PHONY: help setup corpus tokenizer train-mini train-flagship novelty demo export eval app-data workbench test all clean
