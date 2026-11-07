# SHENNONG HF Space — the fine-tuned 1.5B, served for live query + Track-02 screening.
# CPU only, no GPU, no torch: llama-cpp-python runs the Q4 GGUF directly.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Code + demo page are cloned at build time so the Space can never drift from the repo.
# Layout must match space/app.py: ROOT = /app (app.py lives at /app/space/app.py, so parent.parent = /app),
# DEMO_DIR = /app/docs/demo, models at /app/artifacts and /app/models/baseline.
RUN git clone --depth 1 https://github.com/cptlight/shennong.git /tmp/src \
    && mkdir -p /app/space /app/docs /app/artifacts /app/models/baseline \
               /app/corpus/processed/structured /app/scripts \
    && cp -r /tmp/src/shennong /app/shennong \
    && cp -r /tmp/src/docs/demo /app/docs/demo \
    && cp /tmp/src/space/app.py /app/space/app.py \
    && cp /tmp/src/corpus/processed/structured/compounds.csv /app/corpus/processed/structured/compounds.csv \
    && cp /tmp/src/scripts/build_fingerprints.py /app/scripts/build_fingerprints.py \
    && rm -rf /tmp/src

# prebuilt CPU wheel — avoids a long source compile
RUN pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
      llama-cpp-python "numpy<2" pyyaml rdkit

# precompute the compound fingerprints so the live screen is ~2 s instead of ~40 s (2-vCPU timeout)
RUN python scripts/build_fingerprints.py

# the two models: the fine-tuned 1.5B and the unfine-tuned baseline for the side-by-side
RUN curl -sSL -o /app/artifacts/shennong-1.5b-sft-Q4_K_M.gguf \
      https://github.com/cptlight/shennong/releases/download/v1.17.0/shennong-1.5b-sft-Q4_K_M.gguf \
 && curl -sSL -o /app/models/baseline/qwen2.5-1.5b-instruct-q4_k_m.gguf \
      https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

EXPOSE 7860

CMD ["python", "space/app.py"]
