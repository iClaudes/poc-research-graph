# database

Schema PostgreSQL + pgvector e loader que carrega os chunks + embeddings
produzidos pelo `embedding/` no banco.

## Schema (`schema.sql`)

- `documents` — um registro por acervo (`cod_acervo` como PK, `titulo`,
  `autor`, `tipo_obra`, `fonte_url`).
- `chunks` — um registro por chunk (`cod_acervo` FK com `ON DELETE
  CASCADE`, `chunk_index`, `text`, offsets, `embedding VECTOR(384)`,
  `embedding_model`). `UNIQUE (cod_acervo, chunk_index)`.
- Índice `hnsw` em `chunks.embedding` com `vector_cosine_ops` — busca por
  similaridade de cosseno, usada pelo `recommender/` na próxima etapa. HNSW
  foi escolhido em vez de `ivfflat` por não exigir dados pré-carregados nem
  ajuste de parâmetro (`lists`) pra ficar eficaz.

O schema é aplicado automaticamente pelo Postgres na primeira
inicialização do volume, via `docker-entrypoint-initdb.d/` (não é uma
migração — se o schema mudar depois de já ter dado `docker compose up`,
recrie o volume `pgdata`).

## Subindo o banco

```
docker compose up -d postgres
```

Espera até o healthcheck (`pg_isready`) reportar saudável. Credenciais
locais de POC (fixas em `docker-compose.yml`): usuário/senha/banco
`research_graph`/`research_graph`/`research_graph`, porta `5432` publicada
no host.

## Rodando o loader

Requer os dados do `embedding/` em `embedded/` (ver `embedding/README.md`).

```
docker compose run --rm db-loader
```

Ou localmente (Python 3.12+, banco acessível):

```
cd database
pip install -r requirements.txt
python -m database.cli --in ../embedded --database-url postgresql://research_graph:research_graph@localhost:5432/research_graph
```

Recarregar um documento já existente é seguro — o loader apaga e reinsere
os chunks daquele `cod_acervo` a cada execução (idempotente).

## Inspecionando manualmente

```
docker compose exec postgres psql -U research_graph -d research_graph
```

```sql
SELECT count(*) FROM documents;
SELECT count(*) FROM chunks;

-- 5 chunks mais similares a um chunk conhecido (ex. acervo 100, chunk 0)
SELECT c2.cod_acervo, c2.chunk_index, c2.embedding <=> c1.embedding AS dist
FROM chunks c1, chunks c2
WHERE c1.cod_acervo = 100 AND c1.chunk_index = 0
ORDER BY dist
LIMIT 5;
```

## Como testar

1. Gerar dados de entrada com `crawler/` + `ingestion/` + `embedding/` (ver
   READMEs respectivos).
2. `docker compose up -d postgres` e aguardar saudável.
3. `docker compose run --rm db-loader`.
4. Conferir `SELECT count(*) FROM documents;` / `chunks;` batem com o
   resumo impresso pelo loader.
5. Rodar a query de similaridade acima — o próprio chunk de referência deve
   aparecer em primeiro lugar, com distância ≈ 0.
6. Rodar `docker compose run --rm db-loader` de novo — contagens não devem
   mudar (idempotência).
