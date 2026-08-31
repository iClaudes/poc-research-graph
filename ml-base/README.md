# ml-base

Imagem base compartilhada por `processing/embedding/` e `api/` — os dois
módulos que precisam do `sentence-transformers` (`BAAI/bge-m3`) rodando
localmente. Não é um serviço (não faz parte do `docker-compose.yml`, nunca
é executado sozinho) — é só a camada pesada de dependências, construída
uma vez e reaproveitada pelos dois, em vez de cada um baixar sua própria
cópia de PyTorch + `sentence-transformers` + o modelo.

Contém:
- PyTorch — **CPU por padrão**
  (`--index-url https://download.pytorch.org/whl/cpu`, o wheel padrão do
  PyPI traz ~4,6GB de bibliotecas CUDA/NVIDIA não usadas em máquinas sem
  GPU), com uma variante **GPU opcional** pra quem tem NVIDIA + driver
  instalados (ver "Build com GPU" abaixo).
- `sentence-transformers`.
- Os pesos do modelo `BAAI/bge-m3` já baixados (bake-in em tempo de build,
  mesma lógica que cada módulo tinha individualmente antes). Modelo
  multilíngue treinado pra recuperação/busca (não "paraphrase mining"
  como o modelo anterior, `paraphrase-multilingual-MiniLM-L12-v2`) —
  separa melhor tema de estilo de escrita, o que importa pro `api/`
  (ver "Limitações conhecidas" em `api/README.md`).

## Build (CPU, padrão)

**Precisa ser construída antes de `processing/embedding/` ou `api/`** — os
Dockerfiles deles usam `FROM poc-research-graph-ml-base:${ML_BASE_TAG}`
(padrão `latest`), que precisa existir localmente (não é publicada em
nenhum registry):

```
docker build -t poc-research-graph-ml-base:latest ./ml-base
```

Reconstrua sempre que mudar a versão do PyTorch/`sentence-transformers`
aqui — os módulos dependentes só pegam a mudança depois de rebuildados
também (`docker compose build embedding api`).

## Build com GPU (opcional)

Se a máquina tiver uma GPU NVIDIA com driver instalado e o Docker
reconhecer o runtime `nvidia` (`docker info` deve listar `nvidia` em
`Runtimes:`), dá pra buildar uma variante acelerada, com uma tag separada
(`:gpu`) pra não conflitar com a imagem CPU:

```
docker build -t poc-research-graph-ml-base:gpu \
  --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124 \
  ./ml-base
```

Confira em https://pytorch.org/get-started/locally/ qual tag `cuXXX` o
PyTorch publica no momento do build — drivers NVIDIA são retrocompatíveis
com versões de CUDA mais antigas, então geralmente a tag estável mais
recente funciona mesmo com um driver mais novo.

Depois, use o override `docker-compose.gpu.yml` (raiz do repositório) pra
fazer `processing/embedding/` e `api/` usarem essa imagem e reservarem a
GPU:

```
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build embedding api
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm embedding
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d api
```

`sentence-transformers` seleciona `cuda` automaticamente quando disponível
— não precisa mudar nenhum código dos módulos, só a imagem base e o
override do Compose. Sem esses dois, tudo continua CPU-only (padrão).

Verificar que o build pegou a GPU:

```
docker run --rm poc-research-graph-ml-base:gpu python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Deve imprimir `True` e o nome da placa.
