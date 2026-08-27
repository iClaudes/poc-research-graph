"""Wrapper fino em torno do SentenceTransformer: carrega o modelo e gera embeddings em batch."""
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str], batch_size: int) -> list[list[float]]:
        vectors = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return [vector.tolist() for vector in vectors]
