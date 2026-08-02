"""Monta e busca a árvore hierárquica de um anexo (TreeRAG, specs/013).

Reaproveita `chunk_markdown` (folhas) e o encoder de embeddings do RAG
existente — nada de chunker/modelo novo (research.md R2). `.txt` sem heading
produz só raiz + 1 folha, o próprio `chunk_markdown` já cobre isso.

Sem índice vetorial dedicado: embeddings comparados por cosine em Python
puro, mesmo fallback que `rag/search/query.py` já usa e testa.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from rag.chunking.markdown import chunk_markdown
from rag.embeddings.encoder import (
    cosine_distance,
    deserialize_embedding,
    encode_texts,
    serialize_embedding,
)

from app.domain.assistant import AttachmentRetrievedSource

# Conteúdo de seção/raiz é só material de embedding, nunca citado — truncar
# corta custo de codificação sem perder o propósito (research.md R2).
_SECTION_CONTENT_MAX_CHARS = 2000

# Mesmo limiar calibrado usado pela busca RAG existente (rag_search.py).
DEFAULT_MAX_DISTANCE = 0.50
_SECTION_LIMIT = 3
_LEAF_LIMIT = 5


@dataclass
class AttachmentNode:
    id: uuid.UUID
    parent_id: uuid.UUID | None
    node_type: Literal["root", "section", "leaf"]
    level: int
    heading_path: str
    content: str
    embedding: bytes | None
    start_line: int | None
    end_line: int | None


def _truncate(text: str) -> str:
    return text[:_SECTION_CONTENT_MAX_CHARS]


def build_tree(text: str) -> list[AttachmentNode]:
    """Raiz sintética + seções (agrupadas por prefixo de heading_path) + folhas
    (1:1 com `chunk_markdown`) — research.md R2.
    """
    chunks = chunk_markdown(text)

    root_id = uuid.uuid4()
    leaves: list[AttachmentNode] = []
    section_children: dict[str, list[str]] = {}

    for chunk in chunks:
        segments = [s.strip() for s in chunk.heading_path.split(">")] if chunk.heading_path else []
        segments = [s for s in segments if s]
        for i in range(1, len(segments)):
            prefix = " > ".join(segments[:i])
            section_children.setdefault(prefix, []).append(chunk.content)
        leaves.append(
            AttachmentNode(
                id=uuid.uuid4(),
                parent_id=None,
                node_type="leaf",
                level=len(segments),
                heading_path=chunk.heading_path,
                content=chunk.content,
                embedding=None,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
        )

    sections = [
        AttachmentNode(
            id=uuid.uuid4(),
            parent_id=None,
            node_type="section",
            level=len(path.split(" > ")),
            heading_path=path,
            content=_truncate(" ".join(children)),
            embedding=None,
            start_line=None,
            end_line=None,
        )
        for path, children in sorted(section_children.items())
    ]

    root = AttachmentNode(
        id=root_id,
        parent_id=None,
        node_type="root",
        level=0,
        heading_path="",
        content=_truncate(" ".join(leaf.content for leaf in leaves)),
        embedding=None,
        start_line=None,
        end_line=None,
    )

    # Parentesco por prefixo mais longo já registrado — usado pelo cascade no
    # repositório, não pela busca (que compara por heading_path direto).
    by_path: dict[str, uuid.UUID] = {"": root.id}
    for section in sections:
        segments = section.heading_path.split(" > ")
        parent_path = " > ".join(segments[:-1])
        section.parent_id = by_path.get(parent_path, root.id)
        by_path[section.heading_path] = section.id
    for leaf in leaves:
        segments = [s for s in (leaf.heading_path.split(" > ") if leaf.heading_path else [])]
        parent_path = " > ".join(segments[:-1])
        leaf.parent_id = by_path.get(parent_path, root.id)

    nodes = [root, *sections, *leaves]
    contents = [node.content for node in nodes]
    vectors = encode_texts(contents)
    for node, vector in zip(nodes, vectors):
        node.embedding = serialize_embedding(vector)

    return nodes


def search(
    nodes: list[AttachmentNode],
    query: str,
    *,
    file_name: str,
    max_distance: float = DEFAULT_MAX_DISTANCE,
) -> list[AttachmentRetrievedSource]:
    """Busca bidirecional (research.md R3): raiz->folha restringe a seção
    candidata, folha->raiz cita o trecho exato dentro dela. Sem evidência
    acima do limiar, lista vazia — nunca inventa (FR-007).
    """
    leaves = [n for n in nodes if n.node_type == "leaf"]
    sections = [n for n in nodes if n.node_type == "section"]
    if not leaves:
        return []

    query_vector = encode_texts([query])[0]

    if sections:
        scored_sections = sorted(
            sections,
            key=lambda s: cosine_distance(query_vector, deserialize_embedding(s.embedding)),
        )
        candidate_paths = {s.heading_path for s in scored_sections[:_SECTION_LIMIT]}
        candidate_leaves = [
            leaf
            for leaf in leaves
            if leaf.heading_path in candidate_paths
            or any(leaf.heading_path.startswith(p + " > ") for p in candidate_paths)
        ]
    else:
        candidate_leaves = leaves

    scored_leaves = sorted(
        (
            (leaf, cosine_distance(query_vector, deserialize_embedding(leaf.embedding)))
            for leaf in candidate_leaves
        ),
        key=lambda pair: pair[1],
    )

    return [
        AttachmentRetrievedSource(
            file_path=file_name,
            heading_path=leaf.heading_path or file_name,
            start_line=leaf.start_line or 1,
            end_line=leaf.end_line or 1,
            distance=distance,
            content=leaf.content,
        )
        for leaf, distance in scored_leaves
        if distance <= max_distance
    ][:_LEAF_LIMIT]
