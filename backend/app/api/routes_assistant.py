"""Rota do assistente. Sempre 200 — o resultado vive em `status`.

422 só para `question` vazia ou acima de 2000 caracteres, o que a validação do
próprio modelo já faz.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.domain.assistant import AssistantAnswer, AssistantQuestion
from app.integrations.openrouter import (
    AssistantClientProtocol,
    FakeAssistantClient,
    OpenRouterClient,
)
from app.integrations.rag_search import RagSearchClient, RagSearchClientProtocol
from app.services import assistant as service


def create_assistant_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

    def get_rag_client() -> RagSearchClientProtocol:
        return RagSearchClient(settings.rag_search_url)

    def get_model_client() -> AssistantClientProtocol:
        if not settings.assistant_is_configured:
            return FakeAssistantClient()
        return OpenRouterClient(
            base_url=settings.assistant_base_url,
            api_key=settings.openrouter_api_key.get_secret_value(),  # type: ignore[union-attr]
            model=settings.assistant_model,
            timeout_seconds=settings.assistant_timeout_seconds,
        )

    router.get_rag_client = get_rag_client  # type: ignore[attr-defined]
    router.get_model_client = get_model_client  # type: ignore[attr-defined]

    @router.post("/ask", response_model=AssistantAnswer)
    def ask(
        payload: AssistantQuestion,
        rag_client: RagSearchClientProtocol = Depends(get_rag_client),
        model_client: AssistantClientProtocol = Depends(get_model_client),
    ) -> AssistantAnswer:
        return service.ask(
            payload,
            enabled=settings.assistant_is_configured,
            rag_client=rag_client,
            # Função, não instância: o serviço só chama o cliente quando o
            # assistente está habilitado.
            model_client_factory=lambda: model_client,
            max_context_chars=settings.assistant_max_context_chars,
        )

    return router
