# api

Serviço HTTP (FastAPI) que expõe busca semântica e recomendação sobre o
acervo CESAR, consultando o PostgreSQL/pgvector já carregado pelo
`database/`. Reaproveita a mesma lógica de agregação por similaridade
máxima do `recommender/` (ver `recommender/README.md` para o algoritmo e
as limitações conhecidas — elas se aplicam aqui também).

**Diferente dos módulos anteriores**, que são ferramentas de linha de
comando pontuais (`docker compose run --rm ...`), a `api/` é um processo
de longa duração — fica de pé como o `postgres`, via `docker compose up`.
Por isso ela também carrega o modelo de embedding e abre o pool de conexão
com o banco **uma única vez**, no startup, em vez de a cada execução.

## Rotas

- `GET /health` — `{"status": "ok"}`.
- `GET /documents?limit=50&offset=0` — lista documentos.
- `GET /documents/{cod_acervo}` — detalhe de um documento (`404` se não
  existir).
- `GET /documents/{cod_acervo}/recommendations?top_n=5` — documentos mais
  parecidos com esse (`404` se o documento não existir).
- `GET /search?q=texto+livre&top_n=5` — busca semântica em texto livre.

Documentação interativa (Swagger UI) em `/docs`.

## Rodando com Docker

PyTorch + `sentence-transformers` vêm da imagem base
[`ml-base/`](../ml-base/README.md) (compartilhada com `embedding/` e
`recommender/`) — **precisa buildar `ml-base/` antes** (ver seu README):

```
docker build -t poc-research-graph-ml-base:latest ./ml-base   # se ainda não existir
docker compose up -d postgres api
```

Requer o `postgres` com dados carregados (ver `database/README.md`).

```
curl localhost:8000/health
curl localhost:8000/documents
curl localhost:8000/documents/100
curl "localhost:8000/documents/100/recommendations?top_n=5"
curl "localhost:8000/search?q=design+de+interfaces+para+streaming&top_n=5"
```

## Rodando localmente

```
cd api
pip install -r requirements.txt
DATABASE_URL=postgresql://research_graph:research_graph@localhost:5432/research_graph uvicorn api.main:app --reload
```

## Como testar

1. Ter o pipeline completo rodando (`crawler` → `ingestion` → `embedding`
   → `db-loader`, ver READMEs respectivos).
2. `docker compose up -d postgres api`.
3. Rodar os `curl` acima e conferir: `/health` responde ok; `/documents`
   lista os documentos carregados; `/documents/{id}` inexistente retorna
   `404`; `/search` e `/recommendations` retornam resultados coerentes
   (mesmo comportamento já validado no `recommender/` CLI).
4. Conferir nos logs do container (`docker compose logs api`) que "Load
   pretrained SentenceTransformer" aparece só uma vez, no startup — não a
   cada requisição de `/search`.
