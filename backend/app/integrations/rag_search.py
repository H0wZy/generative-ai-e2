"""Cliente do serviço HTTP de busca do RAG.

O serviço devolve `content` cru; quem envolve em `<untrusted_document>` é o
serviço do assistente, ao montar o prompt (contracts/rag-search.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.domain.assistant import RetrievedSource

# Limiar calibrado em rag/search/query.py — não é chute (research.md R5).
DEFAULT_MAX_DISTANCE = 0.50


class RagUnavailable(Exception):
    """Busca não respondeu.

    Distinto de lista vazia de propósito: `results: []` é resposta legítima e
    vira `no_grounding`; serviço fora do ar virando `no_grounding` diria ao
    usuário "não há evidência na documentação" quando o que houve foi uma
    falha de infraestrutura.
    """


class RagSearchClientProtocol(Protocol):
    def search(self, query: str, limit: int = 5) -> list[RetrievedSource]: ...


class RagSearchClient:
    def __init__(self, base_url: str, timeout_seconds: int = 15) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def search(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/search",
                    json={"query": query, "limit": limit, "max_distance": DEFAULT_MAX_DISTANCE},
                )
        except httpx.HTTPError as exc:
            raise RagUnavailable(type(exc).__name__) from exc

        if response.status_code != 200:
            raise RagUnavailable(f"HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            raise RagUnavailable("corpo inválido") from exc

        return [RetrievedSource(**hit) for hit in body.get("results", [])]


@dataclass
class FakeRagSearchClient:
    """Fake determinístico. `results = []` exercita o corte de `no_grounding`."""

    failure: RagUnavailable | None = None
    results: list[RetrievedSource] = field(
        default_factory=lambda: [
            RetrievedSource(
                file_path="docs/handoffs/freshservice-jira.md",
                heading_path="Arquitetura > Worker de outbox",
                start_line=120,
                end_line=148,
                distance=0.31,
                content="O worker reivindica um evento por vez com SELECT FOR UPDATE SKIP LOCKED.",
            )
        ]
    )
    calls: list[str] = field(default_factory=list)

    def search(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        self.calls.append(query)
        if self.failure is not None:
            raise self.failure
        return self.results[:limit]
