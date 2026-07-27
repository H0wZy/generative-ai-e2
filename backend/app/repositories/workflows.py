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
    TicketIngestRequest,
    TicketRecord,
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
        )

    # ------------------------------------------------------------------
    # Dashboard — list, metrics, reprocess
    # ------------------------------------------------------------------

    def list_workflows(self, status: str | None, limit: int) -> WorkflowListResponse:
        filters = [WorkflowExecutionRow.status == status] if status is not None else []

        total = self._session.execute(
            select(func.count()).select_from(WorkflowExecutionRow).where(*filters)
        ).scalar_one()

        stmt = (
            select(WorkflowExecutionRow, TicketRow, JiraIssueLinkRow)
            .join(TicketRow, TicketRow.id == WorkflowExecutionRow.ticket_id)
            .outerjoin(JiraIssueLinkRow, JiraIssueLinkRow.ticket_id == TicketRow.id)
            .where(*filters)
            .order_by(WorkflowExecutionRow.updated_at.desc())
            .limit(limit)
        )
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
                ticket=WorkflowTicketSummary(
                    source_ticket_id=ticket.source_ticket_id,
                    subject=ticket.subject,
                    category=ticket.category,
                    priority=ticket.priority,
                ),
                updated_at=workflow.updated_at,
            )
            for workflow, ticket, link in rows
        ]
        return WorkflowListResponse(items=items, total=total)

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
