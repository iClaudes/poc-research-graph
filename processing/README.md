# processing

Agrupa `ingestion/` e `embedding/` — os dois estágios de processamento de
texto entre o `crawler/` e o `database/`. É só organização visual: cada um
continua com seu próprio Dockerfile/imagem/README, exatamente como antes.
**Não foram fundidos** porque têm pesos de dependência muito diferentes —
`ingestion/` só precisa de `pypdf` (~194MB), enquanto `embedding/` precisa
da imagem base [`ml-base/`](../ml-base/README.md) (~2,86GB). Forçar os dois
a compartilhar uma imagem faria `ingestion/` herdar peso que não usa.

- [`ingestion/`](ingestion/README.md) — extrai texto dos PDFs baixados pelo
  `crawler/`, remove cabeçalho/rodapé repetido, gera chunks de tamanho
  fixo.
- [`embedding/`](embedding/README.md) — gera um vetor de 1024 dimensões por
  chunk com um modelo local multilíngue.

Os diretórios de entrada/saída (`downloads/`, `ingested/`, `embedded/`)
ficam na raiz do repositório (bind mounts do `docker-compose.yml`), não
dentro de `processing/`.
