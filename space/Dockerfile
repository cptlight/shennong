# SHENNONG — Hugging Face Space (Docker SDK)
#
# Clones the public repo rather than duplicating it, so the Space can never drift from the source. The
# checkpoint comes from the project's own release, which is also Apache-2.0.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf

RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone --depth 1 https://github.com/cptlight/shennong.git . \
    && rm -rf .git

RUN pip install "numpy<2" tokenizers pyyaml tqdm safetensors \
    && pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

# corpus is committed compressed; the retrieval index needs it plain
RUN test -f corpus/processed/corpus.jsonl.gz && gunzip -c corpus/processed/corpus.jsonl.gz > corpus/processed/corpus.jsonl

# trained weights from the project's release (Apache-2.0)
RUN mkdir -p training/runs/seed \
    && curl -sSL -o training/runs/seed/ckpt-best.pt \
       https://github.com/cptlight/shennong/releases/download/ckpt-base/ckpt-best.pt \
    && ls -l training/runs/seed/ckpt-best.pt

ENV SHENNONG_CKPT=training/runs/seed/ckpt-best.pt
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
    CMD curl -fsS http://127.0.0.1:7860/api/health || exit 1

CMD ["python", "app/serve.py", "--host", "0.0.0.0", "--port", "7860", "--demo-root"]
