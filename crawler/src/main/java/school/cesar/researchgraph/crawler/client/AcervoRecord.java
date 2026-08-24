package school.cesar.researchgraph.crawler.client;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Locale;
import java.util.Optional;

/**
 * Wraps the raw JSON returned by {@code GET /api/acervo/{id}}.
 *
 * <p>The Pergamum API represents bibliographic data as a list of MARC-style
 * fields ({@code campos}) identified by numeric codes (245 = título, 100 =
 * autor principal, 520 = resumo, 856 = acesso eletrônico) rather than fixed
 * top-level properties, and the shape of nested nodes (e.g. {@code link_data})
 * varies between an object and an empty array depending on the record. A tree
 * model is used instead of a fixed POJO so lookups stay tolerant of that.
 */
public final class AcervoRecord {

    private static final String CAMPO_TITULO = "245";
    private static final String CAMPO_AUTOR = "100";
    private static final String CAMPO_RESUMO = "520";

    private final int codAcervo;
    private final JsonNode root;

    AcervoRecord(int codAcervo, JsonNode root) {
        this.codAcervo = codAcervo;
        this.root = root;
    }

    public int codAcervo() {
        return codAcervo;
    }

    public String tipoObra() {
        return root.path("tipo_obra").asText("");
    }

    public String titulo() {
        return campoTexto(CAMPO_TITULO);
    }

    public String autor() {
        return campoTexto(CAMPO_AUTOR);
    }

    public String resumo() {
        return campoTexto(CAMPO_RESUMO);
    }

    public boolean isTeseOuTcc() {
        String tipo = tipoObra().toLowerCase(Locale.ROOT);
        return tipo.contains("tese") || tipo.contains("tcc") || tipo.contains("dissert");
    }

    /**
     * Walks the 856 (electronic access) entries looking for one flagged
     * {@code download_pdf: "S"} and returns its URL, if any.
     */
    public Optional<String> pdfDownloadUrl() {
        for (JsonNode campo : root.path("campos")) {
            for (JsonNode detalhe : campo.path("detalhes")) {
                JsonNode linkData = detalhe.path("link_data");
                if ("S".equals(linkData.path("download_pdf").asText(null))) {
                    String url = linkData.path("url_link").asText(null);
                    if (url == null || url.isBlank()) {
                        url = detalhe.path("link_acesso").asText(null);
                    }
                    if (url != null && !url.isBlank()) {
                        return Optional.of(url);
                    }
                }
            }
        }
        return Optional.empty();
    }

    private String campoTexto(String marcCode) {
        for (JsonNode campo : root.path("campos")) {
            if (marcCode.equals(campo.path("ordem").asText())) {
                StringBuilder texto = new StringBuilder();
                for (JsonNode detalhe : campo.path("detalhes")) {
                    for (JsonNode parte : detalhe.path("descricao")) {
                        if (texto.length() > 0) {
                            texto.append(" ");
                        }
                        texto.append(parte.asText());
                    }
                }
                return texto.toString();
            }
        }
        return "";
    }
}
