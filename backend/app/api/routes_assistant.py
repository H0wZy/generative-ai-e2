"""Rota do assistente. Sempre 200 — o resultado vive em `status`.

422 só para `question` vazia ou acima de 2000 caracteres, o que a validação do
próprio modelo já faz.
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.domain.assistant import AssistantAnswer, AssistantQuestion
from app.integrations.openrouter import (
    AssistantClientProtocol,
    FakeAssistantClient,
    OpenRouterClient,
)
from app.integrations.rag_search import RagSearchClient, RagSearchClientProtocol
from app.repositories.assistant import AssistantConversationRepository
from app.repositories.workflows import WorkflowRepository
from app.services import assistant as service


def _parse_session_id(x_session_id: str | None) -> uuid.UUID | None:
    if not x_session_id:
        return None
    try:
        return uuid.UUID(x_session_id)
    except ValueError:
        return None


def create_assistant_router(settings: Settings, session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

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

    @router.get("/conversation")
    def get_conversation(
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        """Histórico da sessão. Sem header, ou header inválido, devolve vazio — nunca 404."""
        session_id = _parse_session_id(x_session_id)
        if session_id is None:
            return {"messages": []}

        rows = AssistantConversationRepository(session).list_messages(session_id)
        messages = []
        for row in rows:
            message: dict = {"role": row.role, "text": row.text}
            if row.sources_json:
                envelope = json.loads(row.sources_json)
                message["sources"] = envelope.get("sources", [])
                message["ticket_context"] = envelope.get("ticket_context")
            messages.append(message)
        return {"messages": messages}

    @router.post("/ask", response_model=AssistantAnswer)
    def ask(
        payload: AssistantQuestion,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        rag_client: RagSearchClientProtocol = Depends(get_rag_client),
        model_client: AssistantClientProtocol = Depends(get_model_client),
        session: Session = Depends(get_session),
    ) -> AssistantAnswer:
        result = service.ask(
            payload,
            enabled=settings.assistant_is_configured,
            rag_client=rag_client,
            # Função, não instância: o serviço só chama o cliente quando o
            # assistente está habilitado.
            model_client_factory=lambda: model_client,
            max_context_chars=settings.assistant_max_context_chars,
            ticket_lookup=lambda key: WorkflowRepository(session).find_by_jira_key(key),
        )

        session_id = _parse_session_id(x_session_id)
        if session_id is not None:
            # Best-effort, igual ao padrão de busca RAG em services/assistant.py:
            # uma falha aqui nunca derruba a resposta já computada.
            try:
                repo = AssistantConversationRepository(session)
                repo.append_message(session_id, "user", payload.question, None)
                repo.append_message(
                    session_id,
                    "assistant",
                    result.answer or "",
                    json.dumps({
                        "sources": [s.model_dump() for s in result.sources],
                        "ticket_context": (
                            result.ticket_context.model_dump() if result.ticket_context else None
                        ),
                    }),
                )
            except Exception:  # noqa: BLE001
                session.rollback()

        return result

    return router
