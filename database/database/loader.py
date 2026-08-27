"""Carga de documentos/chunks (saída do embedding/) no PostgreSQL + pgvector."""
import psycopg


def load_document(conn: psycopg.Connection, records: list[dict]) -> int:
    first = records[0]

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (cod_acervo, titulo, autor, tipo_obra, fonte_url)
            VALUES (%(codAcervo)s, %(titulo)s, %(autor)s, %(tipoObra)s, %(fonteUrl)s)
            ON CONFLICT (cod_acervo) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                autor = EXCLUDED.autor,
                tipo_obra = EXCLUDED.tipo_obra,
                fonte_url = EXCLUDED.fonte_url
            """,
            first,
        )

        cur.execute("DELETE FROM chunks WHERE cod_acervo = %s", (first["codAcervo"],))

        cur.executemany(
            """
            INSERT INTO chunks (
                cod_acervo, chunk_index, chunk_count, text,
                char_start, char_end, embedding, embedding_model
            ) VALUES (
                %(codAcervo)s, %(chunkIndex)s, %(chunkCount)s, %(text)s,
                %(charStart)s, %(charEnd)s, %(embedding)s, %(embeddingModel)s
            )
            """,
            records,
        )

    conn.commit()
    return len(records)
