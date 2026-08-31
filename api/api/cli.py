"""CLI de recomendação: por documento existente ou por busca em texto livre."""
import argparse
import json
import logging
import os
import sys

import psycopg
from pgvector.psycopg import register_vector

from api.embedder import DEFAULT_MODEL, Embedder
from api.search import fetch_document_vectors, recommend

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
logger = logging.getLogger("api.cli")

DEFAULT_DATABASE_URL = "postgresql://research_graph:research_graph@postgres:5432/research_graph"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recomenda documentos por similaridade de embeddings.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cod-acervo", type=int, help="Recomenda documentos parecidos com este acervo")
    group.add_argument("--query", help="Recomenda documentos a partir de uma busca em texto livre")
    parser.add_argument("--top-n", type=int, default=5, help="Número de documentos a retornar")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="String de conexão PostgreSQL",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo sentence-transformers (modo --query)")
    parser.add_argument("--out", help="Caminho opcional para gravar o resultado em JSON")
    return parser.parse_args()


def print_results(results: list[dict]) -> None:
    if not results:
        print("Nenhum resultado encontrado.")
        return
    for rank, r in enumerate(results, start=1):
        trechos = f"{r['match_count']} trecho{'s' if r['match_count'] != 1 else ''} parecido{'s' if r['match_count'] != 1 else ''}"
        print(f"{rank}. [{r['similarity']:.3f}] acervo {r['cod_acervo']} - {r.get('titulo')} ({trechos})")
        print(f"   autor: {r.get('autor')} | tipo: {r.get('tipo_obra')}")
        print(f"   trecho (chunk {r['chunk_index']}): {r['snippet']}")


def main() -> None:
    args = parse_args()

    with psycopg.connect(args.database_url) as conn:
        register_vector(conn)

        if args.cod_acervo is not None:
            query_vectors = fetch_document_vectors(conn, args.cod_acervo)
            if not query_vectors:
                logger.error("acervo %s não encontrado no banco (sem chunks)", args.cod_acervo)
                sys.exit(1)
            results = recommend(conn, query_vectors, exclude_cod_acervo=args.cod_acervo, top_n=args.top_n)
        else:
            embedder = Embedder(args.model)
            query_vector = embedder.encode_one(args.query)
            results = recommend(conn, [query_vector], exclude_cod_acervo=None, top_n=args.top_n)

    print_results(results)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("resultado gravado em %s", args.out)


if __name__ == "__main__":
    main()
