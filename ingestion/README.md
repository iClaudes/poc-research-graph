# ingestion

Pega os PDFs + metadados JSON gerados pelo `crawler/`, extrai o texto de
cada PDF, remove cabeçalho/rodapé repetido e produz chunks de texto de
tamanho fixo, prontos para a etapa de embedding.

## Formato de entrada

Diretório com pares `{id}.pdf` + `{id}.json` (saída do `crawler/`), onde o
`.json` tem pelo menos os campos `codAcervo`, `tipoObra`, `titulo`, `autor`,
`fonteUrl`.

## Formato de saída

Para cada `{id}.pdf` processado com sucesso, gera `{id}.chunks.jsonl` no
diretório de saída, uma linha JSON por chunk:

```json
{"codAcervo": 100, "chunkIndex": 0, "chunkCount": 12, "text": "...", "charStart": 0, "charEnd": 998, "titulo": "...", "autor": "...", "tipoObra": "...", "fonteUrl": "..."}
```

`{id}.pdf` sem `{id}.json` correspondente, ou PDF sem texto extraível
(ex. escaneado sem OCR), são pulados e contabilizados no resumo final.

**Nota sobre o chunking:** o tamanho do chunk é medido em **caracteres**,
não em tokens — o modelo de embedding (e portanto o tokenizer/limite de
contexto certo) ainda não foi escolhido; isso é decisão da próxima etapa do
pipeline (`embedding/`). Os defaults (1000 caracteres, overlap de 150) dão
uma margem segura para a maioria dos modelos de embedding comuns, mas devem
ser revisitados quando o modelo for definido.

## Build e uso local

Requer Python 3.12+.

```
cd ingestion
pip install -r requirements.txt
python -m ingestion.cli --in ../downloads --out ../ingested [--chunk-size 1000] [--chunk-overlap 150]
```

## Rodando com Docker

A partir da raiz do repositório:

```
docker build -t ingestion ./ingestion
docker run --rm -v "$(pwd)/downloads:/app/downloads:ro" -v "$(pwd)/ingested:/app/ingested" ingestion
```

Ou via docker compose (volumes já configurados no `docker-compose.yml` da
raiz, apontando para `downloads/` do crawler e `ingested/`):

```
docker compose run --rm ingestion
```

## Como testar

1. Gerar dados de entrada com o crawler (ver `crawler/README.md`), ex.:
   ```
   docker compose run --rm crawler --start 95 --end 105 --out /app/downloads --delay-ms 300
   ```
2. Rodar a ingestão sobre `downloads/`:
   ```
   docker compose run --rm ingestion
   ```
3. Conferir para um id baixado (ex. 100):
   - `ingested/100.chunks.jsonl` existe, cada linha é um JSON válido.
   - Concatenando os campos `text` dos chunks em ordem de `chunkIndex`
     (descontando o overlap) reproduz o texto extraído do PDF.
   - Nenhuma linha de cabeçalho/rodapé óbvia (repetida em várias páginas do
     PDF original) sobra no texto dos chunks.
   - `titulo`/`autor`/`tipoObra`/`fonteUrl` batem com `downloads/100.json`.
4. Testar caso de borda: apagar um `.json` correspondente a um `.pdf` e
   rodar de novo — deve logar aviso e seguir sem quebrar, resumo final com
   `pulados > 0`.
