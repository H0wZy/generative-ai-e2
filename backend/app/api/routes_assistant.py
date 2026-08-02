"""Rotas do assistente. `/ask` é sempre 200 — o resultado vive em `status`.

422 só para `question` vazia ou acima de 2000 caracteres, o que a validação do
próprio modelo já faz. As rotas de conversa (`/conversations*`) são recursos
de verdade: 400 sem sessão válida, 404 se a conversa não existe ou não
pertence à sessão que pediu.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.domain.assistant import AssistantAnswer, AssistantQuestion, AttachmentSummary
from app.integrations.ocr import FakeOcrClient, OcrClientError, OcrClientProtocol, OllamaOcrClient
from app.integrations.openrouter import (
    AssistantClientProtocol,
    FakeAssistantClient,
    OpenRouterClient,
)
from app.integrations.pdf_extract import (
    PdfExtractError,
    extract_first_page_image,
    extract_pdf_text,
)
from app.integrations.rag_search import RagSearchClient, RagSearchClientProtocol
from app.repositories.assistant import AssistantConversationRepository
from app.repositories.attachment import AssistantAttachmentRepository
from app.repositories.schema import AssistantAttachmentRow, AssistantConversationRow
from app.repositories.workflows import WorkflowRepository
from app.services import assistant as service
from app.services import attachment_tree

# Extensão -> mime declarado (data-model.md §1). `.pdf` é validado por
# assinatura de conteúdo (b"%PDF"), não só extensão — FR-002/edge case de
# formato não suportado.
_TEXT_MIME_BY_EXTENSION = {".md": "text/markdown", ".txt": "text/plain"}

_UNSUPPORTED_FORMAT_DETAIL = "Formato não suportado. Envie .md, .txt ou .pdf."
_EMPTY_DOCUMENT_ERROR = "Documento vazio ou sem conteúdo textual aproveitável."
_PDF_EXTRACTION_FAILED_ERROR = "Não foi possível extrair texto do PDF."


class AskRequest(AssistantQuestion):
    # Ausente = não persiste (mesma tolerância de X-Session-Id ausente) — só
    # os testes de resposta/roteamento pura não precisam se importar com isso.
    conversation_id: uuid.UUID | None = None


class ConversationUpdateRequest(BaseModel):
    # Todos opcionais — PATCH parcial: renomear, favoritar e arquivar são ações
    # independentes na sidebar (menu de contexto), não um formulário único.
    title: str | None = None
    is_favorite: bool | None = None
    # Booleano, não data: a interface alterna um estado. O carimbo é gravado
    # pelo servidor (specs/007 R3).
    is_archived: bool | None = None


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
        "archived_at": row.archived_at.isoformat() if row.archived_at else None,
    }


def _attachment_summary(row: AssistantAttachmentRow) -> AttachmentSummary:
    return AttachmentSummary(
        id=row.id,
        file_name=row.file_name,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        status=row.status,  # type: ignore[arg-type]
        error_reason=row.error_reason,
    )


def _detect_text_mime(filename: str, content: bytes) -> str | None:
    mime = _TEXT_MIME_BY_EXTENSION.get(Path(filename).suffix.lower())
    if mime is None:
        return None
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return mime


def _extract_document_text(
    mime_type: str, content: bytes, ocr_client: OcrClientProtocol
) -> tuple[str, str | None]:
    """Retorna (texto, motivo_da_falha). Motivo não-``None`` = ``status: failed``
    (nunca segue como se o documento estivesse disponível — FR-012).
    """
    if mime_type != "application/pdf":
        text = content.decode("utf-8")
        if not text.strip():
            return "", _EMPTY_DOCUMENT_ERROR
        return text, None

    try:
        text = extract_pdf_text(content)
    except PdfExtractError:
        return "", _PDF_EXTRACTION_FAILED_ERROR

    if text:
        return text, None

    # Sem camada de texto embutida — PDF escaneado, aciona OCR (research.md
    # R4). O modelo de visão espera uma imagem rasterizada, não o PDF
    # inteiro: extrai a imagem embutida da página antes de chamar o OCR.
    try:
        image_bytes = extract_first_page_image(content)
    except PdfExtractError:
        return "", _PDF_EXTRACTION_FAILED_ERROR
    if image_bytes is None:
        return "", _PDF_EXTRACTION_FAILED_ERROR

    try:
        text = ocr_client.extract_text(image_bytes)
    except OcrClientError:
        return "", _PDF_EXTRACTION_FAILED_ERROR

    if not text.strip():
        return "", _PDF_EXTRACTION_FAILED_ERROR
    return text, None


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

    def get_ocr_client() -> OcrClientProtocol:
        return OllamaOcrClient(settings)

    router.get_rag_client = get_rag_client  # type: ignore[attr-defined]
    router.get_model_client = get_model_client  # type: ignore[attr-defined]
    router.get_ocr_client = get_ocr_client  # type: ignore[attr-defined]

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
        state: Literal["active", "archived"] = "active",
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        """Sem sessão, ou header inválido, devolve lista vazia — nunca 404.

        `state` default `active`: quem já consumia esta rota antes do
        arquivamento continua vendo o mesmo, agora sem as arquivadas.
        """
        session_id = _parse_session_id(x_session_id)
        if session_id is None:
            return {"conversations": []}
        rows = AssistantConversationRepository(session).list_conversations(session_id, state)
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
        # `conversation`: a tela precisa saber que a conversa aberta está
        # arquivada pra avisar (specs/007 US2). Arquivada some das listas
        # ativas, então essa informação não chegaria por `GET /conversations`
        # — e uma requisição só pra isso seria desperdício. Campo aditivo.
        return {"messages": messages, "conversation": _conversation_summary(conversation)}

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
        if payload.is_archived is not None:
            repo.set_archived(conversation_id, session_id, payload.is_archived)

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

    def _get_owned_conversation_or_404(
        conversation_id: uuid.UUID, x_session_id: str | None, session: Session
    ) -> None:
        session_id = _parse_session_id(x_session_id)
        conversation = (
            AssistantConversationRepository(session).get_owned(conversation_id, session_id)
            if session_id
            else None
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    @router.post(
        "/conversations/{conversation_id}/attachment", status_code=201, response_model=AttachmentSummary
    )
    def upload_attachment(
        conversation_id: uuid.UUID,
        file: UploadFile,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        ocr_client: OcrClientProtocol = Depends(get_ocr_client),
        session: Session = Depends(get_session),
    ) -> AttachmentSummary:
        _get_owned_conversation_or_404(conversation_id, x_session_id, session)

        content = file.file.read()
        filename = file.filename or "documento"
        is_pdf_extension = Path(filename).suffix.lower() == ".pdf"

        if is_pdf_extension:
            mime_type = "application/pdf" if content.startswith(b"%PDF") else None
            max_bytes = settings.attachment_max_bytes_pdf
        else:
            mime_type = _detect_text_mime(filename, content)
            max_bytes = settings.attachment_max_bytes_text

        if mime_type is None:
            raise HTTPException(status_code=422, detail=_UNSUPPORTED_FORMAT_DETAIL)
        if len(content) > max_bytes:
            limit_mb = max_bytes // 1_000_000
            raise HTTPException(
                status_code=413, detail=f"Arquivo acima do limite permitido ({limit_mb} MB)."
            )

        attachment_repo = AssistantAttachmentRepository(session)
        text, error_reason = _extract_document_text(mime_type, content, ocr_client)

        if error_reason is not None:
            attachment = attachment_repo.create_or_replace(
                conversation_id,
                file_name=filename,
                mime_type=mime_type,
                size_bytes=len(content),
                status="failed",
                error_reason=error_reason,
            )
            return _attachment_summary(attachment)

        nodes = attachment_tree.build_tree(text)
        attachment = attachment_repo.create_or_replace(
            conversation_id,
            file_name=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            status="ready",
            content=text,
        )
        attachment_repo.bulk_insert_nodes(attachment.id, nodes)
        return _attachment_summary(attachment)

    @router.get("/conversations/{conversation_id}/attachment")
    def get_attachment(
        conversation_id: uuid.UUID,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        _get_owned_conversation_or_404(conversation_id, x_session_id, session)
        attachment = AssistantAttachmentRepository(session).get_by_conversation(conversation_id)
        if attachment is None:
            return {"attachment": None}
        return {"attachment": _attachment_summary(attachment).model_dump()}

    @router.get("/conversations/{conversation_id}/attachment/content")
    def get_attachment_content(
        conversation_id: uuid.UUID,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> dict:
        """Texto completo do anexo, pra visualização — separado de
        `get_attachment` de propósito: aquele é buscado toda vez que a
        conversa carrega (indicador na tela), este só quando a pessoa abre o
        documento pra ler (specs/013 follow-up)."""
        _get_owned_conversation_or_404(conversation_id, x_session_id, session)
        attachment = AssistantAttachmentRepository(session).get_by_conversation(conversation_id)
        if attachment is None or attachment.status != "ready":
            raise HTTPException(status_code=404, detail="Documento não disponível para visualização.")
        return {"file_name": attachment.file_name, "content": attachment.content or ""}

    @router.delete("/conversations/{conversation_id}/attachment", status_code=204)
    def delete_attachment(
        conversation_id: uuid.UUID,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        session: Session = Depends(get_session),
    ) -> None:
        _get_owned_conversation_or_404(conversation_id, x_session_id, session)
        AssistantAttachmentRepository(session).delete_by_conversation(conversation_id)

    @router.post("/ask", response_model=AssistantAnswer)
    def ask(
        payload: AskRequest,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        rag_client: RagSearchClientProtocol = Depends(get_rag_client),
        model_client: AssistantClientProtocol = Depends(get_model_client),
        session: Session = Depends(get_session),
    ) -> AssistantAnswer:
        session_id = _parse_session_id(x_session_id)

        attachment_search = None
        # Sem isso, qualquer chamador que soubesse/adivinhasse um
        # conversation_id de outra sessão conseguiria extrair conteúdo do
        # anexo alheio via resposta do assistente (FR-009/SC-004) — mesma
        # checagem de posse que as 3 rotas de anexo já fazem, só que aqui
        # sem 404: `/ask` é sempre 200, então sem posse é tratado como
        # "sem anexo", igual ao best-effort de persistência de mensagem
        # logo abaixo.
        if payload.conversation_id is not None and session_id is not None:
            owned_conversation = AssistantConversationRepository(session).get_owned(
                payload.conversation_id, session_id
            )
            if owned_conversation is not None:
                attachment_repo = AssistantAttachmentRepository(session)
                attachment = attachment_repo.get_by_conversation(payload.conversation_id)
                if attachment is not None and attachment.status == "ready":
                    nodes = attachment_repo.get_nodes(attachment.id)
                    file_name = attachment.file_name
                    attachment_search = lambda q: attachment_tree.search(  # noqa: E731
                        nodes, q, file_name=file_name
                    )

        result = service.ask(
            AssistantQuestion(question=payload.question, history=payload.history),
            enabled=settings.assistant_is_configured,
            rag_client=rag_client,
            # Função, não instância: o serviço só chama o cliente quando o
            # assistente está habilitado.
            model_client_factory=lambda: model_client,
            max_context_chars=settings.assistant_max_context_chars,
            ticket_lookup=lambda key: WorkflowRepository(session).find_by_jira_key(key),
            attachment_search=attachment_search,
        )

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
