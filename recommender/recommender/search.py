"""Busca KNN no pgvector + agregação por documento (similaridade máxima entre chunks)."""
import psycopg

PER_QUERY_LIMIT = 20
MAX_REFERENCE_VECTORS = 150


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
    best_per_doc: dict[int, dict] = {}

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
                current = best_per_doc.get(cod_acervo)
                if current is None or similarity > current["similarity"]:
                    best_per_doc[cod_acervo] = {
                        "cod_acervo": cod_acervo,
                        "similarity": similarity,
                        "chunk_index": chunk_index,
                        "snippet": text[:200],
                    }

    ranked = sorted(best_per_doc.values(), key=lambda r: r["similarity"], reverse=True)[:top_n]

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
