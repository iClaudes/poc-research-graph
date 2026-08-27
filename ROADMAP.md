# Roadmap

Status e próximos passos do pipeline **Crawler → Ingestion → Embedding →
PostgreSQL/pgvector → Recomendação**. Para o que já foi feito e testado, ver
[`crawler/README.md`](crawler/README.md),
[`ingestion/README.md`](ingestion/README.md) e
[`embedding/README.md`](embedding/README.md).

## Stack por módulo

| Módulo | Status | Tecnologia | Por quê |
|---|---|---|---|
| `crawler/` | ✅ feito e testado | Java 17 + Maven | Só HTTP + JSON, sem necessidade de ecossistema de ML; time já conhece Java; nada no mercado obriga trocar aqui. |
| `ingestion/` | ✅ feito e testado | Python 3.12 + `pypdf` | Extrair texto dos PDFs baixados, normalizar e gerar chunks de tamanho fixo prontos pra embedding. |
| `embedding/` | ✅ feito e testado | Python 3.12 + `sentence-transformers` | Modelo local `paraphrase-multilingual-MiniLM-L12-v2` (multilíngue, bom em português, roda em CPU) — **vetores de 384 dimensões**, valor a usar no schema pgvector do `database/`. |
| `database/` | não iniciado | PostgreSQL + pgvector | Mantido da ideia original — compete de igual pra igual com bancos vetoriais dedicados em escala de POC/médio porte, e mantém dados relacionais (metadados, grafo de relações) junto com os vetores. |
| `recommender/` | não iniciado | Python | Similaridade vetorial e/ou abordagem baseada em grafo; mesma razão do `embedding/`. |
| `api/` | não iniciado | **em aberto** | Ainda não decidido se expõe em Python (FastAPI, mais natural se `embedding`/`recommender` já forem Python) ou Java (Spring Boot, mais natural se quiser reaproveitar código/padrões do `crawler`). Decidir quando chegarmos nessa etapa. |

Ou seja: o pipeline vai ficar poliglota — Java na borda de ingestão de dados
externos, Python no núcleo de ML/recomendação. É um padrão comum em projetos
reais desse tipo.

## Próximos passos (em ordem)

1. **`database/`** — próximo módulo a construir, agora sem incertezas de
   schema: desenhar o schema PostgreSQL com pgvector: tabela de documentos
   (metadados), tabela de chunks/embeddings (`vector(384)`, FK pro
   documento — dimensão já definida pelo `embedding/`), índice
   `ivfflat`/`hnsw` pra busca por similaridade. Carregar os arquivos
   `{id}.chunks.jsonl` gerados pelo `embedding/` (já incluem texto,
   metadados e vetor por chunk).
2. **`recommender/`** — a partir de um documento (ou de uma busca em texto
   livre), retornar os N documentos mais relacionados via similaridade de
   embeddings (cosine distance no pgvector), com possibilidade de evoluir
   pra abordagem baseada em grafo (relações autor/tema/citação) depois que
   o básico por similaridade estiver validado.
3. **`api/`** — expor crawler/ingestion/embedding/recommender como serviço
   consultável (ex. endpoint de busca semântica, endpoint de recomendação
   por documento). Decidir linguagem nessa hora, com o resto do pipeline já
   rodando.

## Coisas para revisitar mais pra frente

- Descoberta de documentos no crawler hoje é por varredura sequencial de ID;
  existe um endpoint de busca (`/api/consulta`) no Pergamum que poderia
  tornar isso mais direcionado — ver limitações em `crawler/README.md`.
- Fallback de download de arquivo grande no Google Drive (página de aviso de
  vírus) ainda não foi validado contra um arquivo real que dispare esse
  comportamento.
