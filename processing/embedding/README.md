# embedding

Gera os vetores de embedding a partir dos chunks de texto produzidos pelo
`ingestion/`, prontos para carga no `database/` (PostgreSQL + pgvector).

## Modelo

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`:
- **Dimensão do vetor: 384** — valor a usar no schema pgvector do
  `database/` (`vector(384)`).
- Multilíngue, com bom desempenho em português (idioma da maioria dos
  documentos do acervo CESAR).
- Roda em CPU com velocidade razoável — importante porque documentos
  individuais podem gerar centenas de chunks (uma tese de doutorado testada
  gerou 722).
- Rodando local (não API de terceiro): sem custo por chamada, valida rápido
  sem dependência externa em tempo de execução.

PyTorch (CPU-only) + `sentence-transformers` + os pesos do modelo já vêm
prontos da imagem base [`ml-base/`](../../ml-base/README.md) (compartilhada
com `api/`) — este `Dockerfile` só adiciona o código do módulo em cima.
**Precisa buildar `ml-base/` antes** (ver seu README).

## Formato de entrada

Diretório com `{id}.chunks.jsonl` gerados pelo `ingestion/` (um JSON por
linha, cada um um chunk com pelo menos o campo `text`).

## Formato de saída

Para cada `{id}.chunks.jsonl` de entrada, gera `{id}.chunks.jsonl` na saída
com os **mesmos registros do `ingestion/`, mais dois campos**:

```json
{"codAcervo": 100, "chunkIndex": 0, "chunkCount": 12, "text": "...", "charStart": 0, "charEnd": 998, "titulo": "...", "autor": "...", "tipoObra": "...", "fonteUrl": "...", "embedding": [0.0123, -0.0456, ...], "embeddingModel": "paraphrase-multilingual-MiniLM-L12-v2"}
```

`embeddingModel` fica registrado em cada chunk para rastrear qual modelo
gerou o vetor, caso o modelo mude no futuro.

## Build e uso local

Requer Python 3.12+.

```
cd processing/embedding
pip install -r requirements.txt
python -m embedding.cli --in ../../ingested --out ../../embedded [--model paraphrase-multilingual-MiniLM-L12-v2] [--batch-size 32]
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
   - Cada linha tem `embedding` com exatamente 384 floats, e
     `embeddingModel` preenchido.
   - Demais campos idênticos ao registro correspondente do `ingestion/`.
4. Sanity check semântico: calcular similaridade de cosseno entre chunks do
   mesmo documento (deve ser relativamente alta) e entre chunks de
   documentos de temas bem diferentes (deve ser menor) — não é um teste de
   precisão formal, só confirma que o modelo está gerando vetores
   coerentes.
