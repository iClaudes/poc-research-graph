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
| `processing/embedding/` | ✅ feito e testado | Python 3.12 + `sentence-transformers` | Modelo local `BAAI/bge-m3` (multilíngue, treinado pra recuperação/busca — trocado do `paraphrase-multilingual-MiniLM-L12-v2` original, que não separava bem tema de estilo acadêmico; roda em CPU por padrão, GPU opcional via `docker-compose.gpu.yml`) — **vetores de 1024 dimensões**, valor a usar no schema pgvector do `database/`. |
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
diretório-pai tipo "infra/": é uma imagem base de build (PyTorch, CPU por
padrão/GPU opcional + `sentence-transformers` + modelo, reaproveitada por `processing/embedding/`
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
- **Linguagem acadêmica genérica dominando o ranking** — **melhorado
  substancialmente, não 100% eliminado**. Ao ampliar o corpus pra validar
  o item acima, apareceu um problema mais sério: candidatos conseguiam
  match alto só por compartilharem o "sotaque" de metodologia acadêmica
  com o documento de referência, não o tema (ex. acervo 96 recomendando 8
  documentos sem nenhuma relação temática real). Duas mitigações
  combinadas: (1) descartar vetores de referência cujos vizinhos mais
  próximos caem espalhados por documentos demais (`DIVERSITY_THRESHOLD`
  em `search.py`); (2) **trocar o modelo de embedding** de
  `paraphrase-multilingual-MiniLM-L12-v2` (treinado pra "paraphrase
  mining", 384 dim) pra `BAAI/bge-m3` (treinado pra recuperação/busca,
  1024 dim). Resultado real no mesmo teste (acervo 96): os dois
  documentos genuinamente temáticos (visão computacional) subiram de
  posições 5/8 pra **1ª e 3ª**, com similaridades bem mais espalhadas
  (0.69–0.86, contra 0.88–0.95 antes — sinal de discriminação real). Não
  ficou perfeito: metade do top-8 ainda são papers de ML aplicado a outros
  domínios, não ao tema exato — mas dado o corpus atual (58 documentos sem
  curadoria por tema) ter poucos exemplos genuinamente próximos, isso já é
  um resultado razoável. Ver números completos em "Limitações conhecidas"
  no `api/README.md`.
- ~~Ampliar o corpus de teste~~ — **feito**: crawler rodado até a faixa
  1–600 (58 documentos com PDF elegível carregados no banco), o suficiente
  pra revelar o item acima, que o lote original de 8 documentos não deixava
  aparecer.
- ~~Trocar o modelo de embedding por um mais robusto~~ — **feito**: ver
  item acima. Também foi a motivação pra adicionar suporte a GPU opcional
  (`ml-base/README.md`, `docker-compose.gpu.yml`) — o `bge-m3` (568M
  parâmetros) seria impraticavelmente lento em CPU pro corpus atual;
  numa RTX 3050 (4GB) o reprocessamento dos ~10 mil chunks levou ~64min.
  CPU continua o padrão (portabilidade), GPU é opt-in.
- Otimizações de throughput de embedding, ainda não aplicadas (levantadas
  ao notar que a GPU não estava sendo bem aproveitada — batches pequenos
  pra chunks curtos): aumentar `--batch-size` (hoje 32, provavelmente cabe
  bem mais em 4GB pra chunks de ~150-300 tokens) e/ou `torch.backends.
  cudnn.benchmark = True` — nenhum dos dois muda a precisão numérica.
  `torch.compile()` e TF32 (`torch.backends.cuda.matmul.allow_tf32`) são
  opções mais agressivas (a segunda tecnicamente reduz precisão da
  mantissa em GPUs Ampere+, embora o efeito prático em embeddings de
  similaridade costume ser desprezível).
- Outras melhorias de recomendação discutidas e deixadas de fora por ora,
  em ordem crescente de esforço/risco:
  - Reranking por metadado (mesmo `tipo_obra`/autor) como critério de
    desempate — risco de viés introduzido com um corpus pequeno.
  - Ajustar `chunk_size`/`chunk_overlap` da ingestão — exige reprocessar
    tudo; com o modelo novo (`bge-m3` suporta até 8192 tokens de contexto,
    bem mais que os ~1000 caracteres usados hoje) valeria revisitar, mas
    sem evidência ainda de que seja o gargalo atual.
  - Busca híbrida (léxica + vetorial) — mais complexo, provavelmente
    overkill pro estágio atual da POC.
