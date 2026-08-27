FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database ./database
RUN mkdir -p embedded
ENTRYPOINT ["python", "-m", "database.cli"]
