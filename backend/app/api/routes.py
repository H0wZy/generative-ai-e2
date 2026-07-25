"""API routes — HTTP boundary only.  No business rules here."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.domain.models import IngestResponse, TicketIngestRequest, WorkflowResponse
from app.integrations.jira import FakeJiraClient, JiraClient
from app.services.ingestion import IngestionService
from app.services.processing import ProcessingService


def create_router(settings: Settings, session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["tickets"])

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_jira_client():
        if settings.jira_is_configured:
            return JiraClient(settings)
        return FakeJiraClient()

    @router.post(
        "/tickets/ingest",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=IngestResponse,
    )
    def ingest_ticket(
        payload: TicketIngestRequest,
        session: Session = Depends(get_session),
    ) -> IngestResponse:
        return IngestionService(session).ingest(payload)

    @router.post(
        "/workflows/process-next",
        status_code=status.HTTP_200_OK,
    )
    def process_next(
        session: Session = Depends(get_session),
        jira_client=Depends(get_jira_client),
    ):
        result = ProcessingService(session, jira_client, settings).process_next()
        if result is None:
            return {"status": "queue_empty"}
        return {
            "workflow_execution_id": str(result.workflow_execution_id),
            "status": result.status,
            "attempt_count": result.attempt_count,
            "jira_issue_key": result.jira_issue_key,
        }

    return router
