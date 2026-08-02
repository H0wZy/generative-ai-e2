"""
Busca semântica no banco RAG.

Modos:
  - sqlite-vec disponível: KNN via tabela virtual vec0.
  - Fallback: leitura de todos os embeddings BLOB + cosine similarity Python puro.

Retorna fontes verificáveis (arquivo, linhas, score, conteúdo).
Nunca inventa resultados — se não há evidência, retorna lista vazia.

Conteúdo retornado é tratado como não confiável pelo consumidor.
"""

from __future__ import annotations

import fnmatch
import logging
import sqlite3
from dataclasses import dataclass

from rag.db import SQLITE_VEC_AVAILABLE
from rag.embeddings.encoder import (
    EMBEDDING_MODEL,
    cosine_distance,
    deserialize_embedding,
    encode_texts,
    serialize_embedding,
)

logger = logging.getLogger(__name__)

MAX_LIMIT = 20           # teto absoluto de resultados por chamada
DEFAULT_LIMIT = 5
# Distância cosine máxima aceita (0=idêntico, 2=oposto). Medido no corpus
# atual (docs/**/*.md, all-MiniLM-L6-v2): a menor distância obtida por uma
# pergunta genuinamente fora de domínio é 0.5019 ("como fazer um bolo de
# cenoura"). 0.45 foi testado e cortou hits legítimos do golden set que
# caem em 0.46-0.54 (recall@5 caiu de 0.92 para 0.50) — não existe um
# limiar único que preserve todo o recall e ainda bloqueie as consultas
# fora de domínio, porque a distância de alguns hits reais (até 0.535)
# excede a do pior caso fora de domínio (0.5019). 0.50 é o maior valor
# redondo abaixo desse piso: bloqueia as 3 perguntas fora de domínio
# testadas e recupera recall@5 para 0.75. Se o corpus mudar, remeça.
DEFAULT_MAX_DISTANCE = 0.50


@dataclass
class SearchResult:
    """Um chunk recuperado com metadados de proveniência e score."""
    file_path: str
    heading_path: str
    start_line: int
    end_line: int
    distance: float        # menor = mais similar
    content: str           # trecho recuperado — tratar como não confiável


def _search_vec(
    conn: sqlite3.Connection,
    query_vec_bytes: bytes,
    prefetch: int,
) -> list[sqlite3.Row]:
    """Busca KNN via sqlite-vec (quando disponível)."""
    return conn.execute(
        """
        SELECT
            e.chunk_id,
            e.distance,
            dc.content,
            dc.heading_path,
            dc.start_line,
            dc.end_line,
            sf.file_path
        FROM embeddings e
        JOIN document_chunks dc ON dc.id = e.chunk_id
        JOIN source_files sf    ON sf.id = dc.file_id
        WHERE sf.status = 'active'
          AND e.embedding MATCH ?
          AND k = ?
        ORDER BY e.distance
        """,
        (query_vec_bytes, prefetch),
    ).fetchall()


def _has_vec_table(conn: sqlite3.Connection) -> bool:
    """O banco em uso tem a tabela virtual `embeddings` (vec0)?

    `SQLITE_VEC_AVAILABLE` diz se a extensão carrega *neste* processo — não
    diz se o `.db` conectado foi sincronizado com ela disponível. Um banco
    sincronizado sem sqlite-vec só tem `embeddings_fallback`; consultar
    `embeddings` nesse caso lançaria `OperationalError`, capturado como "sem
    resultado" (research.md/db.py) — silenciosamente incorreto.
    """
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embeddings'"
    ).fetchone()
    return row is not None


def _search_fallback(
    conn: sqlite3.Connection,
    query_vector: list[float],
    prefetch: int,
) -> list[tuple[int, float, str, str, int, int, str]]:
    """
    Busca cosine em Python puro sobre tabela embeddings_fallback.
    Retorna lista de tuplas (chunk_id, distance, content, heading_path,
    start_line, end_line, file_path) ordenada por distância.
    """
    rows = conn.execute(
        """
        SELECT
            ef.chunk_id,
            ef.embedding,
            dc.content,
            dc.heading_path,
            dc.start_line,
            dc.end_line,
            sf.file_path
        FROM embeddings_fallback ef
        JOIN document_chunks dc ON dc.id = ef.chunk_id
        JOIN source_files sf    ON sf.id = dc.file_id
        WHERE sf.status = 'active'
        """
    ).fetchall()

    scored: list[tuple[float, tuple]] = []
    for row in rows:
        stored_vec = deserialize_embedding(bytes(row[1]))
        dist = cosine_distance(query_vector, stored_vec)
        scored.append((dist, (row[0], dist, row[2], row[3], row[4], row[5], row[6])))

    scored.sort(key=lambda x: x[0])
    return [item[1] for item in scored[:prefetch]]


def search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = DEFAULT_LIMIT,
    file_glob: str | None = None,
    max_distance: float = DEFAULT_MAX_DISTANCE,
    model_name: str = EMBEDDING_MODEL,
) -> list[SearchResult]:
    """
    Busca semântica por similaridade cosine.

    Args:
        conn: Conexão SQLite.
        query: Texto da consulta (não confiável — sanitizado internamente).
        limit: Número máximo de resultados (capado em MAX_LIMIT).
        file_glob: Padrão glob para filtrar por caminho do arquivo.
        max_distance: Limiar de distância — resultados acima são descartados.
        model_name: Modelo de embedding para codificar a query.

    Returns:
        Lista de SearchResult ordenada por distância crescente.
        Lista vazia se não há evidência suficiente.
    """
    if not query or not query.strip():
        return []

    # Sanitização básica: limitar tamanho
    query_clean = query.strip()[:2000]

    effective_limit = min(max(1, limit), MAX_LIMIT)

    # Gera embedding da query
    vectors = encode_texts([query_clean], model_name=model_name)
    if not vectors:
        return []

    query_vector = vectors[0]
    query_vec_bytes = serialize_embedding(query_vector)

    # Busca os N mais próximos
    prefetch = effective_limit * 4

    try:
        if SQLITE_VEC_AVAILABLE and _has_vec_table(conn):
            raw_rows = _search_vec(conn, query_vec_bytes, prefetch)
            # Converter Row objects para tuplas uniformes
            rows = [
                (row["chunk_id"], row["distance"], row["content"],
                 row["heading_path"], row["start_line"], row["end_line"],
                 row["file_path"])
                for row in raw_rows
            ]
        else:
            rows = _search_fallback(conn, query_vector, prefetch)

    except sqlite3.OperationalError as exc:
        logger.error("Busca falhou por erro do SQLite (%s) — resultado vazio NÃO significa 'sem evidência'", type(exc).__name__)
        return []

    results: list[SearchResult] = []

    for row in rows:
        chunk_id, distance, content, heading_path, start_line, end_line, file_path = row

        if distance > max_distance:
            continue

        if file_glob and not fnmatch.fnmatch(file_path, file_glob):
            continue

        results.append(
            SearchResult(
                file_path=file_path,
                heading_path=heading_path,
                start_line=start_line,
                end_line=end_line,
                distance=round(distance, 6),
                content=content,
            )
        )

        if len(results) >= effective_limit:
            break

    logger.debug(
        "Busca retornou %d resultado(s) de %d candidatos (limit=%d, max_distance=%.2f, vec=%s)",
        len(results), len(rows), effective_limit, max_distance, SQLITE_VEC_AVAILABLE,
    )

    return results
