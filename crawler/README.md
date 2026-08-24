# crawler

Baixa PDFs de TCCs/dissertações/teses do acervo da Biblioteca CESAR
(`biblioteca.cesar.school`) junto com seus metadados, para alimentar as
próximas etapas do pipeline (embeddings, pgvector, recomendação).

## Como o site funciona

`biblioteca.cesar.school` é um sistema **Pergamum** (SPA em React) — o HTML
servido não tem conteúdo, mas existe uma API JSON no mesmo domínio, sob
`/api`, que não está documentada publicamente mas foi mapeada por engenharia
reversa do bundle JS:

- `GET https://biblioteca.cesar.school/api/acervo/{id}` retorna o registro
  bibliográfico completo em JSON. O formato é estilo MARC: os dados (título,
  autor, resumo, links) ficam dentro de um array `campos`, cada um
  identificado por um código numérico (`245` = título, `100` = autor
  principal, `520` = resumo, `856` = acesso eletrônico). Ver
  `AcervoRecord` para os detalhes de extração.
- IDs sem registro retornam `404` — a numeração tem buracos, é esperado.
- A maioria dos registros é do tipo **Livros** (acervo físico) e não tem PDF.
- Registros de **Teses / Dissertações / TCC - Graduação** que têm PDF
  disponível marcam `download_pdf: "S"` num campo `link_data` aninhado dentro
  de `856`, e o link aponta para o **Google Drive** — o PDF não fica
  hospedado no próprio Pergamum.
- `robots.txt` do site é totalmente permissivo.

Por isso o crawler não usa browser headless: ele fala HTTP+JSON direto com
essa API, e resolve os PDFs via `https://drive.google.com/uc?export=download&id={fileId}`.

**Atenção:** essa API não é documentada oficialmente e pode mudar sem aviso.
Todo o conhecimento específico do site fica isolado em
`CesarLibraryClient`/`AcervoRecord`, então uma mudança no formato deve exigir
alterações só ali.

## Build

```
mvn clean package
```

Gera `target/crawler-0.1.0.jar` (fat jar via shade plugin).

## Uso

```
java -jar target/crawler-0.1.0.jar --start 1 --end 500 --out ./downloads [--delay-ms 500]
```

- `--start` / `--end`: faixa de IDs do acervo a varrer (obrigatório).
- `--out`: diretório de saída (padrão `./downloads`).
- `--delay-ms`: pausa entre requisições, em ms (padrão `500`) — por educação
  com o servidor.

Para cada ID na faixa que for Tese/Dissertação/TCC com PDF disponível, gera:

- `{id}.pdf` — o arquivo baixado do Google Drive.
- `{id}.json` — metadados normalizados (`codAcervo`, `tipoObra`, `titulo`,
  `autor`, `resumo`, `fonteUrl`, `driveFileId`, `baixadoEm`).

Registros sem PDF elegível (livros, teses sem PDF anexado, etc.) e IDs
inexistentes (404) são pulados e contabilizados no resumo impresso ao final.

## Como testar

1. Build: `mvn clean package`.
2. Rodar contra uma faixa pequena e conhecida (inclui TCCs com PDF, uma
   dissertação sem PDF e um livro):
   ```
   java -jar target/crawler-0.1.0.jar --start 95 --end 105 --out ./downloads --delay-ms 300
   ```
3. Conferir:
   - `downloads/{id}.pdf` existe pros IDs baixados, e o arquivo começa com
     `%PDF-` (magic bytes de PDF válido).
   - `downloads/{id}.json` tem `titulo`/`autor`/`resumo` preenchidos e
     `fonteUrl` apontando pro Google Drive.
   - O resumo impresso no final bate com a contagem de arquivos gerados.
4. Testar o caminho de erro/borda com uma faixa que inclua um ID inexistente,
   ex. `--start 1 --end 2` (o ID 1 não existe nesse acervo) — deve logar
   `-> 404, pulando` e continuar sem quebrar.

## Testes já realizados (2026-08-24)

Rodado contra o site real (`biblioteca.cesar.school`), não contra mocks.

**Investigação da API** (antes de escrever código): confirmado por engenharia
reversa do bundle JS e chamadas HTTP diretas que a API real vive em `/api`
(descoberta testando prefixos candidatos), que `GET /api/acervo/{id}`
devolve o registro completo, e que o PDF de teses/TCCs fica no Google Drive
(`link_acesso` dentro de `856` → `link_data.download_pdf == "S"`). Validado
que `https://drive.google.com/uc?export=download&id={fileId}` baixa direto
via redirect HTTP simples, sem precisar de autenticação, para o arquivo de
teste (id 100, ~6.9MB).

**Execução `--start 95 --end 105 --out ./downloads --delay-ms 300`:**

```
acervo 95  -> baixado (3.531.309 bytes)  TCC - Graduação
acervo 96  -> baixado (1.000.349 bytes)  TCC - Graduação
acervo 97  -> baixado (7.606.196 bytes)  TCC - Graduação
acervo 98  -> baixado (29.367.415 bytes) TCC - Graduação
acervo 99  -> baixado (12.495.318 bytes) TCC - Graduação
acervo 100 -> baixado (6.927.142 bytes)  TCC - Graduação
acervo 101 -> baixado (57.624.651 bytes) TCC - Graduação
acervo 102 -> baixado (9.596.759 bytes)  TCC - Graduação
acervo 103 -> pulado, tipo 'Dissertações' sem PDF elegível
acervo 104 -> pulado, tipo 'Dissertações' sem PDF elegível
acervo 105 -> pulado, tipo 'Livros' sem PDF elegível
Resumo: varridos=11 404=0 pulados=3 baixados=8 erros=0
```

Verificado manualmente:
- `100.pdf` começa com `%PDF-1.4` (PDF válido, não HTML de erro/permissão).
- `100.json` tem título, autor e resumo extraídos corretamente dos campos
  MARC 245/100/520.
- Arquivos de ~1MB a ~57MB baixaram sem disparar o interstitial de "aviso de
  vírus" do Drive (esse caminho de fallback continua não validado — ver
  limitações abaixo).

**Execução `--start 1 --end 2`:** confirmado tratamento de 404 (`acervo 1 ->
404, pulando`) sem interromper a varredura.

## Limitações conhecidas

- **Descoberta por varredura de ID sequencial.** É simples e já validada,
  mas gera muitas chamadas "vazias" (404 ou tipo não elegível). A API tem um
  endpoint de busca (`/api/consulta`, parâmetro `termo_pesquisa`) que
  poderia substituir isso por uma descoberta mais direcionada — os
  parâmetros exatos de filtro por tipo de obra não foram confirmados.
- **Arquivos grandes no Google Drive.** Para arquivos acima do limite de
  verificação de vírus do Drive (na prática, dezenas de MB), o Drive
  costuma devolver uma página HTML de confirmação em vez do arquivo. Há um
  fallback em `GoogleDriveDownloader` que tenta extrair o token `confirm=`
  dessa página e refazer a requisição, mas esse caminho é best-effort — não
  foi validado contra um arquivo real que disparasse esse comportamento
  nesta sessão (os arquivos testados, de ~1MB a ~57MB, baixaram direto sem
  interstitial).
