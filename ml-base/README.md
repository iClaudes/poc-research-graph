# ml-base

Imagem base compartilhada por `embedding/`, `recommender/` e `api/` — os
três módulos que precisam do `sentence-transformers`
(`paraphrase-multilingual-MiniLM-L12-v2`) rodando localmente. Não é um
serviço (não faz parte do `docker-compose.yml`, nunca é executado sozinho)
— é só a camada pesada de dependências, construída uma vez e reaproveitada
pelos três, em vez de cada um baixar sua própria cópia de PyTorch +
`sentence-transformers` + o modelo.

Contém:
- PyTorch **CPU-only** (`--index-url https://download.pytorch.org/whl/cpu`)
  — o wheel padrão do PyPI traz ~4,6GB de bibliotecas CUDA/NVIDIA não
  usadas, já que nenhum desses containers tem acesso a GPU.
- `sentence-transformers`.
- Os pesos do modelo `paraphrase-multilingual-MiniLM-L12-v2` já baixados
  (bake-in em tempo de build, mesma lógica que cada módulo tinha
  individualmente antes).

## Build

**Precisa ser construída antes de `embedding/`, `recommender/` ou
`api/`** — os Dockerfiles deles usam `FROM
poc-research-graph-ml-base:latest`, que precisa existir localmente (não é
publicada em nenhum registry):

```
docker build -t poc-research-graph-ml-base:latest ./ml-base
```

Reconstrua sempre que mudar a versão do PyTorch/`sentence-transformers`
aqui — os módulos dependentes só pegam a mudança depois de rebuildados
também (`docker compose build embedding recommender api`).
