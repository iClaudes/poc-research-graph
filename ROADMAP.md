# Roadmap

Status e próximos passos do pipeline **Crawler → Ingestion → Embedding →
PostgreSQL/pgvector → Recomendação**. Para o que já foi feito e testado, ver
[`crawler/README.md`](crawler/README.md) e
[`ingestion/README.md`](ingestion/README.md).

## Stack por módulo

| Módulo | Status | Tecnologia | Por quê |
|---|---|---|---|
| `crawler/` | ✅ feito e testado | Java 17 + Maven | Só HTTP + JSON, sem necessidade de ecossistema de ML; time já conhece Java; nada no mercado obriga trocar aqui. |
| `ingestion/` | ✅ feito e testado | Python 3.12 + `pypdf` | Extrair texto dos PDFs baixados, normalizar e gerar chunks de tamanho fixo prontos pra embedding. |
| `embedding/` | não iniciado | Python | É onde vive o ecossistema de ML (sentence-transformers, APIs de embedding); tentar fazer isso em Java significa nadar contra a corrente do mercado. |
| `database/` | não iniciado | PostgreSQL + pgvector | Mantido da ideia original — compete de igual pra igual com bancos vetoriais dedicados em escala de POC/médio porte, e mantém dados relacionais (metadados, grafo de relações) junto com os vetores. |
| `recommender/` | não iniciado | Python | Similaridade vetorial e/ou abordagem baseada em grafo; mesma razão do `embedding/`. |
| `api/` | não iniciado | **em aberto** | Ainda não decidido se expõe em Python (FastAPI, mais natural se `embedding`/`recommender` já forem Python) ou Java (Spring Boot, mais natural se quiser reaproveitar código/padrões do `crawler`). Decidir quando chegarmos nessa etapa. |

Ou seja: o pipeline vai ficar poliglota — Java na borda de ingestão de dados
externos, Python no núcleo de ML/recomendação. É um padrão comum em projetos
reais desse tipo.

## Próximos passos (em ordem)

1. **`database/`** — próximo módulo a construir. Desenhar o schema
   PostgreSQL com pgvector: tabela de documentos (metadados), tabela de
   chunks/embeddings (vetor + FK pro documento), índice `ivfflat`/`hnsw`
   pra busca por similaridade.
   - Decisão em aberto: dimensão do vetor depende do modelo de embedding
     escolhido na etapa seguinte — desenhar o schema depois de decidir o
     modelo, não antes.
2. **`embedding/`** — gerar os vetores a partir dos chunks de texto
   (produzidos pelo `ingestion/`, um chunk por linha em `{id}.chunks.jsonl`).
   - Decisão em aberto: modelo local (ex. `sentence-transformers`, roda
     offline, sem custo por chamada) vs. API de terceiro (OpenAI, Cohere,
     Voyage — melhor qualidade, mas custo e dependência externa). Pra POC,
     modelo local costuma ser o caminho mais simples de validar rápido.
   - Definir o modelo aqui também define o tamanho de chunk ideal (hoje o
     `ingestion/` usa um tamanho fixo em caracteres, não em tokens — ver
     `ingestion/README.md`).
3. **`recommender/`** — a partir de um documento (ou de uma busca em texto
   livre), retornar os N documentos mais relacionados via similaridade de
   embeddings (cosine distance no pgvector), com possibilidade de evoluir
   pra abordagem baseada em grafo (relações autor/tema/citação) depois que
   o básico por similaridade estiver validado.
4. **`api/`** — expor crawler/ingestion/embedding/recommender como serviço
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
