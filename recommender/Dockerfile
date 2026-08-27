FROM poc-research-graph-ml-base:latest
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY recommender ./recommender
RUN mkdir -p recommendations
ENTRYPOINT ["python", "-m", "recommender.cli"]
