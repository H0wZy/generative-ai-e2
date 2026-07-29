"""
Serviço HTTP de busca do RAG.

Envolve `rag.search.query.search()` sem alterá-lo — o limiar calibrado e o
fallback de cosine continuam onde estão. Consumido apenas pelo backend, nunca
pelo navegador; não é publicado no compose.

Diferença deliberada em relação a `rag/mcp/server.py`: aqui o `content` vai
cru. Quem envolve em `<untrusted_document>` é o backend, ao montar o prompt —
a marcação é aplicada no ponto de uso, não no transporte.

Para iniciar:
    uvicorn rag.http.app:app --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.db import DEFAULT_DB_PATH, EMBEDDING_MODEL, load_vec_extension
from rag.search.query import (
    DEFAULT_LIMIT,
    DEFAULT_MAX_DISTANCE,
    MAX_LIMIT,
    SearchResult,
    search,
)

_DB_PATH = Path(os.environ.get("RAG_DB_PATH", str(DEFAULT_DB_PATH)))

app = FastAPI(title="RAG — busca semântica", version="0.1.0", docs_url=None, redoc_url=None)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    max_distance: float = Field(default=DEFAULT_MAX_DISTANCE, gt=0)
    file_glob: str | None = None


class SearchHit(BaseModel):
    file_path: str
    heading_path: str
    start_line: int
    end_line: int
    distance: float
    content: str


class SearchResponse(BaseModel):
    results: list[SearchHit]
    total: int
    embedding_model: str


def _open_readonly() -> sqlite3.Connection:
    """Abre o banco em modo somente leitura no nível do SO.

    A conexão é por requisição, não global: o caminho do banco é resolvido a
    cada chamada e o serviço nunca escreve.
    """
    if not _DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Base de conhecimento indisponível. Rode `make rag-sync`.",
        )
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    load_vec_extension(conn)
    return conn


def _to_hit(result: SearchResult) -> SearchHit:
    return SearchHit(
        file_path=result.file_path,
        heading_path=result.heading_path,
        start_line=result.start_line,
        end_line=result.end_line,
        distance=result.distance,
        content=result.content,
    )


@app.post("/search", response_model=SearchResponse)
def post_search(payload: SearchRequest) -> SearchResponse:
    conn = _open_readonly()
    try:
        results = search(
            conn=conn,
            query=payload.query,
            limit=payload.limit,
            file_glob=payload.file_glob,
            max_distance=payload.max_distance,
        )
    finally:
        conn.close()

    # Lista vazia é 200: é o caminho que leva a `no_grounding` no assistente.
    return SearchResponse(
        results=[_to_hit(r) for r in results],
        total=len(results),
        embedding_model=EMBEDDING_MODEL,
    )


@app.get("/health")
def health() -> dict[str, object]:
    conn = _open_readonly()
    try:
        indexed_chunks = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
    finally:
        conn.close()
    return {"status": "ok", "indexed_chunks": indexed_chunks}
