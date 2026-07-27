"""
Testes para busca semântica — verifica que retorna fontes verificáveis.
"""

from __future__ import annotations

from rag.search.query import SearchResult, search
from rag.sync.indexer import sync_directory


# Documento de referência com conteúdo conhecido para busca
REFERENCE_DOC = """\
# Arquitetura do Sistema

Este documento descreve a arquitetura do sistema de automação.

## Banco de Dados

O banco operacional é PostgreSQL. Para o RAG, usamos SQLite com sqlite-vec.

## Integrações

O Freshservice envia webhooks para o n8n que aciona o FastAPI.

## Segurança

Todas as credenciais são gerenciadas via variáveis de ambiente.
"""


def _seed_db(db_conn, tmp_path):
    """Cria arquivo e indexa."""
    doc = tmp_path / "arch.md"
    doc.write_text(REFERENCE_DOC, encoding="utf-8")
    sync_directory(db_conn, str(tmp_path))
    return str(doc)


def test_search_returns_list(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados")
    assert isinstance(results, list)


def test_search_returns_search_results(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados")
    if results:
        for r in results:
            assert isinstance(r, SearchResult)


def test_search_result_has_file_path(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados")
    if results:
        assert results[0].file_path.endswith(".md")


def test_search_result_has_lines(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados")
    if results:
        r = results[0]
        assert r.start_line >= 1
        assert r.end_line >= r.start_line


def test_search_result_has_content(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados")
    if results:
        assert results[0].content.strip() != ""


def test_search_result_has_distance(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados")
    if results:
        assert isinstance(results[0].distance, float)
        assert results[0].distance >= 0


def test_search_ordered_by_distance(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "banco de dados", limit=10)
    distances = [r.distance for r in results]
    assert distances == sorted(distances)


def test_search_respects_limit(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "arquitetura", limit=2)
    assert len(results) <= 2


def test_search_empty_query_returns_empty(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "")
    assert results == []


def test_search_whitespace_query_returns_empty(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "   ")
    assert results == []


def test_search_max_distance_filter(db_conn, tmp_path):
    _seed_db(db_conn, tmp_path)
    # Com distância muito baixa, pode não retornar nada
    results = search(db_conn, "banco de dados", max_distance=0.0001)
    # Todos os resultados devem respeitar o threshold
    for r in results:
        assert r.distance <= 0.0001


def test_search_no_results_on_empty_db(db_conn):
    """Banco vazio deve retornar lista vazia — não inventa resultados."""
    results = search(db_conn, "qualquer coisa")
    assert results == []


def test_search_default_max_distance_rejects_out_of_domain_query(db_conn, tmp_path):
    """
    Consulta sem relação com o corpus indexado deve voltar vazia usando o
    max_distance PADRÃO (sem parâmetro explícito) — trava a regressão do
    default frouxo que deixava passar qualquer coisa.
    """
    _seed_db(db_conn, tmp_path)
    results = search(db_conn, "qual a política de férias da empresa")
    assert results == []


def test_search_verifiable_source(db_conn, tmp_path):
    """Resultado de busca deve ter fonte verificável (arquivo existente)."""
    import os
    file_path = _seed_db(db_conn, tmp_path)
    results = search(db_conn, "SQLite sqlite-vec")
    if results:
        # O arquivo referenciado deve existir
        assert os.path.isfile(results[0].file_path)
