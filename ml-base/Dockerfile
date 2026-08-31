FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# CPU-only by default — the default PyPI wheel pulls in ~4.6GB of unused
# CUDA/NVIDIA libraries on machines with no GPU. Override TORCH_INDEX_URL
# (e.g. --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124)
# to build a GPU-enabled variant instead — see docker-compose.gpu.yml.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir torch --index-url ${TORCH_INDEX_URL}
RUN pip install --no-cache-dir "sentence-transformers>=3.0,<4"

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
