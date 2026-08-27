"""Chunking de tamanho fixo (em caracteres) com overlap, quebrando em limites de palavra."""
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    char_start: int
    char_end: int


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if not text:
        return []
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap deve ser menor que chunk_size")

    words = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    if not words:
        return []

    chunks: list[Chunk] = []
    start_idx = 0
    n = len(words)

    while start_idx < n:
        chunk_start_char = words[start_idx][1]
        end_idx = start_idx
        while end_idx < n and words[end_idx][2] - chunk_start_char <= chunk_size:
            end_idx += 1
        if end_idx == start_idx:
            end_idx = start_idx + 1

        chunk_end_char = words[end_idx - 1][2]
        chunks.append(Chunk(
            text=text[chunk_start_char:chunk_end_char],
            char_start=chunk_start_char,
            char_end=chunk_end_char,
        ))

        if end_idx >= n:
            break

        target_start_char = chunk_end_char - chunk_overlap
        next_idx = end_idx - 1
        while next_idx > start_idx and words[next_idx][1] > target_start_char:
            next_idx -= 1
        start_idx = max(next_idx, start_idx + 1)

    return chunks
