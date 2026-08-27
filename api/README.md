# api

Recomenda documentos do acervo CESAR por similaridade de embeddings, a
partir de um documento existente ou de uma busca em texto livre —
consultando direto o PostgreSQL/pgvector já carregado pelo `database/`.
Dois jeitos de usar a mesma lógica: **serviço HTTP** (FastAPI) e **CLI**
(`python -m api.cli`), ambos no mesmo módulo/imagem — não há duplicação
entre eles, os dois importam de `search.py`/`embedder.py`.

**Diferente de `crawler`/`processing/*`/`db-loader`** (ferramentas batch
pontuais, `docker compose run --rm ...`), o modo HTTP é um processo de
longa duração — fica de pé como o `postgres`, via `docker compose up`. Por
isso ele carrega o modelo de embedding e abre o pool de conexão com o
banco **uma única vez**, no startup, em vez de a cada requisição. O modo
CLI, por ser pontual, abre uma conexão simples por execução (sem pool),
igual às outras ferramentas batch do repositório.

## Algoritmo

Um documento é relevante se **algum** chunk dele for muito parecido com
**algum** chunk do documento/busca de referência — a agregação usa
**similaridade máxima** por documento candidato, não a média de todos os
chunks. Isso importa porque o teste de sanidade do `embedding/` mostrou que
o centróide de um documento inteiro dilui o sinal temático (muito
vocabulário estrutural acadêmico — metodologia, referências, cabeçalhos —
compartilhado entre todos os TCCs/teses).

Para cada vetor de referência, roda uma busca KNN via pgvector (usa o
índice HNSW), pega os 20 chunks mais próximos, e por documento candidato
guarda a menor distância (= maior similaridade) encontrada. Se o documento
de referência tiver muitos chunks, usa uma amostra de até 150 (espaçados
uniformemente) como vetores de referência, para não gerar centenas de
consultas ao banco por chamada.

## Modelo (busca por texto livre)

Mesmo modelo do `embedding/`: `paraphrase-multilingual-MiniLM-L12-v2`.
**Precisa ser o mesmo** — vetores gerados por modelos diferentes não são
comparáveis entre si. PyTorch + `sentence-transformers` vêm da imagem base
[`ml-base/`](../ml-base/README.md) (compartilhada com
`processing/embedding/`) — **precisa buildar `ml-base/` antes** (ver seu
README).

## Modo HTTP

### Rotas

- `GET /health` — `{"status": "ok"}`.
- `GET /documents?limit=50&offset=0` — lista documentos.
- `GET /documents/{cod_acervo}` — detalhe de um documento (`404` se não
  existir).
- `GET /documents/{cod_acervo}/recommendations?top_n=5` — documentos mais
  parecidos com esse (`404` se o documento não existir).
- `GET /search?q=texto+livre&top_n=5` — busca semântica em texto livre.

Documentação interativa (Swagger UI) em `/docs`.

### Rodando com Docker

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

### Rodando localmente

```
cd api
pip install -r requirements.txt
DATABASE_URL=postgresql://research_graph:research_graph@localhost:5432/research_graph uvicorn api.main:app --reload
```

## Modo CLI

```
python -m api.cli --cod-acervo 100 --top-n 5
python -m api.cli --query "design de interfaces para aplicativos de streaming" --top-n 5
```

- `--cod-acervo` ou `--query`: exatamente um dos dois, obrigatório.
- `--top-n`: default 5.
- `--out`: opcional, grava o resultado também em JSON.

### Rodando com Docker

O `Dockerfile` usa `CMD` (não `ENTRYPOINT`), então dá pra sobrescrever o
comando padrão (o servidor HTTP) e rodar o CLI direto na mesma imagem:

```
docker compose run --rm api python -m api.cli --cod-acervo 100 --top-n 5
docker compose run --rm api python -m api.cli --query "design de interfaces para aplicativos de streaming"
```

Requer o serviço `postgres` de pé com dados carregados (ver
`database/README.md`). Para salvar o resultado em arquivo:

```
docker compose run --rm api python -m api.cli --query "..." --out /app/recommendations/resultado.json
```

## Limitações conhecidas

Valem pros dois modos, já que compartilham a mesma lógica de agregação
(`search.recommend`):

- **Viés de tamanho na recomendação por documento** (`--cod-acervo` /
  `/documents/{id}/recommendations`). A agregação por similaridade máxima
  favorece documentos candidatos com muitos chunks: quanto mais chunks um
  candidato tem, mais chances estatísticas de um deles gerar um match alto
  por acaso (ex. trechos de metodologia/referências genéricos), mesmo sem
  relação temática real. Observado no teste manual: recomendando a partir
  do acervo 96 (visão computacional/cana-de-açúcar, sem nenhum documento
  genuinamente relacionado nos 8 testados), o acervo 102 (tese de 722
  chunks) ficou em 1º lugar com um match cujo trecho era só linguagem
  acadêmica genérica — não um match temático de verdade. Já na busca por
  texto livre (`--query`/`/search`, um único vetor de referência, sem esse
  efeito de escala), o sinal foi bem mais nítido (ex. busca por
  "streaming"/design retornou o documento certo com folga). Mitigação
  futura possível: normalizar por `log(chunk_count)` ou exigir múltiplos
  chunks acima de um limiar em vez de aceitar um único pico.
- Recomendação por documento com poucos documentos genuinamente
  relacionados no banco (como no lote de teste de 8 documentos) não tem
  como validar qualidade de recomendação de forma robusta — o teste manual
  confere comportamento (não recomenda a si mesmo, não quebra), não
  precisão.

## Como testar

1. Ter o pipeline completo rodando (`crawler` → `processing/ingestion` →
   `processing/embedding` → `db-loader`, ver READMEs respectivos).
2. **CLI**: `docker compose run --rm api python -m api.cli --cod-acervo 96`
   (documento sobre visão computacional em cana-de-açúcar — o mais atípico
   do lote de teste no `embedding/`). Confirmar que ele mesmo não aparece
   nos resultados.
   `docker compose run --rm api python -m api.cli --query "design de interfaces para aplicativos de streaming"`
   — esperado: documentos de "design" rankeados acima dos demais.
   `docker compose run --rm api python -m api.cli --cod-acervo 99999` (id
   inexistente) — deve logar erro claro e sair com código de erro, sem
   stack trace não tratada.
3. **HTTP**: `docker compose up -d postgres api`, rodar os `curl` da seção
   de rotas e conferir: `/health` responde ok; `/documents` lista os
   documentos carregados; `/documents/{id}` inexistente retorna `404`;
   `/search` e `/recommendations` retornam os mesmos resultados já
   validados via CLI.
4. Conferir latência consistente entre a primeira e as próximas chamadas a
   `/search` (confirma que o modelo carrega uma vez no startup, não a cada
   requisição).
