# embedding

Gera os vetores de embedding a partir dos chunks de texto produzidos pelo
`ingestion/`, prontos para carga no `database/` (PostgreSQL + pgvector).

## Modelo

`BAAI/bge-m3`:
- **Dimensão do vetor: 1024** — valor a usar no schema pgvector do
  `database/` (`vector(1024)`).
- Multilíngue, treinado especificamente pra tarefas de recuperação/busca
  (não "paraphrase mining") — separa melhor tema de estilo/registro de
  escrita do que o modelo anterior (`paraphrase-multilingual-MiniLM-L12-v2`,
  384 dim), que dominava o ranking de recomendação com linguagem
  estrutural genérica de metodologia acadêmica em vez de conteúdo real
  (ver "Limitações conhecidas" em `api/README.md`).
- Bem mais pesado que o modelo anterior (~568M parâmetros vs. ~118M) —
  importante porque documentos individuais podem gerar centenas de chunks
  (uma tese de doutorado testada gerou 722). Roda em CPU por padrão, mas
  se beneficia bastante de GPU pra corpus maiores — ver `ml-base/README.md`
  (`docker-compose.gpu.yml`).
- Rodando local (não API de terceiro): sem custo por chamada, valida rápido
  sem dependência externa em tempo de execução.

PyTorch + `sentence-transformers` + os pesos do modelo já vêm prontos da
imagem base [`ml-base/`](../../ml-base/README.md) (compartilhada com
`api/`) — este `Dockerfile` só adiciona o código do módulo em cima.
**Precisa buildar `ml-base/` antes** (ver seu README, inclusive a opção de
build com GPU).

## Formato de entrada

Diretório com `{id}.chunks.jsonl` gerados pelo `ingestion/` (um JSON por
linha, cada um um chunk com pelo menos o campo `text`).

## Formato de saída

Para cada `{id}.chunks.jsonl` de entrada, gera `{id}.chunks.jsonl` na saída
com os **mesmos registros do `ingestion/`, mais dois campos**:

```json
{"codAcervo": 100, "chunkIndex": 0, "chunkCount": 12, "text": "...", "charStart": 0, "charEnd": 998, "titulo": "...", "autor": "...", "tipoObra": "...", "fonteUrl": "...", "embedding": [0.0123, -0.0456, ...], "embeddingModel": "BAAI/bge-m3"}
```

`embeddingModel` fica registrado em cada chunk para rastrear qual modelo
gerou o vetor, caso o modelo mude no futuro.

## Build e uso local

Requer Python 3.12+.

```
cd processing/embedding
pip install -r requirements.txt
python -m embedding.cli --in ../../ingested --out ../../embedded [--model BAAI/bge-m3] [--batch-size 32]
```

## Rodando com Docker

A partir da raiz do repositório (a imagem `ml-base` precisa existir
localmente primeiro):

```
docker build -t poc-research-graph-ml-base:latest ./ml-base   # se ainda não existir
docker build -t embedding ./processing/embedding
docker run --rm -v "$(pwd)/ingested:/app/ingested:ro" -v "$(pwd)/embedded:/app/embedded" embedding
```

Ou via docker compose (volumes já configurados no `docker-compose.yml` da
raiz):

```
docker compose run --rm embedding
```

## Como testar

1. Gerar dados de entrada com `crawler/` + `ingestion/` (ver READMEs
   respectivos).
2. Rodar a geração de embeddings sobre `ingested/`:
   ```
   docker compose run --rm embedding
   ```
3. Conferir para um id (ex. 100):
   - `embedded/100.chunks.jsonl` tem o mesmo número de linhas que
     `ingested/100.chunks.jsonl`.
   - Cada linha tem `embedding` com exatamente 1024 floats, e
     `embeddingModel` preenchido.
   - Demais campos idênticos ao registro correspondente do `ingestion/`.
4. Sanity check semântico: calcular similaridade de cosseno entre chunks do
   mesmo documento (deve ser relativamente alta) e entre chunks de
   documentos de temas bem diferentes (deve ser menor) — não é um teste de
   precisão formal, só confirma que o modelo está gerando vetores
   coerentes.
