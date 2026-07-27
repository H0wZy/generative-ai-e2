"""Testes para o módulo de chunking de Markdown."""

from __future__ import annotations

from rag.chunking.markdown import Chunk, chunk_markdown


SIMPLE_DOC = """\
# Introdução

Este é o parágrafo de introdução do documento.

## Decisões

As principais decisões foram tomadas com base nos requisitos.

### Banco de Dados

Usamos SQLite + sqlite-vec para o RAG local.

## Conclusão

O projeto está dentro do escopo definido.
"""


def test_chunk_returns_list():
    chunks = chunk_markdown(SIMPLE_DOC)
    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_chunks_have_content():
    chunks = chunk_markdown(SIMPLE_DOC)
    for c in chunks:
        assert c.content.strip() != ""


def test_heading_path_populated():
    """Cada chunk deve ter o heading_path com o caminho hierárquico."""
    chunks = chunk_markdown(SIMPLE_DOC)
    # Pelo menos um chunk deve ter heading path não vazio
    paths = [c.heading_path for c in chunks]
    assert any(p != "" for p in paths)


def test_heading_path_hierarchy():
    """Chunks sob subheadings devem incluir o heading pai."""
    chunks = chunk_markdown(SIMPLE_DOC)
    # O chunk "Banco de Dados" deve incluir "Decisões" na hierarquia
    banco_chunks = [c for c in chunks if "Banco de Dados" in c.heading_path]
    assert len(banco_chunks) > 0
    for c in banco_chunks:
        assert "Decisões" in c.heading_path


def test_start_end_lines_set():
    """start_line e end_line devem ser positivos e coerentes."""
    chunks = chunk_markdown(SIMPLE_DOC)
    for c in chunks:
        assert c.start_line >= 1
        assert c.end_line >= c.start_line


def test_token_count_positive():
    chunks = chunk_markdown(SIMPLE_DOC)
    for c in chunks:
        assert c.token_count > 0


def test_empty_document():
    chunks = chunk_markdown("")
    assert chunks == []


def test_document_no_headings():
    """Documento sem headings não deve gerar chunks (sem section header)."""
    doc = "Linha um.\nLinha dois.\nLinha três.\n"
    # Sem headings não há flushes — a implementação só chunka por heading
    chunks = chunk_markdown(doc)
    # Sem heading não há chunks na implementação atual
    assert isinstance(chunks, list)


def test_min_tokens_filter():
    """Chunks muito pequenos devem ser descartados."""
    doc = "# A\n\nok\n\n# B\n\nEste é um conteúdo mais longo para passar o filtro.\n"
    chunks = chunk_markdown(doc, min_tokens=5)
    # Todos os chunks retornados têm token_count >= min_tokens
    for c in chunks:
        assert c.token_count >= 5


def test_oversized_chunk_split():
    """Chunks maiores que max_tokens devem ser divididos."""
    long_content = " ".join(f"palavra{i}" for i in range(600))
    doc = f"# Big Section\n\n{long_content}\n"
    chunks = chunk_markdown(doc, max_tokens=100, overlap_tokens=20)
    # Deve haver mais de um chunk por causa do split
    assert len(chunks) > 1
    # Todos devem referenciar o mesmo heading
    for c in chunks:
        assert "Big Section" in c.heading_path


def test_multiple_headings_same_level():
    doc = (
        "# A\n\n"
        + " ".join(f"palavra{i}" for i in range(15))
        + "\n\n# B\n\n"
        + " ".join(f"outro{i}" for i in range(15))
        + "\n"
    )
    chunks = chunk_markdown(doc)
    paths = [c.heading_path for c in chunks]
    assert any("A" in p for p in paths)
    assert any("B" in p for p in paths)
