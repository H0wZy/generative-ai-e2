"""Domain types — no I/O, no database, no network."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# API payload / response types (Pydantic)
# ---------------------------------------------------------------------------


class Attachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(ge=0, le=25_000_000)


class TicketIngestRequest(BaseModel):
    event_id: Annotated[str, Field(min_length=1, max_length=128)]
    event_type: Literal["ticket.created", "ticket.updated"] = "ticket.created"
    occurred_at: datetime
    source_ticket_id: Annotated[str, Field(min_length=1, max_length=80)]
    subject: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=20_000)] = ""
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    category: str | None = Field(default=None, max_length=80)
    # Squad as the source system reported it. Drives deterministic routing.
    squad: str | None = Field(default=None, max_length=40)
    requester: str | None = Field(default=None, max_length=255)
    attachments: list[Attachment] = Field(default_factory=list)
    external_correlation_id: str | None = Field(default=None, max_length=128)


class TicketUpdateRequest(BaseModel):
    """PATCH /workflows/{id}/ticket — todos os campos opcionais (contracts/api-tickets.md)."""

    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    category: str | None = Field(default=None, max_length=80)


class IngestResponse(BaseModel):
    workflow_execution_id: UUID
    internal_correlation_id: UUID
    status: Literal["accepted", "duplicate"]


class WorkflowResponse(BaseModel):
    workflow_execution_id: UUID
    internal_correlation_id: UUID
    source_ticket_id: str
    status: str
    attempt_count: int
    squad_id: str | None
    needs_human_review: bool
    jira_issue_key: str | None


WorkflowStatus = Literal[
    "pending", "processing", "retry_scheduled", "completed", "failed", "needs_human_review"
]


class WorkflowTicketSummary(BaseModel):
    """Ticket fields safe to expose on the dashboard — no requester/PII."""

    source_ticket_id: str
    subject: str
    category: str | None
    priority: str


class WorkflowListItem(BaseModel):
    workflow_execution_id: UUID
    internal_correlation_id: UUID
    status: WorkflowStatus
    attempt_count: int
    squad_id: str | None
    routing_confidence: float | None
    routing_rule_version: str | None
    needs_human_review: bool
    last_error: str | None
    jira_issue_key: str | None
    link_origin: Literal["deterministic", "best_effort"] | None = None
    reprocess_eligible: bool
    ticket: WorkflowTicketSummary
    updated_at: datetime
    resolved_at: datetime | None = None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowListItem]
    total: int


class TicketDetail(BaseModel):
    """Ticket completo do detalhe.

    `subject` e `description` são conteúdo externo não confiável (Princípio II):
    são renderizados como texto, nunca como HTML, e nunca entram em log, erro
    ou evidência.
    """

    source_ticket_id: str
    subject: str
    description: str
    category: str | None
    priority: str
    requester: str | None
    source_system: str


class TimelineEvent(BaseModel):
    at: datetime
    event_type: str
    summary: str
    detail: dict[str, object]


class SlaState(BaseModel):
    """Derivado, não persistido — não há coluna de prazo no schema."""

    available: bool
    minutes_left: int | None
    tone: Literal["ok", "warning", "critical", "unknown"]


class WorkflowDetail(BaseModel):
    workflow_execution_id: UUID
    internal_correlation_id: UUID
    status: WorkflowStatus
    attempt_count: int
    squad_id: str | None
    routing_confidence: float | None
    routing_rule_version: str | None
    routing_reason: str | None
    needs_human_review: bool
    last_error: str | None
    next_attempt_at: datetime | None
    jira_issue_key: str | None
    jira_issue_url: str | None
    link_origin: Literal["deterministic", "best_effort"] | None = None
    ticket: TicketDetail
    timeline: list[TimelineEvent]
    created_at: datetime
    updated_at: datetime
    reprocess_eligible: bool
    resolved_at: datetime | None = None


class MetricsResponse(BaseModel):
    received: int
    pending: int
    completed: int
    retry_scheduled: int
    failed: int
    needs_human_review: int
    duplicates_avoided: int | None


class ReprocessResponse(BaseModel):
    workflow_execution_id: UUID
    status: WorkflowStatus
    jira_issue_key: str | None
    reprocessed: bool
    reason: Literal["already_linked", "not_eligible"] | None = None


# ---------------------------------------------------------------------------
# Pure domain value objects (dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TicketRecord:
    id: UUID
    source_ticket_id: str
    subject: str
    description: str
    priority: str
    category: str | None
    squad: str | None = None


@dataclass(frozen=True)
class RoutingDecision:
    squad_id: str | None
    rule_version: str
    confidence: float
    needs_human_review: bool


@dataclass(frozen=True)
class ProcessResult:
    workflow_execution_id: UUID
    status: Literal["completed", "retry_scheduled", "failed", "needs_human_review"]
    attempt_count: int
    jira_issue_key: str | None
