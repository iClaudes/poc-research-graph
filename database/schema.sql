CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    cod_acervo INTEGER PRIMARY KEY,
    titulo TEXT,
    autor TEXT,
    tipo_obra TEXT,
    fonte_url TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    cod_acervo INTEGER NOT NULL REFERENCES documents(cod_acervo) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    embedding_model TEXT NOT NULL,
    UNIQUE (cod_acervo, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
