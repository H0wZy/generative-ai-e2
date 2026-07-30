"""WorkflowRepository — all PostgreSQL commands and transactions.

No business rules live here.  One transaction per public method.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import (
    IngestResponse,
    MetricsResponse,
    ProcessResult,
    TicketDetail,
    TicketIngestRequest,
    TicketRecord,
    TimelineEvent,
    WorkflowDetail,
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowTicketSummary,
)
from app.repositories.schema import (
    AuditLogRow,
    ExternalReferenceRow,
    JiraIssueLinkRow,
    OutboxEventRow,
    RoutingDecisionRow,
    TicketRow,
    WorkflowExecutionRow,
)


# Mapa fechado de evento de auditoria: rótulo em português e chaves que podem
# sair na timeline. `details_json` NUNCA é devolvido inteiro — se algum
# escritor de log passar a incluir assunto ou descrição do ticket, a lista
# branca impede o vazamento (Princípio II). Tipo desconhecido devolve {}.
_TIMELINE_EVENTS: dict[str, tuple[str, frozenset[str]]] = {
    "ticket.ingested": ("Ticket recebido", frozenset({"source_ticket_id", "event_id"})),
    "jira.issue_linked": ("Issue criada no Jira", frozenset({"jira_issue_key"})),
    "routing.review_required": ("Enviado para revisão humana", frozenset({"reason"})),
    "jira.retry_scheduled": ("Nova tentativa agendada", frozenset({"error_category"})),
    "jira.failed": ("Falha na criação da issue", frozenset({"error_category"})),
    "workflow.reprocess_requested": ("Reprocessamento solicitado", frozenset()),
}

REPROCESS_ELIGIBLE_STATUSES = ("failed", "needs_human_review")


class TicketAlreadyResolved(Exception):
    """Raised by `update_ticket_fields` when the ticket's `resolved_at` is set."""


def _timeline_event(row: AuditLogRow) -> TimelineEvent:
    summary, allowed = _TIMELINE_EVENTS.get(row.event_type, (row.event_type, frozenset()))
    detail: dict[str, object] = {}
    if allowed:
        try:
            raw = json.loads(row.details_json)
        except (ValueError, TypeError):
            raw = {}
        if isinstance(raw, dict):
            detail = {k: v for k, v in raw.items() if k in allowed}
    return TimelineEvent(
        at=row.created_at,
        event_type=row.event_type,
        summary=summary,
        detail=detail,
    )


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Ingestion — atomic ticket + workflow + outbox + audit
    # ------------------------------------------------------------------

    def ingest(self, payload: TicketIngestRequest) -> IngestResponse:
        """Persist ticket and workflow in one transaction.

        Returns an ``IngestResponse`` with ``status='duplicate'`` when the
        same source event already exists, without writing new rows.
        """
        existing = self._find_existing_workflow(payload)
        if existing is not None:
            return IngestResponse(
                workflow_execution_id=existing.id,
                internal_correlation_id=existing.internal_correlation_id,
                status="duplicate",
            )

        ticket = TicketRow(
            id=uuid.uuid4(),
            source_system="freshservice",
            source_ticket_id=payload.source_ticket_id,
            event_type=payload.event_type,
            event_id=payload.event_id,
            subject=payload.subject,
            description=payload.description,
            priority=payload.priority,
            category=payload.category,
            squad=payload.squad,
            requester=payload.requester,
            occurred_at=payload.occurred_at,
        )
        self._session.add(ticket)
        self._session.flush()  # get ticket.id

        internal_correlation_id = uuid.uuid4()
        workflow = WorkflowExecutionRow(
            id=uuid.uuid4(),
            ticket_id=ticket.id,
            internal_correlation_id=internal_correlation_id,
            status="pending",
        )
        self._session.add(workflow)
        self._session.flush()  # get workflow.id

        # Store optional external reference for reconciliation only
        if payload.external_correlation_id:
            self._session.add(
                ExternalReferenceRow(
                    id=uuid.uuid4(),
                    workflow_execution_id=workflow.id,
                    source_system="freshservice",
                    external_correlation_id=payload.external_correlation_id,
                )
            )

        # Outbox event for the worker to claim
        self._session.add(
            OutboxEventRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                event_type="ticket.process",
                payload_json=json.dumps({"source_ticket_id": payload.source_ticket_id}),
                claimed=False,
            )
        )

        # Append-only audit entry
        self._session.add(
            AuditLogRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                internal_correlation_id=internal_correlation_id,
                event_type="ticket.ingested",
                details_json=json.dumps({
                    "source_ticket_id": payload.source_ticket_id,
                    "event_id": payload.event_id,
                }),
            )
        )

        self._session.commit()
        return IngestResponse(
            workflow_execution_id=workflow.id,
            internal_correlation_id=internal_correlation_id,
            status="accepted",
        )

    # ------------------------------------------------------------------
    # Worker claim — SELECT FOR UPDATE SKIP LOCKED
    # ------------------------------------------------------------------

    def claim_pending_outbox(self) -> tuple[OutboxEventRow, WorkflowExecutionRow, TicketRow] | None:
        """Atomically claim the oldest unclaimed outbox event.

        Returns ``(outbox_event, workflow, ticket)`` or ``None`` if the
        queue is empty.  The caller MUST commit or rollback the session.
        """
        stmt = (
            select(OutboxEventRow)
            .where(OutboxEventRow.claimed.is_(False))
            .order_by(OutboxEventRow.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        outbox = self._session.execute(stmt).scalar_one_or_none()
        if outbox is None:
            return None

        outbox.claimed = True
        workflow = self._session.get(WorkflowExecutionRow, outbox.workflow_execution_id)
        ticket = self._session.get(TicketRow, workflow.ticket_id)  # type: ignore[union-attr]
        workflow.status = "processing"  # type: ignore[union-attr]
        workflow.attempt_count = (workflow.attempt_count or 0) + 1  # type: ignore[union-attr]
        workflow.updated_at = datetime.now(timezone.utc)  # type: ignore[union-attr]
        self._session.flush()
        return outbox, workflow, ticket  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # State transitions after routing / Jira call
    # ------------------------------------------------------------------

    def record_routing_decision(
        self,
        workflow: WorkflowExecutionRow,
        squad_id: str | None,
        rule_version: str,
        confidence: float,
        reason: str,
        needs_human_review: bool,
    ) -> None:
        self._session.add(
            RoutingDecisionRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                rule_version=rule_version,
                squad_id=squad_id,
                confidence=confidence,
                reason=reason,
                needs_human_review=needs_human_review,
            )
        )
        workflow.squad_id = squad_id
        workflow.routing_rule_version = rule_version
        workflow.routing_confidence = confidence
        workflow.needs_human_review = needs_human_review
        workflow.updated_at = datetime.now(timezone.utc)

    def complete_with_jira_link(
        self,
        workflow: WorkflowExecutionRow,
        ticket: TicketRow,
        jira_issue_key: str,
    ) -> None:
        """Set workflow to completed and persist the Jira link (idempotent)."""
        existing = self._session.execute(
            select(JiraIssueLinkRow).where(JiraIssueLinkRow.ticket_id == ticket.id)
        ).scalar_one_or_none()

        if existing is None:
            self._session.add(
                JiraIssueLinkRow(
                    id=uuid.uuid4(),
                    ticket_id=ticket.id,
                    jira_issue_key=jira_issue_key,
                    link_origin="deterministic",
                )
            )

        workflow.status = "completed"
        workflow.last_error = None
        workflow.updated_at = datetime.now(timezone.utc)

        self._session.add(
            AuditLogRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                internal_correlation_id=workflow.internal_correlation_id,
                event_type="jira.issue_linked",
                details_json=json.dumps({"jira_issue_key": jira_issue_key}),
            )
        )

    def mark_needs_human_review(self, workflow: WorkflowExecutionRow, reason: str) -> None:
        workflow.status = "needs_human_review"
        workflow.updated_at = datetime.now(timezone.utc)
        self._session.add(
            AuditLogRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                internal_correlation_id=workflow.internal_correlation_id,
                event_type="routing.review_required",
                details_json=json.dumps({"reason": reason}),
            )
        )

    def schedule_retry(
        self,
        workflow: WorkflowExecutionRow,
        next_attempt_at: datetime,
        error_category: str,
    ) -> None:
        workflow.status = "retry_scheduled"
        workflow.last_error = error_category
        workflow.next_attempt_at = next_attempt_at
        workflow.updated_at = datetime.now(timezone.utc)

        # Re-open an outbox event for the next worker pick-up
        self._session.add(
            OutboxEventRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                event_type="ticket.process",
                payload_json="{}",
                claimed=False,
            )
        )

        self._session.add(
            AuditLogRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                internal_correlation_id=workflow.internal_correlation_id,
                event_type="jira.retry_scheduled",
                details_json=json.dumps({"error_category": error_category}),
            )
        )

    def mark_failed(self, workflow: WorkflowExecutionRow, error_category: str) -> None:
        workflow.status = "failed"
        workflow.last_error = error_category
        workflow.updated_at = datetime.now(timezone.utc)
        self._session.add(
            AuditLogRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                internal_correlation_id=workflow.internal_correlation_id,
                event_type="jira.failed",
                details_json=json.dumps({"error_category": error_category}),
            )
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_workflow_response(self, workflow_id: uuid.UUID) -> ProcessResult | None:
        workflow = self._session.get(WorkflowExecutionRow, workflow_id)
        if workflow is None:
            return None
        ticket = self._session.get(TicketRow, workflow.ticket_id)
        link = self._session.execute(
            select(JiraIssueLinkRow).where(JiraIssueLinkRow.ticket_id == workflow.ticket_id)
        ).scalar_one_or_none()
        return ProcessResult(
            workflow_execution_id=workflow.id,
            status=workflow.status,  # type: ignore[arg-type]
            attempt_count=workflow.attempt_count,
            jira_issue_key=link.jira_issue_key if link else None,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_existing_workflow(self, payload: TicketIngestRequest) -> WorkflowExecutionRow | None:
        ticket_stmt = (
            select(TicketRow)
            .where(
                TicketRow.source_system == "freshservice",
                TicketRow.source_ticket_id == payload.source_ticket_id,
                TicketRow.event_type == payload.event_type,
                TicketRow.event_id == payload.event_id,
            )
        )
        ticket = self._session.execute(ticket_stmt).scalar_one_or_none()
        if ticket is None:
            return None
        # Return the most recent workflow execution for this ticket
        stmt = (
            select(WorkflowExecutionRow)
            .where(WorkflowExecutionRow.ticket_id == ticket.id)
            .order_by(WorkflowExecutionRow.created_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def ticket_record_from_row(self, ticket: TicketRow) -> TicketRecord:
        return TicketRecord(
            id=ticket.id,
            source_ticket_id=ticket.source_ticket_id,
            subject=ticket.subject,
            description=ticket.description,
            priority=ticket.priority,
            category=ticket.category,
            squad=ticket.squad,
        )

    # ------------------------------------------------------------------
    # Dashboard — list, metrics, reprocess
    # ------------------------------------------------------------------

    def list_workflows(
        self,
        status: str | None,
        limit: int,
        offset: int = 0,
        priority: str | None = None,
        squad: str | None = None,
        q: str | None = None,
    ) -> WorkflowListResponse:
        filters = [WorkflowExecutionRow.status == status] if status is not None else []
        if priority is not None:
            filters.append(TicketRow.priority == priority)
        if squad is not None:
            filters.append(WorkflowExecutionRow.squad_id == squad)
        if q:
            needle = f"%{q}%"
            filters.append(
                TicketRow.subject.ilike(needle) | TicketRow.source_ticket_id.ilike(needle)
            )

        base = (
            select(WorkflowExecutionRow, TicketRow, JiraIssueLinkRow)
            .join(TicketRow, TicketRow.id == WorkflowExecutionRow.ticket_id)
            .outerjoin(JiraIssueLinkRow, JiraIssueLinkRow.ticket_id == TicketRow.id)
            .where(*filters)
        )

        total = self._session.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()

        stmt = base.order_by(WorkflowExecutionRow.updated_at.desc()).limit(limit).offset(offset)
        rows = self._session.execute(stmt).all()

        items = [
            WorkflowListItem(
                workflow_execution_id=workflow.id,
                internal_correlation_id=workflow.internal_correlation_id,
                status=workflow.status,  # type: ignore[arg-type]
                attempt_count=workflow.attempt_count,
                squad_id=workflow.squad_id,
                routing_confidence=workflow.routing_confidence,
                routing_rule_version=workflow.routing_rule_version,
                needs_human_review=workflow.needs_human_review,
                last_error=workflow.last_error,
                jira_issue_key=link.jira_issue_key if link else None,
                link_origin=link.link_origin if link else None,  # type: ignore[arg-type]
                reprocess_eligible=workflow.status in REPROCESS_ELIGIBLE_STATUSES,
                ticket=WorkflowTicketSummary(
                    source_ticket_id=ticket.source_ticket_id,
                    subject=ticket.subject,
                    category=ticket.category,
                    priority=ticket.priority,
                ),
                updated_at=workflow.updated_at,
                resolved_at=ticket.resolved_at,
            )
            for workflow, ticket, link in rows
        ]
        return WorkflowListResponse(items=items, total=total)

    def get_workflow_detail(
        self, workflow_execution_id: uuid.UUID, jira_base_url: str | None = None
    ) -> WorkflowDetail | None:
        row = self._session.execute(
            select(WorkflowExecutionRow, TicketRow, JiraIssueLinkRow)
            .join(TicketRow, TicketRow.id == WorkflowExecutionRow.ticket_id)
            .outerjoin(JiraIssueLinkRow, JiraIssueLinkRow.ticket_id == TicketRow.id)
            .where(WorkflowExecutionRow.id == workflow_execution_id)
        ).first()
        if row is None:
            return None
        workflow, ticket, link = row

        routing = self._session.execute(
            select(RoutingDecisionRow)
            .where(RoutingDecisionRow.workflow_execution_id == workflow.id)
            .order_by(RoutingDecisionRow.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        audit_rows = self._session.execute(
            select(AuditLogRow)
            .where(AuditLogRow.workflow_execution_id == workflow.id)
            .order_by(AuditLogRow.created_at.asc())
        ).scalars().all()

        issue_key = link.jira_issue_key if link else None
        issue_url = (
            f"{jira_base_url.rstrip('/')}/browse/{issue_key}"
            if issue_key and jira_base_url
            else None
        )

        return WorkflowDetail(
            workflow_execution_id=workflow.id,
            internal_correlation_id=workflow.internal_correlation_id,
            status=workflow.status,  # type: ignore[arg-type]
            attempt_count=workflow.attempt_count,
            squad_id=workflow.squad_id,
            routing_confidence=workflow.routing_confidence,
            routing_rule_version=workflow.routing_rule_version,
            routing_reason=routing.reason if routing else None,
            needs_human_review=workflow.needs_human_review,
            last_error=workflow.last_error,
            next_attempt_at=workflow.next_attempt_at,
            jira_issue_key=issue_key,
            jira_issue_url=issue_url,
            link_origin=link.link_origin if link else None,  # type: ignore[arg-type]
            ticket=TicketDetail(
                source_ticket_id=ticket.source_ticket_id,
                subject=ticket.subject,
                description=ticket.description,
                category=ticket.category,
                priority=ticket.priority,
                requester=ticket.requester,
                source_system=ticket.source_system,
            ),
            timeline=[_timeline_event(r) for r in audit_rows],
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            reprocess_eligible=workflow.status in REPROCESS_ELIGIBLE_STATUSES,
            resolved_at=ticket.resolved_at,
        )

    def update_ticket_fields(
        self,
        workflow_execution_id: uuid.UUID,
        *,
        subject: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        category: str | None = None,
    ) -> WorkflowDetail | None:
        """Edit ticket fields while the ticket is still open (FR-052).

        Raises ``TicketAlreadyResolved`` if `resolved_at` is set (route turns
        that into 409). Returns ``None`` if the workflow doesn't exist (404).
        Only fields passed as non-None are changed.
        """
        workflow = self._session.get(WorkflowExecutionRow, workflow_execution_id)
        if workflow is None:
            return None
        ticket = self._session.get(TicketRow, workflow.ticket_id)
        if ticket.resolved_at is not None:  # type: ignore[union-attr]
            raise TicketAlreadyResolved()

        if subject is not None:
            ticket.subject = subject  # type: ignore[union-attr]
        if description is not None:
            ticket.description = description  # type: ignore[union-attr]
        if priority is not None:
            ticket.priority = priority  # type: ignore[union-attr]
        if category is not None:
            ticket.category = category  # type: ignore[union-attr]

        self._session.commit()
        return self.get_workflow_detail(workflow_execution_id)

    def mark_resolved(self, workflow_execution_id: uuid.UUID) -> datetime | None:
        """Mark the ticket as concluded (FR-053).

        Idempotent: repeating the call after it's already resolved returns
        the ORIGINAL timestamp unchanged, never a new one and never an error.
        """
        workflow = self._session.get(WorkflowExecutionRow, workflow_execution_id)
        if workflow is None:
            return None
        ticket = self._session.get(TicketRow, workflow.ticket_id)
        if ticket.resolved_at is not None:  # type: ignore[union-attr]
            return ticket.resolved_at  # type: ignore[union-attr]

        ticket.resolved_at = datetime.now(timezone.utc)  # type: ignore[union-attr]
        self._session.commit()
        return ticket.resolved_at  # type: ignore[union-attr]

    def find_by_jira_key(self, jira_issue_key: str) -> WorkflowDetail | None:
        """Lookup for the assistant's ticket-context heuristic (FR-060).

        Best-effort by design: caller catches DB errors and treats them the
        same as "not found" — never blocks the assistant's answer.
        """
        link = self._session.execute(
            select(JiraIssueLinkRow).where(JiraIssueLinkRow.jira_issue_key == jira_issue_key)
        ).scalar_one_or_none()
        if link is None:
            return None
        workflow = self._session.execute(
            select(WorkflowExecutionRow).where(WorkflowExecutionRow.ticket_id == link.ticket_id)
        ).scalar_one_or_none()
        if workflow is None:
            return None
        return self.get_workflow_detail(workflow.id)

    def get_metrics(self) -> MetricsResponse:
        counts_by_status = dict(
            self._session.execute(
                select(WorkflowExecutionRow.status, func.count()).group_by(WorkflowExecutionRow.status)
            ).all()
        )
        received = self._session.execute(select(func.count()).select_from(WorkflowExecutionRow)).scalar_one()
        return MetricsResponse(
            received=received,
            pending=counts_by_status.get("pending", 0),
            completed=counts_by_status.get("completed", 0),
            retry_scheduled=counts_by_status.get("retry_scheduled", 0),
            failed=counts_by_status.get("failed", 0),
            needs_human_review=counts_by_status.get("needs_human_review", 0),
            # ponytail: not derivable from current schema without a dedicated
            # counter/table (duplicate ingests are rejected before any row is
            # written). Add a counter column if this becomes a real need.
            duplicates_avoided=None,
        )

    def reprocess_workflow(self, workflow_id: uuid.UUID) -> ReprocessOutcome:
        """Reschedule a failed/needs_human_review workflow for reprocessing.

        Idempotent: if the ticket already has a Jira link, no new outbox
        event is created and the existing link is returned instead.
        """
        workflow = self._session.get(WorkflowExecutionRow, workflow_id)
        if workflow is None:
            return ReprocessOutcome(found=False, conflict=False, status=None, jira_issue_key=None, reason=None)

        existing_link = self._session.execute(
            select(JiraIssueLinkRow).where(JiraIssueLinkRow.ticket_id == workflow.ticket_id)
        ).scalar_one_or_none()
        if existing_link is not None:
            return ReprocessOutcome(
                found=True,
                conflict=True,
                status=workflow.status,
                jira_issue_key=existing_link.jira_issue_key,
                reason="already_linked",
            )

        if workflow.status not in ("failed", "needs_human_review"):
            return ReprocessOutcome(
                found=True, conflict=True, status=workflow.status, jira_issue_key=None, reason="not_eligible"
            )

        workflow.status = "pending"
        workflow.updated_at = datetime.now(timezone.utc)
        self._session.add(
            OutboxEventRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                event_type="ticket.process",
                payload_json="{}",
                claimed=False,
            )
        )
        self._session.add(
            AuditLogRow(
                id=uuid.uuid4(),
                workflow_execution_id=workflow.id,
                internal_correlation_id=workflow.internal_correlation_id,
                event_type="workflow.reprocess_requested",
                details_json="{}",
            )
        )
        self._session.commit()
        return ReprocessOutcome(found=True, conflict=False, status="pending", jira_issue_key=None, reason=None)


@dataclass(frozen=True)
class ReprocessOutcome:
    found: bool
    conflict: bool
    status: str | None
    jira_issue_key: str | None
    reason: str | None
