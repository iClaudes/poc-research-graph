package school.cesar.researchgraph.crawler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import school.cesar.researchgraph.crawler.client.AcervoRecord;
import school.cesar.researchgraph.crawler.client.CesarLibraryClient;
import school.cesar.researchgraph.crawler.download.GoogleDriveDownloader;

import java.io.IOException;
import java.net.http.HttpClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Varre uma faixa de IDs do acervo da Biblioteca CESAR, identifica teses/TCCs
 * com PDF disponível (hospedado no Google Drive) e baixa o PDF junto com um
 * sidecar de metadados em JSON.
 *
 * <p>Cada ID é processado numa virtual thread própria (I/O-bound: é tudo
 * espera de rede), com o grau de paralelismo real limitado por um semáforo
 * ({@code --concurrency}) — paraleliza a espera de rede sem virar uma
 * varredura "o mais rápido possível" contra um servidor de terceiro que não
 * documenta nem garante limites de taxa.
 *
 * <p>Uso: {@code java -jar crawler.jar --start 1 --end 500 --out ./downloads [--delay-ms 500] [--concurrency 4]}
 */
public final class CrawlerApp {

    private static final Logger log = LoggerFactory.getLogger(CrawlerApp.class);
    private static final long DEFAULT_DELAY_MS = 500;
    private static final int DEFAULT_CONCURRENCY = 4;

    public static void main(String[] args) throws Exception {
        CliArgs cli = CliArgs.parse(args);

        HttpClient httpClient = HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NORMAL)
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        ObjectMapper objectMapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

        CesarLibraryClient client = new CesarLibraryClient(httpClient, objectMapper);
        GoogleDriveDownloader downloader = new GoogleDriveDownloader(httpClient);

        Path outDir = Path.of(cli.outDir);
        Files.createDirectories(outDir);

        Summary summary = new Summary();
        Semaphore concurrencyLimit = new Semaphore(cli.concurrency);

        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int id = cli.start; id <= cli.end; id++) {
                int currentId = id;
                concurrencyLimit.acquire();
                executor.submit(() -> {
                    try {
                        summary.scanned.incrementAndGet();
                        try {
                            processarRegistro(currentId, client, downloader, outDir, objectMapper, summary);
                        } catch (Exception e) {
                            summary.erros.incrementAndGet();
                            log.error("acervo {} -> erro: {}", currentId, e.getMessage());
                        }
                        Thread.sleep(cli.delayMs);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    } finally {
                        concurrencyLimit.release();
                    }
                });
            }
        } // fecha o executor e aguarda todas as virtual threads terminarem

        log.info("Resumo: varridos={} 404={} pulados={} baixados={} erros={}",
                summary.scanned.get(), summary.notFound.get(), summary.skipped.get(),
                summary.downloaded.get(), summary.erros.get());
    }

    private static void processarRegistro(int id, CesarLibraryClient client, GoogleDriveDownloader downloader,
                                            Path outDir, ObjectMapper objectMapper, Summary summary)
            throws IOException, InterruptedException {
        Optional<AcervoRecord> maybeRecord = client.buscar(id);
        if (maybeRecord.isEmpty()) {
            summary.notFound.incrementAndGet();
            log.info("acervo {} -> 404, pulando", id);
            return;
        }

        AcervoRecord record = maybeRecord.get();
        Optional<String> pdfUrl = record.pdfDownloadUrl();

        if (!record.isTeseOuTcc() || pdfUrl.isEmpty()) {
            summary.skipped.incrementAndGet();
            log.info("acervo {} -> tipo '{}' sem PDF elegível, pulando", id, record.tipoObra());
            return;
        }

        Optional<String> fileId = downloader.extractFileId(pdfUrl.get());
        if (fileId.isEmpty()) {
            summary.skipped.incrementAndGet();
            log.warn("acervo {} -> link '{}' não é um link de compartilhamento do Drive reconhecido, pulando",
                    id, pdfUrl.get());
            return;
        }

        byte[] pdfBytes = downloader.download(fileId.get());
        Path pdfPath = outDir.resolve(id + ".pdf");
        Files.write(pdfPath, pdfBytes);

        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("codAcervo", record.codAcervo());
        metadata.put("tipoObra", record.tipoObra());
        metadata.put("titulo", record.titulo());
        metadata.put("autor", record.autor());
        metadata.put("resumo", record.resumo());
        metadata.put("fonteUrl", pdfUrl.get());
        metadata.put("driveFileId", fileId.get());
        metadata.put("baixadoEm", Instant.now().toString());

        Path metadataPath = outDir.resolve(id + ".json");
        objectMapper.writeValue(metadataPath.toFile(), metadata);

        summary.downloaded.incrementAndGet();
        log.info("acervo {} -> baixado ({} bytes): {}", id, pdfBytes.length, record.titulo());
    }

    private static final class Summary {
        final AtomicInteger scanned = new AtomicInteger();
        final AtomicInteger notFound = new AtomicInteger();
        final AtomicInteger skipped = new AtomicInteger();
        final AtomicInteger downloaded = new AtomicInteger();
        final AtomicInteger erros = new AtomicInteger();
    }

    private static final class CliArgs {
        final int start;
        final int end;
        final String outDir;
        final long delayMs;
        final int concurrency;

        private CliArgs(int start, int end, String outDir, long delayMs, int concurrency) {
            this.start = start;
            this.end = end;
            this.outDir = outDir;
            this.delayMs = delayMs;
            this.concurrency = concurrency;
        }

        static CliArgs parse(String[] args) {
            Integer start = null;
            Integer end = null;
            String outDir = "./downloads";
            long delayMs = DEFAULT_DELAY_MS;
            int concurrency = DEFAULT_CONCURRENCY;

            for (int i = 0; i < args.length; i++) {
                switch (args[i]) {
                    case "--start" -> start = Integer.parseInt(args[++i]);
                    case "--end" -> end = Integer.parseInt(args[++i]);
                    case "--out" -> outDir = args[++i];
                    case "--delay-ms" -> delayMs = Long.parseLong(args[++i]);
                    case "--concurrency" -> concurrency = Integer.parseInt(args[++i]);
                    default -> throw new IllegalArgumentException("Argumento desconhecido: " + args[i]);
                }
            }

            if (start == null || end == null) {
                throw new IllegalArgumentException(
                        "Uso: --start <id> --end <id> [--out <dir>] [--delay-ms <ms>] [--concurrency <n>]");
            }
            if (start > end) {
                throw new IllegalArgumentException("--start deve ser <= --end");
            }
            if (concurrency < 1) {
                throw new IllegalArgumentException("--concurrency deve ser >= 1");
            }

            return new CliArgs(start, end, outDir, delayMs, concurrency);
        }
    }
}
