# poc-research-graph
Sistema de aquisição e recomendação de documentos baseado em processamento semântico, embeddings e busca vetorial com PostgreSQL/pgvector.

Pipeline poliglota (Java na borda de aquisição, Python no núcleo de
ML/recomendação): **crawler → processing (ingestion + embedding) →
database → api**. Decisões de arquitetura, alternativas consideradas e
limitações conhecidas de cada etapa estão documentadas em
[`ROADMAP.md`](ROADMAP.md); um passo a passo narrado de como operar o
sistema (com exemplo prático e solução de problemas comuns) está em
[`USAGE.md`](USAGE.md) — este README é só o mapa geral + como rodar.

## Requisitos

- Docker + Docker Compose v2 (`docker compose`, não `docker-compose`).
- **~15–18 GB de espaço em disco.** `processing/embedding/` e `api/`
  compartilham uma imagem base ([`ml-base/`](ml-base/README.md), ~2,9 GB)
  com PyTorch (build **CPU-only** — o wheel padrão do PyPI traz ~4,6 GB de
  bibliotecas CUDA/NVIDIA não usadas, já que nenhum container aqui tem
  GPU) + `sentence-transformers` + o modelo já baixado. Cada um dos dois
  soma só suas próprias dependências extras em cima disso (poucos MB).
  `crawler`/`processing/ingestion`/`database` são independentes e leves
  (200–450 MB cada).
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
| [`ml-base/`](ml-base/README.md) | Imagem base compartilhada por `processing/embedding/` e `api/` — PyTorch CPU-only + `sentence-transformers` + modelo já baixado. Não é um serviço, precisa ser buildada antes dos dois. Fica solta na raiz (não agrupada com `database/` como "infra"): é uma camada de build reaproveitada por outros módulos, `database/` é um serviço com estado de verdade — categorias diferentes, agrupar as duas só pelo "não é lógica de negócio" bagunçaria mais do que ajudaria. | — | Imagem base (`docker build`) |
| [`processing/`](processing/README.md) | Agrupa os dois estágios de processamento de texto: [`ingestion/`](processing/ingestion/README.md) (extrai texto dos PDFs, gera chunks) e [`embedding/`](processing/embedding/README.md) (gera vetores de 384 dim por chunk). Dockerfiles/imagens separados de propósito — pesos de dependência bem diferentes. | Python 3.12 (`pypdf` / `sentence-transformers` via `ml-base/`) | Batch (`run --rm`) |
| [`database/`](database/README.md) | Schema PostgreSQL/pgvector (índice HNSW) + loader idempotente dos chunks/vetores. | PostgreSQL 16 + pgvector | Serviço (`postgres`, longa duração) + loader batch |
| [`api/`](api/README.md) | Recomenda documentos por id existente ou por busca em texto livre, via similaridade máxima entre chunks — como CLI (`python -m api.cli`), como serviço HTTP (`/search`, `/documents/{id}/recommendations`, docs em `/docs`) e como interface web simples (HTML/JS puro, sem build, servida na raiz `/` pelo mesmo processo), mesmo código pros três. | Python 3.12 + FastAPI/Uvicorn + `psycopg`/`pgvector`/`sentence-transformers` | CLI batch + serviço HTTP (longa duração) |

`crawler`/`ingestion`/`embedding`/`db-loader` são ferramentas batch
(`docker compose run --rm ...`, cada uma processa e termina). `api` serve
os dois papéis: `docker compose run --rm api python -m api.cli ...` pra
uso pontual, ou `docker compose up -d api` pra deixar o servidor HTTP de
pé (junto com `postgres`, os únicos serviços de longa duração).

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
docker compose run --rm api python -m api.cli --cod-acervo 100 --top-n 5
docker compose run --rm api python -m api.cli --query "design de interfaces para aplicativos de streaming"

# 5b. ou subir a API e consultar via HTTP
docker compose up -d api
curl "localhost:8000/search?q=design+de+interfaces+para+streaming&top_n=5"
curl "localhost:8000/documents/100/recommendations?top_n=5"

# 5c. ou abrir http://localhost:8000/ no navegador (mesma API, interface web)
```

Detalhes de cada comando (flags, formato de entrada/saída, plano de teste
manual) estão no README de cada módulo, linkado na tabela acima.
