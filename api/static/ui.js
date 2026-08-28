function escapeHtml(value) {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function docMeta(doc) {
  const parts = [doc.autor, doc.tipo_obra].filter(Boolean).map(escapeHtml);
  return parts.join(" · ");
}

function renderError(message) {
  document.getElementById("content").innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
}

function renderEmpty(message) {
  document.getElementById("content").innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
}

function renderDocumentList(docs, limit, offset) {
  if (!docs.length && offset === 0) {
    renderEmpty("Nenhum documento cadastrado.");
    return;
  }
  const items = docs
    .map(
      (doc) => `
    <a class="card" href="#/doc/${doc.cod_acervo}">
      <h3>${escapeHtml(doc.titulo) || "(sem título)"}</h3>
      <div class="meta">${docMeta(doc)}</div>
    </a>`
    )
    .join("");
  const prevOffset = Math.max(0, offset - limit);
  const nextOffset = offset + limit;
  const hasPrev = offset > 0;
  const hasNext = docs.length === limit;
  document.getElementById("content").innerHTML = `
    ${items || '<div class="empty">Nenhum resultado nesta página.</div>'}
    <div class="pagination">
      <button ${hasPrev ? "" : "disabled"} onclick="location.hash='#/?limit=${limit}&offset=${prevOffset}'">Anterior</button>
      <button ${hasNext ? "" : "disabled"} onclick="location.hash='#/?limit=${limit}&offset=${nextOffset}'">Próxima</button>
    </div>`;
}

function renderSearchResults(results, q) {
  if (!results.length) {
    renderEmpty(`Nenhum resultado para "${escapeHtml(q)}".`);
    return;
  }
  const items = results
    .map(
      (r) => `
    <a class="card" href="#/doc/${r.cod_acervo}">
      <h3>${escapeHtml(r.titulo) || "(sem título)"}<span class="similarity-badge">${(r.similarity * 100).toFixed(1)}%</span></h3>
      <div class="meta">${docMeta(r)}</div>
      <div class="snippet">${escapeHtml(r.snippet)}</div>
    </a>`
    )
    .join("");
  document.getElementById("content").innerHTML = items;
}

function renderDocumentDetail(doc, recommendations) {
  const recItems = recommendations
    .map(
      (r) => `
    <a class="card" href="#/doc/${r.cod_acervo}">
      <h3>${escapeHtml(r.titulo) || "(sem título)"}<span class="similarity-badge">${(r.similarity * 100).toFixed(1)}%</span></h3>
      <div class="meta">${docMeta(r)}</div>
      <div class="snippet">${escapeHtml(r.snippet)}</div>
    </a>`
    )
    .join("");
  document.getElementById("content").innerHTML = `
    <div class="doc-detail">
      <h2>${escapeHtml(doc.titulo) || "(sem título)"}</h2>
      <div class="meta">${docMeta(doc)}${doc.fonte_url ? ` · <a href="${escapeHtml(doc.fonte_url)}" target="_blank" rel="noopener">fonte</a>` : ""}</div>
    </div>
    <h3 class="section-title">Recomendações</h3>
    ${recItems || '<div class="empty">Nenhuma recomendação encontrada.</div>'}`;
}
