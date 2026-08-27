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

/**
 * Varre uma faixa de IDs do acervo da Biblioteca CESAR, identifica teses/TCCs
 * com PDF disponível (hospedado no Google Drive) e baixa o PDF junto com um
 * sidecar de metadados em JSON.
 *
 * <p>Uso: {@code java -jar crawler.jar --start 1 --end 500 --out ./downloads [--delay-ms 500]}
 */
public final class CrawlerApp {

    private static final Logger log = LoggerFactory.getLogger(CrawlerApp.class);
    private static final long DEFAULT_DELAY_MS = 500;

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

        for (int id = cli.start; id <= cli.end; id++) {
            summary.scanned++;
            try {
                processarRegistro(id, client, downloader, outDir, objectMapper, summary);
            } catch (Exception e) {
                summary.erros++;
                log.error("acervo {} -> erro: {}", id, e.getMessage());
            }

            if (id < cli.end) {
                Thread.sleep(cli.delayMs);
            }
        }

        log.info("Resumo: varridos={} 404={} pulados={} baixados={} erros={}",
                summary.scanned, summary.notFound, summary.skipped, summary.downloaded, summary.erros);
    }

    private static void processarRegistro(int id, CesarLibraryClient client, GoogleDriveDownloader downloader,
                                            Path outDir, ObjectMapper objectMapper, Summary summary)
            throws IOException, InterruptedException {
        Optional<AcervoRecord> maybeRecord = client.buscar(id);
        if (maybeRecord.isEmpty()) {
            summary.notFound++;
            log.info("acervo {} -> 404, pulando", id);
            return;
        }

        AcervoRecord record = maybeRecord.get();
        Optional<String> pdfUrl = record.pdfDownloadUrl();

        if (!record.isTeseOuTcc() || pdfUrl.isEmpty()) {
            summary.skipped++;
            log.info("acervo {} -> tipo '{}' sem PDF elegível, pulando", id, record.tipoObra());
            return;
        }

        Optional<String> fileId = downloader.extractFileId(pdfUrl.get());
        if (fileId.isEmpty()) {
            summary.skipped++;
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

        summary.downloaded++;
        log.info("acervo {} -> baixado ({} bytes): {}", id, pdfBytes.length, record.titulo());
    }

    private static final class Summary {
        int scanned;
        int notFound;
        int skipped;
        int downloaded;
        int erros;
    }

    private static final class CliArgs {
        final int start;
        final int end;
        final String outDir;
        final long delayMs;

        private CliArgs(int start, int end, String outDir, long delayMs) {
            this.start = start;
            this.end = end;
            this.outDir = outDir;
            this.delayMs = delayMs;
        }

        static CliArgs parse(String[] args) {
            Integer start = null;
            Integer end = null;
            String outDir = "./downloads";
            long delayMs = DEFAULT_DELAY_MS;

            for (int i = 0; i < args.length; i++) {
                switch (args[i]) {
                    case "--start" -> start = Integer.parseInt(args[++i]);
                    case "--end" -> end = Integer.parseInt(args[++i]);
                    case "--out" -> outDir = args[++i];
                    case "--delay-ms" -> delayMs = Long.parseLong(args[++i]);
                    default -> throw new IllegalArgumentException("Argumento desconhecido: " + args[i]);
                }
            }

            if (start == null || end == null) {
                throw new IllegalArgumentException(
                        "Uso: --start <id> --end <id> [--out <dir>] [--delay-ms <ms>]");
            }
            if (start > end) {
                throw new IllegalArgumentException("--start deve ser <= --end");
            }

            return new CliArgs(start, end, outDir, delayMs);
        }
    }
}
