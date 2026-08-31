package school.cesar.researchgraph.crawler.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import school.cesar.researchgraph.crawler.http.RetryingHttp;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Optional;

/**
 * Client for the undocumented Pergamum REST API behind
 * {@code biblioteca.cesar.school}. Every site-specific detail (base URL,
 * response shape) is isolated here so the rest of the crawler only deals
 * with {@link AcervoRecord}.
 */
public final class CesarLibraryClient {

    private static final String BASE_URL = "https://biblioteca.cesar.school/api/acervo/";
    private static final String USER_AGENT =
            "poc-research-graph-crawler/0.1 (uso educacional - CESAR School)";

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public CesarLibraryClient(HttpClient httpClient, ObjectMapper objectMapper) {
        this.httpClient = httpClient;
        this.objectMapper = objectMapper;
    }

    /**
     * Fetches the catalog record for the given id.
     *
     * @return the record, or {@link Optional#empty()} if the API returned 404
     * @throws IOException if the API returned an unexpected status or the
     *                      response body could not be parsed as JSON
     */
    public Optional<AcervoRecord> buscar(int codAcervo) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + codAcervo))
                .header("Accept", "application/json")
                .header("User-Agent", USER_AGENT)
                .GET()
                .build();

        HttpResponse<String> response = RetryingHttp.send(httpClient, request, HttpResponse.BodyHandlers.ofString(), 3, 300);

        if (response.statusCode() == 404) {
            return Optional.empty();
        }
        if (response.statusCode() != 200) {
            throw new IOException("HTTP " + response.statusCode() + " ao buscar acervo " + codAcervo);
        }

        JsonNode root = objectMapper.readTree(response.body());
        return Optional.of(new AcervoRecord(codAcervo, root));
    }
}
