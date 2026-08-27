# recommender

Recomenda documentos do acervo por similaridade de embeddings, a partir de
um documento existente ou de uma busca em texto livre. Consulta direto o
PostgreSQL/pgvector já carregado pelo `database/`.

Por enquanto é uma ferramenta de linha de comando — o `api/` (próxima
etapa do roadmap) vai expor isso como serviço HTTP.

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

## Modelo (modo `--query`)

Mesmo modelo do `embedding/`: `paraphrase-multilingual-MiniLM-L12-v2`.
**Precisa ser o mesmo** — vetores gerados por modelos diferentes não são
comparáveis entre si.

## Uso

```
python -m recommender.cli --cod-acervo 100 --top-n 5
python -m recommender.cli --query "design de interfaces para aplicativos de streaming" --top-n 5
```

- `--cod-acervo` ou `--query`: exatamente um dos dois, obrigatório.
- `--top-n`: default 5.
- `--out`: opcional, grava o resultado também em JSON.

## Rodando com Docker

PyTorch + `sentence-transformers` vêm da imagem base
[`ml-base/`](../ml-base/README.md) (compartilhada com `embedding/` e
`api/`) — **precisa buildar `ml-base/` antes** (ver seu README):

```
docker build -t poc-research-graph-ml-base:latest ./ml-base   # se ainda não existir
docker compose run --rm recommender --cod-acervo 100 --top-n 5
docker compose run --rm recommender --query "design de interfaces para aplicativos de streaming"
```

Requer o serviço `postgres` de pé com dados carregados (ver
`database/README.md`). Para salvar o resultado em arquivo:

```
docker compose run --rm recommender --query "..." --out /app/recommendations/resultado.json
```

## Limitações conhecidas

- **Viés de tamanho no modo `--cod-acervo`.** A agregação por similaridade
  máxima favorece documentos candidatos com muitos chunks: quanto mais
  chunks um candidato tem, mais chances estatísticas de um deles gerar um
  match alto por acaso (ex. trechos de metodologia/referências genéricos),
  mesmo sem relação temática real. Observado no teste manual: recomendando
  a partir do acervo 96 (visão computacional/cana-de-açúcar, sem nenhum
  documento genuinamente relacionado nos 8 testados), o acervo 102 (tese de
  722 chunks) ficou em 1º lugar com um match cujo trecho era só linguagem
  acadêmica genérica — não um match temático de verdade. Já para o modo
  `--query` (um único vetor de referência, sem esse efeito de escala), o
  sinal foi bem mais nítido (ex. busca por "streaming"/design retornou o
  documento certo com folga). Mitigação futura possível: normalizar por
  `log(chunk_count)` ou exigir múltiplos chunks acima de um limiar em vez
  de aceitar um único pico.
- Modo `--cod-acervo` com poucos documentos genuinamente relacionados no
  banco (como no lote de teste de 8 documentos) não tem como validar
  qualidade de recomendação de forma robusta — o teste manual confere
  comportamento (não recomenda a si mesmo, não quebra), não precisão.

## Como testar

1. Ter o pipeline completo rodando (`crawler` → `ingestion` → `embedding`
   → `database`, ver READMEs respectivos).
2. `docker compose run --rm recommender --cod-acervo 96` (documento sobre
   visão computacional em cana-de-açúcar — o mais atípico do lote de teste
   no `embedding/`). Confirmar que ele mesmo não aparece nos resultados.
3. `docker compose run --rm recommender --query "design de interfaces para aplicativos de streaming"`.
   Esperado: documentos de "design" rankeados acima dos demais.
4. `docker compose run --rm recommender --cod-acervo 99999` (id
   inexistente) — deve logar erro claro e sair com código de erro, sem
   stack trace não tratada.
5. Rodar com `--out` e conferir que o arquivo gerado é um JSON válido com
   os mesmos resultados impressos no stdout.
