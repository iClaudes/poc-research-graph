# poc-research-graph
Sistema de aquisição e recomendação de documentos baseado em processamento semântico, embeddings e busca vetorial com PostgreSQL/pgvector.

Pipeline completo: **crawler → ingestion → embedding → database → recommender/api**.
Detalhes de cada etapa (arquitetura, decisões, limitações conhecidas) em
[`ROADMAP.md`](ROADMAP.md) e no README de cada módulo.

## Quickstart

```
# 1. baixar PDFs + metadados do acervo CESAR
docker compose run --rm crawler --start 95 --end 105 --out /app/downloads --delay-ms 300

# 2. extrair texto e gerar chunks
docker compose run --rm ingestion

# 3. gerar embeddings (384 dim, paraphrase-multilingual-MiniLM-L12-v2)
docker compose run --rm embedding

# 4. subir o Postgres/pgvector e carregar os dados
docker compose up -d postgres
docker compose run --rm db-loader

# 5. subir a API
docker compose up -d api
curl "localhost:8000/search?q=design+de+interfaces+para+streaming&top_n=5"
```

`crawler`/`ingestion`/`embedding`/`db-loader`/`recommender` são ferramentas
batch (`docker compose run --rm ...`, cada uma processa e termina).
`postgres` e `api` são os únicos serviços de longa duração (`docker compose
up -d ...`).
