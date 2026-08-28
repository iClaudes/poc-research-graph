async function apiGet(path) {
  let res;
  try {
    res = await fetch(path);
  } catch (err) {
    throw { status: 0, message: "API indisponível, verifique se o backend está rodando." };
  }
  if (!res.ok) {
    if (res.status === 404) {
      throw { status: 404, message: "Não encontrado." };
    }
    throw { status: res.status, message: `Erro na API (${res.status}).` };
  }
  return res.json();
}

function fetchDocuments(limit, offset) {
  return apiGet(`/documents?limit=${limit}&offset=${offset}`);
}

function fetchDocument(codAcervo) {
  return apiGet(`/documents/${codAcervo}`);
}

function fetchRecommendations(codAcervo, topN) {
  return apiGet(`/documents/${codAcervo}/recommendations?top_n=${topN}`);
}

function search(q, topN) {
  return apiGet(`/search?q=${encodeURIComponent(q)}&top_n=${topN}`);
}
