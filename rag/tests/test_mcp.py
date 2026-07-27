"""
Testes para o servidor MCP — verifica estrutura da resposta da tool.

Testa a função diretamente sem iniciar o servidor HTTP.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from rag.db import init_schema, load_vec_extension, upsert_settings
from rag.search.query import SearchResult


# Cria uma conexão de teste separada para o MCP server
def _make_test_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    load_vec_extension(conn)
    init_schema(conn)
    upsert_settings(conn)
    return conn


def _call_tool(query: str, limit: int = 5, file_glob=None, max_distance=1.0) -> dict[str, Any]:
    """
    Chama a lógica da tool diretamente, mockando a conexão do servidor.
    """
    import rag.mcp.server as mcp_module

    test_conn = _make_test_conn()

    with patch.object(mcp_module, "_conn", test_conn):
        # Importa a função após o patch
        from rag.mcp.server import search_architecture_knowledge
        return search_architecture_knowledge.fn(
            query=query,
            limit=limit,
            file_glob=file_glob,
            max_distance=max_distance,
        )


def test_mcp_tool_returns_dict():
    result = _call_tool("arquitetura")
    assert isinstance(result, dict)


def test_mcp_tool_has_results_key():
    result = _call_tool("arquitetura")
    assert "results" in result


def test_mcp_tool_results_is_list():
    result = _call_tool("arquitetura")
    assert isinstance(result["results"], list)


def test_mcp_tool_has_total_key():
    result = _call_tool("arquitetura")
    assert "total" in result


def test_mcp_tool_total_matches_results():
    result = _call_tool("arquitetura")
    assert result["total"] == len(result["results"])


def test_mcp_tool_empty_query_returns_no_results():
    result = _call_tool("")
    assert result["results"] == []
    assert result["total"] == 0
    assert result["query_received"] is False


def test_mcp_tool_result_structure():
    """Cada resultado deve ter os campos obrigatórios."""
    # Usa banco com dados reais para ter resultado
    from rag.sync.indexer import sync_directory

    test_conn = _make_test_conn()

    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        doc = Path(tmpdir) / "test.md"
        doc.write_text(
            "# Arquitetura\n\nO sistema usa FastAPI e PostgreSQL para automação.\n",
            encoding="utf-8",
        )
        sync_directory(test_conn, tmpdir)

        with patch("rag.mcp.server._conn", test_conn):
            from rag.mcp.server import search_architecture_knowledge
            result = search_architecture_knowledge.fn(query="FastAPI PostgreSQL")

    if result["results"]:
        r = result["results"][0]
        assert "file_path" in r
        assert "heading_path" in r
        assert "start_line" in r
        assert "end_line" in r
        assert "distance" in r
        assert "content" in r


def test_mcp_tool_limit_capped_at_max():
    """Limit acima do máximo deve ser capado."""
    result = _call_tool("teste", limit=9999)
    # Não deve lançar exceção e total <= MAX_LIMIT
    from rag.search.query import MAX_LIMIT
    assert result["total"] <= MAX_LIMIT


def test_mcp_tool_invalid_glob_rejected():
    """Glob com caracteres inválidos não deve causar erro."""
    # Injection attempt — não deve crashar
    result = _call_tool("teste", file_glob="../../etc/passwd; DROP TABLE--")
    assert isinstance(result, dict)
    assert "results" in result


def test_mcp_tool_enforces_path_allowlist():
    """
    Chunk indexado fora do allowlist de caminho nunca deve ser retornado,
    mesmo que seja o resultado mais relevante da busca.
    """
    import rag.mcp.server as mcp_module

    test_conn = _make_test_conn()
    cur = test_conn.execute(
        "INSERT INTO source_files (file_path, content_hash) VALUES (?, ?)",
        ("/etc/passwd", "deadbeef"),
    )
    file_id = cur.lastrowid
    test_conn.execute(
        """
        INSERT INTO document_chunks (file_id, content, heading_path, start_line, end_line, token_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (file_id, "root:x:0:0:root:/root:/bin/bash segredo do sistema", "", 1, 1, 5),
    )
    test_conn.commit()
    from rag.sync.indexer import _index_file  # reuse embedding persistence path
    from rag.embeddings.encoder import persist_embeddings

    chunk_id = test_conn.execute(
        "SELECT id FROM document_chunks WHERE file_id = ?", (file_id,)
    ).fetchone()[0]
    persist_embeddings(test_conn, [chunk_id], ["root:x:0:0:root:/root:/bin/bash segredo do sistema"])

    with patch.object(mcp_module, "_conn", test_conn), \
         patch.object(mcp_module, "_ALLOWED_PREFIXES", ["docs"]):
        from rag.mcp.server import search_architecture_knowledge
        result = search_architecture_knowledge.fn(
            query="segredo do sistema", limit=5, max_distance=2.0
        )

    assert result["results"] == []
