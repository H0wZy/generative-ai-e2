"""Testes para sincronização incremental de arquivos Markdown."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.sync.indexer import compute_hash, sync_directory


def test_sync_new_file(db_conn, tmp_md_dir):
    """Novo arquivo deve ser indexado com status 'added'."""
    result = sync_directory(db_conn, str(tmp_md_dir))
    assert result.added == 2
    assert result.unchanged == 0
    assert result.updated == 0
    assert result.removed == 0


def test_sync_unchanged_file(db_conn, tmp_md_dir):
    """Arquivo sem mudança na segunda sync não deve ser reindexado."""
    sync_directory(db_conn, str(tmp_md_dir))
    result2 = sync_directory(db_conn, str(tmp_md_dir))
    assert result2.unchanged == 2
    assert result2.added == 0
    assert result2.updated == 0


def test_sync_updated_file(db_conn, tmp_md_dir):
    """Arquivo alterado deve ser reindexado."""
    sync_directory(db_conn, str(tmp_md_dir))

    # Modifica um arquivo
    doc_a = tmp_md_dir / "doc_a.md"
    doc_a.write_text(
        "# Título A Modificado\n\nNovo conteúdo do documento A modificado.\n",
        encoding="utf-8",
    )

    result2 = sync_directory(db_conn, str(tmp_md_dir))
    assert result2.updated == 1
    assert result2.unchanged == 1
    assert result2.added == 0


def test_sync_removed_file(db_conn, tmp_md_dir):
    """Arquivo removido do disco deve ser marcado como 'removed' no banco."""
    sync_directory(db_conn, str(tmp_md_dir))

    # Remove um arquivo
    (tmp_md_dir / "doc_b.md").unlink()

    result2 = sync_directory(db_conn, str(tmp_md_dir))
    assert result2.removed == 1
    assert result2.unchanged == 1

    # Verifica status no banco
    row = db_conn.execute(
        "SELECT status FROM source_files WHERE file_path LIKE '%doc_b.md'"
    ).fetchone()
    assert row is not None
    assert row["status"] == "removed"


def test_sync_removed_file_no_orphan_chunks(db_conn, tmp_md_dir):
    """Chunks de arquivo removido não devem permanecer no banco."""
    sync_directory(db_conn, str(tmp_md_dir))
    (tmp_md_dir / "doc_b.md").unlink()
    sync_directory(db_conn, str(tmp_md_dir))

    # Busca chunks de arquivo removido — deve estar vazio
    file_id_row = db_conn.execute(
        "SELECT id FROM source_files WHERE file_path LIKE '%doc_b.md'"
    ).fetchone()
    assert file_id_row is not None
    chunks = db_conn.execute(
        "SELECT id FROM document_chunks WHERE file_id = ?",
        (file_id_row["id"],),
    ).fetchall()
    assert len(chunks) == 0


def test_sync_chunks_created(db_conn, tmp_md_dir):
    """Após sync, deve haver chunks no banco."""
    sync_directory(db_conn, str(tmp_md_dir))
    count = db_conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
    assert count > 0


def test_sync_embeddings_created(db_conn, tmp_md_dir):
    """Após sync, deve haver embeddings para os chunks."""
    sync_directory(db_conn, str(tmp_md_dir))
    count = db_conn.execute("SELECT COUNT(*) FROM embedding_meta").fetchone()[0]
    assert count > 0


def test_compute_hash_deterministic():
    """Hash do mesmo conteúdo deve ser idêntico."""
    h1 = compute_hash("hello world")
    h2 = compute_hash("hello world")
    assert h1 == h2


def test_compute_hash_differs():
    """Hash de conteúdos diferentes deve diferir."""
    h1 = compute_hash("conteúdo A")
    h2 = compute_hash("conteúdo B")
    assert h1 != h2


def test_sync_idempotent_multiple_runs(db_conn, tmp_md_dir):
    """Múltiplas sync sem alteração devem ser idempotentes."""
    sync_directory(db_conn, str(tmp_md_dir))
    count1 = db_conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
    sync_directory(db_conn, str(tmp_md_dir))
    count2 = db_conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
    assert count1 == count2
