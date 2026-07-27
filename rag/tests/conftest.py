"""
Fixtures compartilhadas para os testes do RAG.
Usa banco em memória para isolamento e velocidade.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

# `python -m pytest` (cwd=rag/) puts '' on sys.path[0], which makes the
# local `rag/mcp/` directory shadow the real `mcp` SDK package (fastmcp
# dependency) since both resolve to top-level name "mcp". Drop the cwd
# entry so the real site-packages `mcp` wins.
sys.path[:] = [p for p in sys.path if p not in ("", str(Path(__file__).resolve().parent.parent))]

import pytest

from rag.db import init_schema, load_vec_extension, upsert_settings


@pytest.fixture()
def db_conn():
    """
    Conexão SQLite em memória com sqlite-vec e schema inicializados.
    Isolada por teste — descartada ao final.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    load_vec_extension(conn)
    init_schema(conn)
    upsert_settings(conn)
    yield conn
    conn.close()


@pytest.fixture()
def tmp_md_dir(tmp_path: Path):
    """Diretório temporário com alguns arquivos Markdown para testes de sync."""
    (tmp_path / "doc_a.md").write_text(
        "# Título A\n\nConteúdo do documento A.\n\n## Seção 1\n\nTexto da seção 1.\n",
        encoding="utf-8",
    )
    (tmp_path / "doc_b.md").write_text(
        "# Título B\n\nConteúdo do documento B.\n",
        encoding="utf-8",
    )
    return tmp_path
