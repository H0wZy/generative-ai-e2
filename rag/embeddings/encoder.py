"""
Geração e persistência de embeddings com sentence-transformers.

Modelo padrão: all-MiniLM-L6-v2 (384 dimensões, ~22M params, CPU-friendly).
O modelo é carregado uma única vez (singleton por processo).

Persistência:
  - Se sqlite-vec disponível: tabela virtual `embeddings` via vec0.
  - Fallback: tabela `embeddings_fallback` com BLOB; busca cosine em Python puro.
"""

from __future__ import annotations

import logging
import math
import sqlite3
import struct
from typing import TYPE_CHECKING

from sentence_transformers import SentenceTransformer

from rag.db import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, SQLITE_VEC_AVAILABLE

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_model_cache: dict[str, SentenceTransformer] = {}


def get_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    """
    Retorna o modelo carregado (singleton por nome de modelo).
    O download automático ocorre apenas na primeira chamada.
    """
    if model_name not in _model_cache:
        logger.info("Carregando modelo de embedding: %s", model_name)
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def encode_texts(
    texts: list[str],
    model_name: str = EMBEDDING_MODEL,
    batch_size: int = 32,
) -> list[list[float]]:
    """
    Gera vetores de embedding para uma lista de textos.

    Args:
        texts: Textos a serem codificados.
        model_name: Nome do modelo sentence-transformers.
        batch_size: Tamanho do lote para inferência.

    Returns:
        Lista de vetores (lista de floats), um por texto.
    """
    if not texts:
        return []
    model = get_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # cosine similarity = dot product
    )
    return [vec.tolist() for vec in embeddings]


def serialize_embedding(vector: list[float]) -> bytes:
    """Serializa um vetor de floats para bytes (formato sqlite-vec / BLOB)."""
    return struct.pack(f"{len(vector)}f", *vector)


def deserialize_embedding(data: bytes) -> list[float]:
    """Deserializa bytes para lista de floats."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


def cosine_distance(a: list[float], b: list[float]) -> float:
    """
    Distância cosine entre dois vetores normalizados.
    Como os vetores são L2-normalizados, distância = 1 - dot_product.
    Retorna valor em [0, 2].
    """
    dot = sum(x * y for x, y in zip(a, b))
    # Clamping para evitar erros numéricos fora de [-1, 1]
    dot = max(-1.0, min(1.0, dot))
    return 1.0 - dot


def persist_embeddings(
    conn: sqlite3.Connection,
    chunk_ids: list[int],
    texts: list[str],
    model_name: str = EMBEDDING_MODEL,
) -> None:
    """
    Gera e persiste embeddings para os chunks fornecidos.

    Pula chunks que já possuem embedding (idempotente).
    Usa sqlite-vec se disponível; caso contrário, BLOB fallback.

    Args:
        conn: Conexão SQLite.
        chunk_ids: IDs dos chunks em document_chunks.
        texts: Textos correspondentes a cada chunk_id.
        model_name: Modelo a usar para geração.
    """
    if not chunk_ids:
        return

    # Verifica quais já existem para não reprocessar
    existing = {
        row[0]
        for row in conn.execute(
            f"SELECT chunk_id FROM embedding_meta WHERE chunk_id IN ({','.join('?' * len(chunk_ids))})",
            chunk_ids,
        ).fetchall()
    }

    to_process = [
        (cid, txt)
        for cid, txt in zip(chunk_ids, texts)
        if cid not in existing
    ]

    if not to_process:
        logger.debug("Todos os embeddings já existem — nenhuma ação necessária.")
        return

    ids_to_embed = [cid for cid, _ in to_process]
    texts_to_embed = [txt for _, txt in to_process]

    logger.info("Gerando %d embeddings com modelo %s", len(texts_to_embed), model_name)
    vectors = encode_texts(texts_to_embed, model_name=model_name)

    embedding_version = "1"

    with conn:
        for chunk_id, vector in zip(ids_to_embed, vectors):
            serialized = serialize_embedding(vector)

            if SQLITE_VEC_AVAILABLE:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings(chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, serialized),
                )
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings_fallback(chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, serialized),
                )

            conn.execute(
                """
                INSERT INTO embedding_meta (chunk_id, embedding_model, embedding_version)
                VALUES (?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    embedding_model   = excluded.embedding_model,
                    embedding_version = excluded.embedding_version,
                    embedded_at       = datetime('now')
                """,
                (chunk_id, model_name, embedding_version),
            )

    logger.info("Embeddings persistidos: %d chunks.", len(ids_to_embed))
