"""pytest configuration and shared fixtures.

Uses a real PostgreSQL database (the Docker Compose service) with an isolated
test database.  Tables are truncated between test functions for isolation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import create_router
from app.api.routes_agile import create_agile_router
from app.api.routes_assistant import create_assistant_router
from app.core.config import Settings
from app.core.database import make_engine
from app.integrations.jira import FakeJiraClient
from app.integrations.jira_agile import FakeJiraAgileClient
from app.integrations.openrouter import FakeAssistantClient
from app.integrations.rag_search import FakeRagSearchClient
from app.repositories.schema import Base
from app.services.analytics.tables import ANALYTICS_SCHEMA, analytics_metadata


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
    with eng.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {ANALYTICS_SCHEMA}"))
    Base.metadata.create_all(eng)
    analytics_metadata.create_all(eng)
    yield eng
    analytics_metadata.drop_all(eng)
    Base.metadata.drop_all(eng)
    eng.dispose()


# ---------------------------------------------------------------------------
# Truncate all tables between tests for isolation
# ---------------------------------------------------------------------------

# Tables in dependency order so FK constraints don't break TRUNCATE CASCADE
_TABLES = [
    "analytics.chamados_abertos",
    "analytics.chamados_fechados",
    "analytics.jira_cards",
    "sync_state",
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
        jira_project_key="SQD",
    )


@pytest.fixture()
def fake_jira() -> FakeJiraClient:
    return FakeJiraClient()


@pytest.fixture()
def fake_agile() -> FakeJiraAgileClient:
    return FakeJiraAgileClient()


@pytest.fixture()
def fake_rag() -> FakeRagSearchClient:
    return FakeRagSearchClient()


@pytest.fixture()
def fake_assistant() -> FakeAssistantClient:
    return FakeAssistantClient()


# ---------------------------------------------------------------------------
# HTTP test client
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(
    test_settings: Settings,
    session_factory: sessionmaker[Session],
    fake_jira: FakeJiraClient,
    fake_agile: FakeJiraAgileClient,
) -> TestClient:
    """TestClient on the production router, with the Jira client faked.

    Nada de rota redeclarada aqui: a suíte exercita exatamente o que envia.
    """
    app = FastAPI()

    @app.get("/health", tags=["ops"])
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    router = create_router(test_settings, session_factory)
    app.include_router(router)
    app.dependency_overrides[router.get_jira_client] = lambda: fake_jira

    agile = create_agile_router(test_settings)
    app.include_router(agile)
    app.dependency_overrides[agile.get_client] = lambda: fake_agile

    return TestClient(app)


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def synthetic_ticket(
    event_id: str = "evt-001",
    source_ticket_id: str = "FS-100",
    category: str = "incident",
    squad: str | None = "SQUAD-04",
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
        "squad": squad,
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
