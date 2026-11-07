# SHENNONG HF Space — the fine-tuned 1.5B, served for live query (CPU, no GPU, no torch).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# the code + demo page (cloned at build time so it can never drift from the repo)
RUN git clone --depth 1 https://github.com/cptlight/shennong.git /tmp/src \
    && cp -r /tmp/src/shennong /tmp/src/docs/demo /tmp/src/space/app.py /app/ \
    && mkdir -p /app/artifacts /app/models/baseline \
    && rm -rf /tmp/src

RUN pip install llama-cpp-python pyyaml "numpy<2"

# the two models (fine-tuned 1.5B + the unfine-tuned baseline for the side-by-side)
RUN curl -sSL -o /app/artifacts/shennong-1.5b-sft-Q4_K_M.gguf \
      https://github.com/cptlight/shennong/releases/download/v1.17.0/shennong-1.5b-sft-Q4_K_M.gguf \
 && curl -sSL -o /app/models/baseline/qwen2.5-1.5b-instruct-q4_k_m.gguf \
      https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

EXPOSE 7860

CMD ["python", "space/app.py"]
