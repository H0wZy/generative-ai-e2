"""API routes — HTTP boundary only.  No business rules here."""
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.domain.models import (
    IngestResponse,
    MetricsResponse,
    ReprocessResponse,
    TicketIngestRequest,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowStatus,
)
from app.integrations.jira import FakeJiraClient, JiraClient
from app.repositories.workflows import WorkflowRepository
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

    @router.get("/workflows", response_model=WorkflowListResponse)
    def list_workflows(
        status_filter: WorkflowStatus | None = Query(default=None, alias="status"),
        limit: int = Query(default=50, ge=1, le=200),
        session: Session = Depends(get_session),
    ) -> WorkflowListResponse:
        return WorkflowRepository(session).list_workflows(status=status_filter, limit=limit)

    @router.get("/metrics", response_model=MetricsResponse)
    def get_metrics(session: Session = Depends(get_session)) -> MetricsResponse:
        return WorkflowRepository(session).get_metrics()

    @router.post("/workflows/{workflow_execution_id}/reprocess", response_model=ReprocessResponse)
    def reprocess_workflow(
        workflow_execution_id: UUID,
        session: Session = Depends(get_session),
    ) -> ReprocessResponse | JSONResponse:
        outcome = WorkflowRepository(session).reprocess_workflow(workflow_execution_id)
        if not outcome.found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workflow not found")

        response = ReprocessResponse(
            workflow_execution_id=workflow_execution_id,
            status=outcome.status,  # type: ignore[arg-type]
            jira_issue_key=outcome.jira_issue_key,
            reprocessed=not outcome.conflict,
            reason=outcome.reason,  # type: ignore[arg-type]
        )
        if outcome.conflict:
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=response.model_dump(mode="json"))
        return response

    return router
