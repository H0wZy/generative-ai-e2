"""
Testes do serviço HTTP do RAG (rag/http/app.py).

Consumido apenas pelo backend, nunca pelo navegador — ver
specs/002-unified-itsm-agile-ui/contracts/rag-search.md.

Sem rede, sem download de modelo: usa banco sqlite real em arquivo
temporário, seguindo o mesmo padrão de rag/tests/test_mcp.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import rag.http.app as app_module
from rag.db import initialize_db
from rag.sync.indexer import sync_directory


@pytest.fixture()
def synced_db_path(tmp_path: Path) -> Path:
    """Banco sqlite real, sincronizado com um doc de exemplo."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "arquitetura.md").write_text(
        "# Arquitetura\n\nO sistema usa FastAPI e PostgreSQL para automação.\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "knowledge.db"
    conn = initialize_db(db_path)
    sync_directory(conn, docs_dir)
    conn.close()
    return db_path


def test_search_empty_query_returns_422(synced_db_path):
    with patch.object(app_module, "_DB_PATH", synced_db_path):
        client = TestClient(app_module.app)
        resp = client.post("/search", json={"query": ""})
    assert resp.status_code == 422


def test_search_out_of_domain_returns_200_total_zero(synced_db_path):
    with patch.object(app_module, "_DB_PATH", synced_db_path):
        client = TestClient(app_module.app)
        resp = client.post("/search", json={"query": "como fazer um bolo de cenoura"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["results"] == []


def test_search_missing_db_returns_503(tmp_path):
    missing_path = tmp_path / "does-not-exist.db"
    with patch.object(app_module, "_DB_PATH", missing_path):
        client = TestClient(app_module.app)
        resp = client.post("/search", json={"query": "arquitetura"})
    assert resp.status_code == 503


def test_search_returns_raw_content_not_wrapped(synced_db_path):
    """Diferença deliberada do MCP: content cru, sem <untrusted_document>."""
    with patch.object(app_module, "_DB_PATH", synced_db_path):
        client = TestClient(app_module.app)
        resp = client.post("/search", json={"query": "FastAPI PostgreSQL", "max_distance": 1.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert "<untrusted_document>" not in body["results"][0]["content"]
    assert body["embedding_model"]


def test_health_ok(synced_db_path):
    with patch.object(app_module, "_DB_PATH", synced_db_path):
        client = TestClient(app_module.app)
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["indexed_chunks"] >= 1


def test_health_missing_db_returns_503(tmp_path):
    missing_path = tmp_path / "does-not-exist.db"
    with patch.object(app_module, "_DB_PATH", missing_path):
        client = TestClient(app_module.app)
        resp = client.get("/health")
    assert resp.status_code == 503
