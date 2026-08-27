"""Remoção de cabeçalho/rodapé repetido e normalização de espaços."""
import re
from collections import Counter

REPEATED_LINE_THRESHOLD = 0.5


def clean_pages(pages: list[str]) -> str:
    if not pages:
        return ""

    page_lines = [[line.strip() for line in page.splitlines()] for page in pages]

    line_counts = Counter()
    for lines in page_lines:
        for line in set(lines):
            if line:
                line_counts[line] += 1

    num_pages = len(pages)
    boilerplate = {
        line
        for line, count in line_counts.items()
        if count / num_pages > REPEATED_LINE_THRESHOLD
    }

    cleaned_pages = []
    for lines in page_lines:
        kept = [line for line in lines if line and line not in boilerplate]
        cleaned_pages.append("\n".join(kept))

    text = "\n\n".join(page for page in cleaned_pages if page)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
