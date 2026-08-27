# poc-research-graph
Sistema de aquisição e recomendação de documentos baseado em processamento semântico, embeddings e busca vetorial com PostgreSQL/pgvector.

Pipeline poliglota (Java na borda de aquisição, Python no núcleo de
ML/recomendação) com 6 módulos independentes, cada um seu próprio
Dockerfile: **crawler → ingestion → embedding → database →
recommender/api**. Decisões de arquitetura, alternativas consideradas e
limitações conhecidas de cada etapa estão documentadas em
[`ROADMAP.md`](ROADMAP.md) — este README é só o mapa geral + como rodar.

## Requisitos

- Docker + Docker Compose v2 (`docker compose`, não `docker-compose`).
- **~15–18 GB de espaço em disco.** `embedding/`, `recommender/` e `api/`
  compartilham uma imagem base ([`ml-base/`](ml-base/README.md), ~2,9 GB)
  com PyTorch (build **CPU-only** — o wheel padrão do PyPI traz ~4,6 GB de
  bibliotecas CUDA/NVIDIA não usadas, já que nenhum container aqui tem
  GPU) + `sentence-transformers` + o modelo já baixado. Cada um dos três
  soma só suas próprias dependências extras em cima disso (poucos MB).
  `crawler`/`ingestion`/`database` são independentes e leves (200–450 MB
  cada).
- Acesso à rede: `crawler` baixa de `biblioteca.cesar.school` e
  `drive.google.com`; `ml-base` baixa PyTorch, `sentence-transformers` e os
  pesos do modelo (`paraphrase-multilingual-MiniLM-L12-v2`) durante o
  `docker build`.
- Nenhuma credencial externa necessária — tudo é público (acervo CESAR,
  Google Drive) ou local (Postgres com credenciais fixas de POC em
  `docker-compose.yml`, ver `database/README.md`).

## Módulos

| Módulo | O que faz | Tecnologia | Tipo |
|---|---|---|---|
| [`crawler/`](crawler/README.md) | Varre o acervo da Biblioteca CESAR por id, baixa PDF + metadados de TCCs/dissertações/teses elegíveis. | Java 17 + Maven | Batch (`run --rm`) |
| [`ingestion/`](ingestion/README.md) | Extrai texto dos PDFs, remove cabeçalho/rodapé repetido, gera chunks de tamanho fixo. | Python 3.12 + `pypdf` | Batch (`run --rm`) |
| [`ml-base/`](ml-base/README.md) | Imagem base compartilhada por `embedding/`/`recommender/`/`api/` — PyTorch CPU-only + `sentence-transformers` + modelo já baixado. Não é um serviço, precisa ser buildada antes dos três. | — | Imagem base (`docker build`) |
| [`embedding/`](embedding/README.md) | Gera um vetor de 384 dimensões por chunk com um modelo local multilíngue. | Python 3.12 + `sentence-transformers` (via `ml-base/`) | Batch (`run --rm`) |
| [`database/`](database/README.md) | Schema PostgreSQL/pgvector (índice HNSW) + loader idempotente dos chunks/vetores. | PostgreSQL 16 + pgvector | Serviço (`postgres`, longa duração) + loader batch |
| [`recommender/`](recommender/README.md) | CLI: recomenda documentos por id existente ou por busca em texto livre, via similaridade máxima entre chunks. | Python 3.12 + `psycopg`/`pgvector`/`sentence-transformers` | Batch (`run --rm`) |
| [`api/`](api/README.md) | Expõe a mesma lógica do `recommender/` como serviço HTTP (`/search`, `/documents/{id}/recommendations`, docs em `/docs`). | Python 3.12 + FastAPI + Uvicorn | Serviço (longa duração) |

`crawler`/`ingestion`/`embedding`/`db-loader`/`recommender` são ferramentas
batch (`docker compose run --rm ...`, cada uma processa e termina).
`postgres` e `api` são os únicos serviços de longa duração (`docker compose
up -d ...`).

## Quickstart

```
# 0. build da imagem base de ML (uma vez; refaça se mudar dependências em ml-base/)
docker build -t poc-research-graph-ml-base:latest ./ml-base

# 1. baixar PDFs + metadados do acervo CESAR
docker compose run --rm crawler --start 95 --end 105 --out /app/downloads --delay-ms 300

# 2. extrair texto e gerar chunks
docker compose run --rm ingestion

# 3. gerar embeddings (384 dim, paraphrase-multilingual-MiniLM-L12-v2)
docker compose run --rm embedding

# 4. subir o Postgres/pgvector e carregar os dados
docker compose up -d postgres
docker compose run --rm db-loader

# 5a. recomendar via CLI (por documento ou por busca em texto livre)
docker compose run --rm recommender --cod-acervo 100 --top-n 5
docker compose run --rm recommender --query "design de interfaces para aplicativos de streaming"

# 5b. ou subir a API e consultar via HTTP
docker compose up -d api
curl "localhost:8000/search?q=design+de+interfaces+para+streaming&top_n=5"
curl "localhost:8000/documents/100/recommendations?top_n=5"
```

Detalhes de cada comando (flags, formato de entrada/saída, plano de teste
manual) estão no README de cada módulo, linkado na tabela acima.
