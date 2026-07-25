"""ProcessingService — claims one pending outbox event and drives it to completion."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.models import ProcessResult
from app.integrations.jira import JiraClientError, JiraClientProtocol
from app.repositories.workflows import WorkflowRepository
from app.services.routing import route_ticket

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 2


def _next_attempt_at(attempt_count: int) -> datetime:
    """Exponential backoff with jitter, capped at 300 s."""
    delay = min(300, BASE_BACKOFF_SECONDS ** attempt_count) + random.uniform(0, 1)
    return datetime.now(timezone.utc) + timedelta(seconds=delay)


def _squad_project_key(squad_id: str, settings: Settings) -> str | None:
    mapping = {
        "identity": settings.jira_project_identity,
        "finance": settings.jira_project_finance,
        "platform": settings.jira_project_platform,
    }
    return mapping.get(squad_id)


class ProcessingService:
    def __init__(
        self,
        session: Session,
        jira_client: JiraClientProtocol,
        settings: Settings,
    ) -> None:
        self._session = session
        self._repo = WorkflowRepository(session)
        self._jira = jira_client
        self._settings = settings

    def process_next(self) -> ProcessResult | None:
        """Claim and process one pending outbox event.

        Returns ``None`` when the queue is empty.
        """
        claimed = self._repo.claim_pending_outbox()
        if claimed is None:
            return None

        outbox, workflow, ticket = claimed

        # ------------------------------------------------------------------
        # Deterministic routing
        # ------------------------------------------------------------------
        decision = route_ticket(ticket.category)
        self._repo.record_routing_decision(
            workflow=workflow,
            squad_id=decision.squad_id,
            rule_version=decision.rule_version,
            confidence=decision.confidence,
            reason=decision.rule_version,
            needs_human_review=decision.needs_human_review,
        )

        if decision.needs_human_review:
            self._repo.mark_needs_human_review(
                workflow=workflow,
                reason=f"no routing rule matched category: {ticket.category!r}",
            )
            self._session.commit()
            return ProcessResult(
                workflow_execution_id=workflow.id,
                status="needs_human_review",
                attempt_count=workflow.attempt_count,
                jira_issue_key=None,
            )

        # ------------------------------------------------------------------
        # Jira call
        # ------------------------------------------------------------------
        project_key = _squad_project_key(decision.squad_id or "", self._settings)
        if not project_key:
            # Treat missing project config as a terminal failure
            self._repo.mark_failed(
                workflow=workflow,
                error_category=f"no_project_key_for_squad:{decision.squad_id}",
            )
            self._session.commit()
            return ProcessResult(
                workflow_execution_id=workflow.id,
                status="failed",
                attempt_count=workflow.attempt_count,
                jira_issue_key=None,
            )

        ticket_record = self._repo.ticket_record_from_row(ticket)

        try:
            jira_key = self._jira.create_issue(
                ticket=ticket_record,
                project_key=project_key,
                internal_correlation_id=workflow.internal_correlation_id,
            )
        except JiraClientError as exc:
            if exc.retryable and workflow.attempt_count < MAX_ATTEMPTS:
                next_at = _next_attempt_at(workflow.attempt_count)
                self._repo.schedule_retry(
                    workflow=workflow,
                    next_attempt_at=next_at,
                    error_category=f"retryable:{exc.message}",
                )
                self._session.commit()
                return ProcessResult(
                    workflow_execution_id=workflow.id,
                    status="retry_scheduled",
                    attempt_count=workflow.attempt_count,
                    jira_issue_key=None,
                )
            # Non-retryable or attempts exhausted
            self._repo.mark_failed(
                workflow=workflow,
                error_category=f"terminal:{exc.message}",
            )
            self._session.commit()
            return ProcessResult(
                workflow_execution_id=workflow.id,
                status="failed",
                attempt_count=workflow.attempt_count,
                jira_issue_key=None,
            )

        # ------------------------------------------------------------------
        # Success
        # ------------------------------------------------------------------
        self._repo.complete_with_jira_link(
            workflow=workflow,
            ticket=ticket,
            jira_issue_key=jira_key,
        )
        self._session.commit()
        return ProcessResult(
            workflow_execution_id=workflow.id,
            status="completed",
            attempt_count=workflow.attempt_count,
            jira_issue_key=jira_key,
        )
