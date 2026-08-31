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
**algum** chunk do documento/busca de referência, não a média de todos os
chunks. Isso importa porque o teste de sanidade do `embedding/` mostrou que
o centróide de um documento inteiro dilui o sinal temático (muito
vocabulário estrutural acadêmico — metodologia, referências, cabeçalhos —
compartilhado entre todos os TCCs/teses).

Para cada vetor de referência, roda uma busca KNN via pgvector (usa o
índice HNSW), pega os 20 chunks mais próximos, e por documento candidato
guarda a melhor similaridade encontrada **para cada chunk-alvo distinto**
(um mesmo chunk do candidato pode aparecer nos resultados de várias buscas,
uma por vetor de referência). Se o documento de referência tiver muitos
chunks, usa uma amostra de até 150 (espaçados uniformemente) como vetores
de referência, para não gerar centenas de consultas ao banco por chamada.

**Ranqueamento por múltiplos chunks (não só o pico).** A pontuação usada
pra ordenar os candidatos é a média dos `TOP_K_CHUNKS` (3) chunks-alvo
distintos de maior similaridade, com zero-padding se o candidato tiver
menos que isso — ou seja, um documento precisa de **várias partes**
realmente parecidas com a referência pra pontuar bem, um único chunk
isolado não basta. No modo de busca em texto livre (`--query`/`/search`),
que usa um único vetor de referência, isso equivale ao comportamento
anterior (só o melhor chunk importa) — não há vetores extras pra formar um
pico espúrio nesse modo, então nada muda ali. Essa é a correção do "viés de
tamanho" descrito abaixo. O campo `similarity` retornado continua sendo o
valor do melhor chunk isolado (não a média com zero-padding) — é o número
mostrado ao usuário, e teria pouco significado como um valor artificialmente
reduzido pela ausência de mais matches. `match_count` informa quantos
chunks distintos (de 1 a 3) entraram nessa pontuação, pra dar transparência
sobre a confiança do resultado.

Resultados cujo melhor chunk fica abaixo de `MIN_SIMILARITY` (0.35) são
descartados — a API pode retornar menos que `top_n` resultados (inclusive
lista vazia) quando não há match de qualidade, em vez de forçar
recomendações fracas só para preencher a contagem pedida.

**Filtro de vetor de referência genérico (mitigação parcial, ver
"Limitações conhecidas").** Testado com um corpus maior (58 documentos, ver
histórico do repositório), ficou claro que nem todo chunk do documento de
referência carrega sinal temático — trechos de metodologia acadêmica
("abordagem qualitativa e quantitativa...") se repetem quase iguais em
quase toda tese/TCC em português. Antes de aceitar os resultados de um
vetor de referência (modo por documento, vários vetores), checamos em
quantos documentos **distintos** os 20 vizinhos mais próximos daquele vetor
caem — se `>= DIVERSITY_THRESHOLD` (0.5) do total, é sinal de linguagem
genérica batendo um pouco em quase tudo, e descartamos esse vetor de
referência inteiro (não conta pra nenhum candidato). Não se aplica à busca
em texto livre (1 vetor só — descartá-lo deixaria a busca sem resultado
nenhum).

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
  parecidos com esse (`404` se o documento não existir; pode retornar menos
  que `top_n`, inclusive lista vazia, se não houver match acima do piso
  mínimo de similaridade).
- `GET /search?q=texto+livre&top_n=5` — busca semântica em texto livre (mesma
  regra de piso mínimo).

Documentação interativa (Swagger UI) em `/docs`.

### Interface web

`GET /` (e demais paths estáticos) serve uma SPA em HTML/JS puro a partir
de `api/static/` — sem Node, sem build, sem framework: `index.html` +
`style.css` + três scripts clássicos (`api.js` chamadas fetch, `ui.js`
renderização, `app.js` roteamento). É o mesmo processo Uvicorn do serviço
HTTP (`app.mount("/", StaticFiles(...))` em `main.py`, registrado por
último para não conflitar com as rotas de API) — não precisa de container
nem porta separados, e como está na mesma origem não precisa de CORS.

Navegação por hash (`#/`, `#/search?q=...`, `#/doc/{id}`) em vez de rotas
de servidor: o path real requisitado ao Uvicorn é sempre `/`, então
recarregar a página numa rota profunda (`#/doc/100`) funciona sem
precisar de fallback de SPA no `StaticFiles`.

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
  `/documents/{id}/recommendations`) — **mitigado**. Com agregação por
  similaridade máxima pura, documentos candidatos com muitos chunks tinham
  vantagem estatística: quanto mais chunks um candidato tem, mais chances de
  um deles gerar um match alto por acaso (ex. trechos de
  metodologia/referências genéricos), mesmo sem relação temática real.
  Observado no teste manual original (corpus de 8 documentos): recomendando
  a partir do acervo 96 (visão computacional/cana-de-açúcar), o acervo 102
  (tese de 722 chunks) ficou em 1º lugar com um match cujo trecho era só
  linguagem acadêmica genérica. A mitigação aplicada (ver "Algoritmo"
  acima): ranquear pela média dos `TOP_K_CHUNKS` (3) melhores chunks
  distintos do candidato, com zero-padding — um pico isolado passa a
  pontuar mal. Continua sem afetar a busca por texto livre (`--query`/
  `/search`, um único vetor de referência, onde o sinal já era nítido).
- **Linguagem acadêmica genérica dominando o ranking (parcialmente
  mitigado, limitação real e observada — não hipotética).** Ampliando o
  corpus pra 58 documentos reais (crawler, faixa 1–600) pra validar a
  correção acima, apareceu um problema relacionado e mais sério: como
  **todos** os chunks do documento de referência viram vetor de busca
  (inclusive os de metodologia), muitos candidatos conseguem `match_count`
  máximo só por compartilharem o "sotaque" acadêmico comum ao corpus, não o
  tema. No teste com o acervo 96, o top-8 inteiro veio com `match_count: 3`
  e similaridade ~0.92–0.95, mas nenhum resultado era sobre visão
  computacional ou agricultura. Mitigação aplicada (ver "Algoritmo" acima):
  descartar vetores de referência cujos 20 vizinhos mais próximos caem
  espalhados por documentos demais (`DIVERSITY_THRESHOLD`). Resultado
  **real, mas parcial**: com o filtro, os acervos 69 ("visão computacional
  para reconhecimento de abelhas e vespas") e 59 ("visão computacional
  resiliente a ataques adversariais") — matches genuinamente temáticos —
  passaram a aparecer no top-8 do acervo 96, onde antes não apareciam
  nenhum; mas ainda misturados com resultados sem relação de tema, não
  claramente no topo do ranking. `DIVERSITY_THRESHOLD = 0.5` foi escolhido
  testando 0.75/0.5/0.35 nesse mesmo caso (96) — **calibração em cima de um
  único exemplo, não validada contra um conjunto de teste maior**, então é
  o palpite mais informado disponível, não um valor definitivo. Causa raiz
  provável: `paraphrase-multilingual-MiniLM-L12-v2` é um modelo leve
  (bom custo/benefício em CPU, mas limitado) e, em chunks de ~1000
  caracteres de português acadêmico, o vocabulário estrutural de pesquisa
  (metodologia, discussão, referencial teórico) pesa mais no embedding do
  que o vocabulário específico do tema — ver opção "trocar o modelo de
  embedding" no `ROADMAP.md`, provavelmente a correção mais efetiva daqui
  pra frente, mas fora de escopo por ora (reprocessar todo o corpus).
- Piso mínimo de similaridade (`MIN_SIMILARITY = 0.35` em `search.py`):
  descarta candidatos cujo melhor chunk fica abaixo disso, em vez de forçar
  `top_n` resultados mesmo sem nenhum match de qualidade. Valor inicial por
  julgamento, não calibrado estatisticamente — ajustar se o teste manual
  mostrar resultados bons sendo descartados ou ruins passando.

## Como testar

1. Ter o pipeline completo rodando (`crawler` → `processing/ingestion` →
   `processing/embedding` → `db-loader`, ver READMEs respectivos).
2. **CLI**: `docker compose run --rm api python -m api.cli --cod-acervo 96`
   (documento sobre visão computacional em cana-de-açúcar). Confirmar que
   ele mesmo não aparece nos resultados, e que o acervo 102 (tese de 722
   chunks) não domina mais o topo por um match isolado — conferir
   `match_count` na saída: um candidato com `match_count` baixo (1) e
   `similarity` alta isolada deve perder posição pra um com `match_count`
   maior (2-3) e similaridades mais consistentes. Testado num corpus de 58
   documentos (crawler, faixa 1–600): os acervos 69 ("visão computacional
   para reconhecimento de abelhas e vespas") e 59 ("visão computacional
   resiliente a ataques adversariais") devem aparecer no top-8 — matches
   genuinamente temáticos que só passaram a aparecer depois do filtro de
   vetor de referência genérico (ver "Limitações conhecidas": mitigação
   real mas parcial, ainda misturado com resultados sem relação de tema).
   `docker compose run --rm api python -m api.cli --query "design de interfaces para aplicativos de streaming"`
   — esperado: documentos de "design" rankeados acima dos demais (regressão:
   resultado deve ser igual ao de antes da mudança, já que a busca em texto
   livre usa `k_effective=1`).
   `docker compose run --rm api python -m api.cli --cod-acervo 99999` (id
   inexistente) — deve logar erro claro e sair com código de erro, sem
   stack trace não tratada.
3. **HTTP**: `docker compose up -d postgres api`, rodar os `curl` da seção
   de rotas e conferir: `/health` responde ok; `/documents` lista os
   documentos carregados; `/documents/{id}` inexistente retorna `404`;
   `/search` e `/recommendations` retornam os mesmos resultados já
   validados via CLI, incluindo o campo `match_count`; uma busca sem nenhum
   match de qualidade (`q` fora do domínio do acervo) retorna lista menor
   que `top_n` (ou vazia) em vez de forçar resultados fracos.
4. Conferir latência consistente entre a primeira e as próximas chamadas a
   `/search` (confirma que o modelo carrega uma vez no startup, não a cada
   requisição).
5. **UI web**: abrir `http://localhost:8000/`, fazer uma busca e abrir o
   detalhe de um documento — conferir que o badge "N trechos parecidos"
   aparece ao lado do badge de similaridade nos cards de resultado.
