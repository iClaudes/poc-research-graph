ARG ML_BASE_TAG=latest
FROM poc-research-graph-ml-base:${ML_BASE_TAG}
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
COPY static ./static
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
