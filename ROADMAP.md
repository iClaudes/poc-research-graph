# Roadmap

Status e próximos passos do pipeline **Crawler → Ingestion → Embedding →
PostgreSQL/pgvector → Recomendação**. Para o que já foi feito e testado, ver
[`crawler/README.md`](crawler/README.md),
[`processing/ingestion/README.md`](processing/ingestion/README.md),
[`processing/embedding/README.md`](processing/embedding/README.md),
[`database/README.md`](database/README.md),
[`api/README.md`](api/README.md) e
[`ml-base/README.md`](ml-base/README.md).

## Stack por módulo

| Módulo | Status | Tecnologia | Por quê |
|---|---|---|---|
| `crawler/` | ✅ feito e testado | Java 25 (virtual threads) + Maven | Só HTTP + JSON, sem necessidade de ecossistema de ML; time já conhece Java; nada no mercado obriga trocar aqui. Virtual threads (estáveis desde o 21, 25 é a LTS atual) paralelizam a espera de rede — I/O-bound, um ID por thread — sem o custo de threads de SO; concorrência real segue limitada por semáforo (`--concurrency`), não "o mais rápido possível". |
| `processing/ingestion/` | ✅ feito e testado | Python 3.12 + `pypdf` | Extrair texto dos PDFs baixados, normalizar e gerar chunks de tamanho fixo prontos pra embedding. |
| `processing/embedding/` | ✅ feito e testado | Python 3.12 + `sentence-transformers` | Modelo local `paraphrase-multilingual-MiniLM-L12-v2` (multilíngue, bom em português, roda em CPU) — **vetores de 384 dimensões**, valor a usar no schema pgvector do `database/`. |
| `database/` | ✅ feito e testado | PostgreSQL 16 + pgvector (índice HNSW) | Mantido da ideia original — compete de igual pra igual com bancos vetoriais dedicados em escala de POC/médio porte, e mantém dados relacionais (metadados, grafo de relações) junto com os vetores. |
| `api/` | ✅ feito e testado | Python 3.12 + FastAPI/Uvicorn + `psycopg`/`pgvector`/`sentence-transformers` | Recomenda por documento existente ou busca em texto livre, agregando por similaridade máxima entre chunks (cosine distance, índice HNSW) — como CLI e como serviço HTTP, mesma lógica pros dois (nasceu como dois módulos separados — `recommender/` e `api/` — fundidos depois que ficou claro que `search.py`/`embedder.py` eram cópias idênticas). Docs interativas em `/docs` de graça. |

Ou seja: o pipeline vai ficar poliglota — Java na borda de ingestão de dados
externos, Python no núcleo de ML/recomendação. É um padrão comum em projetos
reais desse tipo.

`ingestion/` e `embedding/` vivem dentro de `processing/` — mesma
separação de Dockerfile/imagem de sempre, só agrupados numa pasta pra
navegação (pesos de dependência muito diferentes pra fundir as imagens:
`ingestion/` é leve, `embedding/` carrega a stack de ML via `ml-base/`).

`ml-base/` fica solto na raiz, não dentro de `database/` nem de um
diretório-pai tipo "infra/": é uma imagem base de build (PyTorch CPU-only
+ `sentence-transformers` + modelo, reaproveitada por `processing/embedding/`
e `api/`), nunca roda como serviço. `database/` é um serviço com estado de
verdade (Postgres). São categorias diferentes — agrupar as duas só por
"nenhuma é lógica de negócio" bagunçaria mais do que ajudaria.

## Próximos passos

Todos os módulos planejados originalmente estão implementados e testados —
o pipeline completo funciona de ponta a ponta (`crawler` →
`processing/ingestion` → `processing/embedding` → `database` → `api`). Não
há próximo módulo definido; ver "Coisas para revisitar mais pra frente"
abaixo pra melhorias incrementais sobre o que já existe.

## Coisas para revisitar mais pra frente

- Descoberta de documentos no crawler hoje é por varredura sequencial de ID;
  existe um endpoint de busca (`/api/consulta`) no Pergamum que poderia
  tornar isso mais direcionado — ver limitações em `crawler/README.md`.
- Fallback de download de arquivo grande no Google Drive (página de aviso de
  vírus) ainda não foi validado contra um arquivo real que dispare esse
  comportamento.
- ~~Viés de tamanho na recomendação por documento~~ — **mitigado e
  validado**: `api/` passou a ranquear pela média dos `TOP_K_CHUNKS` (3)
  melhores chunks distintos por candidato (com zero-padding), em vez de só
  o pico máximo — ver "Algoritmo" e "Limitações conhecidas" em
  `api/README.md`. Validado no corpus ampliado (item abaixo, já feito).
- **Linguagem acadêmica genérica dominando o ranking** — **parcialmente
  mitigado, não resolvido**. Ao ampliar o corpus pra validar o item acima,
  apareceu um problema mais sério: candidatos conseguem match alto só por
  compartilharem o "sotaque" de metodologia acadêmica com o documento de
  referência, não o tema (ex. acervo 96 recomendando 8 documentos sem
  nenhuma relação temática real, todos com match_count máximo). Mitigação
  aplicada: descartar vetores de referência cujos vizinhos mais próximos
  caem espalhados por documentos demais (`DIVERSITY_THRESHOLD` em
  `search.py`) — melhorou de forma real e mensurável (matches
  genuinamente temáticos passaram a aparecer), mas não limpou o ranking
  (ainda misturado com ruído, não no topo). Ver detalhe e números em
  "Limitações conhecidas" no `api/README.md`. Causa raiz provável: o
  modelo de embedding atual não separa bem vocabulário de pesquisa
  (comum a todo TCC/tese) de vocabulário de tema, em chunks curtos de
  português acadêmico — ver "trocar o modelo de embedding" abaixo,
  provavelmente a correção mais efetiva daqui pra frente.
- ~~Ampliar o corpus de teste~~ — **feito**: crawler rodado até a faixa
  1–600 (58 documentos com PDF elegível carregados no banco), o suficiente
  pra revelar o item acima, que o lote original de 8 documentos não deixava
  aparecer.
- Outras melhorias de recomendação discutidas e deixadas de fora por ora,
  em ordem crescente de esforço/risco:
  - Reranking por metadado (mesmo `tipo_obra`/autor) como critério de
    desempate — risco de viés introduzido com um corpus pequeno.
  - **Trocar o modelo de embedding por um mais robusto** — com a evidência
    do item acima, esse é agora o candidato mais forte a próxima melhoria
    de recomendação: o `paraphrase-multilingual-MiniLM-L12-v2` atual é leve
    (bom custo/benefício em CPU) mas parece não separar bem vocabulário de
    pesquisa de vocabulário de tema. Custo: reprocessar todos os chunks
    (`processing/embedding/` + `db-loader`), download e CPU maiores.
  - Ajustar `chunk_size`/`chunk_overlap` da ingestão — exige reprocessar
    tudo, sem evidência ainda de que o chunking atual seja o gargalo
    (o problema observado parece mais de modelo que de tamanho de chunk).
  - Busca híbrida (léxica + vetorial) — mais complexo, provavelmente
    overkill pro estágio atual da POC.
