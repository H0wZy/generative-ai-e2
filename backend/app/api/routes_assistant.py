"""Rotas do assistente. `/ask` é sempre 200 — o resultado vive em `status`.

422 só para `question` vazia ou acima de 2000 caracteres, o que a validação do
próprio modelo já faz. As rotas de conversa (`/conversations*`) são recursos
de verdade: 400 sem sessão válida, 404 se a conversa não existe ou não
pertence à sessão que pediu.
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
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
from app.repositories.schema import AssistantConversationRow
from app.repositories.workflows import WorkflowRepository
from app.services import assistant as service


class AskRequest(AssistantQuestion):
    # Ausente = não persiste (mesma tolerância de X-Session-Id ausente) — só
    # os testes de resposta/roteamento pura não precisam se importar com isso.
    conversation_id: uuid.UUID | None = None


class ConversationUpdateRequest(BaseModel):
    # Ambos opcionais — PATCH parcial: renomear e favoritar são ações
    # independentes na sidebar (menu de contexto), não um formulário único.
    title: str | None = None
    is_favorite: bool | None = None


def _parse_session_id(x_session_id: str | None) -> uuid.UUID | None:
    if not x_session_id:
        return None
    try:
        return uuid.UUID(x_session_id)
    except ValueError:
        return None


def _conversation_summary(row: AssistantConversationRow) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "updated_at": row.updated_at.isoformat(),
        "is_favorite": row.is_favorite,
    }


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
            max_tokens=settings.assistant_max_tokens,
        )

    router.get_rag_client = get_rag_client  # type: ignore[attr-defined]
    router.get_model_client = get_model_client  # type: ignore[attr-defined]

    @router.post("/conversations", status_code=201)
    def create_conversation(
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        session_id = _parse_session_id(x_session_id)
        if session_id is None:
            raise HTTPException(status_code=400, detail="X-Session-Id ausente ou inválido.")
        conversation = AssistantConversationRepository(session).create_conversation(session_id)
        return _conversation_summary(conversation)

    @router.get("/conversations")
    def list_conversations(
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        """Sem sessão, ou header inválido, devolve lista vazia — nunca 404."""
        session_id = _parse_session_id(x_session_id)
        if session_id is None:
            return {"conversations": []}
        rows = AssistantConversationRepository(session).list_conversations(session_id)
        return {"conversations": [_conversation_summary(row) for row in rows]}

    @router.get("/conversations/{conversation_id}/messages")
    def get_conversation_messages(
        conversation_id: uuid.UUID,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        session_id = _parse_session_id(x_session_id)
        repo = AssistantConversationRepository(session)
        conversation = repo.get_owned(conversation_id, session_id) if session_id else None
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")

        messages = []
        for row in repo.list_messages(conversation_id):
            message: dict = {"role": row.role, "text": row.text}
            if row.sources_json:
                envelope = json.loads(row.sources_json)
                message["sources"] = envelope.get("sources", [])
                message["ticket_context"] = envelope.get("ticket_context")
            messages.append(message)
        return {"messages": messages}

    @router.patch("/conversations/{conversation_id}")
    def update_conversation(
        conversation_id: uuid.UUID,
        payload: ConversationUpdateRequest,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        session_id = _parse_session_id(x_session_id)
        if session_id is None:
            raise HTTPException(status_code=400, detail="X-Session-Id ausente ou inválido.")
        repo = AssistantConversationRepository(session)
        conversation = repo.get_owned(conversation_id, session_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")

        if payload.title is not None:
            trimmed = payload.title.strip()
            if not trimmed:
                raise HTTPException(status_code=422, detail="Título não pode ser vazio.")
            repo.rename_conversation(conversation_id, session_id, trimmed)
        if payload.is_favorite is not None:
            repo.set_favorite(conversation_id, session_id, payload.is_favorite)

        session.refresh(conversation)
        return _conversation_summary(conversation)

    @router.delete("/conversations/{conversation_id}", status_code=204)
    def delete_conversation(
        conversation_id: uuid.UUID,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> None:
        session_id = _parse_session_id(x_session_id)
        if session_id is None:
            raise HTTPException(status_code=400, detail="X-Session-Id ausente ou inválido.")
        if not AssistantConversationRepository(session).delete_conversation(conversation_id, session_id):
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    @router.post("/ask", response_model=AssistantAnswer)
    def ask(
        payload: AskRequest,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        rag_client: RagSearchClientProtocol = Depends(get_rag_client),
        model_client: AssistantClientProtocol = Depends(get_model_client),
        session: Session = Depends(get_session),
    ) -> AssistantAnswer:
        result = service.ask(
            AssistantQuestion(question=payload.question, history=payload.history),
            enabled=settings.assistant_is_configured,
            rag_client=rag_client,
            # Função, não instância: o serviço só chama o cliente quando o
            # assistente está habilitado.
            model_client_factory=lambda: model_client,
            max_context_chars=settings.assistant_max_context_chars,
            ticket_lookup=lambda key: WorkflowRepository(session).find_by_jira_key(key),
        )

        session_id = _parse_session_id(x_session_id)
        if session_id is not None and payload.conversation_id is not None:
            repo = AssistantConversationRepository(session)
            # Best-effort, igual ao padrão de busca RAG em services/assistant.py:
            # uma falha (ou conversa inexistente/de outra sessão) aqui nunca
            # derruba a resposta já computada.
            try:
                if repo.get_owned(payload.conversation_id, session_id) is not None:
                    repo.append_message(payload.conversation_id, "user", payload.question, None)
                    repo.append_message(
                        payload.conversation_id,
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
