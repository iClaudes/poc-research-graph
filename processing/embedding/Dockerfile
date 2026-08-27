FROM poc-research-graph-ml-base:latest
WORKDIR /app
COPY embedding ./embedding
RUN mkdir -p ingested embedded
ENTRYPOINT ["python", "-m", "embedding.cli"]
