"""CLI de embedding: chunks do ingestion/ -> chunks + vetores prontos para o database/."""
import argparse
import json
import logging
from pathlib import Path

from embedding.embedder import Embedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
logger = logging.getLogger("embedding")

DEFAULT_MODEL = "BAAI/bge-m3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera embeddings para os chunks produzidos pelo ingestion/.")
    parser.add_argument("--in", dest="in_dir", default="ingested", help="Diretório com {id}.chunks.jsonl do ingestion")
    parser.add_argument("--out", dest="out_dir", default="embedded", help="Diretório de saída")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Nome do modelo sentence-transformers")
    parser.add_argument("--batch-size", type=int, default=32, help="Tamanho do batch para o encode")
    return parser.parse_args()


def process_document(jsonl_path: Path, out_dir: Path, embedder: Embedder, batch_size: int) -> int:
    records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        return 0

    embeddings = embedder.encode([record["text"] for record in records], batch_size)

    out_path = out_dir / jsonl_path.name
    with out_path.open("w", encoding="utf-8") as f:
        for record, embedding in zip(records, embeddings):
            record["embedding"] = embedding
            record["embeddingModel"] = embedder.model_name
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(records)


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("carregando modelo %s", args.model)
    embedder = Embedder(args.model)

    processados = 0
    pulados = 0
    erros = 0
    total_chunks = 0

    for jsonl_path in sorted(in_dir.glob("*.chunks.jsonl")):
        acervo_id = jsonl_path.name.removesuffix(".chunks.jsonl")
        try:
            n_chunks = process_document(jsonl_path, out_dir, embedder, args.batch_size)
        except Exception:
            logger.exception("acervo %s -> erro ao processar", acervo_id)
            erros += 1
            continue

        if n_chunks == 0:
            logger.warning("acervo %s -> sem chunks, pulando", acervo_id)
            pulados += 1
        else:
            logger.info("acervo %s -> %d chunks embeddados", acervo_id, n_chunks)
            processados += 1
            total_chunks += n_chunks

    logger.info(
        "Resumo: processados=%d chunks_embeddados=%d pulados=%d erros=%d",
        processados, total_chunks, pulados, erros,
    )


if __name__ == "__main__":
    main()
