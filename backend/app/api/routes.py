"""API routes — HTTP boundary only.  No business rules here."""
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
from app.services.analytics import indicators as analytics
from app.services.analytics.excel_ingestion import ingest_dataframe
from app.services.analytics.upload_detection import MAX_UPLOAD_BYTES, detect_file_type
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

    # ------------------------------------------------------------------
    # Historical base — the "before" side of the comparison
    # ------------------------------------------------------------------

    def get_engine():
        return session_factory.kw["bind"]

    # Every file is held in memory while it is parsed. The per-file ceiling
    # bounds each one; this bounds how many can pile up in one request.
    MAX_FILES_PER_REQUEST = 10

    def _detect_all(files: list[UploadFile]) -> list[dict]:
        if len(files) > MAX_FILES_PER_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"no máximo {MAX_FILES_PER_REQUEST} arquivos por requisição",
            )
        results = []
        for upload in files:
            # Read one byte past the ceiling and no further: an oversized file
            # is rejected without ever holding all of it in memory.
            raw = upload.file.read(MAX_UPLOAD_BYTES + 1)
            results.append(detect_file_type(upload.filename or "", raw))
        return results

    @router.post("/analytics/upload/detect")
    def upload_detect(files: list[UploadFile] = File(...)):
        """Classify each file and count the rows a commit would write. Persists nothing."""
        return {
            "files": [
                {"filename": r["filename"], "kind": r["kind"], "row_count": r["row_count"]}
                for r in _detect_all(files)
            ]
        }

    @router.post("/analytics/upload/commit")
    def upload_commit(files: list[UploadFile] = File(...), engine=Depends(get_engine)):
        """Persist the same files. Always merges, never replaces.

        Each file is its own transaction, so one bad file does not take the
        others down with it.
        """
        inserted = updated = 0
        skipped: list[str] = []
        for result in _detect_all(files):
            if result["kind"] in ("unknown", "unreadable", "too_large") or result["dataframe"] is None:
                skipped.append(result["filename"])
                continue
            file_inserted, file_updated = ingest_dataframe(engine, result["kind"], result["dataframe"])
            inserted += file_inserted
            updated += file_updated
        return {"inserted": inserted, "updated": updated, "skipped_files": skipped}

    @router.get("/analytics/data-status")
    def data_status(engine=Depends(get_engine)):
        return analytics.data_status(engine)

    # ------------------------------------------------------------------
    # Indicators and the comparison
    # ------------------------------------------------------------------

    @router.get("/analytics/filter-options")
    def filter_options(
        filters: analytics.CommonFilters = Depends(),
        engine=Depends(get_engine),
    ):
        return analytics.filter_options(engine, filters)

    @router.get("/analytics/throughput")
    def throughput(
        filters: analytics.CommonFilters = Depends(),
        periodicidade: str = Query(default="mes"),
        engine=Depends(get_engine),
    ):
        return analytics.throughput(engine, filters, periodicidade)

    @router.get("/analytics/distribuicao-trabalho")
    def distribuicao_trabalho(
        filters: analytics.CommonFilters = Depends(),
        engine=Depends(get_engine),
    ):
        return analytics.distribuicao_trabalho(engine, filters)

    @router.get("/analytics/lead-time")
    def lead_time(
        filters: analytics.CommonFilters = Depends(),
        periodicidade: str = Query(default="mes"),
        engine=Depends(get_engine),
    ):
        return analytics.lead_time(engine, filters, periodicidade)

    @router.get("/analytics/link-coverage")
    def link_coverage(
        session: Session = Depends(get_session),
        engine=Depends(get_engine),
    ):
        """Best-effort coverage against deterministic coverage. The headline number."""
        return analytics.link_coverage(engine, session)

    return router
