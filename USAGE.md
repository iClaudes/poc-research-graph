# Guia de utilização

Este guia é um passo a passo narrado de como operar o sistema de ponta a
ponta — do zero até fazer uma busca semântica real. Pra referência rápida
de comandos, ver o Quickstart em [`README.md`](README.md); pra entender
por que cada peça foi construída do jeito que foi, ver
[`ROADMAP.md`](ROADMAP.md).

## O que esse sistema faz

Baixa TCCs/dissertações/teses do acervo da Biblioteca CESAR, extrai o
texto dos PDFs, gera vetores semânticos (embeddings) e guarda tudo num
banco com busca por similaridade — pra no final você poder perguntar "quais
documentos são parecidos com este?" ou "quais documentos falam sobre X?"
e receber uma resposta ranqueada, não uma busca por palavra-chave.

## Antes de começar

Ver [Requisitos no README](README.md#requisitos) — Docker Compose v2,
~15–18 GB de disco, acesso à rede. Nenhuma credencial externa é
necessária.

## Passo a passo completo

### 0. Build da imagem base de ML

```
docker build -t poc-research-graph-ml-base:latest ./ml-base
```

Baixa PyTorch (CPU-only) + `sentence-transformers` + os pesos do modelo de
embedding. Demora alguns minutos na primeira vez (baixa ~1-2GB); as
próximas builds de `processing/embedding/` e `api/` reaproveitam essa
camada e ficam rápidas. Só precisa rodar de novo se você mudar as
dependências de `ml-base/Dockerfile`.

### 1. Baixar documentos (crawler)

```
docker compose run --rm crawler --start 95 --end 105 --out /app/downloads --delay-ms 300
```

Varre o acervo por id (`--start`/`--end`), baixa PDF + metadados de cada
TCC/dissertação/tese elegível em `downloads/` (na raiz do repo). IDs sem
registro (404) ou sem PDF elegível (livros, dissertações sem anexo) são
pulados — o resumo no final mostra quantos de cada. Escolha uma faixa
maior (`--start 1 --end 2000`, por exemplo) pra um acervo mais completo;
isso só demora mais (o `--delay-ms` existe pra não sobrecarregar o
servidor da biblioteca).

### 2. Extrair texto e gerar chunks (ingestion)

```
docker compose run --rm ingestion
```

Lê tudo que tem em `downloads/`, extrai o texto de cada PDF, limpa
cabeçalho/rodapé repetido e divide em chunks de ~1000 caracteres, gravando
em `ingested/`. PDFs sem texto extraível (escaneados sem OCR) são pulados
com aviso.

### 3. Gerar embeddings (embedding)

```
docker compose run --rm embedding
```

Lê `ingested/`, gera um vetor de 1024 dimensões por chunk (modelo
`BAAI/bge-m3`, roda local em CPU por padrão — ou GPU, se buildado com o
override `docker-compose.gpu.yml`, ver `ml-base/README.md`) e grava em
`embedded/`. Para poucas dezenas de documentos isso leva segundos a
minutos; um acervo grande pode levar bem mais em CPU — GPU acelera bastante
com esse modelo.

### 4. Subir o banco e carregar os dados

```
docker compose up -d postgres
docker compose run --rm db-loader
```

O `postgres` sobe com o schema pgvector já aplicado automaticamente
(tabelas `documents`/`chunks`, índice HNSW). O `db-loader` lê `embedded/`
e carrega tudo — pode rodar de novo a qualquer momento sem duplicar dados
(recarregar um documento apaga e reinsere os chunks dele).

### 5. Consultar

Dois jeitos, mesma lógica por trás:

**Via CLI**, direto no terminal:
```
docker compose run --rm api python -m api.cli --query "design de interfaces para aplicativos" --top-n 5
docker compose run --rm api python -m api.cli --cod-acervo 100 --top-n 5
```

**Via HTTP**, deixando o servidor de pé:
```
docker compose up -d api
curl "localhost:8000/search?q=design+de+interfaces+para+streaming&top_n=5"
curl "localhost:8000/documents/100/recommendations?top_n=5"
```
Documentação interativa em `http://localhost:8000/docs`.

**Via navegador**, mesma API, sem montar URL na mão:
```
docker compose up -d api
```
Abra `http://localhost:8000/` — busca por texto no topo, lista de
documentos paginada abaixo, clique num documento pra ver detalhe e
recomendações.

## Exemplo prático: achar documentos por tema

Depois dos passos 1–4 rodados (mesmo que só com uma faixa pequena, tipo
`--start 95 --end 105`), pergunte em texto livre:

```
docker compose run --rm api python -m api.cli --query "sustentabilidade e áreas verdes urbanas" --top-n 3
```

Saída esperada — um ranking com similaridade, título, autor e um trecho do
chunk que justificou o match:

```
1. [0.XXX] acervo 100 - Design e sustentabilidade urbana referências para inclusão de áreas verdes em recife ...
   autor: Rocha, Mayara Silva da | tipo: TCC - Graduação
   trecho (chunk N): ...
```

Pra achar documentos parecidos com um específico (em vez de buscar por
texto), use `--cod-acervo <id>` com o id retornado numa busca anterior.

## Rodando de novo / ampliando o acervo

Todos os passos são seguros de rodar de novo:

- `crawler` com uma faixa de IDs diferente/maior só adiciona mais arquivos
  em `downloads/` (não apaga o que já tinha).
- `ingestion`/`embedding` reprocessam tudo que estiver no diretório de
  entrada — rodar de novo depois de adicionar mais documentos ao
  `downloads/` reprocessa os novos junto com os antigos (sobrescrevendo os
  arquivos de saída com o mesmo id, sem duplicar).
- `db-loader` é idempotente: recarregar um `cod_acervo` que já existe
  atualiza os dados dele, não duplica.

Pra crescer o acervo, é só repetir os passos 1–4 com uma faixa de
`--start`/`--end` diferente.

## Inspecionando o banco diretamente

```
docker compose exec postgres psql -U research_graph -d research_graph
```

```sql
SELECT count(*) FROM documents;
SELECT count(*) FROM chunks;
SELECT cod_acervo, titulo FROM documents ORDER BY cod_acervo;
```

Mais exemplos de query (incluindo busca por similaridade manual via SQL)
em [`database/README.md`](database/README.md).

## Solução de problemas comuns

- **`docker build`/`docker run` falha achando `poc-research-graph-ml-base:latest`
  não existe** — rode o passo 0 primeiro; essa imagem não é publicada em
  registry nenhum, precisa existir localmente.
- **`db-loader` ou `api` reclamam de conexão recusada com o Postgres** —
  espere o `postgres` ficar `healthy` antes (`docker compose up -d
  postgres` e aguardar; `docker ps` mostra o status).
- **No Windows com Git Bash, `docker run -v "$(pwd)/...:/app/..."` monta
  um diretório vazio ou dá erro de caminho** — é o Git Bash reescrevendo o
  lado direito do `-v` como se fosse um caminho do Windows. Prefixe o
  comando com `MSYS_NO_PATHCONV=1` (ex.: `MSYS_NO_PATHCONV=1 docker run
  ...`). Isso não afeta `docker compose`, só `docker run` direto.
- **Build muito lento / baixando PyTorch de novo** — confirme que está
  usando `docker compose build` (que reaproveita cache de camadas) e que
  `ml-base` já foi buildado; builds do zero de `ml-base` demoram porque
  baixam PyTorch (~1-2GB) — normal na primeira vez.
- **Pouco espaço em disco** — ver o cálculo em
  [Requisitos no README](README.md#requisitos); `docker system df` mostra
  o uso real, `docker image prune` limpa imagens não usadas (com cuidado,
  isso afeta outros projetos Docker na máquina também).

## Onde saber mais

- [`README.md`](README.md) — visão geral, requisitos, tabela de módulos.
- [`ROADMAP.md`](ROADMAP.md) — decisões de arquitetura, alternativas
  consideradas, limitações conhecidas.
- README de cada módulo (`crawler/`, `processing/ingestion/`,
  `processing/embedding/`, `database/`, `api/`, `ml-base/`) — detalhes de
  formato de entrada/saída, flags de CLI, e planos de teste manual.
