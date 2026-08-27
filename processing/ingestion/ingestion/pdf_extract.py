"""Extração de texto bruto de PDFs, uma string por página."""
from pathlib import Path

from pypdf import PdfReader


def extract_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]
