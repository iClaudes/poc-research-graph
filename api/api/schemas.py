"""Modelos Pydantic de resposta da API."""
from pydantic import BaseModel


class Document(BaseModel):
    cod_acervo: int
    titulo: str | None = None
    autor: str | None = None
    tipo_obra: str | None = None
    fonte_url: str | None = None


class Recommendation(BaseModel):
    cod_acervo: int
    similarity: float
    match_count: int
    chunk_index: int
    snippet: str
    titulo: str | None = None
    autor: str | None = None
    tipo_obra: str | None = None
    fonte_url: str | None = None
