"""Testes de app/services/attachment_tree.py (specs/013, T009/T011).

Usa `encode_texts` real (modelo já cacheado localmente, mesmo do RAG
existente) — sem fake aqui: é a própria montagem/busca da árvore que está
sob teste, não um cliente externo.
"""
from __future__ import annotations

from app.services.attachment_tree import build_tree, search

_MD_THREE_LEVELS = """\
# Manual do Sistema

## Autenticação

O login usa OAuth2 com token de curta duração.

## Faturamento

### Notas fiscais

Notas fiscais são emitidas automaticamente todo dia 5 do mês, em formato PDF.
"""


def test_build_tree_produces_root_sections_and_leaves_matching_chunk_markdown():
    nodes = build_tree(_MD_THREE_LEVELS)

    roots = [n for n in nodes if n.node_type == "root"]
    sections = [n for n in nodes if n.node_type == "section"]
    leaves = [n for n in nodes if n.node_type == "leaf"]

    assert len(roots) == 1
    assert roots[0].heading_path == ""
    assert roots[0].embedding is not None

    section_paths = {s.heading_path for s in sections}
    assert "Manual do Sistema" in section_paths
    assert "Manual do Sistema > Faturamento" in section_paths

    leaf_paths = {leaf.heading_path for leaf in leaves}
    assert "Manual do Sistema > Autenticação" in leaf_paths
    assert "Manual do Sistema > Faturamento > Notas fiscais" in leaf_paths
    assert all(leaf.embedding is not None for leaf in leaves)


def test_build_tree_plain_text_without_heading_yields_root_plus_single_leaf():
    nodes = build_tree("Só um parágrafo solto, sem nenhum heading Markdown.")

    assert len([n for n in nodes if n.node_type == "root"]) == 1
    assert [n for n in nodes if n.node_type == "section"] == []
    leaves = [n for n in nodes if n.node_type == "leaf"]
    assert len(leaves) == 1
    assert leaves[0].heading_path == ""


def test_search_returns_leaf_from_matching_section_not_the_other():
    nodes = build_tree(_MD_THREE_LEVELS)

    results = search(nodes, "como funciona o login e autenticação de usuários", file_name="manual.md")

    assert results, "esperava ao menos uma fonte para pergunta coberta pelo documento"
    assert results[0].heading_path == "Manual do Sistema > Autenticação"
    assert "Faturamento" not in results[0].heading_path


def test_search_without_coverage_returns_empty_never_invents():
    nodes = build_tree(_MD_THREE_LEVELS)

    results = search(nodes, "receita de bolo de cenoura com cobertura de chocolate", file_name="manual.md")

    assert results == []
