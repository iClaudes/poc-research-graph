"""Wrapper fino em torno do SentenceTransformer — mesmo modelo usado no embedding/.

Precisa ser o MESMO modelo do embedding/, senão os vetores gerados aqui não
são comparáveis com os já armazenados no banco.
"""
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode_one(self, text: str):
        """Retorna um numpy array — mesmo tipo que fetch_document_vectors devolve
        do banco (via register_vector), para o adaptador vector do psycopg funcionar."""
        return self.model.encode([text], show_progress_bar=False)[0]
