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
| `crawler/` | ✅ feito e testado | Java 17 + Maven | Só HTTP + JSON, sem necessidade de ecossistema de ML; time já conhece Java; nada no mercado obriga trocar aqui. |
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
- Viés de tamanho na recomendação por documento (`api/` — modo
  `--cod-acervo`/`/recommendations`): documentos com muitos chunks têm
  vantagem estatística na agregação por similaridade máxima, mesmo sem
  relação temática real — ver limitações em `api/README.md`. Vale
  revisitar quando houver um corpus maior pra validar com mais confiança
  (o lote de 8 documentos testado não tem documentos genuinamente
  relacionados entre si pra maioria dos temas).
