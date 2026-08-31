"""Busca KNN no pgvector + agregação por documento.

Agregação: por documento candidato, junta o melhor match por chunk-alvo
distinto (mesmo chunk pode aparecer nos resultados de várias buscas KNN, uma
por vetor de referência). O ranqueamento usa a média dos TOP_K_CHUNKS
melhores chunks distintos, com zero-padding se houver menos que isso — exige
múltiplas partes do candidato realmente parecidas em vez de aceitar um único
pico (ver "Viés de tamanho" em api/README.md). No modo de busca em texto
livre (um só vetor de referência) isso equivale a pegar só o melhor chunk,
igual ao comportamento anterior — não há vetores extras pra formar um pico
espúrio nesse modo.
"""
import psycopg

PER_QUERY_LIMIT = 20
MAX_REFERENCE_VECTORS = 150
TOP_K_CHUNKS = 3
MIN_SIMILARITY = 0.35


def sample_evenly(items: list, max_count: int) -> list:
    if len(items) <= max_count:
        return items
    step = len(items) / max_count
    return [items[int(i * step)] for i in range(max_count)]


def fetch_document_vectors(conn: psycopg.Connection, cod_acervo: int) -> list[list[float]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding FROM chunks WHERE cod_acervo = %s ORDER BY chunk_index",
            (cod_acervo,),
        )
        vectors = [row[0] for row in cur.fetchall()]
    return sample_evenly(vectors, MAX_REFERENCE_VECTORS)


def recommend(
    conn: psycopg.Connection,
    query_vectors: list,
    exclude_cod_acervo: int | None,
    top_n: int,
) -> list[dict]:
    # cod_acervo -> chunk_index -> {"similarity": ..., "snippet": ...}
    chunk_hits: dict[int, dict[int, dict]] = {}

    with conn.cursor() as cur:
        for vector in query_vectors:
            if exclude_cod_acervo is not None:
                cur.execute(
                    """
                    SELECT cod_acervo, chunk_index, text, embedding <=> %s AS dist
                    FROM chunks
                    WHERE cod_acervo != %s
                    ORDER BY dist
                    LIMIT %s
                    """,
                    (vector, exclude_cod_acervo, PER_QUERY_LIMIT),
                )
            else:
                cur.execute(
                    """
                    SELECT cod_acervo, chunk_index, text, embedding <=> %s AS dist
                    FROM chunks
                    ORDER BY dist
                    LIMIT %s
                    """,
                    (vector, PER_QUERY_LIMIT),
                )

            for cod_acervo, chunk_index, text, dist in cur.fetchall():
                similarity = 1 - dist
                doc_hits = chunk_hits.setdefault(cod_acervo, {})
                current = doc_hits.get(chunk_index)
                if current is None or similarity > current["similarity"]:
                    doc_hits[chunk_index] = {"similarity": similarity, "snippet": text[:200]}

    # k_effective: no modo texto-livre (1 vetor de referência) fica 1, ou
    # seja, sem zero-padding e sem penalidade — só o melhor chunk conta,
    # igual ao comportamento anterior. No modo por documento (até 150
    # vetores) fica TOP_K_CHUNKS, exigindo múltiplos chunks parecidos.
    k_effective = min(TOP_K_CHUNKS, len(query_vectors)) if query_vectors else 1

    candidates = []
    for cod_acervo, hits in chunk_hits.items():
        top_hits = sorted(hits.items(), key=lambda kv: kv[1]["similarity"], reverse=True)[:k_effective]
        similarities = [hit["similarity"] for _, hit in top_hits]
        best_chunk_index, best_hit = top_hits[0]

        if best_hit["similarity"] < MIN_SIMILARITY:
            continue

        padded = similarities + [0.0] * (k_effective - len(similarities))
        score = sum(padded) / k_effective

        candidates.append({
            "cod_acervo": cod_acervo,
            "score": score,
            "similarity": best_hit["similarity"],
            "match_count": len(similarities),
            "chunk_index": best_chunk_index,
            "snippet": best_hit["snippet"],
        })

    ranked = sorted(candidates, key=lambda r: r["score"], reverse=True)[:top_n]
    for r in ranked:
        del r["score"]

    if not ranked:
        return []

    with conn.cursor() as cur:
        cur.execute(
            "SELECT cod_acervo, titulo, autor, tipo_obra, fonte_url FROM documents WHERE cod_acervo = ANY(%s)",
            ([r["cod_acervo"] for r in ranked],),
        )
        docs = {row[0]: {"titulo": row[1], "autor": row[2], "tipo_obra": row[3], "fonte_url": row[4]} for row in cur.fetchall()}

    for r in ranked:
        r.update(docs.get(r["cod_acervo"], {}))

    return ranked
