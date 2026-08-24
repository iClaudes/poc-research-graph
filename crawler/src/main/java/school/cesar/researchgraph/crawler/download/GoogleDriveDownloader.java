package school.cesar.researchgraph.crawler.download;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Downloads files shared via Google Drive links, which is where the CESAR
 * library hosts the full text of theses/TCCs (the Pergamum server itself
 * only serves cover images).
 */
public final class GoogleDriveDownloader {

    private static final Logger log = LoggerFactory.getLogger(GoogleDriveDownloader.class);

    private static final Pattern FILE_ID_PATTERN = Pattern.compile("/d/([a-zA-Z0-9_-]+)");
    private static final Pattern CONFIRM_TOKEN_PATTERN = Pattern.compile("confirm=([0-9A-Za-z_-]+)");
    private static final String USER_AGENT =
            "poc-research-graph-crawler/0.1 (uso educacional - CESAR School)";

    private final HttpClient httpClient;

    public GoogleDriveDownloader(HttpClient httpClient) {
        this.httpClient = httpClient;
    }

    public Optional<String> extractFileId(String driveShareUrl) {
        Matcher matcher = FILE_ID_PATTERN.matcher(driveShareUrl);
        return matcher.find() ? Optional.of(matcher.group(1)) : Optional.empty();
    }

    /**
     * Downloads the file's bytes. For files above Drive's virus-scan size
     * threshold, Drive returns an HTML interstitial instead of the file; this
     * method makes a best-effort attempt to extract the {@code confirm}
     * token from that page and retry. That fallback path has not been
     * exercised against a real oversized file.
     */
    public byte[] download(String fileId) throws IOException, InterruptedException {
        String url = "https://drive.google.com/uc?export=download&id=" + fileId;
        HttpResponse<byte[]> response = get(url);

        String contentType = response.headers().firstValue("content-type").orElse("");
        if (contentType.startsWith("text/html")) {
            String body = new String(response.body(), StandardCharsets.UTF_8);
            Matcher matcher = CONFIRM_TOKEN_PATTERN.matcher(body);
            if (matcher.find()) {
                log.warn("Drive retornou página de confirmação para fileId={}, tentando novamente com token", fileId);
                response = get(url + "&confirm=" + matcher.group(1));
            } else {
                throw new IOException("Resposta HTML inesperada do Google Drive para fileId=" + fileId
                        + " (arquivo pode ter sido removido ou exigir permissão de acesso)");
            }
        }

        return response.body();
    }

    private HttpResponse<byte[]> get(String url) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("User-Agent", USER_AGENT)
                .GET()
                .build();
        return httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
    }
}
