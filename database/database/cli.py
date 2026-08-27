"""CLI de carga: chunks + embeddings do embedding/ -> PostgreSQL/pgvector."""
import argparse
import json
import logging
import os
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from database.loader import load_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
logger = logging.getLogger("database")

DEFAULT_DATABASE_URL = "postgresql://research_graph:research_graph@postgres:5432/research_graph"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carrega chunks + embeddings no PostgreSQL/pgvector.")
    parser.add_argument("--in", dest="in_dir", default="embedded", help="Diretório com {id}.chunks.jsonl do embedding")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="String de conexão PostgreSQL",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)

    documentos = 0
    total_chunks = 0
    erros = 0

    with psycopg.connect(args.database_url) as conn:
        register_vector(conn)

        for jsonl_path in sorted(in_dir.glob("*.chunks.jsonl")):
            acervo_id = jsonl_path.name.removesuffix(".chunks.jsonl")
            records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not records:
                logger.warning("acervo %s -> sem chunks, pulando", acervo_id)
                continue

            try:
                n_chunks = load_document(conn, records)
            except Exception:
                conn.rollback()
                logger.exception("acervo %s -> erro ao carregar", acervo_id)
                erros += 1
                continue

            logger.info("acervo %s -> %d chunks carregados", acervo_id, n_chunks)
            documentos += 1
            total_chunks += n_chunks

    logger.info(
        "Resumo: documentos=%d chunks_carregados=%d erros=%d",
        documentos, total_chunks, erros,
    )


if __name__ == "__main__":
    main()
