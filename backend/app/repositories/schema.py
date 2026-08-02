"""SQLAlchemy ORM table definitions."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class TicketRow(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_system: Mapped[str] = mapped_column(String(80), nullable=False)
    source_ticket_id: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Squad as the source system reported it — not the routing decision.
    squad: Mapped[str | None] = mapped_column(String(40), nullable=True)
    requester: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # NULL = chamado aberto. Preenchido = concluído (FR-053). Setar só quando
    # NULL torna "marcar como concluído" idempotente.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow_executions: Mapped[list[WorkflowExecutionRow]] = relationship(back_populates="ticket")
    jira_issue_link: Mapped[JiraIssueLinkRow | None] = relationship(back_populates="ticket", uselist=False)

    __table_args__ = (
        UniqueConstraint("source_system", "source_ticket_id", "event_type", "event_id", name="uq_ticket_event"),
    )


class WorkflowExecutionRow(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="RESTRICT"), nullable=False
    )
    internal_correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=_uuid)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    squad_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    routing_rule_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    routing_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    ticket: Mapped[TicketRow] = relationship(back_populates="workflow_executions")
    external_references: Mapped[list[ExternalReferenceRow]] = relationship(back_populates="workflow_execution")
    routing_decisions: Mapped[list[RoutingDecisionRow]] = relationship(back_populates="workflow_execution")
    outbox_events: Mapped[list[OutboxEventRow]] = relationship(back_populates="workflow_execution")
    audit_logs: Mapped[list[AuditLogRow]] = relationship(back_populates="workflow_execution")


class ExternalReferenceRow(Base):
    __tablename__ = "external_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False
    )
    source_system: Mapped[str] = mapped_column(String(80), nullable=False)
    external_correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow_execution: Mapped[WorkflowExecutionRow] = relationship(back_populates="external_references")

    __table_args__ = (
        Index("ix_external_refs_source_extid", "source_system", "external_correlation_id"),
    )


class RoutingDecisionRow(Base):
    __tablename__ = "routing_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False
    )
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    squad_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow_execution: Mapped[WorkflowExecutionRow] = relationship(back_populates="routing_decisions")


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    claimed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow_execution: Mapped[WorkflowExecutionRow] = relationship(back_populates="outbox_events")


class JiraIssueLinkRow(Base):
    __tablename__ = "jira_issue_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    jira_issue_key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    # 'deterministic' = created by the automation. 'best_effort' = reconstructed
    # from free text. The comparison between the two is the point of the feature.
    link_origin: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="deterministic", default="deterministic"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    ticket: Mapped[TicketRow] = relationship(back_populates="jira_issue_link")


class SyncStateRow(Base):
    __tablename__ = "sync_state"

    source: Mapped[str] = mapped_column(Text, primary_key=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    workflow_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True
    )
    internal_correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow_execution: Mapped[WorkflowExecutionRow | None] = relationship(back_populates="audit_logs")


class AssistantConversationRow(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    # Gerado no navegador (crypto.randomUUID()), nunca no servidor — não há
    # login para amarrar a um usuário (FR-058/FR-059). Várias conversas podem
    # ter o mesmo session_id.
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Vazio até a primeira mensagem — vira o começo da pergunta do usuário.
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # Favoritada (fixada) — sobe pra uma seção acima de "Recentes" na sidebar.
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # `NULL` = ativa. Coluna temporal em vez de booleana porque custa o mesmo e
    # já registra QUANDO foi arquivada (specs/007 FR-012). Ortogonal a
    # `is_favorite`: arquivar não desfavorita.
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # `passive_deletes=True`: confia no `ondelete="CASCADE"` do FK (abaixo) em
    # vez do ORM tentar (e falhar) colocar NULL em `conversation_id` ao
    # excluir a conversa.
    messages: Mapped[list[AssistantMessageRow]] = relationship(
        back_populates="conversation",
        order_by="AssistantMessageRow.created_at",
        passive_deletes=True,
    )
    # Um anexo por conversa — `passive_deletes=True` para confiar no FK
    # `ondelete="CASCADE"` em vez de deixar o ORM tentar excluir em cascata.
    attachment: Mapped[AssistantAttachmentRow | None] = relationship(
        back_populates="conversation",
        uselist=False,
        passive_deletes=True,
    )


class AssistantMessageRow(Base):
    __tablename__ = "assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Serialização de RetrievedSource[]/TicketRefSource, ou NULL. Já redigido
    # (redaction.py) antes de chegar aqui — Princípio II não distingue "sair
    # para o modelo" de "sair para o disco".
    sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped[AssistantConversationRow] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_assistant_messages_conversation_created", "conversation_id", "created_at"),
    )


class AssistantAttachmentRow(Base):
    __tablename__ = "assistant_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    # Um anexo por conversa — `unique=True` garante que
    # `create_or_replace` possa usar UPSERT.
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Nome original do arquivo, exibido na UI (FR-013).
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Detectado por assinatura de conteúdo, não só extensão.
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Validado contra `attachment_max_bytes_*` antes de processar.
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Enum fechado: `received`, `processing`, `ready`, `failed`.
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # Preenchido só quando `status = "failed"` — mensagem estática, nunca
    # conteúdo do arquivo (constituição IV).
    error_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Texto extraído (pré-chunking), só quando `status = "ready"` — permite
    # visualizar o documento inteiro sem reconstruir a partir dos nós da
    # árvore (raiz/seções são truncados, folhas podem se sobrepor).
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped[AssistantConversationRow] = relationship(back_populates="attachment")
    # `passive_deletes=True`: confiar no `ondelete="CASCADE"` do FK em vez
    # do ORM tentar excluir nós em cascata.
    nodes: Mapped[list[AssistantAttachmentNodeRow]] = relationship(
        back_populates="attachment",
        passive_deletes=True,
    )


class AssistantAttachmentNodeRow(Base):
    __tablename__ = "assistant_attachment_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    # FK → assistant_attachments.id ON DELETE CASCADE.
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_attachments.id", ondelete="CASCADE"), nullable=False
    )
    # FK autorreferencial para construir a árvore. NULL só na raiz.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assistant_attachment_nodes.id", ondelete="CASCADE"), nullable=True
    )
    # Enum fechado: `root`, `section`, `leaf`.
    node_type: Mapped[str] = mapped_column(String(10), nullable=False)
    # 0 na raiz, cresce por nível de heading.
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    # Caminho completo até este nó (ex.: "Decisões > RAG > Modelo").
    heading_path: Mapped[str] = mapped_column(Text, nullable=False)
    # Folha: trecho literal do documento. Seção/raiz: concatenação truncada
    # dos filhos (usada só para embedding, nunca citada diretamente).
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Serializado com `serialize_embedding` (mesmo formato do RAG).
    # NULL só em estado transitório; nunca NULL quando `status = ready`.
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Só em folhas — NULL em root/section.
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Só em folhas — NULL em root/section.
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)

    attachment: Mapped[AssistantAttachmentRow] = relationship(back_populates="nodes")
    # Autorreferência para navegação sobe/desce na árvore.
    parent: Mapped[AssistantAttachmentNodeRow | None] = relationship(
        back_populates="children",
        remote_side=[id],
        foreign_keys=[parent_id],
    )
    children: Mapped[list[AssistantAttachmentNodeRow]] = relationship(
        back_populates="parent",
        remote_side=[parent_id],
    )

    __table_args__ = (
        Index("ix_assistant_attachment_nodes_attachment_type", "attachment_id", "node_type"),
    )
