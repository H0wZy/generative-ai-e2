"""pytest configuration and shared fixtures.

Uses a real PostgreSQL database (the Docker Compose service) with an isolated
test database.  Tables are truncated between test functions for isolation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.database import make_engine
from app.domain.models import (
    IngestResponse,
    MetricsResponse,
    ReprocessResponse,
    TicketIngestRequest,
    WorkflowListResponse,
    WorkflowStatus,
)
from app.integrations.jira import FakeJiraClient
from app.main import create_app
from app.repositories.schema import Base
from app.repositories.workflows import WorkflowRepository
from app.services.ingestion import IngestionService
from app.services.processing import ProcessingService
from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from uuid import UUID


# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://genai_e2:genai_e2_dev@localhost:5432/genai_e2_test",
    )


# ---------------------------------------------------------------------------
# Engine / schema — session-scoped (create once, drop after all tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _test_database_url()


@pytest.fixture(scope="session")
def engine(test_database_url: str):
    eng = make_engine(test_database_url)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


# ---------------------------------------------------------------------------
# Truncate all tables between tests for isolation
# ---------------------------------------------------------------------------

# Tables in dependency order so FK constraints don't break TRUNCATE CASCADE
_TABLES = [
    "audit_logs",
    "jira_issue_links",
    "outbox_events",
    "routing_decisions",
    "external_references",
    "workflow_executions",
    "tickets",
]

@pytest.fixture(autouse=True)
def truncate_tables(engine):
    """Truncate all tables before each test to ensure isolation."""
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE TABLE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE"
        ))
    yield


# ---------------------------------------------------------------------------
# Session factory — function-scoped
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(engine):
    session = Session(bind=engine)
    yield session
    session.close()


@pytest.fixture()
def session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Settings and Jira fake
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        database_url=test_database_url,  # type: ignore[arg-type]
        jira_base_url=None,
        jira_project_platform="PLAT",
        jira_project_identity="IDEN",
        jira_project_finance="FIN",
    )


@pytest.fixture()
def fake_jira() -> FakeJiraClient:
    return FakeJiraClient()


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(test_settings: Settings, session_factory: sessionmaker[Session], fake_jira: FakeJiraClient) -> TestClient:
    """TestClient with FakeJiraClient and isolated test database."""
    app = create_app(test_settings)

    # Clear automatically registered routes and wire our own with test overrides
    app.router.routes.clear()

    @app.get("/health", tags=["ops"])
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    router = APIRouter(prefix="/api/v1", tags=["tickets"])

    def _get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    @router.post("/tickets/ingest", status_code=202, response_model=IngestResponse)
    def _ingest(payload: TicketIngestRequest, session: Session = Depends(_get_session)):
        return IngestionService(session).ingest(payload)

    @router.post("/workflows/process-next", status_code=200)
    def _process(session: Session = Depends(_get_session)):
        result = ProcessingService(session, fake_jira, test_settings).process_next()
        if result is None:
            return {"status": "queue_empty"}
        return {
            "workflow_execution_id": str(result.workflow_execution_id),
            "status": result.status,
            "attempt_count": result.attempt_count,
            "jira_issue_key": result.jira_issue_key,
        }

    @router.get("/workflows", response_model=WorkflowListResponse)
    def _list_workflows(
        status_filter: WorkflowStatus | None = Query(default=None, alias="status"),
        limit: int = Query(default=50, ge=1, le=200),
        session: Session = Depends(_get_session),
    ):
        return WorkflowRepository(session).list_workflows(status=status_filter, limit=limit)

    @router.get("/metrics", response_model=MetricsResponse)
    def _metrics(session: Session = Depends(_get_session)):
        return WorkflowRepository(session).get_metrics()

    @router.post("/workflows/{workflow_execution_id}/reprocess", response_model=ReprocessResponse)
    def _reprocess(workflow_execution_id: UUID, session: Session = Depends(_get_session)):
        outcome = WorkflowRepository(session).reprocess_workflow(workflow_execution_id)
        if not outcome.found:
            raise HTTPException(status_code=404, detail="workflow not found")
        response = ReprocessResponse(
            workflow_execution_id=workflow_execution_id,
            status=outcome.status,  # type: ignore[arg-type]
            jira_issue_key=outcome.jira_issue_key,
            reprocessed=not outcome.conflict,
            reason=outcome.reason,  # type: ignore[arg-type]
        )
        if outcome.conflict:
            return JSONResponse(status_code=409, content=response.model_dump(mode="json"))
        return response

    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def synthetic_ticket(
    event_id: str = "evt-001",
    source_ticket_id: str = "FS-100",
    category: str = "incident",
    external_correlation_id: str | None = "n8n-execution-001",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": "ticket.created",
        "occurred_at": "2026-07-25T12:00:00Z",
        "source_ticket_id": source_ticket_id,
        "subject": "Servico indisponivel",
        "description": "Aplicacao nao responde.",
        "priority": "high",
        "category": category,
        "requester": "user@example.test",
        "attachments": [],
        "external_correlation_id": external_correlation_id,
    }


@pytest.fixture()
def fixture_payload() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "ticket_created.json"
    return json.loads(fixture_path.read_text())


@pytest.fixture()
def synthetic_ticket_payload() -> dict:
    return synthetic_ticket()
