"""API HTTP (FastAPI) para busca semântica e recomendação sobre o acervo CESAR."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from api.embedder import Embedder
from api.schemas import Document, Recommendation
from api.search import fetch_document_vectors, recommend

DEFAULT_DATABASE_URL = "postgresql://research_graph:research_graph@postgres:5432/research_graph"


def _configure_connection(conn):
    register_vector(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    app.state.pool = ConnectionPool(database_url, configure=_configure_connection, open=True)
    app.state.embedder = Embedder()
    yield
    app.state.pool.close()


app = FastAPI(title="poc-research-graph API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents", response_model=list[Document])
def list_documents(limit: int = 50, offset: int = 0):
    with app.state.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT cod_acervo, titulo, autor, tipo_obra, fonte_url FROM documents ORDER BY cod_acervo LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return cur.fetchall()


@app.get("/documents/{cod_acervo}", response_model=Document)
def get_document(cod_acervo: int):
    with app.state.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT cod_acervo, titulo, autor, tipo_obra, fonte_url FROM documents WHERE cod_acervo = %s",
            (cod_acervo,),
        )
        doc = cur.fetchone()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"acervo {cod_acervo} não encontrado")
    return doc


@app.get("/documents/{cod_acervo}/recommendations", response_model=list[Recommendation])
def get_recommendations(cod_acervo: int, top_n: int = 5):
    with app.state.pool.connection() as conn:
        query_vectors = fetch_document_vectors(conn, cod_acervo)
        if not query_vectors:
            raise HTTPException(status_code=404, detail=f"acervo {cod_acervo} não encontrado")
        return recommend(conn, query_vectors, exclude_cod_acervo=cod_acervo, top_n=top_n)


@app.get("/search", response_model=list[Recommendation])
def search(q: str, top_n: int = 5):
    query_vector = app.state.embedder.encode_one(q)
    with app.state.pool.connection() as conn:
        return recommend(conn, [query_vector], exclude_cod_acervo=None, top_n=top_n)


# Servida por último: interface web (SPA em HTML/JS puro), com fallback para
# index.html em qualquer path não reconhecido — mas como a navegação da SPA é
# via hash (#/...), o servidor nunca recebe esses paths, só sempre "/".
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
