const DEFAULT_LIMIT = 20;
const DEFAULT_TOP_N = 5;

function parseRoute() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, queryString] = raw.split("?");
  const params = new URLSearchParams(queryString || "");
  return { path, params };
}

async function renderRoute() {
  const { path, params } = parseRoute();
  const docMatch = path.match(/^\/doc\/(\d+)$/);

  try {
    if (path === "/search") {
      const q = params.get("q") || "";
      if (!q.trim()) {
        renderEmpty("Digite um termo de busca.");
        return;
      }
      const results = await search(q, DEFAULT_TOP_N);
      renderSearchResults(results, q);
    } else if (docMatch) {
      const codAcervo = Number(docMatch[1]);
      const doc = await fetchDocument(codAcervo);
      const recommendations = await fetchRecommendations(codAcervo, DEFAULT_TOP_N);
      renderDocumentDetail(doc, recommendations);
    } else {
      const limit = Number(params.get("limit")) || DEFAULT_LIMIT;
      const offset = Number(params.get("offset")) || 0;
      const docs = await fetchDocuments(limit, offset);
      renderDocumentList(docs, limit, offset);
    }
  } catch (err) {
    renderError(err.message || "Erro inesperado.");
  }
}

document.getElementById("search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const q = document.getElementById("search-input").value;
  location.hash = `#/search?q=${encodeURIComponent(q)}`;
});

window.addEventListener("hashchange", renderRoute);
window.addEventListener("DOMContentLoaded", renderRoute);
