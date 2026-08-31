ARG ML_BASE_TAG=latest
FROM poc-research-graph-ml-base:${ML_BASE_TAG}
WORKDIR /app
COPY embedding ./embedding
RUN mkdir -p ingested embedded
ENTRYPOINT ["python", "-m", "embedding.cli"]
