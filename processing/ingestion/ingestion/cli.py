"""CLI de ingestão: PDFs + metadados do crawler -> chunks de texto prontos para embedding."""
import argparse
import json
import logging
from pathlib import Path

from ingestion.chunking import chunk_text
from ingestion.cleaning import clean_pages
from ingestion.pdf_extract import extract_pages

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
logger = logging.getLogger("ingestion")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrai texto de PDFs e gera chunks para embedding.")
    parser.add_argument("--in", dest="in_dir", default="downloads", help="Diretório com {id}.pdf/{id}.json do crawler")
    parser.add_argument("--out", dest="out_dir", default="ingested", help="Diretório de saída dos chunks")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Tamanho do chunk em caracteres")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Overlap entre chunks em caracteres")
    return parser.parse_args()


def process_document(pdf_path: Path, json_path: Path, out_dir: Path, chunk_size: int, chunk_overlap: int) -> int:
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    cod_acervo = metadata.get("codAcervo", pdf_path.stem)

    pages = extract_pages(pdf_path)
    text = clean_pages(pages)
    if not text:
        logger.warning("acervo %s -> sem texto extraível, pulando", cod_acervo)
        return 0

    chunks = chunk_text(text, chunk_size, chunk_overlap)
    if not chunks:
        logger.warning("acervo %s -> nenhum chunk gerado, pulando", cod_acervo)
        return 0

    out_path = out_dir / f"{pdf_path.stem}.chunks.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for index, chunk in enumerate(chunks):
            record = {
                "codAcervo": cod_acervo,
                "chunkIndex": index,
                "chunkCount": len(chunks),
                "text": chunk.text,
                "charStart": chunk.char_start,
                "charEnd": chunk.char_end,
                "titulo": metadata.get("titulo"),
                "autor": metadata.get("autor"),
                "tipoObra": metadata.get("tipoObra"),
                "fonteUrl": metadata.get("fonteUrl"),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("acervo %s -> %d chunks gerados", cod_acervo, len(chunks))
    return len(chunks)


def main() -> None:
    args = parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    processados = 0
    pulados = 0
    erros = 0
    total_chunks = 0

    for pdf_path in sorted(in_dir.glob("*.pdf")):
        json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            logger.warning("acervo %s -> metadados ausentes (%s), pulando", pdf_path.stem, json_path.name)
            pulados += 1
            continue

        try:
            n_chunks = process_document(pdf_path, json_path, out_dir, args.chunk_size, args.chunk_overlap)
        except Exception:
            logger.exception("acervo %s -> erro ao processar", pdf_path.stem)
            erros += 1
            continue

        if n_chunks == 0:
            pulados += 1
        else:
            processados += 1
            total_chunks += n_chunks

    logger.info(
        "Resumo: processados=%d chunks_gerados=%d pulados=%d erros=%d",
        processados, total_chunks, pulados, erros,
    )


if __name__ == "__main__":
    main()
