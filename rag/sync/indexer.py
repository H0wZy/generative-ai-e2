"""
Sincronização incremental de arquivos Markdown para o banco RAG.

Lógica:
  - NOVO: arquivo não existe em source_files → indexar.
  - ALTERADO: content_hash diferente → remover chunks/embeddings antigos e reindexar.
  - NÃO ALTERADO: content_hash igual → ignorar.
  - REMOVIDO: arquivo não mais encontrado → marcar status='removed' e remover chunks.

Conteúdo de arquivos é tratado como não confiável (prompt injection possível).
Logs NÃO incluem conteúdo de arquivos.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from rag.chunking.markdown import Chunk, chunk_markdown, iter_markdown_files
from rag.db import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL, SQLITE_VEC_AVAILABLE, to_repo_relative
from rag.embeddings.encoder import persist_embeddings

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Resultado de uma rodada de sincronização."""
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    errors: list[str] = field(default_factory=list)


def compute_hash(content: str) -> str:
    """SHA-256 do conteúdo do arquivo (hex)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _remove_file_data(conn: sqlite3.Connection, file_id: int) -> None:
    """Remove chunks e embeddings de um arquivo pelo seu ID."""
    chunk_ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM document_chunks WHERE file_id = ?", (file_id,)
        ).fetchall()
    ]
    if chunk_ids:
        placeholders = ",".join("?" * len(chunk_ids))
        # Remove da tabela de embeddings (sqlite-vec ou fallback)
        if SQLITE_VEC_AVAILABLE:
            try:
                conn.execute(f"DELETE FROM embeddings WHERE chunk_id IN ({placeholders})", chunk_ids)
            except sqlite3.OperationalError:
                pass
        conn.execute(f"DELETE FROM embeddings_fallback WHERE chunk_id IN ({placeholders})", chunk_ids)
        conn.execute(f"DELETE FROM embedding_meta WHERE chunk_id IN ({placeholders})", chunk_ids)
    conn.execute("DELETE FROM document_chunks WHERE file_id = ?", (file_id,))


def _index_file(
    conn: sqlite3.Connection,
    file_path: str,
    content: str,
    content_hash: str,
    file_id: int | None = None,
) -> int:
    """
    Insere ou atualiza chunks e embeddings para um arquivo.

    Returns:
        Novo file_id.
    """
    if file_id is not None:
        # Arquivo alterado: remove dados antigos
        _remove_file_data(conn, file_id)
        conn.execute(
            "UPDATE source_files SET content_hash=?, indexed_at=datetime('now'), status='active' WHERE id=?",
            (content_hash, file_id),
        )
        new_file_id = file_id
    else:
        try:
            cursor = conn.execute(
                "INSERT INTO source_files (file_path, content_hash) VALUES (?, ?)",
                (file_path, content_hash),
            )
            new_file_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Outro processo de sync já inseriu este file_path entre nosso
            # scan e este INSERT (execução concorrente). Trata como update.
            row = conn.execute("SELECT id FROM source_files WHERE file_path = ?", (file_path,)).fetchone()
            new_file_id = row["id"]
            _remove_file_data(conn, new_file_id)
            conn.execute(
                "UPDATE source_files SET content_hash=?, indexed_at=datetime('now'), status='active' WHERE id=?",
                (content_hash, new_file_id),
            )

    chunks: list[Chunk] = chunk_markdown(
        content,
        max_tokens=CHUNK_SIZE,
        overlap_tokens=CHUNK_OVERLAP,
    )

    chunk_ids: list[int] = []
    chunk_texts: list[str] = []

    for chunk in chunks:
        cur = conn.execute(
            """
            INSERT INTO document_chunks
                (file_id, content, heading_path, start_line, end_line, token_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_file_id,
                chunk.content,
                chunk.heading_path,
                chunk.start_line,
                chunk.end_line,
                chunk.token_count,
            ),
        )
        chunk_ids.append(cur.lastrowid)
        chunk_texts.append(chunk.content)

    # Gera e persiste embeddings para este arquivo
    persist_embeddings(conn, chunk_ids, chunk_texts, model_name=EMBEDDING_MODEL)

    return new_file_id


def sync_directory(
    conn: sqlite3.Connection,
    root: str,
    allowed_prefixes: list[str] | None = None,
) -> SyncResult:
    """
    Sincroniza todos os arquivos .md abaixo de root com o banco.

    Args:
        conn: Conexão SQLite.
        root: Diretório raiz da varredura.
        allowed_prefixes: Se fornecido, apenas paths com esses prefixos são indexados.

    Returns:
        SyncResult com contagens por categoria.
    """
    result = SyncResult()

    # Estado atual no banco (file_path → (id, hash, status))
    db_files: dict[str, tuple[int, str, str]] = {
        row["file_path"]: (row["id"], row["content_hash"], row["status"])
        for row in conn.execute(
            "SELECT id, file_path, content_hash, status FROM source_files"
        ).fetchall()
    }

    found_paths: set[str] = set()

    for abs_path in iter_markdown_files(root, allowed_prefixes=allowed_prefixes):
        # Lê pelo caminho absoluto; grava/compara pelo relativo à raiz do
        # repo — evita vazar o caminho absoluto (e a home do usuário) nas
        # respostas do MCP.
        file_path = to_repo_relative(abs_path)
        found_paths.add(file_path)
        try:
            raw = Path(abs_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Erro ao ler arquivo [path omitido]: %s", type(exc).__name__)
            result.errors.append(file_path)
            continue

        new_hash = compute_hash(raw)

        if file_path not in db_files:
            # NOVO
            with conn:
                _index_file(conn, file_path, raw, new_hash)
            logger.info("Arquivo novo indexado.")
            result.added += 1

        else:
            stored_id, stored_hash, status = db_files[file_path]
            if stored_hash == new_hash and status == "active":
                # NÃO ALTERADO
                result.unchanged += 1
            else:
                # ALTERADO (ou estava marcado como removed mas voltou)
                with conn:
                    _index_file(conn, file_path, raw, new_hash, file_id=stored_id)
                logger.info("Arquivo reindexado (alterado).")
                result.updated += 1

    # Marca como removidos os arquivos que sumiram do disco
    for file_path, (file_id, _, status) in db_files.items():
        if file_path not in found_paths and status == "active":
            with conn:
                _remove_file_data(conn, file_id)
                conn.execute(
                    "UPDATE source_files SET status='removed', indexed_at=datetime('now') WHERE id=?",
                    (file_id,),
                )
            logger.info("Arquivo marcado como removido.")
            result.removed += 1

    logger.info(
        "Sync concluído — adicionados=%d, atualizados=%d, sem_mudança=%d, removidos=%d, erros=%d",
        result.added, result.updated, result.unchanged, result.removed, len(result.errors),
    )
    return result
