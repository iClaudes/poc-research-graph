package school.cesar.researchgraph.crawler.http;

import java.io.IOException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * Envia uma requisição HTTP com algumas tentativas em caso de falha transiente
 * (erro de rede ou HTTP 5xx) — a API do Pergamum e o Google Drive não
 * documentam nenhuma garantia de disponibilidade, então uma falha isolada não
 * deveria descartar um ID inteiro da varredura.
 */
public final class RetryingHttp {

    private RetryingHttp() {
    }

    public static <T> HttpResponse<T> send(
            HttpClient client,
            HttpRequest request,
            HttpResponse.BodyHandler<T> bodyHandler,
            int maxAttempts,
            long backoffMs
    ) throws IOException, InterruptedException {
        IOException lastError = null;

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                HttpResponse<T> response = client.send(request, bodyHandler);
                if (response.statusCode() < 500 || attempt == maxAttempts) {
                    return response;
                }
                lastError = new IOException("HTTP " + response.statusCode() + " em " + request.uri()
                        + " (tentativa " + attempt + "/" + maxAttempts + ")");
            } catch (IOException e) {
                lastError = e;
                if (attempt == maxAttempts) {
                    throw lastError;
                }
            }
            Thread.sleep(backoffMs * attempt);
        }

        throw lastError;
    }
}
